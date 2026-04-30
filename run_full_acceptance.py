import json
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from core.database import init_db
from main import app
from telegram_bot import simulate as simulate_telegram


ROOT = Path(__file__).resolve().parent
DB = ROOT / "storage" / "site_factory_os.db"
REPORTS = ROOT / "reports"
GENERATED = ROOT / "generated_sites"


class FullAcceptance:
    def __init__(self) -> None:
        self.client = TestClient(app)
        self.evidence: dict[str, Any] = {"api": [], "db": [], "files": [], "commands": [], "checks": []}

    def request(self, method: str, url: str, payload: dict | None = None) -> dict:
        response = self.client.request(method, url, json=payload)
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}
        self.evidence["api"].append(
            {
                "method": method,
                "url": url,
                "payload": payload,
                "status_code": response.status_code,
                "response": body,
            }
        )
        return body

    def ok(self, method: str, url: str, payload: dict | None = None) -> dict:
        body = self.request(method, url, payload)
        last = self.evidence["api"][-1]
        assert last["status_code"] < 400, last
        return body

    def db_query(self, sql: str, params: tuple = ()) -> list[dict]:
        with sqlite3.connect(DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        self.evidence["db"].append({"sql": sql, "params": params, "rows": rows[:25], "row_count": len(rows)})
        return rows

    def db_scalar(self, sql: str, params: tuple = ()) -> int:
        rows = self.db_query(sql, params)
        return int(list(rows[0].values())[0]) if rows else 0

    def file_check(self, path: Path, *, contains: list[str] | None = None) -> bool:
        exists = path.exists()
        text = path.read_text(encoding="utf-8") if exists and path.is_file() else ""
        contains_result = {needle: needle in text for needle in (contains or [])}
        passed = exists and all(contains_result.values())
        self.evidence["files"].append(
            {
                "path": str(path),
                "exists": exists,
                "size": path.stat().st_size if exists and path.is_file() else None,
                "contains": contains_result,
            }
        )
        return passed

    def check(self, name: str, passed: bool, details: dict | None = None) -> None:
        self.evidence["checks"].append({"name": name, "pass": bool(passed), "details": details or {}})

    def run_command(self, name: str, command: list[str], cwd: Path) -> bool:
        executable = shutil.which(command[0]) or shutil.which(f"{command[0]}.cmd") or command[0]
        command = [executable, *command[1:]]
        completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, shell=False)
        self.evidence["commands"].append(
            {
                "name": name,
                "command": command,
                "cwd": str(cwd),
                "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-3000:],
                "stderr_tail": completed.stderr[-3000:],
            }
        )
        return completed.returncode == 0


def reset() -> None:
    if DB.exists():
        DB.unlink()
    full_root = ROOT / "sample_data" / "full_acceptance"
    if full_root.exists():
        shutil.rmtree(full_root)
    if GENERATED.exists():
        for child in GENERATED.iterdir():
            if child.is_dir() and child.name.startswith("site_"):
                shutil.rmtree(child)
    REPORTS.mkdir(exist_ok=True)
    init_db()


