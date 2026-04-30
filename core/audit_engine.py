from sqlalchemy.orm import Session

from core.models import AuditLog
from core.utils import new_id, now_iso, to_json


class AuditEngine:
    def record(
        self,
        db: Session,
        *,
        trace_id: str,
        action: str,
        request_id: str | None = None,
        task_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        before: dict | None = None,
        after: dict | None = None,
        actor_id: str | None = None,
    ) -> AuditLog:
        row = AuditLog(
            audit_id=new_id("audit"),
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_json=to_json(before) if before is not None else None,
            after_json=to_json(after) if after is not None else None,
            ip_address=None,
            user_agent=None,
            created_at=now_iso(),
        )
        db.add(row)
        db.commit()
        return row
