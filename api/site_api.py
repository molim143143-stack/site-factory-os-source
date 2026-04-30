from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.build_engine import BuildEngine
from core.database import get_db
from core.errors import require_fields
from core.models import Site, SiteAlias
from core.site_manager import SiteManager
from core.task_engine import TaskEngine
from core.utils import model_dict

router = APIRouter(prefix="/api/v1")
tasks = TaskEngine()
builder = BuildEngine()
sites = SiteManager()


@router.post("/sites")
def create_site(data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id", "domain", "alias"], data.get("request_id"), request.state.trace_id)
    request_id = data["request_id"]

    def action(task):
        return builder.create_site_workflow(db, task=task, payload=data)

    task, result, created = tasks.run(db, request_id=request_id, task_type="build_site", payload=data, site_id=None, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **(result if isinstance(result, dict) else {})}


@router.get("/sites")
def list_sites(db: Session = Depends(get_db)):
    return {"items": [model_dict(s) for s in sites.list_sites(db)]}


@router.get("/sites/{site_id}")
def get_site(site_id: str, db: Session = Depends(get_db)):
    return model_dict(sites.get_site(db, site_id))


@router.patch("/sites/{site_id}")
def patch_site(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    site = sites.get_site(db, site_id)

    def action(task):
        for field in ("alias", "description", "status", "theme_id"):
            if field in data:
                setattr(site, field, data[field])
        db.commit()
        return {"site": model_dict(site)}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="site_update", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/sites/{site_id}/clone")
def clone_site(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    source = sites.get_site(db, site_id)
    payload = {**data, "domain": data["domain"], "alias": data["alias"], "site_type": source.site_type, "template_id": source.template_id}
    require_fields(payload, ["request_id", "domain", "alias"], payload.get("request_id"), request.state.trace_id)
    return create_site(payload, request, db)


@router.post("/sites/{site_id}/pause")
def pause_site(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="site_pause", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: {"site": model_dict(sites.update_status(db, site_id, "inactive"))}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/sites/{site_id}/resume")
def resume_site(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="site_resume", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: {"site": model_dict(sites.update_status(db, site_id, "active"))}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/sites/{site_id}/archive")
def archive_site(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="site_archive", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: {"site": model_dict(sites.update_status(db, site_id, "archived"))}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/sites/{site_id}/delete-request")
def delete_request(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, created = tasks.create_task(
        db,
        request_id=data["request_id"],
        task_type="site_delete_request",
        payload=data,
        trace_id=request.state.trace_id,
        site_id=site_id,
    )
    if created:
        tasks.set_status(
            db,
            task,
            "waiting_confirm",
            node_name="ConfirmNode",
            message="delete requires confirmation",
            result={"site_id": site_id, "status": "waiting_confirm"},
        )
    return {"task_id": task.task_id, "trace_id": task.trace_id, "status": task.status, "idempotent": not created}


@router.post("/sites/{site_id}/delete-confirm")
def delete_confirm(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="site_delete_confirm", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: {"site": model_dict(sites.update_status(db, site_id, "deleted"))}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/sites/{site_id}/aliases")
def add_alias(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id", "alias"], data.get("request_id"), request.state.trace_id)
    sites.get_site(db, site_id)

    def action(task):
        row = SiteAlias(alias_id=f"alias_{task.task_id[-8:]}", site_id=site_id, alias=data["alias"], keywords=data.get("keywords", data["alias"]), created_at=task.created_at)
        db.add(row)
        db.commit()
        return {"alias": model_dict(row)}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="alias_create", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.get("/aliases/search")
def search_aliases(q: str = "", db: Session = Depends(get_db)):
    rows = db.query(SiteAlias).filter(SiteAlias.alias.contains(q)).all()
    return {"items": [model_dict(r) for r in rows]}


@router.get("/aliases/{alias}")
def get_alias(alias: str, db: Session = Depends(get_db)):
    row = db.query(SiteAlias).filter(SiteAlias.alias == alias).first()
    return {"alias": model_dict(row) if row else None}
