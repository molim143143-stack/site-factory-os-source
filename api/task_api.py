from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.errors import AppException
from core.models import Task, TaskLog
from core.task_engine import TaskEngine
from core.utils import model_dict

router = APIRouter(prefix="/api/v1")
tasks = TaskEngine()


@router.post("/tasks")
def create_task(data: dict, db: Session = Depends(get_db)):
    if not data.get("request_id") or not data.get("task_type"):
        raise AppException("SYSTEM_MISSING_FIELD", details={"required": ["request_id", "task_type"]})
    task, created = tasks.create_task(db, request_id=data["request_id"], task_type=data["task_type"], payload=data, site_id=data.get("site_id"))
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created}


@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    return {"items": [model_dict(t) for t in db.query(Task).order_by(Task.created_at.desc()).all()]}


@router.get("/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise AppException("TASK_NOT_FOUND", details={"task_id": task_id})
    return model_dict(task)


@router.get("/tasks/{task_id}/logs")
def task_logs(task_id: str, db: Session = Depends(get_db)):
    return {"items": [model_dict(l) for l in db.query(TaskLog).filter(TaskLog.task_id == task_id).all()]}


@router.post("/tasks/{task_id}/retry")
def retry_task(task_id: str, db: Session = Depends(get_db)):
    return model_dict(tasks.retry(db, task_id))


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str, db: Session = Depends(get_db)):
    return model_dict(tasks.cancel(db, task_id))


@router.post("/tasks/{task_id}/confirm")
def confirm_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise AppException("TASK_NOT_FOUND", details={"task_id": task_id})
    if task.status != "waiting_confirm":
        raise AppException("TASK_INVALID_STATUS", details={"status": task.status})
    tasks.set_status(db, task, "running", node_name="ConfirmNode", message="task confirmed")
    tasks.set_status(db, task, "success", node_name="ConfirmNode", message="confirmed operation completed")
    return model_dict(task)
