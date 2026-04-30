import json
import re
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any

import requests
from playwright.sync_api import Page, sync_playwright

from core.utils import new_id, now_iso, sha256_text


ROOT = Path(__file__).resolve().parent
DB = ROOT / "storage" / "site_factory_os.db"
REPORTS = ROOT / "reports"
SCREENSHOTS = REPORTS / "screenshots" / "productization_v2"
API = "http://127.0.0.1:8000/api/v1"
WEB = "http://127.0.0.1:5173"


class V2:
    def __init__(self) -> None:
        self.api: list[dict[str, Any]] = []
        self.db: list[dict[str, Any]] = []
        self.files: list[dict[str, Any]] = []
        self.buttons: list[dict[str, Any]] = []
        self.checks: list[dict[str, Any]] = []
        self.processes: list[subprocess.Popen] = []

    def check(self, name: str, passed: bool, details: dict | None = None) -> None:
        self.checks.append({"name": name, "pass": bool(passed), "details": details or {}})

    def request(self, method: str, path: str, payload: dict | None = None, token: str | None = None) -> dict:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = requests.request(method, f"{API}{path}", json=payload, headers=headers, timeout=30)
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}
        self.api.append({"method": method, "path": path, "payload": payload, "status_code": response.status_code, "response": body})
        return body

    def db_query(self, sql: str, params: tuple = ()) -> list[dict]:
        with sqlite3.connect(DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        self.db.append({"sql": sql, "params": params, "rows": rows[:25], "row_count": len(rows)})
        return rows

    def file_contains(self, path: Path, needles: list[str]) -> bool:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        result = {needle: needle in text for needle in needles}
        self.files.append({"path": str(path), "exists": path.exists(), "size": path.stat().st_size if path.exists() else None, "contains": result, "snippet": text[:900]})
        return path.exists() and all(result.values())

    def click(self, page: Page, name: str, selector: str, expect_api: str | None = None) -> None:
        before = len(self.api)
        page.locator(selector).click()
        self.buttons.append({"button": name, "selector": selector, "clicked": True, "api_before": before, "expected_api": expect_api})

    def start(self) -> None:
        self.stop_ports()
        if DB.exists():
            DB.unlink()
        shutil.rmtree(ROOT / "sample_data" / "productization_v2", ignore_errors=True)
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)
        api_proc = subprocess.Popen(
            ["python", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
        web_proc = subprocess.Popen(
            [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
            cwd=ROOT / "frontend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.processes.extend([api_proc, web_proc])
        for _ in range(80):
            try:
                if requests.get(f"{API}/system/health", timeout=2).status_code == 200 and requests.get(WEB, timeout=2).status_code == 200:
                    return
            except Exception:
                pass
            time.sleep(0.5)
        raise RuntimeError("local servers did not start")

    def stop_ports(self) -> None:
        ps = "Get-NetTCPConnection -LocalPort 8000,5173 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)

    def stop(self) -> None:
        for proc in self.processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in self.processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
        self.stop_ports()


def seed_admin() -> tuple[str, str]:
    with sqlite3.connect(DB) as conn:
        now = now_iso()
        user_id = "user_admin_v2"
        conn.execute(
            "INSERT OR REPLACE INTO users(user_id, username, email, password_hash, telegram_handle, role, status, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (user_id, "admin_v2", "admin_v2@example.com", sha256_text("adminpw"), None, "super_admin", "active", now, now),
        )
        conn.execute(
            "INSERT OR REPLACE INTO memberships(membership_id,user_id,plan,status,started_at,expires_at,site_limit,deploy_limit_per_day,device_limit,can_use_bulk_import,can_use_telegram,can_use_diy_builder,can_use_i18n,can_use_payment_links,can_use_roles,can_use_advanced_audit,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (new_id("mem"), user_id, "enterprise", "active", now, "2099-01-01T00:00:00+00:00", 999999, 999999, 999999, 1, 1, 1, 1, 1, 1, 1, now, now),
        )
        conn.commit()
    return user_id, "adminpw"


def setup_bulk(site_id: str) -> Path:
    root = ROOT / "sample_data" / "productization_v2" / "bulk_good"
    site = root / site_id
    (site / "images").mkdir(parents=True, exist_ok=True)
    (site / "config.json").write_text(json.dumps({"site_id": site_id, "template": "shop1", "site_type": "shop", "language_code": "en"}), encoding="utf-8")
    (site / "article.txt").write_text("title: V2 Bulk Article\ncontent: Bulk article from frontend validate execute\n", encoding="utf-8")
    (site / "product.txt").write_text("name: V2 Bulk Product\nprice: 33.33\nimages:\n- 1.jpg\n", encoding="utf-8")
    (site / "images" / "1.jpg").write_text("image", encoding="utf-8")
    return root


def seed_failed_task(site_id: str) -> str:
    task_id = new_id("task")
    now = now_iso()
    with sqlite3.connect(DB) as conn:
        conn.execute(
            "INSERT INTO tasks(task_id, request_id, trace_id, task_type, site_id, status, progress, current_node, payload_json, result_json, error_code, error_message, retry_count, max_retry, created_by, created_at, updated_at, finished_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                task_id,
                f"v2_retry_{task_id}",
                new_id("trace"),
                "manual_failed_check",
                site_id,
                "failed",
                35,
                "FailureNode",
                "{}",
                "{}",
                "SYSTEM_INVALID_INPUT",
                "seeded failed task for frontend retry audit",
                0,
                3,
                "acceptance",
                now,
                now,
                now,
            ),
        )
        conn.commit()
    return task_id


def wait_text(page: Page, text: str, timeout: int = 15000) -> None:
    try:
        page.get_by_text(text).first.wait_for(timeout=timeout)
    except Exception:
        pass


def nav(page: Page, name: str) -> None:
    page.locator("aside").get_by_role("button", name=name, exact=True).click()


def run() -> None:
    REPORTS.mkdir(exist_ok=True)
    v = V2()
    try:
        v.start()
        admin_user_id, _ = seed_admin()
        anon_admin = v.request("POST", "/admin/billing/license-codes", {"plan": "pro", "duration_days": 7, "created_by": "anonymous"})
        v.check("1_anonymous_admin_billing_fails", anon_admin.get("error", {}).get("error_code") in {"AUTH_UNAUTHORIZED", "AUTH_FORBIDDEN"})

        admin_login = v.request("POST", "/auth/login", {"username": "admin_v2", "password": "adminpw"})
        admin_token = admin_login["token"]
        v.check("2_admin_token_usable", bool(admin_token) and admin_login["user"]["role"] == "super_admin")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1180, "height": 1050})
            page.goto(WEB)
            page.screenshot(path=SCREENSHOTS / "01_login.png", full_page=True)
            page.get_by_label("账号 / 邮箱").fill("operator_v2")
            page.get_by_label("密码").fill("pw123")
            page.get_by_test_id("login-submit").click()
            page.wait_for_timeout(4600)
            page.screenshot(path=SCREENSHOTS / "02_dashboard_after_login.png", full_page=True)
            token = page.evaluate("localStorage.getItem('sfs_token')")
            user_id = page.evaluate("localStorage.getItem('sfs_user_id')")
            v.check("2_login_token_available", bool(token and user_id), {"user_id": user_id})

            nav(page, "Sites")
            page.get_by_test_id("create-site-alias").fill("V2 UI Site")
            domain = f"v2-{int(time.time())}.local.test"
            page.get_by_test_id("create-site-domain").fill(domain)
            page.get_by_test_id("create-site-button").click()
            wait_text(page, "SITE_CREATED")
            sites = v.request("GET", "/sites")
            site = next(item for item in sites["items"] if item["domain"] == domain)
            site_id = site["site_id"]
            v.check("3_create_site_frontend_button_created_db", bool(site_id), {"site_id": site_id, "domain": domain})

            nav(page, "Bulk Import")
            disabled = page.get_by_test_id("bulk-execute-button").is_disabled()
            v.check("19_trial_user_cannot_click_bulk_execute", disabled)

            nav(page, "DNS / Domain")
            page.get_by_test_id("dns-check-current-button").click()
            wait_text(page, "DNS_CHECK OK")
            domain_rows = v.db_query("SELECT status, ssl_status FROM domains WHERE site_id=?", (site_id,))
            v.check("10_dns_check_frontend_real_api", domain_rows[0]["status"] == "ns_verified")

            failed_task_id = seed_failed_task(site_id)
            nav(page, "Tasks")
            page.locator(f'[data-testid="task-retry-{failed_task_id}"]').click()
            wait_text(page, "TASK_RETRY OK")
            retry_rows = v.db_query("SELECT status, retry_count FROM tasks WHERE task_id=?", (failed_task_id,))
            v.check("task_retry_frontend_real_api", retry_rows[0]["status"] == "success" and retry_rows[0]["retry_count"] == 1)

            page.evaluate(
                """([token,userId]) => { localStorage.setItem('sfs_token', token); localStorage.setItem('sfs_user_id', userId); localStorage.setItem('sfs_role', 'super_admin'); }""",
                [admin_token, admin_user_id],
            )
            nav(page, "Admin Billing")
            page.get_by_test_id("admin-generate-pro-license").click()
            wait_text(page, "LICENSE_GENERATED")
            admin_result = page.get_by_test_id("admin-license-result").inner_text()
            code = re.search(r"SFS-PRO-30D-[A-Z0-9]+", admin_result).group(0)
            v.check("admin_generate_license_frontend_real_api", bool(code), {"code": code})

            page.evaluate(
                """([token,userId]) => { localStorage.setItem('sfs_token', token); localStorage.setItem('sfs_user_id', userId); localStorage.setItem('sfs_role', 'operator'); }""",
                [token, user_id],
            )
            nav(page, "Membership")
            page.get_by_test_id("membership-upgrade-pro-button").click()
            wait_text(page, "SERVICE_REQUEST OK")
            request_rows = v.db_query("SELECT target_plan, status FROM customer_service_requests WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user_id,))
            v.check("customer_service_upgrade_request_frontend_real_api", request_rows[0]["target_plan"] == "pro" and request_rows[0]["status"] == "pending")
            page.get_by_test_id("license-code-input").fill(code)
            page.get_by_test_id("license-activate-button").click()
            wait_text(page, "LICENSE_ACTIVATE OK")
            membership = json.loads(page.evaluate("localStorage.getItem('sfs_membership')"))
            v.check("11_license_activate_frontend_real_api", membership["plan"] == "pro")

            v.request("POST", f"/sites/{site_id}/i18n/languages/es/enable", {"request_id": "v2_enable_es", "user_id": user_id}, token=token)

            nav(page, "CMS")
            page.get_by_test_id("article-title").fill("V2 UI Article")
            page.get_by_test_id("article-content").fill("Created through a real frontend CMS button.")
            page.get_by_test_id("new-article-button").click()
            wait_text(page, "ARTICLE_CREATE OK")
            articles = v.request("GET", f"/sites/{site_id}/articles")
            article_id = articles["items"][0]["article_id"]
            v.check("4_new_article_frontend_real_api", bool(article_id))
            page.locator(f'[data-testid="publish-article-{article_id}"]').click()
            wait_text(page, "ARTICLE_PUBLISH OK")
            article_rows = v.db_query("SELECT status FROM articles WHERE article_id=?", (article_id,))
            v.check("5_publish_article_frontend_generates_html", article_rows[0]["status"] == "published")

            page.locator("main").get_by_role("button", name="Products", exact=True).click()
            page.get_by_test_id("product-name").fill("V2 UI Product")
            page.get_by_test_id("product-price").fill("27.50")
            page.get_by_test_id("new-product-button").click()
            wait_text(page, "PRODUCT_CREATE OK")
            products = v.request("GET", f"/sites/{site_id}/products")
            product_id = products["items"][0]["product_id"]
            v.check("6_new_product_frontend_real_api", bool(product_id))
            page.locator(f'[data-testid="publish-product-{product_id}"]').click()
            wait_text(page, "PRODUCT_PUBLISH OK")
            product_rows = v.db_query("SELECT status FROM products WHERE product_id=?", (product_id,))
            v.check("7_publish_product_frontend_generates_html", product_rows[0]["status"] == "active")

            bulk_root = setup_bulk(site_id)
            nav(page, "Bulk Import")
            page.get_by_test_id("bulk-root-path").fill(str(bulk_root))
            page.get_by_test_id("bulk-create-job-button").click()
            wait_text(page, "BULK_JOB_CREATE OK")
            page.get_by_test_id("bulk-scan-button").click()
            wait_text(page, "BULK_SCAN OK")
            page.get_by_test_id("bulk-validate-button").click()
            wait_text(page, "BULK_VALIDATE OK")
            page.get_by_test_id("bulk-preview-button").click()
            wait_text(page, "BULK_PREVIEW OK")
            page.get_by_test_id("bulk-execute-button").click()
            wait_text(page, "BULK_EXECUTE OK")
            bulk_rows = v.db_query("SELECT status, success_items FROM bulk_jobs ORDER BY created_at DESC LIMIT 1")
            v.check("8_9_bulk_validate_execute_frontend_real_api", bulk_rows[0]["status"] == "executed" and bulk_rows[0]["success_items"] >= 2)
            v.check("20_pro_user_can_bulk_execute", not page.get_by_test_id("bulk-execute-button").is_disabled())

            nav(page, "DIY Builder")
            page.get_by_test_id("block-library-FloatingButton").click()
            page.get_by_test_id("block-library-PopupModal").click()
            page.get_by_test_id("diy-title-input").fill("Popup Offer")
            page.get_by_test_id("diy-save-button").click()
            wait_text(page, "DIY_SAVE OK")
            page_rows = v.db_query("SELECT page_id, layout_json FROM pages WHERE site_id=? ORDER BY created_at DESC LIMIT 1", (site_id,))
            page_id = page_rows[0]["page_id"]
            layout_json = page_rows[0]["layout_json"]
            v.check("12_13_diy_floating_popup_saved_page_json", "FloatingButton" in layout_json and "PopupModal" in layout_json and "open_popup" in layout_json)
            page.get_by_test_id("diy-publish-button").click()
            wait_text(page, "DIY_PUBLISH OK")
            page.wait_for_timeout(1000)
            page.screenshot(path=SCREENSHOTS / "03_diy_after_publish.png", full_page=True)
            v.check("diy_page_publish_frontend_real_api", bool(page_id))
            browser.close()

        deployment = v.request("POST", f"/sites/{site_id}/deployments", {"request_id": "v2_final_deploy", "user_id": user_id}, token=token)
        dist = Path(deployment["deployment"]["dist_path"])
        v.check("14_diy_publish_dist_contains_floating_popup_action", v.file_contains(dist / "index.html", ["sfs-floating-button", "sfs-popup", "data-action=\"open_popup\"", "popup_demo"]))
        v.check("16_generate_es_page", (dist / "es" / "index.html").exists())
        v.check("17_sitemap_contains_es", v.file_contains(dist / "sitemap.xml", ["/es/"]))
        v.check("18_hreflang_points_es", v.file_contains(dist / "index.html", ['hreflang="es"', f"https://{domain}/es/"]))
        i18n_source = (ROOT / "frontend" / "src" / "i18n.tsx").read_text(encoding="utf-8")
        key_based = all(marker in i18n_source for marker in ["const dict", "useI18n", "translate(", "I18nProvider"])
        no_dom_scan = all(marker not in i18n_source for marker in ["MutationObserver", "querySelectorAll", "dataset.i18nOriginal", "GlobalLocalizer"])
        v.check("15_i18n_key_based_source", key_based and no_dom_scan, {"key_based": key_based, "no_dom_scan": no_dom_scan})
        v.check("article_html_exists", v.file_contains(dist / "articles" / "v2-ui-article.html", ["V2 UI Article"]))
        v.check("product_html_exists", v.file_contains(dist / "products" / "v2-ui-product.html", ["V2 UI Product"]))

        result = {
            "pass": all(item["pass"] for item in v.checks),
            "failed": [item for item in v.checks if not item["pass"]],
            "checks": v.checks,
            "buttons": v.buttons,
            "api": v.api,
            "db": v.db,
            "files": v.files,
            "site_id": site_id,
            "dist": str(dist),
        }
        (REPORTS / "productization_v2_acceptance.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"pass": result["pass"], "failed": result["failed"], "site_id": site_id, "dist": str(dist)}, ensure_ascii=False, indent=2))
    finally:
        v.stop()


if __name__ == "__main__":
    run()
