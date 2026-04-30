from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.errors import require_fields
from core.seo_engine import SeoEngine
from core.task_engine import TaskEngine
from core.utils import model_dict

router = APIRouter(prefix="/api/v1")
seo = SeoEngine()
tasks = TaskEngine()


@router.get("/sites/{site_id}/seo")
def get_site_seo(site_id: str, db: Session = Depends(get_db)):
    return seo.sitemap(db, site_id)


@router.patch("/sites/{site_id}/seo")
def patch_site_seo(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id", "title"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="seo_update", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: {"seo": model_dict(seo.update_site_seo(db, site_id, data))}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.patch("/pages/{page_id}/seo")
@router.patch("/articles/{page_id}/seo")
@router.patch("/products/{page_id}/seo")
def patch_entity_seo(page_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id", "site_id", "title"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="seo_entity_update", payload=data, site_id=data["site_id"], trace_id=request.state.trace_id, action=lambda task: {"seo": model_dict(seo.update_site_seo(db, data["site_id"], data))}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/sites/{site_id}/seo/validate")
def validate_seo(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="seo_validate", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: {"valid": True, **seo.sitemap(db, site_id)}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/sites/{site_id}/sitemap/generate")
def generate_sitemap(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="sitemap_generate", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: seo.sitemap(db, site_id), lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.get("/sites/{site_id}/sitemap")
def sitemap(site_id: str, db: Session = Depends(get_db)):
    return seo.sitemap(db, site_id)
