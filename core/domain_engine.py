import subprocess

from sqlalchemy.orm import Session

from core.audit_engine import AuditEngine
from core.errors import AppException
from core.models import Domain
from core.utils import model_dict, new_id, now_iso
from integrations.cloudflare import CloudflareIntegration


class DomainEngine:
    def __init__(self) -> None:
        self.audit = AuditEngine()
        self.cloudflare = CloudflareIntegration()

    def create_zone(self, db: Session, *, site_id: str, domain: str, trace_id: str, request_id: str, task_id: str, owner_user_id: str | None = None, is_public_pool: int = 0, domain_mode: str = "custom_domain", parent_domain: str | None = None) -> Domain:
        if not domain or "." not in domain:
            raise AppException("DNS_DOMAIN_INVALID", details={"domain": domain})
        existing = db.query(Domain).filter(Domain.domain == domain).first()
        if existing:
            return existing
        zone = self.cloudflare.create_zone(domain)
        nameservers = zone.get("nameservers") or []
        now = now_iso()
        row = Domain(
            domain_id=new_id("domain"),
            site_id=site_id,
            owner_user_id=owner_user_id,
            is_public_pool=is_public_pool,
            domain_mode=domain_mode,
            parent_domain=parent_domain,
            full_domain=domain,
            domain=domain,
            cloudflare_zone_id=zone.get("zone_id") or new_id("zone"),
            ns1=nameservers[0] if len(nameservers) > 0 else None,
            ns2=nameservers[1] if len(nameservers) > 1 else None,
            status="pending_ns",
            ssl_status="pending",
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.commit()
        self.audit.record(
            db,
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            action="domain.cloudflare_zone.create",
            resource_type="domain",
            resource_id=row.domain_id,
            after=model_dict(row),
        )
        return row

    def get_by_domain(self, db: Session, domain: str) -> Domain:
        row = db.query(Domain).filter(Domain.domain == domain).first()
        if not row:
            raise AppException("DNS_DOMAIN_INVALID", details={"domain": domain})
        return row

    def check_ns(self, db: Session, *, domain: str, trace_id: str, request_id: str | None = None, task_id: str | None = None) -> Domain:
        row = self.get_by_domain(db, domain)
        actual_ns = self.resolve_ns(domain)
        expected = {value.lower().rstrip(".") for value in [row.ns1, row.ns2] if value}
        actual = {value.lower().rstrip(".") for value in actual_ns}
        if not actual:
            row.status = "pending_ns"
            row.ssl_status = "pending"
            row.last_checked_at = now_iso()
            row.updated_at = now_iso()
            db.commit()
            raise AppException("DNS_NS_NOT_PROPAGATED", details={"domain": domain, "actual_ns": []}, trace_id=trace_id, request_id=request_id, task_id=task_id)
        if expected and not expected.issubset(actual):
            row.status = "ns_mismatch"
            row.ssl_status = "pending"
            row.last_checked_at = now_iso()
            row.updated_at = now_iso()
            db.commit()
            raise AppException("DNS_VERIFICATION_FAILED", details={"domain": domain, "expected_ns": sorted(expected), "actual_ns": sorted(actual)}, trace_id=trace_id, request_id=request_id, task_id=task_id)
        row.status = "ns_verified"
        row.ssl_status = "active"
        row.last_checked_at = now_iso()
        row.updated_at = now_iso()
        db.commit()
        self.audit.record(
            db,
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            action="domain.ns_check",
            resource_type="domain",
            resource_id=row.domain_id,
            after=model_dict(row),
        )
        return row

    def resolve_ns(self, domain: str) -> list[str]:
        if self.cloudflare.mode != "real":
            return list(self.cloudflare.create_zone(domain).get("nameservers") or [])
        try:
            result = subprocess.run(
                ["nslookup", "-type=ns", domain],
                capture_output=True,
                text=True,
                timeout=8,
            )
        except Exception:
            return []
        nameservers: list[str] = []
        for line in (result.stdout + "\n" + result.stderr).splitlines():
            text = line.strip()
            lower = text.lower()
            if "nameserver =" in lower:
                nameservers.append(text.split("=", 1)[1].strip().rstrip("."))
            elif "nameserver" in lower and len(text.split()) >= 2:
                nameservers.append(text.split()[-1].strip().rstrip("."))
        return sorted(set(nameservers))

    def require_ready_for_deploy(self, db: Session, site_id: str) -> None:
        domains = db.query(Domain).filter(Domain.site_id == site_id).all()
        if domains and not any(d.status in {"verified", "dns_ready", "ns_verified", "active", "github_bound"} for d in domains):
            raise AppException("DNS_NS_NOT_PROPAGATED", details={"site_id": site_id})
