import random
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from core.errors import AppException
from core.models import LoginAttempt, LoginCaptcha, LoginLock
from core.utils import new_id, now_iso, sha256_text


class LoginSecurity:
    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _since(self, minutes: int) -> str:
        return (self._now() - timedelta(minutes=minutes)).isoformat()

    def _future(self, minutes: int) -> str:
        return (self._now() + timedelta(minutes=minutes)).isoformat()

    def _active_lock(self, db: Session, scope: str, value: str) -> LoginLock | None:
        return (
            db.query(LoginLock)
            .filter(LoginLock.scope == scope, LoginLock.scope_value == value, LoginLock.locked_until > now_iso())
            .order_by(LoginLock.locked_until.desc())
            .first()
        )

    def _fail_count(self, db: Session, *, username: str | None = None, ip: str | None = None, minutes: int = 5) -> int:
        query = db.query(LoginAttempt).filter(LoginAttempt.success == 0, LoginAttempt.created_at >= self._since(minutes))
        if username is not None:
            query = query.filter(LoginAttempt.username == username)
        if ip is not None:
            query = query.filter(LoginAttempt.ip == ip)
        return query.count()

    def record(self, db: Session, *, username: str, ip: str, user_agent: str, success: bool, reason: str) -> None:
        db.add(LoginAttempt(username=username, ip=ip, user_agent=user_agent, success=1 if success else 0, reason=reason, created_at=now_iso()))
        db.commit()

    def create_captcha(self, db: Session) -> dict:
        left = random.randint(2, 9)
        right = random.randint(2, 9)
        captcha_id = new_id("cap")
        row = LoginCaptcha(
            captcha_id=captcha_id,
            question=f"{left} + {right} = ?",
            answer_hash=sha256_text(str(left + right)),
            expires_at=self._future(5),
            created_at=now_iso(),
        )
        db.add(row)
        db.commit()
        return {"captcha_id": captcha_id, "question": row.question}

    def verify_captcha(self, db: Session, captcha_id: str | None, answer: str | None) -> bool:
        if not captcha_id or answer in (None, ""):
            return False
        row = db.get(LoginCaptcha, captcha_id)
        if not row or row.expires_at <= now_iso():
            return False
        ok = row.answer_hash == sha256_text(str(answer).strip())
        if ok:
            db.delete(row)
            db.commit()
        return ok

    def precheck(self, db: Session, *, username: str, ip: str, captcha_id: str | None = None, captcha_answer: str | None = None) -> None:
        username_lock = self._active_lock(db, "username", username)
        ip_lock = self._active_lock(db, "ip", ip)
        lock = username_lock or ip_lock
        if lock:
            retry_after = max(1, int((datetime.fromisoformat(lock.locked_until) - self._now()).total_seconds()))
            raise AppException("LOGIN_RATE_LIMITED", details={"retry_after_seconds": retry_after}, status_code=429)

        username_5 = self._fail_count(db, username=username, minutes=5)
        ip_5 = self._fail_count(db, ip=ip, minutes=5)
        if username_5 >= 5:
            db.add(LoginLock(scope="username", scope_value=username, locked_until=self._future(15), reason="username_5m_limit", created_at=now_iso()))
            db.commit()
            raise AppException("LOGIN_RATE_LIMITED", details={"retry_after_seconds": 900}, status_code=429)
        if ip_5 >= 20:
            db.add(LoginLock(scope="ip", scope_value=ip, locked_until=self._future(15), reason="ip_5m_limit", created_at=now_iso()))
            db.commit()
            raise AppException("LOGIN_RATE_LIMITED", details={"retry_after_seconds": 900}, status_code=429)
        if username_5 >= 3 or ip_5 >= 10:
            if not self.verify_captcha(db, captcha_id, captcha_answer):
                db.add(LoginAttempt(username=username, ip=ip, user_agent="", success=0, reason="CAPTCHA_REQUIRED", created_at=now_iso()))
                db.commit()
                if self._fail_count(db, username=username, minutes=5) >= 5:
                    db.add(LoginLock(scope="username", scope_value=username, locked_until=self._future(15), reason="username_5m_limit", created_at=now_iso()))
                    db.commit()
                    raise AppException("LOGIN_RATE_LIMITED", details={"retry_after_seconds": 900}, status_code=429)
                raise AppException("CAPTCHA_REQUIRED", details={"captcha": self.create_captcha(db)}, status_code=429)

    def after_failure(self, db: Session, *, username: str, ip: str, user_agent: str, reason: str = "INVALID_CREDENTIALS") -> None:
        self.record(db, username=username, ip=ip, user_agent=user_agent, success=False, reason=reason)
        username_5 = self._fail_count(db, username=username, minutes=5)
        username_60 = self._fail_count(db, username=username, minutes=60)
        ip_5 = self._fail_count(db, ip=ip, minutes=5)
        ip_60 = self._fail_count(db, ip=ip, minutes=60)
        locks = []
        if username_5 >= 5:
            locks.append(("username", username, self._future(15), "username_5m_limit"))
        if username_60 >= 15:
            locks.append(("username", username, self._future(60), "username_1h_limit"))
        if ip_5 >= 20:
            locks.append(("ip", ip, self._future(15), "ip_5m_limit"))
        if ip_60 >= 50:
            locks.append(("ip", ip, self._future(60), "ip_1h_limit"))
        for scope, value, until, lock_reason in locks:
            db.add(LoginLock(scope=scope, scope_value=value, locked_until=until, reason=lock_reason, created_at=now_iso()))
        db.commit()
        if username_5 >= 3 or ip_5 >= 10:
            time.sleep(1 if username_5 <= 5 else 2)

    def after_success(self, db: Session, *, username: str, ip: str, user_agent: str) -> None:
        self.record(db, username=username, ip=ip, user_agent=user_agent, success=True, reason="SUCCESS")
        db.query(LoginCaptcha).filter(LoginCaptcha.expires_at <= now_iso()).delete()
        db.commit()
