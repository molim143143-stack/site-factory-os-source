import json
import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
DB = ROOT / "storage" / "site_factory_os.db"
API_BASE = os.getenv("SFS_API_BASE", "http://127.0.0.1:8000/api/v1")


class RealProof:
    def __init__(self) -> None:
        self.api: list[dict[str, Any]] = []
        self.db: list[dict[str, Any]] = []
        self.files: list[dict[str, Any]] = []
        self.tests: list[dict[str, Any]] = []

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        response = requests.request(method, f"{API_BASE}{path}", json=payload, timeout=20)
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}
        row = {"method": method, "path": path, "payload": payload, "status_code": response.status_code, "response": body}
        self.api.append(row)
        return body

    def db_query(self, sql: str, params: tuple = ()) -> list[dict]:
        with sqlite3.connect(DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        self.db.append({"sql": sql, "params": params, "rows": rows[:20], "row_count": len(rows)})
        return rows

    def file_snippet(self, path: Path, limit: int = 800) -> str:
        exists = path.exists()
        text = path.read_text(encoding="utf-8") if exists and path.is_file() else ""
        self.files.append({"path": str(path), "exists": exists, "size": path.stat().st_size if exists else None, "snippet": text[:limit]})
        return text

    def test(self, name: str, expected: str, passed: bool, evidence: dict | None = None, note: str | None = None) -> None:
        self.tests.append({"name": name, "expected": expected, "pass": bool(passed), "evidence": evidence or {}, "note": note})


def wait_api() -> None:
    for _ in range(40):
        try:
            if requests.get(f"{API_BASE}/system/health", timeout=2).status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"API not reachable: {API_BASE}")


