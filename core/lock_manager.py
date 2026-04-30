from sqlalchemy.orm import Session

from core.errors import AppException
from core.models import ResourceLock
from core.utils import new_id, now_iso


class LockManager:
    def acquire(self, db: Session, resource_type: str, resource_id: str, task_id: str) -> ResourceLock:
        existing = (
            db.query(ResourceLock)
            .filter(
                ResourceLock.resource_type == resource_type,
                ResourceLock.resource_id == resource_id,
            )
            .first()
        )
        if existing and existing.status == "locked" and existing.task_id != task_id:
            raise AppException(
                "TASK_ALREADY_RUNNING",
                details={
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "running_task_id": existing.task_id,
                },
            )
        if existing:
            existing.task_id = task_id
            existing.status = "locked"
            existing.locked_at = now_iso()
            existing.expires_at = None
            db.commit()
            return existing
        row = ResourceLock(
            lock_id=new_id("lock"),
            resource_type=resource_type,
            resource_id=resource_id,
            task_id=task_id,
            status="locked",
            locked_at=now_iso(),
        )
        db.add(row)
        db.commit()
        return row

    def release(self, db: Session, task_id: str) -> None:
        locks = db.query(ResourceLock).filter(ResourceLock.task_id == task_id, ResourceLock.status == "locked").all()
        for lock in locks:
            lock.status = "released"
        db.commit()
