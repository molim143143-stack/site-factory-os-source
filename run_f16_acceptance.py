import json
import shutil
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from core.database import init_db
from main import app


ROOT = Path(__file__).resolve().parent
DB = ROOT / "storage" / "site_factory_os.db"


class F16Acceptance:
    def __init__(self) -> None:
        self.client = TestClient(app)
        self.evidence = {"api": [], "db": [], "checks": []}

    def request(self, method: str, url: str, payload: dict | None = None) -> dict:
        response = self.client.request(method, url, json=payload)
        body = response.json()
        self.evidence["api"].append({"method": method, "url": url, "payload": payload, "status_code": response.status_code, "response": body})
        return body

    def ok(self, method: str, url: str, payload: dict | None = None) -> dict:
        body = self.request(method, url, payload)
        assert self.evidence["api"][-1]["status_code"] < 400, self.evidence["api"][-1]
        return body

    def db_query(self, sql: str) -> list[dict]:
        with sqlite3.connect(DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = [dict(row) for row in conn.execute(sql).fetchall()]
        self.evidence["db"].append({"sql": sql, "rows": rows[:20], "row_count": len(rows)})
        return rows

    def check(self, name: str, passed: bool, details: dict | None = None) -> None:
        self.evidence["checks"].append({"name": name, "pass": bool(passed), "details": details or {}})


def reset() -> None:
    if DB.exists():
        DB.unlink()
    init_db()
    bulk_root = ROOT / "sample_data" / "f16_bulk"
    if bulk_root.exists():
        shutil.rmtree(bulk_root)
    bulk_root.mkdir(parents=True)


def run() -> None:
    reset()
    a = F16Acceptance()
    user = a.ok("POST", "/api/v1/auth/register", {"username": "alice", "password": "pw123", "email": "alice@example.com", "trial_days": 1})
    user_id = user["user"]["user_id"]
    login_bad = a.request("POST", "/api/v1/auth/login", {"username": "alice", "password": "bad"})
    login_ok = a.ok("POST", "/api/v1/auth/login", {"username": "alice", "password": "pw123"})
    plans = a.ok("GET", "/api/v1/membership/plans")
    a.check("auth_login_and_three_plans", login_bad["error"]["error_code"] == "AUTH_LOGIN_FAILED" and login_ok["portal_boot"] == "Portal Boot Sequence" and [p["plan"] for p in plans["plans"]] == ["trial", "pro", "enterprise"])

    site1 = a.ok("POST", "/api/v1/sites", {"request_id": "f16_site_1", "domain": "trial-one.example.com", "alias": "Trial One", "user_id": user_id})
    site2 = a.request("POST", "/api/v1/sites", {"request_id": "f16_site_2", "domain": "trial-two.example.com", "alias": "Trial Two", "user_id": user_id})
    bulk_denied = a.request("POST", "/api/v1/bulk/jobs", {"request_id": "f16_bulk_denied", "root_path": str(ROOT / "sample_data" / "f16_bulk"), "user_id": user_id})
    a.check("trial_limits_enforced", site1["site"]["site_id"].startswith("site_") and site2["error"]["error_code"] == "MEMBERSHIP_PLAN_LIMIT_REACHED" and bulk_denied["error"]["error_code"] == "MEMBERSHIP_FEATURE_NOT_ALLOWED")

    device1 = a.ok("POST", "/api/v1/membership/devices/bind", {"user_id": user_id, "device_fingerprint": "device-a", "label": "Laptop"})
    device2 = a.request("POST", "/api/v1/membership/devices/bind", {"user_id": user_id, "device_fingerprint": "device-b", "label": "Phone"})
    a.check("trial_device_limit", device1["device"]["status"] == "active" and device2["error"]["error_code"] == "DEVICE_LIMIT_REACHED")

    service = a.ok("POST", "/api/v1/membership/service-requests", {"request_id": "open_req_001", "user_id": user_id, "target_plan": "pro", "contact_method": "telegram", "contact_value": "@alice", "note": "用户想开通30天Pro"})
    paid = a.ok("POST", "/api/v1/admin/billing/service-requests/open_req_001/mark-paid", {"admin_id": "admin_001", "note": "offline paid"})
    activated = a.ok("POST", "/api/v1/admin/billing/service-requests/open_req_001/activate", {"admin_id": "admin_001", "duration_days": 30})
    a.check("customer_service_manual_activation", service["request"]["status"] == "pending" and paid["request"]["status"] == "paid" and activated["request"]["status"] == "activated" and activated["membership"]["plan"] == "pro")

    device2_after_pro = a.ok("POST", "/api/v1/membership/devices/bind", {"user_id": user_id, "device_fingerprint": "device-b", "label": "Phone"})
    bulk_allowed = a.ok("POST", "/api/v1/bulk/jobs", {"request_id": "f16_bulk_allowed", "root_path": str(ROOT / "sample_data" / "f16_bulk"), "user_id": user_id})
    a.check("pro_features_enabled", device2_after_pro["device"]["status"] == "active" and bulk_allowed["bulk_job"]["status"] == "created")

    license_row = a.ok("POST", "/api/v1/admin/billing/license-codes", {"plan": "enterprise", "duration_days": 30, "created_by": "admin_001", "code_type": "ENTERPRISE-30D"})
    code = license_row["license"]["code"]
    license_activation = a.ok("POST", "/api/v1/membership/license-codes/activate", {"user_id": user_id, "code": code})
    license_reuse = a.request("POST", "/api/v1/membership/license-codes/activate", {"user_id": user_id, "code": code})
    license_invalid = a.request("POST", "/api/v1/membership/license-codes/activate", {"user_id": user_id, "code": "BAD-CODE"})
    a.check("license_activation_and_reuse_errors", license_activation["membership"]["plan"] == "enterprise" and license_reuse["error"]["error_code"] == "LICENSE_CODE_USED" and license_invalid["error"]["error_code"] == "LICENSE_CODE_INVALID")

    counts = {
        "users": len(a.db_query("SELECT * FROM users")),
        "memberships": len(a.db_query("SELECT * FROM memberships")),
        "customer_service_requests": len(a.db_query("SELECT * FROM customer_service_requests")),
        "license_codes": len(a.db_query("SELECT * FROM license_codes")),
        "device_bindings": len(a.db_query("SELECT * FROM device_bindings")),
        "task_logs_with_membership": len(a.db_query("SELECT * FROM task_logs WHERE node_name IN ('AuthNode','MembershipNode','QuotaNode','PermissionNode')")),
        "error_logs": len(a.db_query("SELECT * FROM error_logs")),
    }
    a.check("sqlite_membership_tables_written", counts["users"] == 1 and counts["memberships"] == 1 and counts["customer_service_requests"] == 1 and counts["license_codes"] == 1 and counts["device_bindings"] == 2 and counts["task_logs_with_membership"] > 0)

    result = {"checks": a.evidence["checks"], "failed": len([c for c in a.evidence["checks"] if not c["pass"]]), "failed_checks": [c for c in a.evidence["checks"] if not c["pass"]], "db_counts": counts}
    result["pass"] = result["failed"] == 0
    a.evidence["summary"] = result
    (ROOT / "reports" / "f16_acceptance_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "reports" / "f16_acceptance_evidence.json").write_text(json.dumps(a.evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