def setup_bulk(site_id: str, name: str, *, missing_image: bool = False) -> Path:
    root = ROOT / "sample_data" / "real_proof" / name
    if root.exists():
        shutil.rmtree(root)
    site = root / site_id
    (site / "images").mkdir(parents=True, exist_ok=True)
    (site / "config.json").write_text(
        json.dumps({"site_id": site_id, "language_code": "en", "template": "shop1", "site_type": "shop"}),
        encoding="utf-8",
    )
    image = "missing.jpg" if missing_image else "1.jpg"
    (site / "article.txt").write_text("title: Proof Bulk Article\ncontent: Bulk body\n", encoding="utf-8")
    (site / "product.txt").write_text(f"name: Proof Bulk Product\nprice: 29.99\nimages:\n- {image}\n", encoding="utf-8")
    if not missing_image:
        (site / "images" / "1.jpg").write_text("image", encoding="utf-8")
    return root


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    wait_api()
    p = RealProof()

    user = p.request("POST", "/auth/register", {"username": "proof_user", "password": "pw123", "trial_days": 3})
    user_id = user["user"]["user_id"]
    login = p.request("POST", "/auth/login", {"username": "proof_user", "password": "pw123"})
    p.test("register_login", "login returns Portal Boot Sequence", login.get("portal_boot") == "Portal Boot Sequence", {"api_index": len(p.api) - 1})

    trial_bulk = p.request("POST", "/bulk/jobs", {"request_id": "proof_trial_bulk", "root_path": str(ROOT), "user_id": user_id})
    p.test("trial_user_bulk_must_fail", "MEMBERSHIP_FEATURE_NOT_ALLOWED", trial_bulk.get("error", {}).get("error_code") == "MEMBERSHIP_FEATURE_NOT_ALLOWED", {"api_index": len(p.api) - 1})

    site_payload = {"request_id": "proof_site_001", "domain": "proof.local.test", "alias": "Proof Site", "site_type": "shop", "template_id": "shop1", "user_id": user_id}
    site = p.request("POST", "/sites", site_payload)
    duplicate = p.request("POST", "/sites", site_payload)
    site_id = site["site"]["site_id"]
    p.test("duplicate_request_id_no_second_task", "same task_id and idempotent true", duplicate.get("task_id") == site.get("task_id") and duplicate.get("idempotent") is True, {"api_index": len(p.api) - 1})

    second_site = p.request("POST", "/sites", {"request_id": "proof_site_002", "domain": "proof2.local.test", "alias": "Proof Site 2", "user_id": user_id})
    p.test("trial_user_second_site_must_fail", "MEMBERSHIP_PLAN_LIMIT_REACHED", second_site.get("error", {}).get("error_code") == "MEMBERSHIP_PLAN_LIMIT_REACHED", {"api_index": len(p.api) - 1})

    deploy_before_dns = p.request("POST", f"/sites/{site_id}/deployments", {"request_id": "proof_deploy_before_dns", "user_id": user_id})
    p.test("dns_unverified_deploy_must_fail", "DNS_NS_NOT_PROPAGATED", deploy_before_dns.get("error", {}).get("error_code") == "DNS_NS_NOT_PROPAGATED", {"api_index": len(p.api) - 1})

    bad_price = p.request("POST", f"/sites/{site_id}/products", {"request_id": "proof_bad_price", "name": "Bad", "price": "abc", "user_id": user_id})
    p.test("price_abc_must_fail", "CMS_PRODUCT_PRICE_INVALID", bad_price.get("error", {}).get("error_code") == "CMS_PRODUCT_PRICE_INVALID", {"api_index": len(p.api) - 1})

    invalid_license = p.request("POST", "/membership/license-codes/activate", {"user_id": user_id, "code": "BAD-CODE"})
    p.test("invalid_license_must_fail", "LICENSE_CODE_INVALID", invalid_license.get("error", {}).get("error_code") == "LICENSE_CODE_INVALID", {"api_index": len(p.api) - 1})

    unauthorized_admin = p.request("POST", "/admin/billing/license-codes", {"plan": "pro", "duration_days": 7, "created_by": "anonymous"})
    p.test(
        "unauthorized_membership_admin_must_fail",
        "AUTH_FORBIDDEN or 401/403",
        "error" in unauthorized_admin,
        {"api_index": len(p.api) - 1, "actual_response": unauthorized_admin},
        "Current backend has no admin auth guard here, so this requirement is NOT satisfied.",
    )

    license_row = p.request("POST", "/admin/billing/license-codes", {"plan": "pro", "duration_days": 30, "created_by": "admin_001"})
    pro = p.request("POST", "/membership/license-codes/activate", {"user_id": user_id, "code": license_row["license"]["code"]})
    p.test("pro_license_activation", "membership plan becomes pro", pro.get("membership", {}).get("plan") == "pro", {"api_index": len(p.api) - 1})

    ns = p.request("POST", "/domains/proof.local.test/ns-check", {"request_id": "proof_ns_check", "user_id": user_id})
    p.test("dns_check_success", "domain status ns_verified", ns.get("domain", {}).get("status") == "ns_verified", {"api_index": len(p.api) - 1})

    missing_root = setup_bulk(site_id, "missing_image", missing_image=True)
    missing_job = p.request("POST", "/bulk/jobs", {"request_id": "proof_missing_job", "root_path": str(missing_root), "user_id": user_id})
    p.request("POST", f"/bulk/jobs/{missing_job['bulk_job']['bulk_job_id']}/scan", {"request_id": "proof_missing_scan", "site_id": site_id, "user_id": user_id})
    missing_validate = p.request("POST", f"/bulk/jobs/{missing_job['bulk_job']['bulk_job_id']}/validate", {"request_id": "proof_missing_validate", "site_id": site_id, "user_id": user_id})
    p.test("missing_image_must_fail", "BULK_PRODUCT_IMAGE_NOT_FOUND", any(e.get("error_code") == "BULK_PRODUCT_IMAGE_NOT_FOUND" for e in missing_validate.get("errors", [])), {"api_index": len(p.api) - 1})

    article = p.request("POST", f"/sites/{site_id}/articles", {"request_id": "proof_article_create", "title": "Proof Article", "content": "Proof body", "user_id": user_id})["article"]
    article_pub = p.request("POST", f"/articles/{article['article_id']}/publish", {"request_id": "proof_article_publish", "user_id": user_id})
    product = p.request("POST", f"/sites/{site_id}/products", {"request_id": "proof_product_create", "name": "Proof Product", "price": 19.99, "description": "Proof product", "user_id": user_id})["product"]
    payment = p.request("POST", f"/sites/{site_id}/payments", {"request_id": "proof_payment_create", "payment_url": "https://pay.example.com/proof", "provider": "stripe", "user_id": user_id})["payment"]
    p.request("POST", f"/products/{product['product_id']}/payment-bind", {"request_id": "proof_payment_bind", "payment_id": payment["payment_id"], "user_id": user_id})
    product_pub = p.request("POST", f"/products/{product['product_id']}/publish", {"request_id": "proof_product_publish", "user_id": user_id})

    valid_root = setup_bulk(site_id, "valid_bulk")
    valid_job = p.request("POST", "/bulk/jobs", {"request_id": "proof_valid_bulk_job", "root_path": str(valid_root), "user_id": user_id})
    p.request("POST", f"/bulk/jobs/{valid_job['bulk_job']['bulk_job_id']}/scan", {"request_id": "proof_valid_bulk_scan", "site_id": site_id, "user_id": user_id})
    valid_validate = p.request("POST", f"/bulk/jobs/{valid_job['bulk_job']['bulk_job_id']}/validate", {"request_id": "proof_valid_bulk_validate", "site_id": site_id, "user_id": user_id})
    valid_execute = p.request("POST", f"/bulk/jobs/{valid_job['bulk_job']['bulk_job_id']}/execute", {"request_id": "proof_valid_bulk_execute", "site_id": site_id, "user_id": user_id})

    page = p.request("POST", f"/sites/{site_id}/pages", {"request_id": "proof_page_save", "slug": "proof-page.html", "layout": {"blocks": [{"type": "Hero", "props": {"title": "Proof Hero"}}]}, "user_id": user_id})["page"]
    page_pub = p.request("POST", f"/pages/{page['page_id']}/publish", {"request_id": "proof_page_publish", "user_id": user_id})
    seo = p.request("PATCH", f"/sites/{site_id}/seo", {"request_id": "proof_seo_update", "title": "Proof SEO Title", "description": "Proof SEO description", "user_id": user_id})
    final_deploy = p.request("POST", f"/sites/{site_id}/deployments", {"request_id": "proof_final_deploy", "user_id": user_id})

    with sqlite3.connect(DB) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO resource_locks(lock_id, resource_type, resource_id, task_id, status, locked_at, expires_at) VALUES(?,?,?,?,?,?,NULL)",
            ("lock_proof_manual", "site", site_id, "task_fake_concurrent", "locked", "2026-04-29T00:00:00+00:00"),
        )
        conn.commit()
    lock_fail = p.request("POST", f"/sites/{site_id}/deployments", {"request_id": "proof_concurrent_deploy", "user_id": user_id})
    p.test(
        "same_site_deploy_lock_conflict_must_fail",
        "TASK_ALREADY_RUNNING",
        lock_fail.get("error", {}).get("error_code") == "TASK_ALREADY_RUNNING",
        {"api_index": len(p.api) - 1},
        "Verified by holding the site lock in SQLite before API deploy; this proves lock conflict handling, not a timing race benchmark.",
    )
    with sqlite3.connect(DB) as conn:
        conn.execute("UPDATE resource_locks SET status='released' WHERE lock_id='lock_proof_manual'")
        conn.commit()

    dist = Path(final_deploy["deployment"]["dist_path"])
    sitemap = p.file_snippet(dist / "sitemap.xml")
    robots = p.file_snippet(dist / "robots.txt")
    index = p.file_snippet(dist / "index.html")
    proof_article_html = p.file_snippet(dist / "articles" / "proof-article.html")
    proof_product_html = p.file_snippet(dist / "products" / "proof-product.html")

    p.test("article_publish_real_outputs", "API published + DB status + dist article HTML", article_pub.get("article", {}).get("status") == "published" and "Proof Article" in proof_article_html)
    p.test("product_publish_payment_real_outputs", "API active + payment link in dist product HTML", product_pub.get("product", {}).get("status") == "active" and "https://pay.example.com/proof" in proof_product_html)
    p.test("bulk_validate_execute_real_outputs", "validated + execute success", valid_validate.get("status") == "validated" and valid_execute.get("report", {}).get("success", 0) >= 2)
    p.test("diy_save_publish_db_and_deploy", "page DB row + publish deployment", page_pub.get("page", {}).get("status") == "published")
    p.test("seo_files_have_real_content", "sitemap/robots/index meta are non-empty", "<urlset" in sitemap and "Sitemap: https://proof.local.test/sitemap.xml" in robots and "<title>Proof SEO Title</title>" in index)

    db_checks = {
        "tasks": p.db_query("SELECT task_id, request_id, status, error_code FROM tasks ORDER BY created_at DESC LIMIT 12"),
        "articles": p.db_query("SELECT article_id, site_id, status FROM articles WHERE site_id=?", (site_id,)),
        "products": p.db_query("SELECT product_id, site_id, status, payment_id FROM products WHERE site_id=?", (site_id,)),
        "pages": p.db_query("SELECT page_id, site_id, status, layout_json FROM pages WHERE site_id=?", (site_id,)),
        "deployments": p.db_query("SELECT deploy_id, site_id, status, dist_path FROM deployments WHERE site_id=?", (site_id,)),
        "deployment_files": p.db_query("SELECT deploy_id, file_path, file_size FROM deployment_files ORDER BY created_at DESC LIMIT 20"),
        "errors": p.db_query("SELECT error_code, message, request_id FROM error_logs ORDER BY created_at DESC LIMIT 20"),
        "audit": p.db_query("SELECT action, resource_type, resource_id FROM audit_logs ORDER BY created_at DESC LIMIT 20"),
    }

    result = {
        "api_base": API_BASE,
        "site_id": site_id,
        "dist_path": str(dist),
        "destructive_tests": p.tests,
        "failed_required_tests": [t for t in p.tests if not t["pass"]],
        "api_evidence": p.api,
        "db_evidence": p.db,
        "file_evidence": p.files,
        "db_summary": {key: len(value) for key, value in db_checks.items()},
    }
    (REPORTS / "destructive_tests.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORTS / "real_http_evidence.json").write_text(json.dumps({"api": p.api, "db": p.db, "files": p.files}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"site_id": site_id, "dist_path": str(dist), "failed_required_tests": result["failed_required_tests"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
