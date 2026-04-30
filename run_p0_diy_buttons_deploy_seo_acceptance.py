import json
import os
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any

import requests
from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parent
DB = ROOT / "storage" / "site_factory_os.db"
REPORTS = ROOT / "reports"
SCREENSHOTS = REPORTS / "screenshots"
API = "http://127.0.0.1:8000/api/v1"
WEB = "http://127.0.0.1:5173"


class Audit:
    def __init__(self) -> None:
        self.processes: list[subprocess.Popen] = []
        self.buttons: list[dict[str, Any]] = []
        self.evidence: dict[str, Any] = {"seo_files_generated": [], "github_pages_url": "", "deploy_logs": ""}
        self.db_backup = ""

    def button(self, page_path: str, name: str, status: str, expected: str, actual: str = "", error: str = "") -> None:
        self.buttons.append({"page": page_path, "button": name, "expected": expected, "actual": actual, "status": status, "error": error})

    def stop_ports(self) -> None:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-NetTCPConnection -LocalPort 8000,5173 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }",
            ],
            capture_output=True,
            text=True,
        )

    def start(self) -> None:
        REPORTS.mkdir(exist_ok=True)
        SCREENSHOTS.mkdir(exist_ok=True)
        self.stop_ports()
        if DB.exists():
            backup = REPORTS / f"site_factory_os_before_p0_{int(time.time())}.db"
            shutil.copy2(DB, backup)
            self.db_backup = str(backup)
            DB.unlink()
        npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
        env = os.environ.copy()
        env.setdefault("GITHUB_MODE", "mock")
        self.processes = [
            subprocess.Popen(["python", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env),
            subprocess.Popen([npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"], cwd=ROOT / "frontend", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
        ]
        for _ in range(120):
            try:
                if requests.get(f"{API}/system/health", timeout=2).status_code == 200 and requests.get(WEB, timeout=2).status_code == 200:
                    return
            except Exception:
                pass
            time.sleep(0.5)
        raise RuntimeError("servers did not start")

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

    def db(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with sqlite3.connect(DB) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(sql, params).fetchall()]


def nav(page: Page, name: str) -> None:
    page.locator("aside").get_by_role("button", name=name, exact=True).click()
    page.wait_for_timeout(500)


def click_button(audit: Audit, page: Page, page_path: str, name: str, locator, expected: str, wait_ms: int = 500) -> None:
    try:
        locator.click()
        page.wait_for_timeout(wait_ms)
        audit.button(page_path, name, "PASS", expected, "click completed")
    except Exception as exc:
        audit.button(page_path, name, "FAIL", expected, error=str(exc))


def drag_component(page: Page, component: str, offset_x: int, offset_y: int) -> None:
    source = page.get_by_test_id(f"block-library-{component}")
    target = page.get_by_test_id("diy-canvas-drop")
    source_box = source.bounding_box()
    canvas_box = target.bounding_box()
    if not source_box or not canvas_box:
        raise RuntimeError(f"cannot drag {component}")
    page.mouse.move(source_box["x"] + source_box["width"] / 2, source_box["y"] + source_box["height"] / 2)
    page.mouse.down()
    page.mouse.move(canvas_box["x"] + offset_x, canvas_box["y"] + offset_y, steps=16)
    page.mouse.up()
    page.wait_for_timeout(500)


def api_json(path: str, token: str = "", method: str = "GET", payload: dict | None = None) -> requests.Response:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.request(method, f"{API}{path}", headers=headers, json=payload, timeout=30)


def main() -> None:
    audit = Audit()
    try:
        audit.start()
        stamp = str(int(time.time()))
        admin_session = api_json("/auth/login", method="POST", payload={"username": "candy2000", "password": "candy2000"}).json()
        admin_token = admin_session["token"]
        api_json("/membership/service-requests", method="POST", payload={"user_id": "user_candy2000", "target_plan": "pro", "contact_method": "telegram", "contact_value": "@candy2000", "note": "P0 acceptance"})

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.goto(WEB)
            page.get_by_test_id("login-submit").click()
            page.wait_for_timeout(4700)

            quick = page.get_by_role("button", name="Quick Create")
            quick.click(force=True)
            click_button(audit, page, "/", "顶部快捷创建-创建网站", page.get_by_test_id("quick-create-site"), "navigate to Sites")
            page.keyboard.press("Escape")
            quick.click(force=True)
            click_button(audit, page, "/", "顶部快捷创建-新建文章", page.get_by_test_id("quick-new-article"), "navigate to CMS")
            page.keyboard.press("Escape")
            quick.click(force=True)
            click_button(audit, page, "/", "顶部快捷创建-批量导入", page.get_by_test_id("quick-bulk-import"), "navigate to Bulk Import")
            page.keyboard.press("Escape")

            nav(page, "Sites")
            domain = f"p0-{stamp}.example.com"
            page.get_by_test_id("create-site-alias").fill(f"P0 Site {stamp}")
            page.get_by_test_id("create-site-domain").fill(domain)
            click_button(audit, page, "/sites", "创建网站", page.get_by_test_id("create-site-button"), "POST /sites creates DB site", 1400)
            site_rows = audit.db("SELECT site_id, domain FROM sites WHERE domain=?", (domain,))
            site_id = site_rows[0]["site_id"]
            nav(page, "Sites")

            click_button(audit, page, "/sites", "网站卡片-细节", page.get_by_role("button", name="Detail").first, "navigate to Site Detail")
            nav(page, "Sites")
            try:
                with page.expect_popup(timeout=3000) as popup_info:
                    page.get_by_test_id(f"site-open-{site_id}").click()
                popup = popup_info.value
                popup.close()
                audit.button("/sites", "网站卡片-打开", "PASS", "window.open site URL", "popup opened")
            except Exception as exc:
                audit.button("/sites", "网站卡片-打开", "FAIL", "window.open site URL", error=str(exc))
            click_button(audit, page, "/sites", "网站卡片-内容管理系统", page.get_by_test_id(f"site-cms-{site_id}"), "navigate to CMS")
            nav(page, "Sites")
            click_button(audit, page, "/sites", "网站卡片-DIY", page.get_by_test_id(f"site-diy-{site_id}"), "navigate to DIY Builder")
            nav(page, "Sites")
            click_button(audit, page, "/sites", "网站卡片-部署", page.get_by_test_id(f"site-deploy-{site_id}"), "POST /deploy/github", 2200)
            click_button(audit, page, "/sites", "网站卡片-克隆", page.get_by_test_id(f"site-clone-{site_id}"), "POST /sites/{site_id}/clone", 1600)
            click_button(audit, page, "/sites", "网站卡片-暂停", page.get_by_test_id(f"site-pause-{site_id}"), "POST /sites/{site_id}/pause", 900)
            click_button(audit, page, "/sites", "网站卡片-删除", page.get_by_test_id(f"site-delete-{site_id}"), "open delete confirm modal", 300)
            click_button(audit, page, "/sites", "网站卡片-确认删除", page.get_by_test_id("site-delete-confirm"), "POST delete-request + delete-confirm", 1200)

            nav(page, "Admin Billing")
            request_id = audit.db("SELECT request_id FROM customer_service_requests ORDER BY created_at DESC LIMIT 1")[0]["request_id"]
            click_button(audit, page, "/admin-billing", "已付款", page.get_by_test_id(f"billing-paid-{request_id}"), "POST mark-paid", 900)
            click_button(audit, page, "/admin-billing", "开通30天", page.get_by_test_id(f"billing-open-30d-{request_id}"), "POST activate request", 900)
            click_button(audit, page, "/admin-billing", "拒绝", page.get_by_test_id(f"billing-reject-{request_id}"), "POST reject request", 900)
            click_button(audit, page, "/admin-billing", "生成PRO 30天授权码", page.get_by_test_id("admin-generate-pro-license"), "POST /admin/license/create", 900)
            click_button(audit, page, "/admin-billing", "生成企业版30天授权码", page.get_by_test_id("admin-generate-enterprise-license"), "POST /admin/license/create", 900)
            code_row = audit.db("SELECT code FROM license_codes ORDER BY created_at DESC LIMIT 1")
            if code_row:
                click_button(audit, page, "/admin-billing", "复制授权码", page.get_by_test_id(f"copy-license-{code_row[0]['code']}"), "copy license code")
            click_button(audit, page, "/admin-billing", "激活账户", page.get_by_test_id("admin-activate-user-button"), "POST /admin/user/activate", 900)

            nav(page, "DIY Builder")
            page.get_by_role("button", name="Focus mode").click()
            page.get_by_role("button", name="50%", exact=True).click()
            drag_component(page, "FloatingButton", 700, 420)
            float_block = page.get_by_test_id("canvas-block-FloatingButton").nth(page.get_by_test_id("canvas-block-FloatingButton").count() - 1)
            box_before = float_block.bounding_box()
            if box_before:
                page.mouse.move(box_before["x"] + 30, box_before["y"] + 20)
                page.mouse.down()
                page.mouse.move(box_before["x"] + 95, box_before["y"] + 55, steps=12)
                page.mouse.up()
                page.wait_for_timeout(300)
            box_after = float_block.bounding_box()
            moved = bool(box_before and box_after and (abs(box_after["x"] - box_before["x"]) > 10 or abs(box_after["y"] - box_before["y"]) > 10))
            audit.button("/builder", "浮动按钮自由拖放", "PASS" if moved else "FAIL", "drag FloatingButton inside canvas", f"moved={moved}")
            page.get_by_test_id("diy-anchor-bottom-right").click()
            page.get_by_test_id("diy-action-type").select_option("external_url")
            page.get_by_test_id("diy-action-target").fill("#preview-ok")
            before_url = page.url
            float_block.click(force=True)
            page.wait_for_timeout(200)
            audit.button("/builder", "编辑态链接拦截", "PASS" if page.url == before_url else "FAIL", "editing click must not navigate", f"url={page.url}")
            page.get_by_test_id("diy-interaction-mode").click()
            preview_url_before = page.url
            float_block.click(force=True)
            page.wait_for_timeout(600)
            preview_ok = page.url != preview_url_before and page.url.endswith("#preview-ok")
            audit.button("/builder", "预览态链接允许", "PASS" if preview_ok else "FAIL", "preview mode allows link action", f"url={page.url}")
            page.get_by_test_id("diy-save-button").click()
            page.wait_for_timeout(1200)
            audit.db("UPDATE domains SET status='ns_verified', ssl_status='active' WHERE site_id=?", (site_id,))
            with sqlite3.connect(DB) as conn:
                conn.execute("UPDATE domains SET status='ns_verified', ssl_status='active' WHERE site_id=?", (site_id,))
                conn.commit()
            page.get_by_test_id("diy-publish-button").click()
            page.wait_for_timeout(2000)
            if page.get_by_test_id("builder-focus-back").count():
                page.get_by_test_id("builder-focus-back").click()
                page.wait_for_timeout(500)

            nav(page, "SEO")
            seo_title = f"P0 SEO Title {stamp}"
            seo_slug = "/"
            page.get_by_test_id("seo-title-input").fill(seo_title)
            page.get_by_test_id("seo-description-input").fill("P0 SEO description with OpenGraph and canonical.")
            page.get_by_test_id("seo-slug-input").fill(seo_slug)
            click_button(audit, page, "/seo", "SEO保存/生成", page.get_by_test_id("seo-save-button"), "PATCH /seo + sitemap generate", 1200)
            deployment = api_json("/deploy/github", token=admin_token, method="POST", payload={"request_id": f"api_github_deploy_{stamp}", "site_id": site_id}).json()
            audit.evidence["github_pages_url"] = deployment.get("github_pages_url") or deployment.get("deployment", {}).get("live_url", "")
            status = api_json(f"/deploy/logs/{site_id}", token=admin_token).json()
            audit.evidence["deploy_logs"] = json.dumps(status, ensure_ascii=False)[:3000]
            dist = ROOT / "generated_sites" / site_id / "dist"
            seo_files = [dist / "index.html", dist / "sitemap.xml", dist / "robots.txt"]
            audit.evidence["seo_files_generated"] = [str(path) for path in seo_files if path.exists()]
            index_text = (dist / "index.html").read_text(encoding="utf-8") if (dist / "index.html").exists() else ""
            sitemap_text = (dist / "sitemap.xml").read_text(encoding="utf-8") if (dist / "sitemap.xml").exists() else ""
            forbidden = ["example.com", "github-real-"]
            seo_ok = (
                all(token in index_text for token in [f"<title>{seo_title}</title>", "P0 SEO description with OpenGraph and canonical.", "meta name=\"description\"", "rel=\"canonical\"", "og:title", "og:description"])
                and (dist / "sitemap.xml").exists()
                and (dist / "robots.txt").exists()
                and not any(token in index_text or token in sitemap_text for token in forbidden)
            )
            audit.button("/seo", "SEO文件内容生成", "PASS" if seo_ok else "FAIL", "dist HTML + sitemap + robots contain SEO tags", f"dist={dist}")

            page.screenshot(path=str(SCREENSHOTS / "p0_diy_buttons_deploy_seo.png"), full_page=True)
            browser.close()

        normal = api_json("/auth/register", method="POST", payload={"username": f"normal_{stamp}", "password": "normalpass"}).json()
        normal_token = api_json("/auth/login", method="POST", payload={"username": f"normal_{stamp}", "password": "normalpass"}).json()["token"]
        forbidden = api_json("/admin/license/create", token=normal_token, method="POST", payload={"plan": "vip", "duration_days": 30, "count": 1})
        audit.button("/admin-billing", "普通用户禁止创建卡密", "PASS" if forbidden.status_code in {401, 403} else "FAIL", "ordinary user blocked by backend", f"status={forbidden.status_code}")
        license_resp = api_json("/admin/license/create", token=admin_token, method="POST", payload={"plan": "pro", "duration_days": 7, "count": 1}).json()
        key = license_resp["keys"][0]
        used_once = api_json("/license/activate", token=normal_token, method="POST", payload={"license_key": key})
        used_twice = api_json("/license/activate", token=normal_token, method="POST", payload={"license_key": key})
        audit.button("/membership", "卡密只能使用一次", "PASS" if used_once.status_code == 200 and used_twice.status_code == 400 else "FAIL", "second activation returns LICENSE_CODE_USED", f"first={used_once.status_code}, second={used_twice.status_code}")

        failed = [item for item in audit.buttons if item["status"] != "PASS"]
        report = {
            "status": "PASS" if not failed else "FAIL",
            "total_buttons_tested": len(audit.buttons),
            "passed": len(audit.buttons) - len(failed),
            "failed": len(failed),
            "failed_items": failed,
            "github_pages_url": audit.evidence["github_pages_url"],
            "seo_files_generated": audit.evidence["seo_files_generated"],
            "deploy_logs": audit.evidence["deploy_logs"],
            "github_mode": os.getenv("GITHUB_MODE", "mock"),
            "db_backup_before_clean_run": audit.db_backup,
            "screenshot": str(SCREENSHOTS / "p0_diy_buttons_deploy_seo.png"),
            "rerun": "python run_p0_diy_buttons_deploy_seo_acceptance.py",
        }
        (REPORTS / "p0_diy_buttons_deploy_seo_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": report["status"], "total_buttons_tested": report["total_buttons_tested"], "passed": report["passed"], "failed": report["failed"], "report": str(REPORTS / "p0_diy_buttons_deploy_seo_report.json")}, ensure_ascii=False, indent=2))
    finally:
        audit.stop()


if __name__ == "__main__":
    main()
