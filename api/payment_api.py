from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.errors import require_fields
from core.models import Payment
from core.payment_engine import PaymentEngine
from core.task_engine import TaskEngine
from core.utils import model_dict

router = APIRouter(prefix="/api/v1")
payments = PaymentEngine()
tasks = TaskEngine()


@router.post("/sites/{site_id}/payments")
def create_payment(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id", "payment_url"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="payment_create", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: {"payment": model_dict(payments.create_payment(db, site_id=site_id, data=data, trace_id=task.trace_id, request_id=task.request_id, task_id=task.task_id))}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.get("/sites/{site_id}/payments")
def list_payments(site_id: str, db: Session = Depends(get_db)):
    return {"items": [model_dict(p) for p in db.query(Payment).filter(Payment.site_id == site_id).all()]}


@router.get("/payments/{payment_id}")
def get_payment(payment_id: str, db: Session = Depends(get_db)):
    return model_dict(db.get(Payment, payment_id))


@router.post("/products/{product_id}/payment-bind")
def bind_product(product_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id", "payment_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="payment_bind_product", payload=data, site_id=None, trace_id=request.state.trace_id, action=lambda task: {"product": model_dict(payments.bind_product(db, product_id=product_id, payment_id=data["payment_id"], trace_id=task.trace_id, request_id=task.request_id, task_id=task.task_id))}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/builder/blocks/{block_id}/payment-bind")
def bind_block(block_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id", "payment_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="payment_bind_button", payload=data, site_id=None, trace_id=request.state.trace_id, action=lambda task: {"block_id": block_id, "payment_id": data["payment_id"]}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/payments/{payment_id}/check")
def check_payment(payment_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    row = db.get(Payment, payment_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="payment_check", payload=data, site_id=row.site_id if row else None, trace_id=request.state.trace_id, action=lambda task: {"payment_id": payment_id, "status": "active"}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}
