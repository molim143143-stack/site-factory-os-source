from pathlib import Path

from sqlalchemy.orm import Session

from core.bulk_executor import BulkExecutor
from core.bulk_parser import load_site_folder, source_hash
from core.bulk_reporter import BulkReporter
from core.bulk_validator import BulkValidator
from core.errors import AppException
from core.models import BulkError, BulkItem, BulkJob
from core.task_engine import TaskEngine
from core.utils import model_dict, new_id, now_iso, to_json


class BulkEngine:
    def __init__(self) -> None:
        self.validator = BulkValidator()
        self.executor = BulkExecutor()
        self.reporter = BulkReporter()
        self.tasks = TaskEngine()

    def create_job(self, db: Session, *, task, root_path: str) -> BulkJob:
        path = Path(root_path)
        if not path.exists() or not path.is_dir():
            raise AppException("BULK_FOLDER_INVALID", details={"root_path": root_path})
        now = now_iso()
        job = BulkJob(
            bulk_job_id=new_id("bulk"),
            task_id=task.task_id,
            request_id=task.request_id,
            trace_id=task.trace_id,
            root_path=str(path),
            status="created",
            created_at=now,
            updated_at=now,
        )
        db.add(job)
        db.commit()
        return job

    def scan(self, db: Session, *, task, bulk_job_id: str) -> dict:
        job = db.get(BulkJob, bulk_job_id)
        if not job:
            raise AppException("BULK_FOLDER_INVALID", details={"bulk_job_id": bulk_job_id})
        root = Path(job.root_path)
        folders = [p for p in root.iterdir() if p.is_dir()]
        job.status = "scanned"
        job.total_items = len(folders)
        job.updated_at = now_iso()
        db.commit()
        return {"bulk_job_id": bulk_job_id, "folders": [str(f) for f in folders], "total": len(folders)}

    def validate(self, db: Session, *, task, bulk_job_id: str) -> dict:
        job = db.get(BulkJob, bulk_job_id)
        if not job:
            raise AppException("BULK_FOLDER_INVALID", details={"bulk_job_id": bulk_job_id})
        db.query(BulkError).filter(BulkError.bulk_job_id == bulk_job_id).delete()
        db.query(BulkItem).filter(BulkItem.bulk_job_id == bulk_job_id).delete()
        errors = []
        total = 0
        for folder in [p for p in Path(job.root_path).iterdir() if p.is_dir()]:
            payload = load_site_folder(folder)
            site_errors = self.validator.validate_site_payload(db, payload)
            config = payload["config"] or {}
            site_id = config.get("site_id", folder.name)
            for item_type, content, file_path in (
                ("product", payload["product"], payload["product_path"]),
                ("article", payload["article"], payload["article_path"]),
            ):
                if content:
                    total += 1
                    item_hash = source_hash(site_id, item_type, str(file_path), 1, content)
                    item_status = "validation_failed" if site_errors else "ready_execute"
                    db.add(
                        BulkItem(
                            bulk_item_id=new_id("bitem"),
                            bulk_job_id=bulk_job_id,
                            site_id=site_id,
                            item_type=item_type,
                            operation="upsert",
                            source_file=str(file_path),
                            source_line=1,
                            source_hash=item_hash,
                            language_code=config.get("language_code", "en"),
                            status=item_status,
                            error_code=site_errors[0]["error_code"] if site_errors else None,
                            error_message=site_errors[0]["message"] if site_errors else None,
                            created_at=now_iso(),
                            updated_at=now_iso(),
                        )
                    )
            for err in site_errors:
                errors.append(err)
                db.add(
                    BulkError(
                        bulk_error_id=new_id("berr"),
                        bulk_job_id=bulk_job_id,
                        error_code=err["error_code"],
                        message=err["message"],
                        file=err.get("file"),
                        line=err.get("line"),
                        field=err.get("field"),
                        details_json=to_json(err),
                        created_at=now_iso(),
                    )
                )
        job.total_items = total
        job.failed_items = len(errors)
        job.success_items = 0
        job.status = "validation_failed" if errors else "validated"
        job.updated_at = now_iso()
        db.commit()
        return {"bulk_job_id": bulk_job_id, "status": job.status, "errors": errors, "total": total}

    def preview(self, db: Session, *, bulk_job_id: str) -> dict:
        return self.reporter.report(db, bulk_job_id)

    def execute(self, db: Session, *, task, bulk_job_id: str) -> dict:
        job = db.get(BulkJob, bulk_job_id)
        if not job:
            raise AppException("BULK_FOLDER_INVALID", details={"bulk_job_id": bulk_job_id})
        if job.status != "validated":
            raise AppException("BULK_VALIDATION_FAILED", details={"bulk_job_id": bulk_job_id, "status": job.status})
        results = []
        for folder in [p for p in Path(job.root_path).iterdir() if p.is_dir()]:
            payload = load_site_folder(folder)
            results.append(self.executor.execute_payload(db, task=task, payload=payload, bulk_job_id=bulk_job_id))
        job.status = "executed"
        job.success_items = db.query(BulkItem).filter(BulkItem.bulk_job_id == bulk_job_id, BulkItem.status == "execute_success").count()
        job.failed_items = db.query(BulkItem).filter(BulkItem.bulk_job_id == bulk_job_id, BulkItem.status.in_(["validation_failed", "execute_failed"])).count()
        job.updated_at = now_iso()
        db.commit()
        return {"bulk_job_id": bulk_job_id, "results": results, "report": self.reporter.report(db, bulk_job_id)}

    def retry_failed(self, db: Session, *, task, bulk_job_id: str) -> dict:
        job = db.get(BulkJob, bulk_job_id)
        if not job:
            raise AppException("BULK_FOLDER_INVALID", details={"bulk_job_id": bulk_job_id})
        failed = db.query(BulkItem).filter(BulkItem.bulk_job_id == bulk_job_id, BulkItem.status.in_(["validation_failed", "execute_failed", "retry_failed"]), BulkItem.retry_count < 3).all()
        retried = 0
        for item in failed:
            item.retry_count += 1
            item.status = "retrying"
            item.last_attempt_at = now_iso()
            item.updated_at = now_iso()
            folder = Path(item.source_file).parent
            payload = load_site_folder(folder)
            errors = self.validator.validate_site_payload(db, payload)
            if errors:
                item.status = "retry_failed"
                item.error_code = errors[0]["error_code"]
                item.error_message = errors[0]["message"]
                db.add(BulkError(bulk_error_id=new_id("berr"), bulk_job_id=bulk_job_id, bulk_item_id=item.bulk_item_id, error_code=errors[0]["error_code"], message=errors[0]["message"], file=errors[0].get("file"), line=errors[0].get("line"), field=errors[0].get("field"), details_json=to_json(errors[0]), created_at=now_iso()))
            else:
                self.executor.execute_payload(db, task=task, payload=payload, bulk_job_id=bulk_job_id)
                retried += 1
        job.success_items = db.query(BulkItem).filter(BulkItem.bulk_job_id == bulk_job_id, BulkItem.status.in_(["execute_success", "retry_success"])).count()
        job.failed_items = db.query(BulkItem).filter(BulkItem.bulk_job_id == bulk_job_id, BulkItem.status.in_(["validation_failed", "execute_failed", "retry_failed"])).count()
        job.status = "retry_success" if retried else "retry_failed"
        job.updated_at = now_iso()
        db.commit()
        return {"bulk_job_id": bulk_job_id, "retried": retried, "report": self.reporter.report(db, bulk_job_id)}
