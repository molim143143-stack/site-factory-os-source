from sqlalchemy.orm import Session
from pathlib import Path

from config import BASE_DIR
from core.models import BulkError, BulkItem, BulkJob
from core.utils import model_dict, to_json


class BulkReporter:
    def report(self, db: Session, bulk_job_id: str) -> dict:
        job = db.get(BulkJob, bulk_job_id)
        if not job:
            return {"error": "bulk job not found"}
        items = db.query(BulkItem).filter(BulkItem.bulk_job_id == bulk_job_id).all()
        errors = db.query(BulkError).filter(BulkError.bulk_job_id == bulk_job_id).all()
        report = {
            "bulk_job_id": bulk_job_id,
            "task_id": job.task_id,
            "status": job.status,
            "total": len(items),
            "success": len([i for i in items if i.status in {"execute_success", "retry_success"}]),
            "failed": len([i for i in items if i.status in {"validation_failed", "execute_failed", "retry_failed"}]),
            "items": [model_dict(i) for i in items],
            "errors": [model_dict(e) for e in errors],
        }
        reports_dir = BASE_DIR / "reports"
        reports_dir.mkdir(exist_ok=True)
        (reports_dir / "bulk_result.json").write_text(to_json(report), encoding="utf-8")
        return report
