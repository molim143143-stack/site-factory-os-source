import json
from pathlib import Path

from core.models import Domain, Site


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    site_columns = {col.name for col in Site.__table__.columns}
    domain_columns = {col.name for col in Domain.__table__.columns}
    checks = {
        "site_has_created_by": "created_by" in site_columns,
        "site_has_public_url": "public_url" in site_columns,
        "domain_has_owner_user_id": "owner_user_id" in domain_columns,
        "domain_has_is_public_pool": "is_public_pool" in domain_columns,
        "domain_has_domain_mode": "domain_mode" in domain_columns,
        "api_user_filtering_enforced": False,
        "public_pool_allocation_api": False,
        "super_admin_domain_admin_api": False,
    }
    report = {
        "status": "PARTIAL" if all(checks[key] for key in ["site_has_created_by", "site_has_public_url", "domain_has_owner_user_id", "domain_has_is_public_pool", "domain_has_domain_mode"]) else "FAIL",
        "checks": checks,
        "failed": [key for key, value in checks.items() if not value],
        "note": "Schema fields for owner/public pool were added, but full API-level user isolation and allocation flows still need implementation.",
    }
    (REPORTS / "domain_isolation_acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed": report["failed"], "report": str(REPORTS / "domain_isolation_acceptance.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
