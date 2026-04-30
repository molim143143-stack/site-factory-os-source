from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.errors import require_fields
from core.f4_bulk_engine import BulkEngine
from core.models import BulkJob
from core.task_engine import TaskEngine
from core.utils import model_dict

router = APIRouter(prefix="/api/v1")
bulk = BulkEngine()
tasks = TaskEngine()


@router.post("/bulk/jobs")
def create_bulk_job(data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id", "root_path"], data.get("request_id"), request.state.trace_id)

    def action(task):
        job = bulk.create_job(db, task=task, root_path=data["root_path"])
        return {"bulk_job": model_dict(job)}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="bulk_job_create", payload=data, site_id=None, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/bulk/jobs/{bulk_job_id}/scan")
def scan_bulk(bulk_job_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="bulk_scan", payload=data, site_id=data.get("site_id"), trace_id=request.state.trace_id, action=lambda task: bulk.scan(db, task=task, bulk_job_id=bulk_job_id), lock=True if data.get("site_id") else False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/bulk/jobs/{bulk_job_id}/validate")
def validate_bulk(bulk_job_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="bulk_validate", payload=data, site_id=data.get("site_id"), trace_id=request.state.trace_id, action=lambda task: bulk.validate(db, task=task, bulk_job_id=bulk_job_id), lock=True if data.get("site_id") else False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/bulk/jobs/{bulk_job_id}/preview")
def preview_bulk(bulk_job_id: str, data: dict | None = None, db: Session = Depends(get_db)):
    return bulk.preview(db, bulk_job_id=bulk_job_id)


@router.post("/bulk/jobs/{bulk_job_id}/execute")
def execute_bulk(bulk_job_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    job = db.get(BulkJob, bulk_job_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="bulk_execute", payload=data, site_id=data.get("site_id"), trace_id=request.state.trace_id, action=lambda task: bulk.execute(db, task=task, bulk_job_id=bulk_job_id), lock=True if data.get("site_id") else False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "bulk_job_id": job.bulk_job_id if job else bulk_job_id, "idempotent": not created, **result}


@router.post("/bulk/jobs/{bulk_job_id}/retry-failed")
def retry_bulk(bulk_job_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="bulk_retry", payload=data, site_id=data.get("site_id"), trace_id=request.state.trace_id, action=lambda task: bulk.retry_failed(db, task=task, bulk_job_id=bulk_job_id), lock=True if data.get("site_id") else False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.get("/bulk/jobs/{bulk_job_id}")
def get_bulk_job(bulk_job_id: str, db: Session = Depends(get_db)):
    return model_dict(db.get(BulkJob, bulk_job_id))


@router.get("/bulk/jobs/{bulk_job_id}/items")
def bulk_items(bulk_job_id: str, db: Session = Depends(get_db)):
    return bulk.preview(db, bulk_job_id=bulk_job_id)["items"]


@router.get("/bulk/jobs/{bulk_job_id}/report")
def bulk_report(bulk_job_id: str, db: Session = Depends(get_db)):
    return bulk.preview(db, bulk_job_id=bulk_job_id)


@router.get("/bulk/jobs/{bulk_job_id}/errors")
def bulk_errors(bulk_job_id: str, db: Session = Depends(get_db)):
    return {"errors": bulk.preview(db, bulk_job_id=bulk_job_id)["errors"]}
