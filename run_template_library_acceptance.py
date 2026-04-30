import json
import os
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any

import requests
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent
DB = ROOT / "storage" / "site_factory_os.db"
REPORTS = ROOT / "reports"
SCREENSHOTS = REPORTS / "screenshots"
API = "http://127.0.0.1:8000/api/v1"
WEB = "http://127.0.0.1:5173"


class Audit:
    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []
        self.processes: list[subprocess.Popen] = []
        self.db_backup = ""

    def record(self, feature: str, status: str, evidence: dict[str, Any]) -> None:
        self.results.append({"feature": feature, "status": status, "evidence": evidence})

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
            backup = REPORTS / f"site_factory_os_before_template_library_{int(time.time())}.db"
            shutil.copy2(DB, backup)
            self.db_backup = str(backup)
            DB.unlink()
        npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
        env = os.environ.copy()
        env["GITHUB_MODE"] = "mock"
        env["CLOUDFLARE_MODE"] = "mock"
        self.processes = [
            subprocess.Popen(["python", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env),
            subprocess.Popen([npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"], cwd=ROOT / "frontend", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env),
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


def nav(page, name: str) -> None:
    page.locator("aside").get_by_role("button", name=name, exact=True).click()
    page.wait_for_timeout(500)


def main() -> None:
    audit = Audit()
    try:
        audit.start()
        stamp = str(int(time.time()))
        api_templates = requests.get(f"{API}/builder/templates", timeout=10).json()["items"]
        available_count = len(api_templates)
        downloaded_available = [item["id"] for item in api_templates if item.get("source") == "github" and item.get("status") == "available" and item.get("can_use_in_builder")]
        audit.record("api_returns_available_normalized_templates", "PASS" if available_count >= 3 and downloaded_available else "FAIL", {"available_count": available_count, "downloaded_available": downloaded_available})
        signatures = {}
        for item in api_templates:
            blocks = item.get("page_schema", {}).get("blocks", [])
            signatures[item["id"]] = {
                "types": [block.get("type") for block in blocks],
                "first_background": (blocks[0].get("style") or {}).get("background") if blocks else "",
                "hero_background": next(((block.get("style") or {}).get("background") for block in blocks if block.get("type") == "Hero"), ""),
                "content_type": next((block.get("type") for block in blocks if block.get("type") in {"ProductCard", "ImageText", "ArticleCard", "ArticleList"}), ""),
            }
        distinct_values = {json.dumps(value, sort_keys=True) for value in signatures.values()}
        audit.record("templates_are_distinct_full_page_skins", "PASS" if len(distinct_values) >= 3 else "FAIL", {"signatures": signatures})

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.goto(WEB)
            page.get_by_test_id("login-submit").click()
            page.wait_for_timeout(4700)
            nav(page, "Sites")
            domain = f"template-{stamp}.example.com"
            page.get_by_test_id("create-site-alias").fill(f"Template Site {stamp}")
            page.get_by_test_id("create-site-domain").fill(domain)
            page.get_by_test_id("create-site-button").click()
            page.wait_for_timeout(1500)
            nav(page, "DIY Builder")
            page.get_by_role("button", name="Focus mode").click()
            page.get_by_test_id("choose-template-button").click()
            modal_cards = page.locator('[data-testid^="apply-template-"]').count()
            audit.record("template_modal_lists_templates", "PASS" if modal_cards >= 3 else "FAIL", {"modal_apply_buttons": modal_cards})
            page.get_by_test_id("apply-template-static_landing_startbootstrap_landing_page").click()
            page.get_by_test_id("template-overwrite-button").click()
            page.wait_for_timeout(700)
            page.evaluate("window.scrollTo(0, 0)")
            page.mouse.wheel(0, 1400)
            page.wait_for_timeout(400)
            scroll_y = page.evaluate("window.scrollY")
            audit.record("focus_mode_allows_page_scroll", "PASS" if scroll_y > 200 else "FAIL", {"window_scroll_y_after_wheel": scroll_y})
            topnav_count = page.get_by_test_id("canvas-block-TopNav").count()
            hero_count = page.get_by_test_id("canvas-block-Hero").count()
            features_count = page.get_by_test_id("canvas-block-TrustBadge").count()
            content_count = page.get_by_test_id("canvas-block-ProductCard").count() + page.get_by_test_id("canvas-block-ArticleCard").count() + page.get_by_test_id("canvas-block-ImageText").count() + page.get_by_test_id("canvas-block-ArticleList").count()
            cta_count = page.get_by_test_id("canvas-block-CTASection").count()
            footer_count = page.get_by_test_id("canvas-block-Footer").count()
            supporting_count = page.get_by_test_id("canvas-block-PricingTable").count() + page.get_by_test_id("canvas-block-CouponBanner").count() + page.get_by_test_id("canvas-block-FormBlock").count()
            floating_count = page.get_by_test_id("canvas-block-FloatingButton").count()
            applied_ok = all(count >= 1 for count in [topnav_count, hero_count, features_count, content_count, cta_count, footer_count, floating_count])
            audit.record(
                "click_template_replaces_canvas_with_full_page",
                "PASS" if applied_ok else "FAIL",
                {"TopNav": topnav_count, "Hero": hero_count, "Features": features_count, "Content": content_count, "CTASection": cta_count, "Footer": footer_count, "Supporting": supporting_count, "FloatingButton": floating_count},
            )
            page.get_by_test_id("diy-save-button").click()
            deadline = time.time() + 15
            rows: list[dict[str, Any]] = []
            while time.time() < deadline:
                rows = audit.db("SELECT layout_json FROM pages ORDER BY updated_at DESC LIMIT 1")
                if rows and all(token in rows[0]["layout_json"] for token in ["TopNav", "Hero", "TrustBadge", "CTASection", "Footer", "FloatingButton"]):
                    break
                time.sleep(0.3)
            saved_ok = bool(rows) and all(token in rows[0]["layout_json"] for token in ["TopNav", "Hero", "TrustBadge", "CTASection", "Footer", "FloatingButton"])
            audit.record("template_save_persists_full_page_json", "PASS" if saved_ok else "FAIL", {"db_table": "pages", "contains_full_page_blocks": saved_ok})
            ns_response = requests.post(f"{API}/domains/{domain}/ns-check", json={"request_id": f"template_ns_{stamp}"}, timeout=20)
            audit.record("template_site_dns_ready_for_publish", "PASS" if ns_response.status_code == 200 else "FAIL", {"api": f"POST /domains/{domain}/ns-check", "status_code": ns_response.status_code})
            page.get_by_test_id("diy-publish-button").click()
            site_rows = audit.db("SELECT site_id FROM sites WHERE domain = ?", (domain,))
            site_id = site_rows[0]["site_id"] if site_rows else ""
            dist_index = ROOT / "generated_sites" / site_id / "dist" / "index.html"
            deadline = time.time() + 20
            dist_text = ""
            while time.time() < deadline:
                if dist_index.exists():
                    dist_text = dist_index.read_text(encoding="utf-8", errors="ignore")
                    if all(token in dist_text for token in ["sfs-topnav", "sfs-hero", "sfs-trust", "sfs-cta", "sfs-footer"]):
                        break
                time.sleep(0.4)
            dist_ok = bool(dist_text) and all(token in dist_text for token in ["sfs-topnav", "sfs-hero", "sfs-trust", "sfs-cta", "sfs-footer"])
            audit.record("template_publish_generates_full_dist_page", "PASS" if dist_ok else "FAIL", {"dist_index": str(dist_index), "contains_full_page_sections": dist_ok})
            shot = SCREENSHOTS / "template_library_apply.png"
            page.screenshot(path=str(shot), full_page=True)
            browser.close()

        failed = [item for item in audit.results if item["status"] != "PASS"]
        report = {
            "status": "PASS" if not failed else "FAIL",
            "summary": {"pass": len(audit.results) - len(failed), "fail": len(failed)},
            "results": audit.results,
            "failed": failed,
            "screenshot": str(SCREENSHOTS / "template_library_apply.png"),
            "db_backup_before_clean_run": audit.db_backup,
            "rerun": "python run_template_library_acceptance.py",
        }
        (REPORTS / "template_library_acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": report["status"], "summary": report["summary"], "report": str(REPORTS / "template_library_acceptance.json")}, ensure_ascii=False, indent=2))
    finally:
        audit.stop()


if __name__ == "__main__":
    main()
