from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import APP_VERSION
from core.database import get_db
from core.models import AuditLog, ErrorLog
from core.system_engine import SystemEngine
from core.utils import model_dict

router = APIRouter(prefix="/api/v1")
system = SystemEngine()


@router.get("/system/health")
def health():
    return {"status": "running"}


@router.get("/system/status")
def status(db: Session = Depends(get_db)):
    return system.status(db)


@router.get("/system/version")
def version():
    return {"version": APP_VERSION}


@router.get("/system/logs")
def logs(db: Session = Depends(get_db)):
    return system.logs(db)


@router.get("/errors")
def errors(db: Session = Depends(get_db)):
    items = []
    for e in db.query(ErrorLog).order_by(ErrorLog.created_at.desc()).all():
        row = model_dict(e)
        row["code"] = row.get("error_code")
        row["priority"] = {"CRITICAL": "P0", "ERROR": "P1", "WARNING": "P2", "INFO": "P3"}.get(row.get("severity"), "P4")
        items.append(row)
    return {"items": items}


@router.get("/errors/{error_id}")
def error(error_id: str, db: Session = Depends(get_db)):
    return model_dict(db.get(ErrorLog, error_id))


@router.post("/errors/{error_id}/retry")
def retry_error(error_id: str):
    return {"error_id": error_id, "retry": "scheduled"}


@router.get("/errors/export")
def export_errors(db: Session = Depends(get_db)):
    return errors(db)


@router.get("/audit-logs")
def audit_logs(db: Session = Depends(get_db)):
    return {"items": [model_dict(a) for a in db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()]}


@router.get("/audit-logs/{trace_id}")
def audit_by_trace(trace_id: str, db: Session = Depends(get_db)):
    return {"items": [model_dict(a) for a in db.query(AuditLog).filter(AuditLog.trace_id == trace_id).all()]}
