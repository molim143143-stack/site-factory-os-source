from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_admin
from core.database import get_db
from core.errors import require_fields
from core.membership_engine import MembershipEngine, PLAN_ALIASES, PLAN_LIMITS
from core.models import CustomerServiceRequest, DeviceBinding, LicenseCode, Membership, User
from core.utils import model_dict

router = APIRouter(prefix="/api/v1")
engine = MembershipEngine()


@router.post("/auth/register")
def register(data: dict, request: Request, db: Session = Depends(get_db)):
    return engine.register(db, data, trace_id=request.state.trace_id)


@router.post("/auth/login")
def login(data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["username", "password"], None, request.state.trace_id)
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    return engine.login(db, data, trace_id=request.state.trace_id, ip=ip, user_agent=user_agent)


@router.post("/auth/refresh")
def refresh(data: dict, db: Session = Depends(get_db)):
    require_fields(data, ["refresh_token"])
    return engine.refresh(db, data["refresh_token"])


@router.get("/membership/plans")
def plans():
    return {
        "plans": [
            {"plan": "trial", "name": "Trial", "limits": PLAN_LIMITS["trial"], "payment_mode": "customer_service_manual"},
            {"plan": "pro", "name": "Pro", "limits": PLAN_LIMITS["pro"], "payment_mode": "customer_service_manual"},
            {"plan": "enterprise", "name": "Enterprise", "limits": PLAN_LIMITS["enterprise"], "payment_mode": "customer_service_manual"},
            {"plan": "free", "name": "Free", "limits": PLAN_LIMITS["trial"], "maps_to": "trial", "payment_mode": "customer_service_manual"},
            {"plan": "basic", "name": "Basic", "limits": PLAN_LIMITS["pro"], "maps_to": "pro", "payment_mode": "customer_service_manual"},
            {"plan": "vip", "name": "VIP", "limits": PLAN_LIMITS["enterprise"], "maps_to": "enterprise", "payment_mode": "customer_service_manual"},
            {"plan": "admin", "name": "Admin", "limits": PLAN_LIMITS["enterprise"], "maps_to": "enterprise", "payment_mode": "customer_service_manual"},
        ]
    }


@router.get("/membership/users/{user_id}")
def membership(user_id: str, db: Session = Depends(get_db)):
    return model_dict(engine.get_membership(db, user_id))


@router.post("/membership/service-requests")
def create_service_request(data: dict, request: Request, db: Session = Depends(get_db)):
    row = engine.create_service_request(db, data, trace_id=request.state.trace_id)
    return {"request": model_dict(row)}


@router.get("/membership/service-requests")
def list_service_requests(db: Session = Depends(get_db)):
    return {"items": [model_dict(r) for r in db.query(CustomerServiceRequest).order_by(CustomerServiceRequest.created_at.desc()).all()]}


@router.post("/admin/billing/service-requests/{request_id}/mark-paid")
def mark_paid(request_id: str, data: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = engine.update_service_request(db, request_id, "paid", admin_id=data.get("admin_id"), note=data.get("note"))
    return {"request": model_dict(row)}


@router.post("/admin/billing/service-requests/{request_id}/activate")
def activate_request(request_id: str, data: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = engine.update_service_request(db, request_id, "activated", admin_id=data.get("admin_id"), note=data.get("note"))
    membership = engine.activate_membership(db, user_id=row.user_id, plan=row.target_plan, duration_days=int(data.get("duration_days", 30)), admin_id=data.get("admin_id"))
    return {"request": model_dict(row), "membership": model_dict(membership)}


@router.post("/admin/billing/service-requests/{request_id}/reject")
def reject_request(request_id: str, data: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = engine.update_service_request(db, request_id, "rejected", admin_id=data.get("admin_id"), note=data.get("note"))
    return {"request": model_dict(row)}


@router.post("/admin/billing/license-codes")
def generate_license(data: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    require_fields(data, ["plan", "duration_days", "created_by"])
    row = engine.generate_license(db, plan=data["plan"], duration_days=int(data["duration_days"]), created_by=data["created_by"], code_type=data.get("code_type", "CUSTOM"))
    return {"license": model_dict(row)}


@router.post("/admin/license/create")
def create_license_compat(data: dict, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    require_fields(data, ["plan", "duration_days"])
    count = max(1, min(int(data.get("count", 1)), 100))
    requested_plan = str(data["plan"]).lower()
    canonical_plan = PLAN_ALIASES.get(requested_plan, requested_plan)
    rows = [
        engine.generate_license(
            db,
            plan=canonical_plan,
            duration_days=int(data["duration_days"]),
            created_by=admin.user_id,
            code_type=data.get("code_type", "CUSTOM"),
        )
        for _ in range(count)
    ]
    return {
        "success": True,
        "plan": requested_plan,
        "canonical_plan": canonical_plan,
        "keys": [row.code for row in rows],
        "licenses": [model_dict(row) for row in rows],
    }


@router.get("/admin/billing/license-codes")
def list_licenses(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return {"items": [model_dict(r) for r in db.query(LicenseCode).order_by(LicenseCode.created_at.desc()).all()]}


@router.post("/membership/license-codes/activate")
def activate_license(data: dict, db: Session = Depends(get_db)):
    require_fields(data, ["user_id", "code"])
    membership = engine.activate_license(db, user_id=data["user_id"], code=data["code"])
    return {"membership": model_dict(membership)}


@router.post("/license/activate")
def activate_license_compat(data: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    code = data.get("license_key") or data.get("code")
    require_fields({"license_key": code}, ["license_key"])
    membership = engine.activate_license(db, user_id=user.user_id, code=code)
    return {"success": True, "plan": membership.plan, "expires_at": membership.expires_at, "membership": model_dict(membership)}


@router.post("/admin/user/activate")
def activate_user_compat(data: dict, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    require_fields(data, ["user_id", "plan", "duration_days"])
    membership = engine.activate_membership(
        db,
        user_id=str(data["user_id"]),
        plan=str(data["plan"]),
        duration_days=int(data["duration_days"]),
        admin_id=admin.user_id,
    )
    return {"success": True, "user_id": str(data["user_id"]), "plan": membership.plan, "expires_at": membership.expires_at, "membership": model_dict(membership)}


@router.post("/membership/devices/bind")
def bind_device(data: dict, db: Session = Depends(get_db)):
    require_fields(data, ["user_id", "device_fingerprint"])
    row = engine.bind_device(db, user_id=data["user_id"], fingerprint=data["device_fingerprint"], label=data.get("label"))
    return {"device": model_dict(row)}


@router.get("/membership/devices/{user_id}")
def list_devices(user_id: str, db: Session = Depends(get_db)):
    return {"items": [model_dict(r) for r in db.query(DeviceBinding).filter(DeviceBinding.user_id == user_id).all()]}
