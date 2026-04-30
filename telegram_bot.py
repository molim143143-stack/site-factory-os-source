import os
import time
from typing import Any

import requests


API_BASE = os.getenv("SFS_API_BASE", "http://127.0.0.1:8000/api/v1")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def keyboard(rows: list[list[tuple[str, str]]]) -> dict[str, Any]:
    return {"inline_keyboard": [[{"text": text, "callback_data": data} for text, data in row] for row in rows]}


MAIN_MENU = keyboard(
    [
        [("Dashboard", "dashboard"), ("Sites", "sites")],
        [("CMS 快速发文章", "quick_article"), ("Product 快速上商品", "quick_product")],
        [("Tasks", "tasks"), ("Errors", "errors")],
        [("DNS", "dns"), ("Membership", "membership")],
        [("Help", "help")],
    ]
)


def api_get(path: str) -> dict:
    try:
        return requests.get(f"{API_BASE}{path}", timeout=8).json()
    except Exception as exc:
        return {"error": str(exc)}


def api_post(path: str, payload: dict) -> dict:
    try:
        return requests.post(f"{API_BASE}{path}", json=payload, timeout=8).json()
    except Exception as exc:
        return {"error": str(exc)}


def render_action(action: str, user_id: str = "user_telegram_trial") -> tuple[str, dict]:
    if action in {"/start", "start"}:
        return "Site Factory OS\n请选择操作：", MAIN_MENU
    if action == "dashboard":
        status = api_get("/system/status")
        return f"Dashboard\nSites: {status.get('sites', 0)}\nRunning: {status.get('tasks_running', 0)}\nFailed: {status.get('tasks_failed', 0)}", MAIN_MENU
    if action == "sites":
        sites = api_get("/sites").get("items", [])
        text = "Sites\n" + "\n".join([f"{s.get('site_id')} · {s.get('alias')} · {s.get('status')}" for s in sites[:8]])
        return text or "No sites", MAIN_MENU
    if action == "tasks":
        tasks = api_get("/tasks").get("items", [])
        text = "Tasks\n" + "\n".join([f"{t.get('task_id')} · {t.get('task_type')} · {t.get('status')}" for t in tasks[:8]])
        return text or "No tasks", MAIN_MENU
    if action == "errors":
        errors = api_get("/errors").get("items", [])
        text = "Errors\n" + "\n".join([f"{e.get('error_code')} · {e.get('severity')}" for e in errors[:8]])
        return text or "No errors", MAIN_MENU
    if action == "membership":
        return "Membership\nTrial / Pro / Enterprise\nTrial 用户不能使用 Bulk / Telegram 高级操作。", MAIN_MENU
    if action in {"quick_article", "quick_product"} and user_id.endswith("trial"):
        return "MEMBERSHIP_FEATURE_NOT_ALLOWED\nTrial 用户不能使用 Telegram 高级操作。", MAIN_MENU
    if action == "quick_article":
        result = api_post("/tasks", {"request_id": f"tg_article_{int(time.time())}", "task_type": "cms_publish", "user_id": user_id})
        return f"快速发文章任务已创建\n{result.get('task_id', result)}", MAIN_MENU
    if action == "quick_product":
        result = api_post("/tasks", {"request_id": f"tg_product_{int(time.time())}", "task_type": "product_publish", "user_id": user_id})
        return f"快速上商品任务已创建\n{result.get('task_id', result)}", MAIN_MENU
    if action == "dns":
        return "DNS\nName.com 第一版只做 NS 设置指引，不做自动购买。", MAIN_MENU
    return "Help\n/start 打开主菜单。所有写操作走 Task Engine。", MAIN_MENU


class TelegramBot:
    def __init__(self, token: str = TELEGRAM_TOKEN) -> None:
        self.token = token
        self.offset = 0

    @property
    def base(self) -> str:
        return f"https://api.telegram.org/bot{self.token}"

    def send_message(self, chat_id: int, text: str, reply_markup: dict | None = None) -> None:
        requests.post(f"{self.base}/sendMessage", json={"chat_id": chat_id, "text": text, "reply_markup": reply_markup}, timeout=10)

    def answer_callback(self, callback_id: str) -> None:
        requests.post(f"{self.base}/answerCallbackQuery", json={"callback_query_id": callback_id}, timeout=10)

    def run(self) -> None:
        if not self.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
        while True:
            updates = requests.get(f"{self.base}/getUpdates", params={"timeout": 30, "offset": self.offset}, timeout=35).json().get("result", [])
            for update in updates:
                self.offset = update["update_id"] + 1
                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    text = update["message"].get("text", "")
                    response, markup = render_action(text)
                    self.send_message(chat_id, response, markup)
                elif "callback_query" in update:
                    callback = update["callback_query"]
                    chat_id = callback["message"]["chat"]["id"]
                    response, markup = render_action(callback.get("data", "help"))
                    self.answer_callback(callback["id"])
                    self.send_message(chat_id, response, markup)


def simulate() -> dict[str, Any]:
    actions = ["/start", "dashboard", "sites", "tasks", "errors", "membership", "quick_article"]
    result = {action.lstrip("/"): {"text": render_action(action)[0], "reply_markup": render_action(action)[1]} for action in actions}
    result["trial_quick_article"] = {
        "text": render_action("quick_article", "user_telegram_trial")[0],
        "blocked": "MEMBERSHIP_FEATURE_NOT_ALLOWED" in render_action("quick_article", "user_telegram_trial")[0],
    }
    return result


if __name__ == "__main__":
    if os.getenv("TELEGRAM_SIMULATE", "0") == "1":
        import json

        print(json.dumps(simulate(), ensure_ascii=False, indent=2))
    else:
        TelegramBot().run()
