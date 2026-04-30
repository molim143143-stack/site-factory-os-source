from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from core.audit_engine import AuditEngine
from core.auth import create_token, decode_token
from core.errors import AppException
from core.login_security import LoginSecurity
from core.models import CustomerServiceRequest, DeviceBinding, LicenseCode, Membership, Site, Task, User
from core.utils import model_dict, new_id, now_iso, password_hash_text, to_json, verify_password


PLAN_LIMITS = {
    "trial": {
        "site_limit": 1,
        "deploy_limit_per_day": 3,
        "device_limit": 1,
        "can_use_bulk_import": 0,
        "can_use_telegram": 0,
        "can_use_diy_builder": 1,
        "can_use_i18n": 0,
        "can_use_payment_links": 0,
        "can_use_roles": 0,
        "can_use_advanced_audit": 0,
    },
    "pro": {
        "site_limit": 30,
        "deploy_limit_per_day": 100,
        "device_limit": 2,
        "can_use_bulk_import": 1,
        "can_use_telegram": 1,
        "can_use_diy_builder": 1,
        "can_use_i18n": 1,
        "can_use_payment_links": 1,
        "can_use_roles": 0,
        "can_use_advanced_audit": 0,
    },
    "enterprise": {
        "site_limit": 999999,
        "deploy_limit_per_day": 999999,
        "device_limit": 999999,
        "can_use_bulk_import": 1,
        "can_use_telegram": 1,
        "can_use_diy_builder": 1,
        "can_use_i18n": 1,
        "can_use_payment_links": 1,
        "can_use_roles": 1,
        "can_use_advanced_audit": 1,
    },
}

PLAN_ALIASES = {
    "free": "trial",
    "basic": "pro",
    "vip": "enterprise",
    "admin": "enterprise",
}

FEATURE_BY_TASK = {
    "build_site": "site_limit",
    "bulk_job_create": "can_use_bulk_import",
    "bulk_scan": "can_use_bulk_import",
    "bulk_validate": "can_use_bulk_import",
    "bulk_execute": "can_use_bulk_import",
    "bulk_retry": "can_use_bulk_import",
    "diy_publish": "can_use_diy_builder",
    "i18n_generate": "can_use_i18n",
    "i18n_validate": "can_use_i18n",
    "i18n_enable": "can_use_i18n",
    "payment_create": "can_use_payment_links",
    "payment_bind_product": "can_use_payment_links",
    "telegram_action": "can_use_telegram",
}


