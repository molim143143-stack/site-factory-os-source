import json
import shutil
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from core.database import init_db
from main import app


ROOT = Path(__file__).resolve().parent
DB = ROOT / "storage" / "site_factory_os.db"


class Acceptance:
    def __init__(self) -> None:
        self.client = TestClient(app)
        self.evidence: dict = {"api": [], "db": [], "checks": []}

    def request(self, method: str, url: str, payload: dict | None = None) -> dict:
        res = self.client.request(method, url, json=payload)
        try:
            body = res.json()
        except Exception:
            body = {"raw": res.text}
        self.evidence["api"].append(
            {
                "method": method,
                "url": url,
                "payload": payload,
                "status_code": res.status_code,
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
        self.evidence["db"].append({"sql": sql, "params": params, "rows": rows[:20], "row_count": len(rows)})
        return rows

    def db_scalar(self, sql: str, params: tuple = ()) -> int:
        rows = self.db_query(sql, params)
        return list(rows[0].values())[0] if rows else 0

    def check(self, name: str, passed: bool, details: dict | None = None) -> None:
        self.evidence["checks"].append({"name": name, "pass": bool(passed), "details": details or {}})


def reset() -> None:
    if DB.exists():
        DB.unlink()
    init_db()


def setup_bulk(site_id: str, *, bad_price: bool = False, missing_image: bool = False, root_name: str = "bulk_upload") -> Path:
    root = ROOT / "sample_data" / root_name
    if root.exists():
        shutil.rmtree(root)
    site = root / site_id
    (site / "images").mkdir(parents=True)
    (site / "config.json").write_text(
        json.dumps({"site_id": site_id, "template": "landing1", "site_type": "shop", "language_code": "en"}, ensure_ascii=False),
        encoding="utf-8",
    )
    price = "abc" if bad_price else "19.99"
    image_ref = "missing.jpg" if missing_image else "1.jpg"
    (site / "product.txt").write_text(f"name: Bulk Shoes\nprice: {price}\nimages:\n- {image_ref}\n", encoding="utf-8")
    (site / "article.txt").write_text("title: Bulk Article\ncontent: Hello from bulk\n", encoding="utf-8")
    if not missing_image:
        (site / "images" / "1.jpg").write_text("mock image", encoding="utf-8")
    return root


def run():
    reset()
    a = Acceptance()

    # Phase 1 positive and negative.
    site_res = a.ok("POST", "/api/v1/sites", {"request_id": "acc_site_001", "domain": "acc.example.com", "alias": "验收站"})
    site_id = site_res["site"]["site_id"]
    task_id = site_res["task_id"]
    dup = a.ok("POST", "/api/v1/sites", {"request_id": "acc_site_001", "domain": "acc.example.com", "alias": "验收站"})
    a.check("phase1_idempotency_same_task", dup["task_id"] == task_id and dup["idempotent"] is True)
    rows = a.db_query("SELECT task_id, request_id, trace_id, status FROM tasks WHERE request_id='acc_site_001'")
    a.check("phase1_db_task_written", len(rows) == 1 and rows[0]["trace_id"])

    deploy_before_ns = a.request("POST", f"/api/v1/sites/{site_id}/deployments", {"request_id": "acc_deploy_before_ns"})
    a.check("phase1_dns_not_propagated_error", deploy_before_ns["error"]["error_code"] == "DNS_NS_NOT_PROPAGATED" and deploy_before_ns["error"]["retryable"] is True and deploy_before_ns["error"]["user_action_required"] is True)

    a.ok("POST", "/api/v1/domains/acc.example.com/ns-check", {"request_id": "acc_ns_001"})
    deploy_1 = a.ok("POST", f"/api/v1/sites/{site_id}/deployments", {"request_id": "acc_deploy_001"})
    rollback_first = a.request("POST", f"/api/v1/deployments/{deploy_1['deployment']['deploy_id']}/rollback", {"request_id": "acc_rollback_no_previous"})
    rollback_missing = a.request("POST", "/api/v1/deployments/deploy_missing/rollback", {"request_id": "acc_rollback_missing"})
    deploy_2 = a.ok("POST", f"/api/v1/sites/{site_id}/deployments", {"request_id": "acc_deploy_002"})
    rollback_ok = a.ok("POST", f"/api/v1/deployments/{deploy_2['deployment']['deploy_id']}/rollback", {"request_id": "acc_rollback_001"})
    a.check("phase1_rollback_negative_paths", rollback_first["error"]["error_code"] == "DEPLOY_ROLLBACK_FAILED" and rollback_missing["error"]["error_code"] == "DEPLOY_ROLLBACK_FAILED")
    a.check("phase1_rollback_success", rollback_ok["deployment"]["status"] == "rollback_success")
    a.check("phase1_deploy_snapshot_db", a.db_scalar("SELECT COUNT(*) AS c FROM deployment_files") > 0)

    with sqlite3.connect(DB) as conn:
        conn.execute("UPDATE resource_locks SET status='locked', task_id='task_fake_running' WHERE resource_type='site' AND resource_id=?", (site_id,))
        conn.commit()
    lock_conflict = a.request("POST", f"/api/v1/sites/{site_id}/deployments", {"request_id": "acc_deploy_lock_conflict"})
    with sqlite3.connect(DB) as conn:
        conn.execute("UPDATE resource_locks SET status='released' WHERE resource_type='site' AND resource_id=?", (site_id,))
        conn.commit()
    a.check("phase1_lock_conflict_error", lock_conflict["error"]["error_code"] == "TASK_ALREADY_RUNNING")

    # Phase 2 positive and negative.
    article = a.ok("POST", f"/api/v1/sites/{site_id}/articles", {"request_id": "acc_article_001", "title": "Hello", "content": "World"})["article"]
    article_pub = a.ok("POST", f"/api/v1/articles/{article['article_id']}/publish", {"request_id": "acc_article_pub_001"})
    deploy_count_after_article = a.db_scalar("SELECT COUNT(*) AS c FROM deployments")
    article_pub_again = a.ok("POST", f"/api/v1/articles/{article['article_id']}/publish", {"request_id": "acc_article_pub_again"})
    deploy_count_after_article_again = a.db_scalar("SELECT COUNT(*) AS c FROM deployments")
    a.check("phase2_repeat_publish_no_extra_deploy", article_pub_again.get("no_op") is True and deploy_count_after_article == deploy_count_after_article_again)

    bad_price_codes = []
    for idx, value in enumerate(["abc", -1, 0, None, ""]):
        response = a.request("POST", f"/api/v1/sites/{site_id}/products", {"request_id": f"acc_product_bad_{idx}", "name": "Bad", "price": value})
        bad_price_codes.append(response["error"]["error_code"])
    product = a.ok("POST", f"/api/v1/sites/{site_id}/products", {"request_id": "acc_product_001", "name": "Shoe", "price": 9.99})["product"]
    product_pub = a.ok("POST", f"/api/v1/products/{product['product_id']}/publish", {"request_id": "acc_product_pub_001"})
    payment = a.ok("POST", f"/api/v1/sites/{site_id}/payments", {"request_id": "acc_payment_001", "payment_url": "https://pay.example.com/x"})["payment"]
    bind = a.ok("POST", f"/api/v1/products/{product['product_id']}/payment-bind", {"request_id": "acc_payment_bind_001", "payment_id": payment["payment_id"]})
    missing_bind = a.request("POST", "/api/v1/products/product_missing/payment-bind", {"request_id": "acc_payment_bind_missing", "payment_id": payment["payment_id"]})
    a.check("phase2_price_invalid_variants", all(code == "CMS_PRODUCT_PRICE_INVALID" for code in bad_price_codes), {"codes": bad_price_codes})
    a.check("phase2_publish_payment_positive", article_pub["article"]["status"] == "published" and product_pub["product"]["status"] == "active" and bind["product"]["payment_id"] == payment["payment_id"])
    a.check("phase2_payment_missing_product_error", missing_bind["error"]["error_code"] == "CMS_PRODUCT_NOT_FOUND")

    # Phase 3 positive, duplicate execute, retry after fixing source.
    bulk_root = setup_bulk(site_id, root_name="bulk_good")
    job = a.ok("POST", "/api/v1/bulk/jobs", {"request_id": "acc_bulk_job_001", "root_path": str(bulk_root)})["bulk_job"]
    scan = a.ok("POST", f"/api/v1/bulk/jobs/{job['bulk_job_id']}/scan", {"request_id": "acc_bulk_scan_001", "site_id": site_id})
    validate = a.ok("POST", f"/api/v1/bulk/jobs/{job['bulk_job_id']}/validate", {"request_id": "acc_bulk_validate_001", "site_id": site_id})
    execute = a.ok("POST", f"/api/v1/bulk/jobs/{job['bulk_job_id']}/execute", {"request_id": "acc_bulk_execute_001", "site_id": site_id})
    duplicate_execute = a.request("POST", f"/api/v1/bulk/jobs/{job['bulk_job_id']}/execute", {"request_id": "acc_bulk_execute_again", "site_id": site_id})
    before_retry_deploys = a.db_scalar("SELECT COUNT(*) AS c FROM deployments")
    retry_zero = a.ok("POST", f"/api/v1/bulk/jobs/{job['bulk_job_id']}/retry-failed", {"request_id": "acc_bulk_retry_zero", "site_id": site_id})
    after_retry_deploys = a.db_scalar("SELECT COUNT(*) AS c FROM deployments")
    a.check("phase3_bulk_positive", scan["total"] == 1 and validate["status"] == "validated" and execute["report"]["success"] >= 2)
    a.check("phase3_duplicate_execute_rejected", duplicate_execute["error"]["error_code"] == "BULK_VALIDATION_FAILED")
    a.check("phase3_retry_zero_no_deploy", retry_zero["retried"] == 0 and before_retry_deploys == after_retry_deploys)

    bad_bulk_root = setup_bulk(site_id, bad_price=True, root_name="bulk_bad_then_fix")
    bad_job = a.ok("POST", "/api/v1/bulk/jobs", {"request_id": "acc_bulk_bad_job", "root_path": str(bad_bulk_root)})["bulk_job"]
    a.ok("POST", f"/api/v1/bulk/jobs/{bad_job['bulk_job_id']}/scan", {"request_id": "acc_bulk_bad_scan", "site_id": site_id})
    bad_validate = a.ok("POST", f"/api/v1/bulk/jobs/{bad_job['bulk_job_id']}/validate", {"request_id": "acc_bulk_bad_validate", "site_id": site_id})
    (bad_bulk_root / site_id / "product.txt").write_text("name: Fixed Bulk Shoes\nprice: 29.99\nimages:\n- 1.jpg\n", encoding="utf-8")
    retry_fixed = a.ok("POST", f"/api/v1/bulk/jobs/{bad_job['bulk_job_id']}/retry-failed", {"request_id": "acc_bulk_bad_retry_fixed", "site_id": site_id})
    image_bad_root = setup_bulk(site_id, missing_image=True, root_name="bulk_missing_image")
    image_job = a.ok("POST", "/api/v1/bulk/jobs", {"request_id": "acc_bulk_image_job", "root_path": str(image_bad_root)})["bulk_job"]
    a.ok("POST", f"/api/v1/bulk/jobs/{image_job['bulk_job_id']}/scan", {"request_id": "acc_bulk_image_scan", "site_id": site_id})
    image_validate = a.ok("POST", f"/api/v1/bulk/jobs/{image_job['bulk_job_id']}/validate", {"request_id": "acc_bulk_image_validate", "site_id": site_id})
    source_hash_rows = a.db_query("SELECT source_hash, COUNT(*) AS c FROM bulk_items GROUP BY source_hash HAVING COUNT(*) > 1")
    a.check("phase3_retry_after_file_fix", bad_validate["errors"][0]["error_code"] == "BULK_PRODUCT_PRICE_INVALID" and retry_fixed["retried"] > 0)
    a.check("phase3_missing_image_error", any(e["error_code"] == "BULK_PRODUCT_IMAGE_NOT_FOUND" for e in image_validate["errors"]))
    a.check("phase3_source_hash_no_collision", len(source_hash_rows) == 0)

    # Phase 4 negative and positive.
    lang = a.ok("POST", f"/api/v1/sites/{site_id}/i18n/languages/es/enable", {"request_id": "acc_i18n_001"})
    page_fail = a.ok("POST", f"/api/v1/sites/{site_id}/pages", {"request_id": "acc_page_fail_001", "layout": {"blocks": [{"type": "Hero", "translations": {"en": {"title": "Home"}}}]}})["page"]
    incomplete_publish = a.request("POST", f"/api/v1/pages/{page_fail['page_id']}/publish", {"request_id": "acc_page_incomplete_i18n"})
    invalid_layout = a.request("POST", f"/api/v1/sites/{site_id}/pages", {"request_id": "acc_page_invalid_layout", "layout": {"blocks": [{"no_type": "bad"}]}})
    seo = a.client.patch(f"/api/v1/sites/{site_id}/seo", json={"request_id": "acc_seo_001", "title": "SEO Title", "description": "Desc"}).json()
    sitemap = a.request("GET", f"/api/v1/sites/{site_id}/sitemap")
    with sqlite3.connect(DB) as conn:
        conn.execute("UPDATE i18n_languages SET completion=100 WHERE site_id=? AND language_code='es'", (site_id,))
        conn.commit()
    page = a.ok("POST", f"/api/v1/sites/{site_id}/pages", {"request_id": "acc_page_001", "layout": {"blocks": [{"type": "Hero", "translations": {"en": {"title": "Home"}, "es": {"title": "Inicio"}}}]}})["page"]
    page_pub = a.ok("POST", f"/api/v1/pages/{page['page_id']}/publish", {"request_id": "acc_page_pub_001"})

    failed_task = a.db_query("SELECT task_id FROM tasks WHERE status='failed' LIMIT 1")[0]["task_id"]
    retry_res = a.ok("POST", f"/api/v1/tasks/{failed_task}/retry")
    pending = a.ok("POST", "/api/v1/tasks", {"request_id": "acc_manual_pending_001", "task_type": "manual_check"})
    cancel_res = a.ok("POST", f"/api/v1/tasks/{pending['task_id']}/cancel")
    delete_req = a.ok("POST", f"/api/v1/sites/{site_id}/delete-request", {"request_id": "acc_delete_request"})
    status = a.request("GET", "/api/v1/system/status")
    logs = a.request("GET", "/api/v1/system/logs")
    a.check("phase4_i18n_blocks_publish", incomplete_publish["error"]["error_code"] == "I18N_MISSING_TRANSLATION")
    a.check("phase4_invalid_layout_rejected", invalid_layout["error"]["error_code"] == "SYSTEM_INVALID_FORMAT")
    a.check("phase4_seo_sitemap_db", seo["seo"]["title"] == "SEO Title" and len(sitemap["sitemap"]) > 0)
    a.check("phase4_task_retry_cancel_confirm_gate", retry_res["status"] == "success" and cancel_res["status"] == "cancelled" and delete_req["status"] == "waiting_confirm")
    a.check("phase4_system_observability", status["sites"] >= 1 and len(logs["audit_logs"]) > 0)

    db_counts = {}
    for table in [
        "sites",
        "tasks",
        "task_logs",
        "deployments",
        "deployment_files",
        "audit_logs",
        "error_logs",
        "articles",
        "products",
        "payments",
        "bulk_jobs",
        "bulk_items",
        "bulk_errors",
        "seo_records",
        "pages",
    ]:
        db_counts[table] = a.db_scalar(f"SELECT COUNT(*) AS c FROM {table}")

    checks = a.evidence["checks"]
    result = {
        "checks": checks,
        "failed": len([c for c in checks if not c["pass"]]),
        "failed_checks": [c for c in checks if not c["pass"]],
        "db_counts": db_counts,
        "pass": all(c["pass"] for c in checks),
    }
    a.evidence["summary"] = result
    (ROOT / "reports" / "acceptance_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "reports" / "acceptance_evidence.json").write_text(json.dumps(a.evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
