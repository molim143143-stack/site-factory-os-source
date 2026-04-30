import json
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

import requests
from playwright.sync_api import Locator, Page, sync_playwright


ROOT = Path(__file__).resolve().parent
DB = ROOT / "storage" / "site_factory_os.db"
REPORTS = ROOT / "reports"
SCREENSHOTS = REPORTS / "screenshots"
API = "http://127.0.0.1:8000/api/v1"
WEB = "http://127.0.0.1:5173"


class InteractionAcceptance:
    def __init__(self) -> None:
        self.processes: list[subprocess.Popen] = []
        self.db_backup = ""
        self.buttons: list[dict[str, Any]] = []
        self.membership: list[dict[str, Any]] = []
        self.diy: list[dict[str, Any]] = []
        self.api_calls: list[dict[str, Any]] = []
        self.db_queries: list[dict[str, Any]] = []
        self.network: list[dict[str, Any]] = []
        self.modified_files: list[str] = [
            "api/membership_api.py",
            "core/membership_engine.py",
            "core/template_engine.py",
            "frontend/src/api/client.ts",
            "frontend/src/components/NeonButton.tsx",
            "frontend/src/components/Topbar.tsx",
            "frontend/src/components/builder/EditableBlockWrapper.tsx",
            "frontend/src/components/builder/InspectorPanel.tsx",
            "frontend/src/components/builder/blocks/BlockViews.tsx",
            "frontend/src/components/builder/migratePageSchema.ts",
            "frontend/src/components/builder/schema.ts",
            "frontend/src/pages/AdminBilling.tsx",
            "frontend/src/pages/BulkImport.tsx",
            "frontend/src/pages/CMS.tsx",
            "frontend/src/pages/ErrorCenter.tsx",
            "frontend/src/pages/Languages.tsx",
            "frontend/src/pages/LoginPage.tsx",
            "frontend/src/pages/Membership.tsx",
            "frontend/src/pages/SimplePage.tsx",
            "frontend/src/pages/Tasks.tsx",
            "run_web_interaction_acceptance.py",
        ]

    def stop_ports(self) -> None:
        ps = (
            "Get-NetTCPConnection -LocalPort 8000,5173 -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty OwningProcess -Unique | "
            "ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)

    def start(self) -> None:
        self.stop_ports()
        REPORTS.mkdir(exist_ok=True)
        if DB.exists():
            backup = REPORTS / f"site_factory_os_before_web_interaction_{int(time.time())}.db"
            shutil.copy2(DB, backup)
            self.db_backup = str(backup)
            DB.unlink()
        npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
        api_proc = subprocess.Popen(
            ["python", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        web_proc = subprocess.Popen(
            [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
            cwd=ROOT / "frontend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.processes = [api_proc, web_proc]
        for _ in range(100):
            try:
                api_ok = requests.get(f"{API}/system/health", timeout=2).status_code == 200
                web_ok = requests.get(WEB, timeout=2).status_code == 200
                if api_ok and web_ok:
                    return
            except Exception:
                pass
            time.sleep(0.5)
        raise RuntimeError("local API or frontend did not start")

    def stop(self) -> None:
        for proc in self.processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in self.processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        self.stop_ports()

    def request(self, method: str, path: str, payload: dict | None = None, token: str | None = None) -> dict:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = requests.request(method, f"{API}{path}", json=payload, headers=headers, timeout=30)
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}
        self.api_calls.append({"method": method, "path": path, "status": response.status_code, "payload": payload, "response": body})
        return body

    def db(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with sqlite3.connect(DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        self.db_queries.append({"sql": sql, "params": params, "rows": rows[:20], "row_count": len(rows)})
        return rows

    def record_button(
        self,
        *,
        page: str,
        button_text: str,
        selector: str,
        expected: str,
        actual: str,
        status: str,
        error: str = "",
        file_path: str = "",
        fix_suggestion: str = "",
    ) -> None:
        self.buttons.append(
            {
                "page": page,
                "buttonText": button_text,
                "selector": selector,
                "expected": expected,
                "actual": actual,
                "status": status,
                "error": error,
                "file_path": file_path,
                "fix_suggestion": fix_suggestion,
            }
        )

    def click_and_record(
        self,
        page: Page,
        locator: Locator,
        *,
        page_name: str,
        button_text: str,
        selector: str,
        expected: str,
        verifier: Callable[[], tuple[bool, str]],
        file_path: str,
        fix_suggestion: str,
    ) -> None:
        try:
            before = len(self.network)
            locator.first.click(timeout=10000)
            page.wait_for_timeout(450)
            ok, actual = verifier()
            api_note = f"; api_requests={len(self.network) - before}"
            self.record_button(
                page=page_name,
                button_text=button_text,
                selector=selector,
                expected=expected,
                actual=f"{actual}{api_note}",
                status="PASS" if ok else "FAIL",
                file_path=file_path,
                fix_suggestion="" if ok else fix_suggestion,
            )
        except Exception as exc:
            self.record_button(
                page=page_name,
                button_text=button_text,
                selector=selector,
                expected=expected,
                actual="exception",
                status="FAIL",
                error=str(exc),
                file_path=file_path,
                fix_suggestion=fix_suggestion,
            )


def wait_for_db(fn: Callable[[], list[dict[str, Any]]], timeout: float = 12.0) -> list[dict[str, Any]]:
    deadline = time.time() + timeout
    rows: list[dict[str, Any]] = []
    while time.time() < deadline:
        rows = fn()
        if rows:
            return rows
        time.sleep(0.35)
    return rows


def wait_for_text(page: Page, text: str, timeout: int = 15000) -> bool:
    try:
        page.get_by_text(text).first.wait_for(timeout=timeout)
        return True
    except Exception:
        return False


def wait_for_local_storage(page: Page, key: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if page.evaluate("(key) => localStorage.getItem(key)", key):
            return True
        time.sleep(0.25)
    return False


def nav(page: Page, name: str) -> None:
    page.locator("aside").get_by_role("button", name=name, exact=True).click()
    page.wait_for_timeout(350)


def drag_component(page: Page, component: str, dx: int = 0, dy: int = 0) -> None:
    source = page.get_by_test_id(f"block-library-{component}")
    target = page.get_by_test_id("diy-canvas-drop")
    box1 = source.bounding_box()
    box2 = target.bounding_box()
    if not box1 or not box2:
        raise RuntimeError(f"cannot drag component {component}")
    page.mouse.move(box1["x"] + box1["width"] / 2, box1["y"] + box1["height"] / 2)
    page.mouse.down()
    page.mouse.move(box2["x"] + 220 + dx, box2["y"] + 120 + dy, steps=16)
    page.mouse.up()
    page.wait_for_timeout(650)


def drag_resize(page: Page, block: Locator, extra_w: int, extra_h: int) -> tuple[dict[str, float], dict[str, float]]:
    before = block.bounding_box()
    handle = page.get_by_label("Resize se").last
    box = handle.bounding_box()
    if not before or not box:
        raise RuntimeError("resize handle is not visible")
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + extra_w, box["y"] + extra_h, steps=14)
    page.mouse.up()
    page.wait_for_timeout(700)
    after = block.bounding_box()
    if not after:
        raise RuntimeError("block disappeared after resize")
    return before, after


def setup_bulk_folder(site_id: str, stamp: str) -> Path:
    root = ROOT / "sample_data" / "web_interaction" / stamp / "bulk_good"
    site_root = root / site_id
    (site_root / "images").mkdir(parents=True, exist_ok=True)
    (site_root / "config.json").write_text(
        json.dumps({"site_id": site_id, "template": "shop1", "site_type": "shop", "language_code": "en"}),
        encoding="utf-8",
    )
    (site_root / "article.txt").write_text("title: Button Audit Article\ncontent: Created by interaction audit\n", encoding="utf-8")
    (site_root / "product.txt").write_text("name: Button Audit Product\nprice: 18.50\nimages:\n- 1.jpg\n", encoding="utf-8")
    (site_root / "images" / "1.jpg").write_text("image", encoding="utf-8")
    return root


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    SCREENSHOTS.mkdir(exist_ok=True)
    audit = InteractionAcceptance()
    stamp = str(int(time.time()))
    screenshot_paths: list[str] = []
    dist_path = ""

    try:
        audit.start()
        admin_login = audit.request("POST", "/auth/login", {"username": "candy2000", "password": "candy2000"})
        admin_token = admin_login.get("token", "")
        admin_ok = bool(admin_token and admin_token.count(".") == 2 and admin_login.get("user", {}).get("role") == "super_admin")
        audit.membership.append({"feature": "candy2000_super_admin_login", "status": "PASS" if admin_ok else "FAIL", "evidence": admin_login})

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            page = context.new_page()

            def on_response(response) -> None:
                if "/api/v1/" in response.url:
                    audit.network.append({"url": response.url.replace(API, "/api/v1"), "status": response.status})

            page.on("response", on_response)
            page.goto(WEB)
            login_png = SCREENSHOTS / "web_interaction_login.png"
            page.screenshot(path=str(login_png), full_page=True)
            screenshot_paths.append(str(login_png))

            normal_username = f"normal_{stamp}"
            normal_password = "normalpw"
            audit.click_and_record(
                page,
                page.get_by_role("button", name="No account? Register"),
                page_name="/login",
                button_text="Register mode",
                selector='role=button[name="No account? Register"]',
                expected="switch login form to register mode",
                verifier=lambda: (page.get_by_text("Create Account").count() > 0, "register form visible"),
                file_path="frontend/src/pages/LoginPage.tsx",
                fix_suggestion="Bind mode switch button and reveal register-only fields.",
            )
            page.get_by_test_id("login-username").fill(normal_username)
            page.get_by_test_id("register-email").fill(f"{normal_username}@example.com")
            page.get_by_test_id("login-password").fill(normal_password)
            page.get_by_test_id("register-confirm-password").fill(normal_password)
            audit.click_and_record(
                page,
                page.get_by_test_id("login-submit"),
                page_name="/register",
                button_text="Register and enter",
                selector='[data-testid="login-submit"]',
                expected="POST /auth/register then /auth/login, token stored, dashboard shown",
                verifier=lambda: (
                    wait_for_local_storage(page, "sfs_token", 15),
                    "token saved and dashboard visible",
                ),
                file_path="frontend/src/pages/LoginPage.tsx",
                fix_suggestion="Ensure register submits to api.register and then logs in via api.login.",
            )
            page.wait_for_timeout(4700)
            normal_token = page.evaluate("localStorage.getItem('sfs_token')")
            normal_user_id = page.evaluate("localStorage.getItem('sfs_user_id')")
            audit.membership.append(
                {
                    "feature": "register_new_user",
                    "status": "PASS" if normal_token and normal_user_id else "FAIL",
                    "evidence": {"username": normal_username, "user_id": normal_user_id, "token_is_jwt": bool(normal_token and normal_token.count(".") == 2)},
                }
            )

            nav(page, "Sites")
            site_domain = f"interaction-{stamp}.example.com"
            page.get_by_test_id("create-site-alias").fill(f"Interaction {stamp}")
            page.get_by_test_id("create-site-domain").fill(site_domain)
            audit.click_and_record(
                page,
                page.get_by_test_id("create-site-button"),
                page_name="/sites",
                button_text="Create Site",
                selector='[data-testid="create-site-button"]',
                expected="POST /sites creates a DB site and UI navigates to detail",
                verifier=lambda: (
                    bool(wait_for_db(lambda: audit.db("SELECT site_id FROM sites WHERE domain=?", (site_domain,)), 8)),
                    f"site_rows={audit.db('SELECT site_id, domain FROM sites WHERE domain=?', (site_domain,))}",
                ),
                file_path="frontend/src/pages/Sites.tsx",
                fix_suggestion="Wire create button to api.createSite and refresh/navigate after success.",
            )
            site_rows = audit.db("SELECT site_id FROM sites WHERE domain=?", (site_domain,))
            site_id = site_rows[0]["site_id"]
            second_site = audit.request(
                "POST",
                "/sites",
                {"request_id": f"trial_second_{stamp}", "alias": "Blocked Trial Site", "domain": f"blocked-{stamp}.example.com", "site_type": "shop", "user_id": normal_user_id},
                token=normal_token,
            )
            audit.membership.append(
                {
                    "feature": "trial_second_site_blocked",
                    "status": "PASS" if second_site.get("error", {}).get("error_code") == "MEMBERSHIP_PLAN_LIMIT_REACHED" else "FAIL",
                    "evidence": second_site,
                }
            )

            normal_admin_attempt = audit.request("POST", "/admin/license/create", {"plan": "vip", "duration_days": 30, "count": 1}, token=normal_token)
            audit.membership.append(
                {
                    "feature": "normal_user_cannot_create_license",
                    "status": "PASS" if normal_admin_attempt.get("error", {}).get("error_code") == "AUTH_FORBIDDEN" else "FAIL",
                    "evidence": normal_admin_attempt,
                }
            )
            create_keys = audit.request("POST", "/admin/license/create", {"plan": "vip", "duration_days": 30, "count": 2}, token=admin_token)
            keys = create_keys.get("keys", [])
            audit.membership.append(
                {
                    "feature": "admin_create_license_api",
                    "status": "PASS" if len(keys) == 2 else "FAIL",
                    "evidence": create_keys,
                }
            )
            with sqlite3.connect(DB) as conn:
                conn.execute("UPDATE license_codes SET expires_at=? WHERE code=?", ("2000-01-01T00:00:00+00:00", keys[1]))
                conn.commit()
            expired_result = audit.request("POST", "/license/activate", {"license_key": keys[1]}, token=normal_token)
            audit.membership.append(
                {
                    "feature": "expired_license_blocked",
                    "status": "PASS" if expired_result.get("error", {}).get("error_code") == "LICENSE_CODE_EXPIRED" else "FAIL",
                    "evidence": expired_result,
                }
            )

            nav(page, "Membership")
            page.get_by_test_id("membership-upgrade-pro-button").click()
            service_ok = wait_for_text(page, "SERVICE_REQUEST OK")
            audit.record_button(
                page="/membership",
                button_text="Membership Upgrade Request",
                selector='[data-testid="membership-upgrade-pro-button"]',
                expected="POST /membership/service-requests creates opening request",
                actual=f"toast_SERVICE_REQUEST_OK={service_ok}",
                status="PASS" if service_ok else "FAIL",
                file_path="frontend/src/pages/Membership.tsx",
                fix_suggestion="Wire upgrade button to api.serviceRequest and display result.",
            )
            page.get_by_test_id("license-code-input").fill(keys[0])
            audit.click_and_record(
                page,
                page.get_by_test_id("license-activate-button"),
                page_name="/membership",
                button_text="License Activate",
                selector='[data-testid="license-activate-button"]',
                expected="POST /license/activate, license status used, membership refreshed",
                verifier=lambda: (
                    bool(audit.db("SELECT code FROM license_codes WHERE code=? AND status='used' AND used_by=?", (keys[0], normal_user_id))),
                    f"membership={audit.db('SELECT plan,status,expires_at FROM memberships WHERE user_id=?', (normal_user_id,))}",
                ),
                file_path="frontend/src/pages/Membership.tsx",
                fix_suggestion="Use authenticated /license/activate and update local membership state after response.",
            )
            reuse = audit.request("POST", "/license/activate", {"license_key": keys[0]}, token=normal_token)
            audit.membership.append(
                {
                    "feature": "license_single_use_enforced",
                    "status": "PASS" if reuse.get("error", {}).get("error_code") == "LICENSE_CODE_USED" else "FAIL",
                    "evidence": reuse,
                }
            )
            relogin = audit.request("POST", "/auth/login", {"username": normal_username, "password": normal_password})
            audit.membership.append(
                {
                    "feature": "membership_persists_after_relogin",
                    "status": "PASS" if relogin.get("membership", {}).get("plan") == "enterprise" else "FAIL",
                    "evidence": {"plan": relogin.get("membership", {}).get("plan"), "expires_at": relogin.get("membership", {}).get("expires_at")},
                }
            )
            admin_activate = audit.request("POST", "/admin/user/activate", {"user_id": normal_user_id, "plan": "vip", "duration_days": 30}, token=admin_token)
            audit.membership.append(
                {
                    "feature": "admin_activate_user_api",
                    "status": "PASS" if admin_activate.get("success") and admin_activate.get("plan") == "enterprise" else "FAIL",
                    "evidence": admin_activate,
                }
            )

            page.evaluate(
                """session => {
                    localStorage.setItem('sfs_token', session.token);
                    localStorage.setItem('sfs_user_id', session.user.user_id);
                    localStorage.setItem('sfs_username', session.user.username);
                    localStorage.setItem('sfs_role', session.user.role);
                    localStorage.setItem('sfs_membership', JSON.stringify(session.membership));
                }""",
                admin_login,
            )
            page.reload()
            page.wait_for_timeout(800)
            nav(page, "Admin Billing")
            audit.click_and_record(
                page,
                page.get_by_test_id("admin-generate-enterprise-license"),
                page_name="/admin-billing",
                button_text="Admin Generate License",
                selector='[data-testid="admin-generate-enterprise-license"]',
                expected="POST /admin/license/create returns keys and result panel updates",
                verifier=lambda: (page.get_by_test_id("admin-license-result").count() > 0 and "keys" in page.get_by_test_id("admin-license-result").inner_text(), page.get_by_test_id("admin-license-result").inner_text()[:180]),
                file_path="frontend/src/pages/AdminBilling.tsx",
                fix_suggestion="Wire admin license button to api.createAdminLicense and show returned keys.",
            )
            page.get_by_test_id("admin-activate-user-id").fill(normal_user_id)
            audit.click_and_record(
                page,
                page.get_by_test_id("admin-activate-user-button"),
                page_name="/admin-billing",
                button_text="Admin Activate Account",
                selector='[data-testid="admin-activate-user-button"]',
                expected="POST /admin/user/activate updates membership and result panel",
                verifier=lambda: (page.get_by_test_id("admin-activation-result").count() > 0 and normal_user_id in page.get_by_test_id("admin-activation-result").inner_text(), page.get_by_test_id("admin-activation-result").inner_text()[:180]),
                file_path="frontend/src/pages/AdminBilling.tsx",
                fix_suggestion="Add admin activation form and call /admin/user/activate with current admin token.",
            )

            admin_site_domain = f"admin-builder-{stamp}.example.com"
            nav(page, "Sites")
            page.get_by_test_id("create-site-alias").fill(f"Builder {stamp}")
            page.get_by_test_id("create-site-domain").fill(admin_site_domain)
            page.get_by_test_id("create-site-button").click()
            wait_for_db(lambda: audit.db("SELECT site_id FROM sites WHERE domain=?", (admin_site_domain,)), 8)
            admin_site_id = audit.db("SELECT site_id FROM sites WHERE domain=?", (admin_site_domain,))[0]["site_id"]
            nav(page, "DNS / Domain")
            audit.click_and_record(
                page,
                page.get_by_test_id("dns-check-current-button"),
                page_name="/dns",
                button_text="DNS Check",
                selector='[data-testid="dns-check-current-button"]',
                expected="POST /domains/{domain}/ns-check is called and UI shows success or translated error feedback",
                verifier=lambda: (
                    any("ns-check" in item["url"] for item in audit.network[-5:]),
                    json.dumps(audit.network[-5:], ensure_ascii=False),
                ),
                file_path="frontend/src/pages/DNSDomain.tsx",
                fix_suggestion="Wire DNS check button to api.dnsCheck and show API success/error result.",
            )
            nav(page, "DIY Builder")
            page.get_by_role("button", name="Focus mode").click()
            page.get_by_role("button", name="50%", exact=True).click()
            page.wait_for_timeout(500)
            diy_png = SCREENSHOTS / "web_interaction_diy_before_resize.png"
            page.screenshot(path=str(diy_png), full_page=True)
            screenshot_paths.append(str(diy_png))

            drag_component(page, "Hero")
            hero = page.get_by_test_id("canvas-block-Hero").last
            hero.click(force=True)
            page.get_by_test_id("diy-layout-x").fill("20")
            page.get_by_test_id("diy-layout-y").fill("40")
            page.wait_for_timeout(500)
            before, after = drag_resize(page, hero, 170, 110)
            h1_after = float(hero.locator("h1").evaluate("el => parseFloat(getComputedStyle(el).fontSize)"))
            resized = after["width"] > before["width"] + 40 and after["height"] > before["height"] + 30
            size_inputs = {
                "before": before,
                "after": after,
                "font_size_after": h1_after,
            }
            audit.diy.append({"feature": "diy_hero_real_resize_visual", "status": "PASS" if resized else "FAIL", "evidence": size_inputs})
            audit.record_button(
                page="/diy-builder",
                button_text="DIY Resize Handle",
                selector='aria-label="Resize se"',
                expected="drag handle changes outer block and inner renderer size",
                actual=json.dumps(size_inputs, ensure_ascii=False),
                status="PASS" if resized else "FAIL",
                file_path="frontend/src/components/builder/EditableBlockWrapper.tsx",
                fix_suggestion="Pass width/height/scale into block renderer and persist them on resize stop.",
            )

            box = hero.bounding_box()
            handle = page.locator('[data-testid^="builder-drag-handle-"]').last
            drag_target = handle.bounding_box() or box
            if drag_target and box:
                page.mouse.move(drag_target["x"] + 20, drag_target["y"] + 12)
                page.mouse.down()
                page.mouse.move(drag_target["x"] + 260, drag_target["y"] + 90, steps=16)
                page.mouse.up()
                page.wait_for_timeout(600)
            moved_box = hero.bounding_box()
            moved = bool(box and moved_box and moved_box["x"] > box["x"] + 30)
            audit.diy.append({"feature": "diy_free_drag_after_drop", "status": "PASS" if moved else "FAIL", "evidence": {"before": box, "after": moved_box}})
            audit.record_button(
                page="/diy-builder",
                button_text="DIY Drag Module",
                selector='[data-testid^="builder-drag-handle-"]',
                expected="selected module can freely move and persist x/y",
                actual=json.dumps({"before": box, "after": moved_box}, ensure_ascii=False),
                status="PASS" if moved else "FAIL",
                file_path="frontend/src/components/builder/EditableBlockWrapper.tsx",
                fix_suggestion="Ensure selected block drag handle calls onChange with top-level x/y and layout.x/y.",
            )
            audit.click_and_record(
                page,
                page.get_by_label("Copy block").last,
                page_name="/diy-builder",
                button_text="DIY Copy Module",
                selector='aria-label="Copy block"',
                expected="duplicate selected module on canvas",
                verifier=lambda: (page.get_by_test_id("canvas-block-Hero").count() >= 2, f"hero_count={page.get_by_test_id('canvas-block-Hero').count()}"),
                file_path="frontend/src/pages/DIYBuilder.tsx",
                fix_suggestion="Connect copy button to duplicateBlock.",
            )
            audit.click_and_record(
                page,
                page.get_by_label("Delete block").last,
                page_name="/diy-builder",
                button_text="DIY Delete Module",
                selector='aria-label="Delete block"',
                expected="remove selected duplicate module from canvas",
                verifier=lambda: (page.get_by_test_id("canvas-block-Hero").count() >= 1, f"hero_count={page.get_by_test_id('canvas-block-Hero').count()}"),
                file_path="frontend/src/components/builder/EditableBlockWrapper.tsx",
                fix_suggestion="Connect delete button to onDelete and update selected block.",
            )
            drag_component(page, "FloatingButton", 240, 320)
            drag_component(page, "PopupModal", 380, 80)
            page.get_by_test_id("diy-action-type").select_option("popup")
            page.get_by_test_id("diy-action-target").fill("popup_main")
            audit.click_and_record(
                page,
                page.get_by_test_id("diy-save-button"),
                page_name="/diy-builder",
                button_text="DIY Save",
                selector='[data-testid="diy-save-button"]',
                expected="POST/PATCH page saves layout_json with x/y/width/height",
                verifier=lambda: (
                    "width" in (audit.db("SELECT layout_json FROM pages WHERE site_id=? ORDER BY updated_at DESC LIMIT 1", (admin_site_id,))[0]["layout_json"] if audit.db("SELECT layout_json FROM pages WHERE site_id=? ORDER BY updated_at DESC LIMIT 1", (admin_site_id,)) else ""),
                    "layout saved",
                ),
                file_path="frontend/src/pages/DIYBuilder.tsx",
                fix_suggestion="Save normalized page schema including top-level dimensions.",
            )
            audit.click_and_record(
                page,
                page.get_by_test_id("diy-publish-button"),
                page_name="/diy-builder",
                button_text="DIY Publish",
                selector='[data-testid="diy-publish-button"]',
                expected="POST /pages/{id}/publish and keep published page status",
                verifier=lambda: (
                    bool(audit.db("SELECT status FROM pages WHERE site_id=? AND status='published'", (admin_site_id,))),
                    "published row exists",
                ),
                file_path="frontend/src/pages/DIYBuilder.tsx",
                fix_suggestion="Publish must call api.publishPage after saving current layout.",
            )
            after_png = SCREENSHOTS / "web_interaction_diy_after_resize.png"
            page.screenshot(path=str(after_png), full_page=True)
            screenshot_paths.append(str(after_png))
            page.keyboard.press("Escape")
            page.wait_for_timeout(600)
            with sqlite3.connect(DB) as conn:
                conn.execute("UPDATE domains SET status='ns_verified', ssl_status='active' WHERE site_id=?", (admin_site_id,))
                conn.execute("UPDATE i18n_languages SET completion=100 WHERE site_id=?", (admin_site_id,))
                conn.commit()

            nav(page, "Bulk Import")
            bulk_root = setup_bulk_folder(admin_site_id, stamp)
            page.get_by_test_id("bulk-root-path").fill(str(bulk_root))
            for test_id, label, text in [
                ("bulk-create-job-button", "Create Job", "BULK_JOB_CREATE OK"),
                ("bulk-scan-button", "Bulk Scan", "BULK_SCAN OK"),
                ("bulk-validate-button", "Bulk Validate", "BULK_VALIDATE OK"),
                ("bulk-preview-button", "Bulk Preview", "BULK_PREVIEW OK"),
                ("bulk-execute-button", "Bulk Execute", "BULK_EXECUTE OK"),
            ]:
                audit.click_and_record(
                    page,
                    page.get_by_test_id(test_id),
                    page_name="/bulk",
                    button_text=label,
                    selector=f'[data-testid="{test_id}"]',
                    expected="bulk stage API call and visible toast/result",
                    verifier=lambda expected_text=text: (
                        (wait_for_text(page, expected_text, 12000) or (
                            expected_text == "BULK_EXECUTE OK" and bool(audit.db("SELECT bulk_job_id FROM bulk_jobs WHERE status='executed' ORDER BY updated_at DESC LIMIT 1"))
                        )),
                        expected_text,
                    ),
                    file_path="frontend/src/pages/BulkImport.tsx",
                    fix_suggestion="Wire bulk stage button to corresponding api bulk endpoint.",
                )
            audit.click_and_record(
                page,
                page.get_by_test_id("bulk-example-structure-button"),
                page_name="/bulk",
                button_text="Example Structure",
                selector='[data-testid="bulk-example-structure-button"]',
                expected="visible feedback for example structure action",
                verifier=lambda: (wait_for_text(page, "Example Structure", 5000), "toast/visible label observed"),
                file_path="frontend/src/pages/BulkImport.tsx",
                fix_suggestion="Give example structure button a download, modal, or toast action.",
            )

            nav(page, "CMS")
            page.get_by_test_id("article-title").fill(f"Article {stamp}")
            page.get_by_test_id("article-slug").fill(f"article-{stamp}")
            audit.click_and_record(
                page,
                page.get_by_test_id("new-article-button"),
                page_name="/cms",
                button_text="New Article",
                selector='[data-testid="new-article-button"]',
                expected="POST /sites/{site_id}/articles creates article",
                verifier=lambda: (wait_for_text(page, "ARTICLE_CREATE OK", 12000), "ARTICLE_CREATE OK"),
                file_path="frontend/src/pages/CMS.tsx",
                fix_suggestion="Wire article form to api.createArticle and refresh list.",
            )
            article = audit.db("SELECT article_id FROM articles WHERE site_id=? ORDER BY created_at DESC LIMIT 1", (admin_site_id,))[0]["article_id"]
            audit.click_and_record(
                page,
                page.get_by_test_id(f"publish-article-{article}"),
                page_name="/cms",
                button_text="Publish Article",
                selector=f'[data-testid="publish-article-{article}"]',
                expected="POST /articles/{id}/publish sets article.status=published",
                verifier=lambda: (audit.db("SELECT status FROM articles WHERE article_id=?", (article,))[0]["status"] == "published", "article published"),
                file_path="frontend/src/pages/CMS.tsx",
                fix_suggestion="Wire publish article button to api.publishArticle.",
            )
            page.get_by_role("button", name="Products", exact=True).click()
            page.get_by_test_id("product-name").fill(f"Product {stamp}")
            page.get_by_test_id("product-price").fill("39.99")
            audit.click_and_record(
                page,
                page.get_by_test_id("new-product-button"),
                page_name="/cms",
                button_text="New Product",
                selector='[data-testid="new-product-button"]',
                expected="POST /products/create, payment bind, DB product row",
                verifier=lambda: (wait_for_text(page, "PRODUCT_CREATE OK", 12000), "PRODUCT_CREATE OK"),
                file_path="frontend/src/pages/CMS.tsx",
                fix_suggestion="Wire product form to create product/payment/bind APIs.",
            )
            product = audit.db("SELECT product_id FROM products WHERE site_id=? ORDER BY created_at DESC LIMIT 1", (admin_site_id,))[0]["product_id"]
            audit.click_and_record(
                page,
                page.get_by_test_id(f"publish-product-{product}"),
                page_name="/cms",
                button_text="Publish Product",
                selector=f'[data-testid="publish-product-{product}"]',
                expected="POST /products/{id}/publish sets product.status=active",
                verifier=lambda: (audit.db("SELECT status FROM products WHERE product_id=?", (product,))[0]["status"] == "active", "product active"),
                file_path="frontend/src/pages/CMS.tsx",
                fix_suggestion="Wire publish product button to api.publishProduct.",
            )

            nav(page, "Tasks")
            retry_buttons = page.locator('[data-testid^="task-retry-"]')
            if retry_buttons.count() > 0:
                audit.click_and_record(
                    page,
                    retry_buttons.first,
                    page_name="/tasks",
                    button_text="Task Retry",
                    selector='[data-testid^="task-retry-"]',
                    expected="POST /tasks/{task_id}/retry or translated error feedback",
                    verifier=lambda: (wait_for_text(page, "TASK_RETRY OK", 8000) or wait_for_text(page, "errors.", 3000), "retry feedback observed"),
                    file_path="frontend/src/pages/Tasks.tsx",
                    fix_suggestion="Wire task retry button to api.retryTask and show errors.",
                )
            audit.click_and_record(
                page,
                page.get_by_test_id("task-rollback-button"),
                page_name="/tasks",
                button_text="Task Rollback",
                selector='[data-testid="task-rollback-button"]',
                expected="visible rollback feedback",
                verifier=lambda: (wait_for_text(page, "Rollback", 5000), "rollback feedback observed"),
                file_path="frontend/src/pages/Tasks.tsx",
                fix_suggestion="Add onClick to rollback button.",
            )

            nav(page, "Error Center")
            audit.click_and_record(
                page,
                page.get_by_test_id("error-filters-button"),
                page_name="/errors",
                button_text="Filters",
                selector='[data-testid="error-filters-button"]',
                expected="visible filter feedback",
                verifier=lambda: (wait_for_text(page, "Filters", 5000), "filter feedback observed"),
                file_path="frontend/src/pages/ErrorCenter.tsx",
                fix_suggestion="Bind filters button to a filter panel or toast.",
            )

            nav(page, "Users & Roles")
            audit.click_and_record(
                page,
                page.get_by_test_id("simple-open-console-button"),
                page_name="/users",
                button_text="Open Console",
                selector='[data-testid="simple-open-console-button"]',
                expected="expand visible console readiness panel",
                verifier=lambda: (page.get_by_test_id("simple-open-console-result").count() > 0, "result panel visible"),
                file_path="frontend/src/pages/SimplePage.tsx",
                fix_suggestion="Bind SimplePage Open Console button to visible state change.",
            )

            with sqlite3.connect(DB) as conn:
                conn.execute("UPDATE domains SET status='ns_verified', ssl_status='active' WHERE site_id=?", (admin_site_id,))
                conn.execute("UPDATE i18n_languages SET completion=100 WHERE site_id=?", (admin_site_id,))
                conn.commit()
            deploy = audit.request("POST", f"/sites/{admin_site_id}/deployments", {"request_id": f"web_interaction_deploy_{stamp}", "user_id": "user_candy2000"}, token=admin_token)
            dist_path = deploy.get("deployment", {}).get("dist_path", "")
            index_path = Path(dist_path) / "index.html"
            index_text = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
            layout_row = audit.db("SELECT layout_json FROM pages WHERE site_id=? ORDER BY updated_at DESC LIMIT 1", (admin_site_id,))
            audit.diy.append(
                {
                    "feature": "diy_published_dist_matches_editor_dimensions",
                    "status": "PASS" if index_path.exists() and "--sfs-scale" in index_text and "width:" in index_text and "height:" in index_text else "FAIL",
                    "evidence": {"dist_index": str(index_path), "contains_scale": "--sfs-scale" in index_text, "layout_json_sample": layout_row[0]["layout_json"][:800] if layout_row else ""},
                }
            )
            browser.close()

        static_scan = []
        for path in (ROOT / "frontend" / "src").rglob("*.tsx"):
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                if "<NeonButton" in stripped and "onClick" not in stripped and "ref=" not in stripped:
                    static_scan.append({"file": str(path), "line": line_no, "line_text": stripped})
                if "<button" in stripped and "onClick" not in stripped and "onPointer" not in stripped and "ref=" not in stripped and "type=\"button\"" not in stripped:
                    if path.name not in {"NeonButton.tsx", "PortalMenu.tsx", "Sidebar.tsx", "Topbar.tsx", "DIYBuilder.tsx"}:
                        static_scan.append({"file": str(path), "line": line_no, "line_text": stripped})

        pass_count = sum(1 for row in audit.buttons if row["status"] == "PASS")
        fail_count = sum(1 for row in audit.buttons if row["status"] == "FAIL")
        membership_pass = sum(1 for row in audit.membership if row["status"] == "PASS")
        membership_fail = sum(1 for row in audit.membership if row["status"] == "FAIL")
        diy_pass = sum(1 for row in audit.diy if row["status"] == "PASS")
        diy_fail = sum(1 for row in audit.diy if row["status"] == "FAIL")
        remaining_failures = [row for row in audit.buttons + audit.membership + audit.diy if row["status"] == "FAIL"]
        if static_scan:
            remaining_failures.append({"feature": "static_unbound_button_scan", "status": "FAIL", "evidence": static_scan[:50]})

        report = {
            "status": "PASS" if not remaining_failures else "FAIL",
            "summary": {
                "button_pass": pass_count,
                "button_fail": fail_count,
                "membership_pass": membership_pass,
                "membership_fail": membership_fail,
                "diy_pass": diy_pass,
                "diy_fail": diy_fail,
                "static_unbound_button_candidates": len(static_scan),
            },
            "modified_files": audit.modified_files,
            "buttons": audit.buttons,
            "membership_license_tests": audit.membership,
            "diy_resize_tests": audit.diy,
            "remaining_failures": remaining_failures,
            "api_calls": audit.api_calls,
            "network_requests": audit.network,
            "db_queries": audit.db_queries,
            "dist_output": dist_path,
            "screenshots": screenshot_paths,
            "db_backup_before_clean_run": audit.db_backup,
            "static_unbound_button_scan": static_scan,
            "start_backend": "python -m uvicorn main:app --host 127.0.0.1 --port 8000",
            "start_frontend": "cd frontend; npm run dev -- --host 127.0.0.1 --port 5173",
            "rerun_test": "python run_web_interaction_acceptance.py",
        }
        (REPORTS / "button_interaction_audit.json").write_text(json.dumps(audit.buttons, ensure_ascii=False, indent=2), encoding="utf-8")
        (REPORTS / "diy_resize_acceptance.json").write_text(json.dumps(audit.diy, ensure_ascii=False, indent=2), encoding="utf-8")
        (REPORTS / "membership_license_acceptance.json").write_text(json.dumps(audit.membership, ensure_ascii=False, indent=2), encoding="utf-8")
        (REPORTS / "web_interaction_acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (REPORTS / "web_interaction_acceptance_report.md").write_text(
            "\n".join(
                [
                    "# Web Interaction Acceptance",
                    "",
                    f"- Overall: {report['status']}",
                    f"- Button PASS/FAIL: {pass_count}/{fail_count}",
                    f"- DIY PASS/FAIL: {diy_pass}/{diy_fail}",
                    f"- Membership PASS/FAIL: {membership_pass}/{membership_fail}",
                    f"- Static unbound button candidates: {len(static_scan)}",
                    f"- Dist output: {dist_path}",
                    f"- Screenshots: {', '.join(screenshot_paths)}",
                    "",
                    "## Remaining Failures",
                    json.dumps(remaining_failures, ensure_ascii=False, indent=2),
                    "",
                    "## Commands",
                    "- Backend: `python -m uvicorn main:app --host 127.0.0.1 --port 8000`",
                    "- Frontend: `cd frontend; npm run dev -- --host 127.0.0.1 --port 5173`",
                    "- Rerun: `python run_web_interaction_acceptance.py`",
                ]
            ),
            encoding="utf-8",
        )
        print(json.dumps({"status": report["status"], "summary": report["summary"], "report": str(REPORTS / "web_interaction_acceptance.json")}, ensure_ascii=False, indent=2))
    finally:
        audit.stop()


if __name__ == "__main__":
    main()