class MembershipEngine:
    def __init__(self) -> None:
        self.audit = AuditEngine()
        self.login_security = LoginSecurity()

    def _expires(self, days: int) -> str:
        return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

    def normalize_plan(self, plan: str) -> str:
        normalized = PLAN_ALIASES.get(str(plan).lower(), str(plan).lower())
        if normalized not in PLAN_LIMITS:
            raise AppException("MEMBERSHIP_STATUS_INVALID", details={"plan": plan})
        return normalized

    def _apply_plan(self, row: Membership, plan: str, duration_days: int) -> Membership:
        plan = self.normalize_plan(plan)
        limits = PLAN_LIMITS[plan]
        row.plan = plan
        row.status = "active"
        row.started_at = now_iso()
        row.expires_at = self._expires(duration_days)
        for key, value in limits.items():
            setattr(row, key, value)
        row.updated_at = now_iso()
        return row

    def register(self, db: Session, data: dict, *, trace_id: str) -> dict:
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            raise AppException("SYSTEM_MISSING_FIELD", details={"required": ["username", "password"]})
        if db.query(User).filter(User.username == username).first():
            raise AppException("SYSTEM_INVALID_INPUT", message="username already exists", details={"username": username})
        now = now_iso()
        user = User(
            user_id=new_id("user"),
            username=username,
            email=data.get("email"),
            password_hash=password_hash_text(password),
            telegram_handle=data.get("telegram_handle"),
            role=data.get("role", "operator"),
            status="active",
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        membership = Membership(
            membership_id=new_id("mem"),
            user_id=user.user_id,
            plan="trial",
            status="active",
            started_at=now,
            expires_at=self._expires(int(data.get("trial_days", 3))),
            created_at=now,
            updated_at=now,
            **PLAN_LIMITS["trial"],
        )
        db.add(membership)
        db.commit()
        self.audit.record(db, trace_id=trace_id, action="auth.register", resource_type="user", resource_id=user.user_id, after=model_dict(user))
        return {"user": model_dict(user), "membership": model_dict(membership)}

    def login(self, db: Session, data: dict, *, trace_id: str, ip: str = "unknown", user_agent: str = "") -> dict:
        username = str(data.get("username") or "")
        self.login_security.precheck(db, username=username, ip=ip, captcha_id=data.get("captcha_id"), captcha_answer=data.get("captcha_answer"))
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(data.get("password", ""), user.password_hash):
            self.login_security.after_failure(db, username=username, ip=ip, user_agent=user_agent, reason="INVALID_CREDENTIALS")
            raise AppException("INVALID_CREDENTIALS", message="用户名或密码错误", status_code=401)
        membership = self.get_membership(db, user.user_id)
        token = create_token(user, token_type="access")
        refresh_token = create_token(user, token_type="refresh")
        self.login_security.after_success(db, username=username, ip=ip, user_agent=user_agent)
        self.audit.record(db, trace_id=trace_id, action="auth.login", resource_type="user", resource_id=user.user_id)
        return {"token": token, "refresh_token": refresh_token, "user": model_dict(user), "membership": model_dict(membership), "portal_boot": "Portal Boot Sequence"}

    def refresh(self, db: Session, refresh_token: str) -> dict:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = db.get(User, payload.get("sub"))
        if not user or user.status != "active":
            raise AppException("AUTH_TOKEN_INVALID", status_code=401)
        membership = self.get_membership(db, user.user_id)
        return {
            "token": create_token(user, token_type="access"),
            "refresh_token": create_token(user, token_type="refresh"),
            "user": model_dict(user),
            "membership": model_dict(membership),
        }

    def get_membership(self, db: Session, user_id: str) -> Membership:
        row = db.query(Membership).filter(Membership.user_id == user_id).first()
        if not row:
            raise AppException("MEMBERSHIP_REQUIRED", details={"user_id": user_id})
        return row

    def create_service_request(self, db: Session, data: dict, *, trace_id: str) -> CustomerServiceRequest:
        for field in ("user_id", "target_plan", "contact_method", "contact_value"):
            if not data.get(field):
                raise AppException("SYSTEM_MISSING_FIELD", details={"missing": field})
        if data["target_plan"] not in {"pro", "enterprise"}:
            raise AppException("MEMBERSHIP_STATUS_INVALID", details={"target_plan": data["target_plan"]})
        now = now_iso()
        row = CustomerServiceRequest(
            request_id=data.get("request_id") or new_id("open_req"),
            user_id=data["user_id"],
            target_plan=data["target_plan"],
            contact_method=data["contact_method"],
            contact_value=data["contact_value"],
            status="pending",
            note=data.get("note"),
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.commit()
        self.audit.record(db, trace_id=trace_id, request_id=row.request_id, action="membership.service_request.create", resource_type="membership_request", resource_id=row.request_id, after=model_dict(row))
        return row

    def update_service_request(self, db: Session, request_id: str, status: str, *, admin_id: str | None = None, note: str | None = None) -> CustomerServiceRequest:
        row = db.get(CustomerServiceRequest, request_id)
        if not row:
            raise AppException("SYSTEM_INVALID_INPUT", details={"request_id": request_id})
        if status not in {"pending", "paid", "activated", "rejected"}:
            raise AppException("MEMBERSHIP_STATUS_INVALID", details={"status": status})
        row.status = status
        row.handled_by = admin_id
        row.note = note or row.note
        row.updated_at = now_iso()
        db.commit()
        return row

    def activate_membership(self, db: Session, *, user_id: str, plan: str, duration_days: int, admin_id: str | None = None) -> Membership:
        plan = self.normalize_plan(plan)
        row = self.get_membership(db, user_id)
        self._apply_plan(row, plan, duration_days)
        db.commit()
        return row

    def generate_license(self, db: Session, *, plan: str, duration_days: int, created_by: str, code_type: str = "CUSTOM") -> LicenseCode:
        plan = self.normalize_plan(plan)
        code = f"SFS-{plan.upper()}-{duration_days}D-{new_id('')[1:].upper()[:6]}"
        row = LicenseCode(
            code=code,
            plan=plan,
            duration_days=duration_days,
            status="unused",
            created_by=created_by,
            created_at=now_iso(),
        )
        db.add(row)
        db.commit()
        return row

    def activate_license(self, db: Session, *, user_id: str, code: str) -> Membership:
        row = db.get(LicenseCode, code)
        if not row:
            raise AppException("LICENSE_CODE_INVALID", details={"code": code})
        if row.status == "used":
            raise AppException("LICENSE_CODE_USED", details={"code": code})
        if row.status == "disabled":
            raise AppException("LICENSE_CODE_DISABLED", details={"code": code})
        if row.status == "expired":
            raise AppException("LICENSE_CODE_EXPIRED", details={"code": code})
        if row.expires_at and datetime.fromisoformat(row.expires_at) < datetime.now(timezone.utc):
            row.status = "expired"
            db.commit()
            raise AppException("LICENSE_CODE_EXPIRED", details={"code": code, "expires_at": row.expires_at})
        membership = self.activate_membership(db, user_id=user_id, plan=row.plan, duration_days=row.duration_days)
        row.status = "used"
        row.used_by = user_id
        row.used_at = now_iso()
        db.commit()
        return membership

    def bind_device(self, db: Session, *, user_id: str, fingerprint: str, label: str | None = None) -> DeviceBinding:
        membership = self.get_membership(db, user_id)
        existing = db.query(DeviceBinding).filter(DeviceBinding.user_id == user_id, DeviceBinding.device_fingerprint == fingerprint).first()
        if existing:
            existing.last_seen_at = now_iso()
            db.commit()
            return existing
        count = db.query(DeviceBinding).filter(DeviceBinding.user_id == user_id, DeviceBinding.status == "active").count()
        if count >= membership.device_limit:
            raise AppException("DEVICE_LIMIT_REACHED", details={"device_limit": membership.device_limit})
        row = DeviceBinding(
            device_id=new_id("device"),
            user_id=user_id,
            device_fingerprint=fingerprint,
            label=label,
            status="active",
            created_at=now_iso(),
            last_seen_at=now_iso(),
        )
        db.add(row)
        db.commit()
        return row

    def check_task_allowed(self, db: Session, *, task_type: str, payload: dict, site_id: str | None = None) -> None:
        user_id = payload.get("user_id")
        if not user_id:
            return
        membership = self.get_membership(db, user_id)
        if membership.status != "active":
            raise AppException("MEMBERSHIP_STATUS_INVALID", details={"status": membership.status})
        if membership.expires_at and datetime.fromisoformat(membership.expires_at) < datetime.now(timezone.utc):
            raise AppException("MEMBERSHIP_EXPIRED", details={"expires_at": membership.expires_at})
        feature = FEATURE_BY_TASK.get(task_type)
        if feature:
            if feature == "site_limit":
                count = db.query(Site).count()
                if count >= membership.site_limit:
                    raise AppException("MEMBERSHIP_PLAN_LIMIT_REACHED", details={"feature": "site_limit", "limit": membership.site_limit})
            elif not getattr(membership, feature):
                raise AppException("MEMBERSHIP_FEATURE_NOT_ALLOWED", details={"feature": feature, "plan": membership.plan})
        if task_type in {"deploy", "publish_article", "publish_product", "bulk_execute", "diy_publish"}:
            if membership.plan == "trial" and task_type in {"deploy", "publish_article", "publish_product", "bulk_execute"}:
                raise AppException("MEMBERSHIP_FEATURE_NOT_ALLOWED", details={"feature": task_type, "plan": membership.plan})
            today = datetime.now(timezone.utc).date().isoformat()
            count = db.query(Task).filter(Task.task_type.in_(["deploy", "publish_article", "publish_product", "bulk_execute", "diy_publish"]), Task.created_at >= today).count()
            if count >= membership.deploy_limit_per_day:
                raise AppException("MEMBERSHIP_PLAN_LIMIT_REACHED", details={"feature": "deploy_limit_per_day", "limit": membership.deploy_limit_per_day})