def setup_bulk(site_id: str) -> Path:
    root = ROOT / "sample_data" / "full_acceptance" / "bulk_good"
    site = root / site_id
    (site / "images").mkdir(parents=True, exist_ok=True)
    (site / "config.json").write_text(
        json.dumps({"site_id": site_id, "template": "landing1", "site_type": "shop", "language_code": "en"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (site / "article.txt").write_text("title: Full Bulk Article\ncontent: Bulk article body\n", encoding="utf-8")
    (site / "product.txt").write_text("name: Full Bulk Product\nprice: 39.99\nimages:\n- 1.jpg\n", encoding="utf-8")
    (site / "images" / "1.jpg").write_text("mock image bytes", encoding="utf-8")
    return root


def write_reports(a: FullAcceptance, result: dict) -> None:
    a.evidence["summary"] = result
    (REPORTS / "full_acceptance_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORTS / "full_acceptance_evidence.json").write_text(json.dumps(a.evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    report = [
        "# Site Factory OS 完整产品化本地验收报告",
        "",
        "## 结论",
        f"- PASS: {result['pass']}",
        f"- Failed: {result['failed']}",
        f"- API 请求证据: `{(REPORTS / 'full_acceptance_evidence.json').as_posix()}`",
        f"- SQLite 查询证据: `{(REPORTS / 'full_acceptance_evidence.json').as_posix()}`",
        f"- Telegram Bot 模拟日志: `{(REPORTS / 'telegram_simulation.json').as_posix()}`",
        "",
        "## 核心产物",
        f"- dist: `{result.get('dist_path')}`",
        f"- sitemap.xml: `{result.get('sitemap_path')}`",
        f"- robots.txt: `{result.get('robots_path')}`",
        "",
        "## 检查项",
    ]
    for item in result["checks"]:
        status = "PASS" if item["pass"] else "FAIL"
        report.append(f"- {status} {item['name']}")
    (REPORTS / "完整产品化验收报告.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def run() -> None:
    reset()
    a = FullAcceptance()

    frontend_ok = a.run_command("frontend_build", ["npm", "run", "build"], ROOT / "frontend")
    a.check("frontend_build_npm_run_build", frontend_ok)

    register = a.ok(
        "POST",
        "/api/v1/auth/register",
        {"username": "full_user", "password": "pw123", "email": "full@example.com", "telegram_handle": "@full_user", "trial_days": 3},
    )
    user_id = register["user"]["user_id"]
    login = a.ok("POST", "/api/v1/auth/login", {"username": "full_user", "password": "pw123"})
    a.check("register_login_portal_boot", login["portal_boot"] == "Portal Boot Sequence" and login["membership"]["plan"] == "trial")

    bulk_denied = a.request("POST", "/api/v1/bulk/jobs", {"request_id": "full_bulk_denied_trial", "root_path": str(ROOT), "user_id": user_id})
    a.check("trial_bulk_permission_denied", bulk_denied["error"]["error_code"] == "MEMBERSHIP_FEATURE_NOT_ALLOWED")

    site = a.ok(
        "POST",
        "/api/v1/sites",
        {"request_id": "full_site_create_001", "domain": "full.local.test", "alias": "Full Acceptance", "site_type": "shop", "template_id": "shop1", "user_id": user_id},
    )
    site_id = site["site"]["site_id"]
    domain = site["domain"]
    second_site = a.request(
        "POST",
        "/api/v1/sites",
        {"request_id": "full_site_create_over_limit", "domain": "full-two.local.test", "alias": "Over Limit", "user_id": user_id},
    )
    a.check(
        "trial_site_limit_denied",
        second_site["error"]["error_code"] == "MEMBERSHIP_PLAN_LIMIT_REACHED"
        and domain["ns1"]
        and site["next_step"].startswith("set NS"),
        {"site_id": site_id, "ns": [domain["ns1"], domain["ns2"]]},
    )

    license_row = a.ok("POST", "/api/v1/admin/billing/license-codes", {"plan": "pro", "duration_days": 30, "created_by": "admin_001", "code_type": "PRO-30D"})
    activated = a.ok("POST", "/api/v1/membership/license-codes/activate", {"user_id": user_id, "code": license_row["license"]["code"]})
    a.check("manual_license_activates_pro", activated["membership"]["plan"] == "pro")

    ns_check = a.ok("POST", "/api/v1/domains/full.local.test/ns-check", {"request_id": "full_ns_check_001", "user_id": user_id})
    a.check("ns_mock_check_verified", ns_check["domain"]["status"] == "ns_verified" and ns_check["domain"]["ssl_status"] == "active")

    article = a.ok(
        "POST",
        f"/api/v1/sites/{site_id}/articles",
        {"request_id": "full_article_create_001", "title": "Launch Note", "content": "Site Factory OS is live.", "seo_description": "Launch article", "user_id": user_id},
    )["article"]
    article_pub = a.ok("POST", f"/api/v1/articles/{article['article_id']}/publish", {"request_id": "full_article_publish_001", "user_id": user_id})
    a.check("article_create_publish", article_pub["article"]["status"] == "published")

    product = a.ok(
        "POST",
        f"/api/v1/sites/{site_id}/products",
        {"request_id": "full_product_create_001", "name": "Neon Builder Pack", "price": 49.99, "description": "Productized site factory kit.", "user_id": user_id},
    )["product"]
    payment = a.ok(
        "POST",
        f"/api/v1/sites/{site_id}/payments",
        {"request_id": "full_payment_create_001", "payment_url": "https://pay.example.com/neon-builder-pack", "provider": "stripe", "user_id": user_id},
    )["payment"]
    bind = a.ok("POST", f"/api/v1/products/{product['product_id']}/payment-bind", {"request_id": "full_payment_bind_001", "payment_id": payment["payment_id"], "user_id": user_id})
    product_pub = a.ok("POST", f"/api/v1/products/{product['product_id']}/publish", {"request_id": "full_product_publish_001", "user_id": user_id})
    a.check("product_payment_publish", bind["product"]["payment_id"] == payment["payment_id"] and product_pub["product"]["status"] == "active")

    bulk_root = setup_bulk(site_id)
    bulk_job = a.ok("POST", "/api/v1/bulk/jobs", {"request_id": "full_bulk_job_001", "root_path": str(bulk_root), "user_id": user_id})["bulk_job"]
    scan = a.ok("POST", f"/api/v1/bulk/jobs/{bulk_job['bulk_job_id']}/scan", {"request_id": "full_bulk_scan_001", "site_id": site_id, "user_id": user_id})
    validate = a.ok("POST", f"/api/v1/bulk/jobs/{bulk_job['bulk_job_id']}/validate", {"request_id": "full_bulk_validate_001", "site_id": site_id, "user_id": user_id})
    preview = a.ok("POST", f"/api/v1/bulk/jobs/{bulk_job['bulk_job_id']}/preview")
    execute = a.ok("POST", f"/api/v1/bulk/jobs/{bulk_job['bulk_job_id']}/execute", {"request_id": "full_bulk_execute_001", "site_id": site_id, "user_id": user_id})
    a.check("bulk_scan_validate_preview_execute", scan["total"] == 1 and validate["status"] == "validated" and len(preview["items"]) >= 2 and execute["report"]["success"] >= 2)

    page = a.ok(
        "POST",
        f"/api/v1/sites/{site_id}/pages",
        {"request_id": "full_diy_save_001", "slug": "custom.html", "layout": {"blocks": [{"type": "Hero", "props": {"title": "Control Cabin"}}]}, "user_id": user_id},
    )["page"]
    page_pub = a.ok("POST", f"/api/v1/pages/{page['page_id']}/publish", {"request_id": "full_diy_publish_001", "user_id": user_id})
    a.check("diy_save_publish", page["status"] == "draft" and page_pub["page"]["status"] == "published")

    seo = a.ok("PATCH", f"/api/v1/sites/{site_id}/seo", {"request_id": "full_seo_update_001", "title": "Full Acceptance SEO", "description": "SEO generated by local acceptance.", "user_id": user_id})
    sitemap_api = a.ok("POST", f"/api/v1/sites/{site_id}/sitemap/generate", {"request_id": "full_sitemap_generate_001", "user_id": user_id})
    deployment = a.ok("POST", f"/api/v1/sites/{site_id}/deployments", {"request_id": "full_deploy_001", "user_id": user_id})["deployment"]
    dist = Path(deployment["dist_path"])
    sitemap_path = dist / "sitemap.xml"
    robots_path = dist / "robots.txt"
    index_path = dist / "index.html"
    article_path = dist / "articles" / "launch-note.html"
    product_path = dist / "products" / "neon-builder-pack.html"
    seo_files_ok = (
        a.file_check(sitemap_path, contains=["<urlset", "https://full.local.test/"])
        and a.file_check(robots_path, contains=["Sitemap: https://full.local.test/sitemap.xml"])
        and a.file_check(index_path, contains=["<title>Full Acceptance SEO</title>", 'rel="canonical"', 'hreflang="zh-CN"', 'property="og:title"'])
        and a.file_check(article_path, contains=["Launch Note", 'rel="canonical"', 'property="og:url"'])
        and a.file_check(product_path, contains=["Neon Builder Pack", "https://pay.example.com/neon-builder-pack"])
    )
    a.check("seo_and_dist_files_generated", seo["seo"]["title"] == "Full Acceptance SEO" and len(sitemap_api["sitemap"]) >= 1 and seo_files_ok)

    tasks = a.ok("GET", "/api/v1/tasks")
    errors = a.ok("GET", "/api/v1/errors")
    task_log_count = a.db_scalar("SELECT COUNT(*) AS c FROM task_logs")
    deploy_file_count = a.db_scalar("SELECT COUNT(*) AS c FROM deployment_files WHERE deploy_id=?", (deployment["deploy_id"],))
    a.check("tasks_errors_db_logs_queryable", len(tasks["items"]) >= 15 and isinstance(errors["items"], list) and task_log_count > 0 and deploy_file_count > 0)

    telegram = simulate_telegram()
    (REPORTS / "telegram_simulation.json").write_text(json.dumps(telegram, ensure_ascii=False, indent=2), encoding="utf-8")
    a.check(
        "telegram_button_menu_and_trial_block",
        "Site Factory OS" in telegram["start"]["text"]
        and "Dashboard" in json.dumps(telegram["start"]["reply_markup"], ensure_ascii=False)
        and "Sites" in json.dumps(telegram["start"]["reply_markup"], ensure_ascii=False)
        and telegram["trial_quick_article"]["blocked"] is True,
    )

    api_status = a.ok("GET", "/api/v1/system/status")
    sites_api = a.ok("GET", "/api/v1/sites")
    a.check("frontend_required_real_api_endpoints_available", api_status["sites"] >= 1 and any(item["site_id"] == site_id for item in sites_api["items"]))

    db_counts = {
        table: a.db_scalar(f"SELECT COUNT(*) AS c FROM {table}")
        for table in [
            "users",
            "memberships",
            "sites",
            "domains",
            "tasks",
            "task_logs",
            "articles",
            "products",
            "payments",
            "bulk_jobs",
            "bulk_items",
            "deployments",
            "deployment_files",
            "seo_records",
            "error_logs",
            "audit_logs",
        ]
    }
    a.check("sqlite_core_tables_have_real_rows", all(db_counts[key] > 0 for key in ["users", "memberships", "sites", "tasks", "task_logs", "deployments", "deployment_files", "audit_logs"]))

    result = {
        "checks": a.evidence["checks"],
        "failed": len([item for item in a.evidence["checks"] if not item["pass"]]),
        "failed_checks": [item for item in a.evidence["checks"] if not item["pass"]],
        "db_counts": db_counts,
        "dist_path": str(dist),
        "sitemap_path": str(sitemap_path),
        "robots_path": str(robots_path),
    }
    result["pass"] = result["failed"] == 0
    write_reports(a, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
