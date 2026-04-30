from sqlalchemy.orm import Session

from core.errors import ERROR_DEFS
from core.models import ErrorLog
from core.utils import new_id, now_iso, to_json


class ErrorEngine:
    def record(
        self,
        db: Session,
        error_code: str,
        message: str,
        *,
        trace_id: str | None = None,
        request_id: str | None = None,
        task_id: str | None = None,
        site_id: str | None = None,
        details: dict | None = None,
    ) -> ErrorLog:
        severity, retryable, user_action_required, _ = ERROR_DEFS.get(
            error_code, ERROR_DEFS["SYSTEM_UNKNOWN_ERROR"]
        )
        row = ErrorLog(
            error_id=new_id("err"),
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            site_id=site_id,
            error_code=error_code,
            message=message,
            severity=severity,
            retryable=int(retryable),
            user_action_required=int(user_action_required),
            details_json=to_json(details or {}),
            created_at=now_iso(),
        )
        db.add(row)
        db.commit()
        return row
