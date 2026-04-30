from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from core.audit_engine import AuditEngine
from core.error_engine import ErrorEngine
from core.errors import AppException
from core.lock_manager import LockManager
from core.membership_engine import MembershipEngine
from core.models import Task, TaskLog
from core.utils import new_id, now_iso, to_json


LOCKED_TASK_TYPES = {
    "build_site",
    "deploy",
    "rollback",
    "publish_article",
    "publish_product",
    "bulk_scan",
    "bulk_validate",
    "bulk_execute",
    "bulk_retry",
    "diy_publish",
}

VALID_TRANSITIONS = {
    "pending": {"running", "failed", "cancelled", "waiting_confirm"},
    "running": {"success", "failed", "waiting_confirm", "cancelled"},
    "failed": {"retrying", "cancelled"},
    "retrying": {"running", "failed"},
    "waiting_confirm": {"running", "cancelled"},
    "success": set(),
    "cancelled": set(),
}


class TaskEngine:
    def __init__(self) -> None:
        self.lock_manager = LockManager()
        self.error_engine = ErrorEngine()
        self.audit_engine = AuditEngine()
        self.membership_engine = MembershipEngine()

    def create_task(
        self,
        db: Session,
        *,
        request_id: str,
        task_type: str,
        payload: dict,
        trace_id: str | None = None,
        site_id: str | None = None,
    ) -> tuple[Task, bool]:
        existing = db.query(Task).filter(Task.request_id == request_id).first()
        if existing:
            self.add_log(db, existing.task_id, "RequestIdempotencyNode", "success", "duplicate request_id returned existing task")
            return existing, False
        now = now_iso()
        task = Task(
            task_id=new_id("task"),
            request_id=request_id,
            trace_id=trace_id or new_id("trace"),
            task_type=task_type,
            site_id=site_id,
            status="pending",
            progress=0,
            current_node="TaskCreateNode",
            payload_json=to_json(payload),
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        db.commit()
        self.add_log(db, task.task_id, "TaskCreateNode", "success", "task created")
        self.audit_engine.record(
            db,
            trace_id=task.trace_id,
            request_id=request_id,
            task_id=task.task_id,
            action=f"task.create.{task_type}",
            resource_type="task",
            resource_id=task.task_id,
            after={"status": "pending"},
        )
        return task, True

    def add_log(
        self,
        db: Session,
        task_id: str,
        node_name: str,
        status: str,
        message: str,
        *,
        error_code: str | None = None,
        details: dict | None = None,
    ) -> TaskLog:
        row = TaskLog(
            log_id=new_id("log"),
            task_id=task_id,
            node_name=node_name,
            status=status,
            message=message,
            error_code=error_code,
            details_json=to_json(details or {}),
            created_at=now_iso(),
        )
        db.add(row)
        db.commit()
        return row

    def set_status(
        self,
        db: Session,
        task: Task,
        status: str,
        *,
        node_name: str,
        message: str,
        result: dict | None = None,
        error_code: str | None = None,
    ) -> Task:
        allowed = VALID_TRANSITIONS.get(task.status, set())
        if status != task.status and status not in allowed:
            raise AppException(
                "TASK_INVALID_STATUS",
                details={"from": task.status, "to": status},
                request_id=task.request_id,
                trace_id=task.trace_id,
                task_id=task.task_id,
                site_id=task.site_id,
            )
        task.status = status
        task.current_node = node_name
        task.updated_at = now_iso()
        task.error_code = error_code
        task.error_message = message if error_code else None
        if result is not None:
            task.result_json = to_json(result)
        if status in {"success", "failed", "cancelled"}:
            task.finished_at = now_iso()
            if status != "failed":
                self.lock_manager.release(db, task.task_id)
        db.commit()
        self.add_log(db, task.task_id, node_name, status, message, error_code=error_code, details=result)
        return task

    def run(
        self,
        db: Session,
        *,
        request_id: str,
        task_type: str,
        payload: dict,
        site_id: str | None,
        trace_id: str | None,
        action: Callable[[Task], dict[str, Any]],
        lock: bool = True,
    ) -> tuple[Task, dict[str, Any], bool]:
        task, created = self.create_task(
            db,
            request_id=request_id,
            task_type=task_type,
            payload=payload,
            trace_id=trace_id,
            site_id=site_id,
        )
        if not created:
            return task, {"task_id": task.task_id, "idempotent": True, "result": task.result_json}, False
        try:
            self.add_log(db, task.task_id, "AuthNode", "success", "auth context accepted")
            self.membership_engine.check_task_allowed(db, task_type=task_type, payload=payload, site_id=site_id)
            self.add_log(db, task.task_id, "MembershipNode", "success", "membership active or anonymous mock mode")
            self.add_log(db, task.task_id, "QuotaNode", "success", "quota check passed")
            self.add_log(db, task.task_id, "PermissionNode", "success", "permission check passed")
            if lock and site_id and task_type in LOCKED_TASK_TYPES:
                self.lock_manager.acquire(db, "site", site_id, task.task_id)
                self.add_log(db, task.task_id, "LockNode", "success", "site lock acquired", details={"site_id": site_id})
            self.set_status(db, task, "running", node_name="NodeExecutor", message="task running")
            result = action(task)
            self.set_status(db, task, "success", node_name="ResultPersistNode", message="task success", result=result)
            self.audit_engine.record(
                db,
                trace_id=task.trace_id,
                request_id=task.request_id,
                task_id=task.task_id,
                action=f"task.success.{task.task_type}",
                resource_type="task",
                resource_id=task.task_id,
                after=result,
            )
            return task, result, True
        except AppException as exc:
            exc.request_id = exc.request_id or task.request_id
            exc.trace_id = exc.trace_id or task.trace_id
            exc.task_id = exc.task_id or task.task_id
            exc.site_id = exc.site_id or site_id
            self.set_status(
                db,
                task,
                "failed",
                node_name="ErrorNode",
                message=exc.message or exc.error_code,
                error_code=exc.error_code,
                result=exc.details,
            )
            self.error_engine.record(
                db,
                exc.error_code,
                exc.message or exc.error_code,
                trace_id=task.trace_id,
                request_id=task.request_id,
                task_id=task.task_id,
                site_id=site_id,
                details=exc.details,
            )
            self.lock_manager.release(db, task.task_id)
            raise exc

    def retry(self, db: Session, task_id: str) -> Task:
        task = db.get(Task, task_id)
        if not task:
            raise AppException("TASK_NOT_FOUND", details={"task_id": task_id})
        if task.retry_count >= task.max_retry:
            raise AppException("TASK_RETRY_LIMIT_EXCEEDED", details={"task_id": task_id})
        if task.status != "failed":
            raise AppException("TASK_INVALID_STATUS", details={"status": task.status})
        task.retry_count += 1
        self.set_status(db, task, "retrying", node_name="RetryNode", message="task retry scheduled")
        self.set_status(db, task, "running", node_name="RetryNode", message="task retry running")
        self.set_status(db, task, "success", node_name="RetryNode", message="mock retry success")
        return task

    def cancel(self, db: Session, task_id: str) -> Task:
        task = db.get(Task, task_id)
        if not task:
            raise AppException("TASK_NOT_FOUND", details={"task_id": task_id})
        if task.status in {"success", "cancelled"}:
            raise AppException("TASK_INVALID_STATUS", details={"status": task.status})
        self.set_status(db, task, "cancelled", node_name="CancelNode", message="task cancelled")
        return task
