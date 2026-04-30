from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.errors import require_fields
from core.i18n_engine import I18nEngine
from core.task_engine import TaskEngine
from core.utils import model_dict

router = APIRouter(prefix="/api/v1")
i18n = I18nEngine()
tasks = TaskEngine()


@router.get("/sites/{site_id}/i18n")
def get_i18n(site_id: str, db: Session = Depends(get_db)):
    return i18n.get_site_i18n(db, site_id)


@router.patch("/sites/{site_id}/i18n")
def patch_i18n(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="i18n_update", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: i18n.status(db, site_id), lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/sites/{site_id}/i18n/languages/{language_code}/enable")
def enable_language(site_id: str, language_code: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="i18n_enable", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: {"language": model_dict(i18n.enable(db, site_id, language_code))}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/sites/{site_id}/i18n/languages/{language_code}/disable")
def disable_language(site_id: str, language_code: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="i18n_disable", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: {"status": "disabled", "language_code": language_code}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.get("/sites/{site_id}/i18n/status")
def i18n_status(site_id: str, db: Session = Depends(get_db)):
    return i18n.status(db, site_id)


@router.get("/sites/{site_id}/i18n/missing-fields")
def i18n_missing(site_id: str, db: Session = Depends(get_db)):
    return i18n.status(db, site_id)["missing_fields"]


@router.post("/sites/{site_id}/i18n/generate")
def i18n_generate(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="i18n_generate", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: {"generated": True, **i18n.status(db, site_id)}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/sites/{site_id}/i18n/validate")
def i18n_validate(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="i18n_validate", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: i18n.status(db, site_id), lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}
