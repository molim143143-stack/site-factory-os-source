import json
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


class DiyEditorAcceptance:
    def __init__(self) -> None:
        self.processes: list[subprocess.Popen] = []
        self.results: list[dict[str, Any]] = []
        self.db_backup = ""
        self.screenshots: list[str] = []

    def record(self, feature: str, status: str, evidence: dict[str, Any] | None = None) -> None:
        self.results.append({"feature": feature, "status": status, "evidence": evidence or {}})

    def stop_ports(self) -> None:
        ps = (
            "Get-NetTCPConnection -LocalPort 8000,5173 -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty OwningProcess -Unique | "
            "ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)

    def start(self) -> None:
        REPORTS.mkdir(exist_ok=True)
        SCREENSHOTS.mkdir(exist_ok=True)
        self.stop_ports()
        if DB.exists():
            backup = REPORTS / f"site_factory_os_before_diy_editor_{int(time.time())}.db"
            shutil.copy2(DB, backup)
            self.db_backup = str(backup)
            DB.unlink()
        npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
        self.processes = [
            subprocess.Popen(["python", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
            subprocess.Popen([npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"], cwd=ROOT / "frontend", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
        ]
        for _ in range(100):
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
    page.wait_for_timeout(300)


def drag_component(page: Page, component: str, offset_x: int, offset_y: int) -> None:
    source = page.get_by_test_id(f"block-library-{component}")
    target = page.get_by_test_id("diy-canvas-drop")
    source_box = source.bounding_box()
    canvas_box = target.bounding_box()
    if not source_box or not canvas_box:
        raise RuntimeError(f"cannot drag {component}")
    page.mouse.move(source_box["x"] + source_box["width"] / 2, source_box["y"] + source_box["height"] / 2)
    page.mouse.down()
    page.mouse.move(canvas_box["x"] + offset_x, canvas_box["y"] + offset_y, steps=14)
    page.mouse.up()
    page.wait_for_timeout(350)


def drag_block_area(page: Page, index: int, dx: int, dy: int) -> tuple[dict[str, float], dict[str, float]]:
    block = page.get_by_test_id("canvas-block-Hero").nth(index)
    block.scroll_into_view_if_needed()
    box = block.bounding_box()
    if not box:
        raise RuntimeError(f"block {index} has no box")
    page.mouse.move(box["x"] + box["width"] * 0.55, box["y"] + box["height"] * 0.45)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] * 0.55 + dx, box["y"] + box["height"] * 0.45 + dy, steps=12)
    page.mouse.up()
    page.wait_for_timeout(250)
    after = block.bounding_box()
    if not after:
        raise RuntimeError(f"block {index} disappeared")
    return box, after


def selected_count(page: Page) -> int:
    return int(page.evaluate("document.querySelectorAll('[data-testid^=\"canvas-block-\"].ring-2').length"))


def rgb(page: Page, selector: str, prop: str) -> str:
    return str(page.locator(selector).first.evaluate("(el, prop) => getComputedStyle(el).getPropertyValue(prop)", prop)).strip()


def main() -> None:
    audit = DiyEditorAcceptance()
    try:
        audit.start()
        stamp = str(int(time.time()))
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.goto(WEB)
            page.get_by_test_id("login-submit").click()
            page.wait_for_timeout(4700)

            nav(page, "Sites")
            domain = f"diy-editor-{stamp}.example.com"
            page.get_by_test_id("create-site-alias").fill(f"DIY Editor {stamp}")
            page.get_by_test_id("create-site-domain").fill(domain)
            page.get_by_test_id("create-site-button").click()
            page.get_by_text("SITE_CREATED").wait_for(timeout=15000)

            nav(page, "DIY Builder")
            page.get_by_role("button", name="Focus mode").click()
            page.get_by_role("button", name="50%", exact=True).click()
            page.wait_for_timeout(500)

            before_count = page.get_by_test_id("canvas-block-Hero").count()
            moved = []
            for index in range(10):
                drag_component(page, "Hero", 140 + (index % 5) * 80, 120 + (index // 5) * 90)
                current_count = page.get_by_test_id("canvas-block-Hero").count()
                if current_count > before_count + index:
                    latest_index = current_count - 1
                    before, after = drag_block_area(page, latest_index, 16, 11)
                    moved.append({"index": latest_index, "before": before, "after": after, "moved": abs(after["x"] - before["x"]) > 4 or abs(after["y"] - before["y"]) > 4})
                else:
                    moved.append({"index": index, "before": None, "after": None, "moved": False, "error": "module was not created"})
            after_count = page.get_by_test_id("canvas-block-Hero").count()
            created_count = after_count - before_count
            audit.record("drag_10_modules_creates_exactly_10", "PASS" if created_count == 10 else "FAIL", {"before": before_count, "after": after_count, "created": created_count})

            audit.record("each_module_drags_from_non_interactive_area", "PASS" if all(item["moved"] for item in moved) else "FAIL", {"moved": moved})

            first = page.get_by_test_id("canvas-block-Hero").nth(before_count)
            first.click(force=True)
            count_before_copy = page.get_by_test_id("canvas-block-Hero").count()
            page.keyboard.press("Control+C")
            page.keyboard.press("Control+V")
            page.wait_for_timeout(300)
            count_after_paste = page.get_by_test_id("canvas-block-Hero").count()
            audit.record("ctrl_c_ctrl_v_copies_and_pastes", "PASS" if count_after_paste == count_before_copy + 1 else "FAIL", {"before": count_before_copy, "after": count_after_paste})

            page.keyboard.press("Delete")
            page.wait_for_timeout(300)
            count_after_delete = page.get_by_test_id("canvas-block-Hero").count()
            audit.record("delete_removes_selected_block", "PASS" if count_after_delete == count_before_copy else "FAIL", {"before": count_after_paste, "after": count_after_delete})

            page.get_by_test_id("canvas-block-Hero").nth(before_count).click(force=True)
            page.keyboard.press("Escape")
            page.wait_for_timeout(150)
            audit.record("esc_clears_selection", "PASS" if selected_count(page) == 0 else "FAIL", {"selected_count": selected_count(page)})

            page.get_by_test_id("canvas-block-Hero").nth(before_count).click(force=True)
            count_before_input_delete = page.get_by_test_id("canvas-block-Hero").count()
            page.get_by_test_id("diy-title-input").fill("Typing protected")
            page.keyboard.press("Delete")
            page.keyboard.press("Control+C")
            page.keyboard.press("Control+V")
            page.wait_for_timeout(200)
            count_after_input_delete = page.get_by_test_id("canvas-block-Hero").count()
            audit.record("hotkeys_disabled_while_input_focused", "PASS" if count_after_input_delete == count_before_input_delete else "FAIL", {"before": count_before_input_delete, "after": count_after_input_delete})

            page.get_by_test_id("canvas-block-Hero").nth(before_count).click(force=True)
            page.get_by_test_id("diy-color-background-hex").fill("#123456")
            page.get_by_test_id("diy-color-text-hex").fill("#abcdef")
            page.get_by_test_id("diy-color-button-hex").fill("#ff00aa")
            page.get_by_test_id("diy-color-border-hex").fill("#00ff99")
            page.get_by_test_id("diy-style-width").fill("840")
            page.get_by_test_id("diy-style-height").fill("420")
            page.get_by_test_id("diy-layout-x").fill("77")
            page.get_by_test_id("diy-layout-y").fill("88")
            page.wait_for_timeout(400)
            block_selector = '[data-testid="canvas-block-Hero"][data-selected="true"] section'
            live_colors = {
                "background": rgb(page, block_selector, "background-color"),
                "text": rgb(page, block_selector, "color"),
                "border": rgb(page, block_selector, "border-top-color"),
                "button": rgb(page, '[data-testid="canvas-block-Hero"][data-selected="true"] a', "background-color"),
            }
            colors_ok = live_colors == {
                "background": "rgb(18, 52, 86)",
                "text": "rgb(171, 205, 239)",
                "border": "rgb(0, 255, 153)",
                "button": "rgb(255, 0, 170)",
            }
            audit.record("palette_hex_updates_live_preview", "PASS" if colors_ok else "FAIL", live_colors)

            page.get_by_test_id("diy-save-button").click()
            saved_rows: list[dict[str, Any]] = []
            deadline = time.time() + 15
            while time.time() < deadline:
                saved_rows = audit.db("SELECT layout_json FROM pages ORDER BY updated_at DESC LIMIT 1")
                if saved_rows:
                    saved_json = saved_rows[0].get("layout_json", "")
                    if all(value in saved_json for value in ["#123456", "#abcdef", "#ff00aa", "#00ff99", '"x": 77', '"y": 88']):
                        break
                time.sleep(0.3)
            save_seen = bool(saved_rows) and all(
                value in saved_rows[0].get("layout_json", "")
                for value in ["#123456", "#abcdef", "#ff00aa", "#00ff99", '"x": 77', '"y": 88']
            )
            audit.record("save_writes_page_json_to_db", "PASS" if save_seen else "FAIL", {
                "db_table": "pages",
                "contains_color_position_size": save_seen,
            })
            shot = SCREENSHOTS / "diy_editor_hotkeys_palette.png"
            page.screenshot(path=str(shot), full_page=True)
            audit.screenshots.append(str(shot))

            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            page.reload()
            page.wait_for_timeout(1000)
            nav(page, "Sites")
            page.get_by_role("button", name="Detail").first.click()
            page.wait_for_timeout(500)
            nav(page, "DIY Builder")
            page.get_by_role("button", name="Focus mode").click()
            page.get_by_role("button", name="50%", exact=True).click()
            page.wait_for_timeout(1200)
            restored_blocks = page.evaluate("""
                () => Array.from(document.querySelectorAll('[data-testid="canvas-block-Hero"]')).map((el) => {
                    const section = el.querySelector('section');
                    const button = el.querySelector('a');
                    const sectionStyle = section ? getComputedStyle(section) : null;
                    const buttonStyle = button ? getComputedStyle(button) : null;
                    const html = el;
                    return {
                        id: html.getAttribute('data-block-id'),
                        background: sectionStyle ? sectionStyle.backgroundColor : '',
                        text: sectionStyle ? sectionStyle.color : '',
                        border: sectionStyle ? sectionStyle.borderTopColor : '',
                        button: buttonStyle ? buttonStyle.backgroundColor : '',
                        width: html.style.width.replace('px', ''),
                        height: html.style.height.replace('px', ''),
                        x: html.style.left.replace('px', ''),
                        y: html.style.top.replace('px', '')
                    };
                })
            """)
            matching = next((item for item in restored_blocks if item == {
                "id": item.get("id"),
                "background": "rgb(18, 52, 86)",
                "text": "rgb(171, 205, 239)",
                "border": "rgb(0, 255, 153)",
                "button": "rgb(255, 0, 170)",
                "width": "840",
                "height": "420",
                "x": "77",
                "y": "88"
            }), None)
            if matching and matching.get("id"):
                page.locator(f'[data-block-id="{matching["id"]}"]').click(force=True)
                page.wait_for_timeout(200)
            restored = {
                "background": page.get_by_test_id("diy-color-background-hex").input_value(),
                "text": page.get_by_test_id("diy-color-text-hex").input_value(),
                "button": page.get_by_test_id("diy-color-button-hex").input_value(),
                "border": page.get_by_test_id("diy-color-border-hex").input_value(),
                "width": page.get_by_test_id("diy-style-width").input_value(),
                "height": page.get_by_test_id("diy-style-height").input_value(),
                "x": page.get_by_test_id("diy-layout-x").input_value(),
                "y": page.get_by_test_id("diy-layout-y").input_value(),
            }
            restore_ok = restored == {"background": "#123456", "text": "#abcdef", "button": "#ff00aa", "border": "#00ff99", "width": "840", "height": "420", "x": "77", "y": "88"}
            rows = audit.db("SELECT layout_json FROM pages ORDER BY updated_at DESC LIMIT 1")
            audit.record("save_refresh_restores_color_position_size", "PASS" if restore_ok and matching else "FAIL", {"restored": restored, "restored_dom_match": matching, "all_restored_blocks": restored_blocks, "layout_json_contains_colors": all(color in rows[0]["layout_json"] for color in ["#123456", "#abcdef", "#ff00aa", "#00ff99"]) if rows else False})
            browser.close()

        failed = [item for item in audit.results if item["status"] != "PASS"]
        report = {
            "status": "PASS" if not failed else "FAIL",
            "summary": {"pass": len(audit.results) - len(failed), "fail": len(failed)},
            "results": audit.results,
            "failed": failed,
            "screenshots": audit.screenshots,
            "db_backup_before_clean_run": audit.db_backup,
            "rerun": "python run_diy_editor_interaction_acceptance.py",
        }
        (REPORTS / "diy_editor_interaction_acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": report["status"], "summary": report["summary"], "report": str(REPORTS / "diy_editor_interaction_acceptance.json")}, ensure_ascii=False, indent=2))
    finally:
        audit.stop()


if __name__ == "__main__":
    main()
