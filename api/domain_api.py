from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.domain_engine import DomainEngine
from core.errors import require_fields
from core.models import Domain
from core.task_engine import TaskEngine
from core.utils import model_dict

router = APIRouter(prefix="/api/v1")
domains = DomainEngine()
tasks = TaskEngine()


@router.post("/sites/{site_id}/domains")
def add_domain(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id", "domain"], data.get("request_id"), request.state.trace_id)

    def action(task):
        row = domains.create_zone(
            db,
            site_id=site_id,
            domain=data["domain"],
            trace_id=task.trace_id,
            request_id=task.request_id,
            task_id=task.task_id,
            owner_user_id=data.get("user_id"),
            is_public_pool=int(bool(data.get("is_public_pool", 0))),
            domain_mode=data.get("domain_mode", "custom_domain"),
            parent_domain=data.get("parent_domain"),
        )
        return {"domain": model_dict(row), "ns": [row.ns1, row.ns2]}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="domain_create", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.get("/sites/{site_id}/domains")
def site_domains(site_id: str, db: Session = Depends(get_db)):
    rows = db.query(Domain).filter(Domain.site_id == site_id).all()
    return {"items": [model_dict(r) for r in rows]}


@router.get("/domains/{domain}/status")
def domain_status(domain: str, db: Session = Depends(get_db)):
    return model_dict(domains.get_by_domain(db, domain))


@router.post("/domains/{domain}/cloudflare-zone")
def cloudflare_zone(domain: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id", "site_id"], data.get("request_id"), request.state.trace_id)
    return add_domain(data["site_id"], {**data, "domain": domain}, request, db)


@router.post("/domains/{domain}/ns-check")
def ns_check(domain: str, data: dict | None = None, request: Request = None, db: Session = Depends(get_db)):
    data = data or {}
    request_id = data.get("request_id", f"ns_check_{domain}")
    row = domains.get_by_domain(db, domain)

    def action(task):
        checked = domains.check_ns(db, domain=domain, trace_id=task.trace_id, request_id=task.request_id, task_id=task.task_id)
        return {"domain": model_dict(checked)}

    task, result, created = tasks.run(db, request_id=request_id, task_type="dns_check", payload=data, site_id=row.site_id, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/domains/{domain}/dns-records")
def dns_records(domain: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    row = domains.get_by_domain(db, domain)
    def action(task):
        record = domains.cloudflare.create_record(
            row.cloudflare_zone_id,
            data.get("record_type", data.get("type", "CNAME")),
            data.get("name", domain),
            data.get("content", data.get("value", domain)),
        )
        return {"domain": model_dict(row), "record": record}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="dns_record_create", payload=data, site_id=row.site_id, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/domains/{domain}/github-pages-bind")
def github_pages_bind(domain: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    row = domains.get_by_domain(db, domain)

    def action(task):
        row.status = "github_bound"
        db.commit()
        return {"domain": model_dict(row)}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="github_pages_bind", payload=data, site_id=row.site_id, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/domains/{domain}/ssl-check")
def ssl_check(domain: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    row = domains.get_by_domain(db, domain)

    def action(task):
        status = domains.cloudflare.zone_status(row.cloudflare_zone_id)
        row.ssl_status = status.get("ssl", "active")
        db.commit()
        return {"domain": model_dict(row), "cloudflare": status}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="ssl_check", payload=data, site_id=row.site_id, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}
