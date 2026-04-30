from sqlalchemy.orm import Session

from core.audit_engine import AuditEngine
from core.errors import AppException
from core.models import Payment, Product
from core.site_manager import SiteManager
from core.utils import model_dict, new_id, now_iso, to_json


class PaymentEngine:
    def __init__(self) -> None:
        self.audit = AuditEngine()
        self.sites = SiteManager()

    def create_payment(self, db: Session, *, site_id: str, data: dict, trace_id: str, request_id: str, task_id: str) -> Payment:
        self.sites.get_site(db, site_id)
        url = data.get("payment_url") or data.get("url")
        if not url or not str(url).startswith(("http://", "https://")):
            raise AppException("PAYMENT_LINK_INVALID", details={"field": "payment_url"})
        now = now_iso()
        row = Payment(
            payment_id=new_id("pay"),
            site_id=site_id,
            provider=data.get("provider", "link"),
            payment_url=url,
            linked_product_id=data.get("linked_product_id"),
            button_text_json=to_json(data.get("button_text", {"en": "Buy Now"})),
            status="active",
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.commit()
        self.audit.record(db, trace_id=trace_id, request_id=request_id, task_id=task_id, action="payment.create", resource_type="payment", resource_id=row.payment_id, after=model_dict(row))
        return row

    def bind_product(self, db: Session, *, product_id: str, payment_id: str, trace_id: str, request_id: str, task_id: str) -> Product:
        product = db.get(Product, product_id)
        payment = db.get(Payment, payment_id)
        if not product:
            raise AppException("CMS_PRODUCT_NOT_FOUND", details={"product_id": product_id})
        if not payment:
            raise AppException("PAYMENT_LINK_INVALID", details={"payment_id": payment_id})
        product.payment_id = payment_id
        payment.linked_product_id = product_id
        product.updated_at = now_iso()
        payment.updated_at = now_iso()
        db.commit()
        self.audit.record(db, trace_id=trace_id, request_id=request_id, task_id=task_id, action="payment.bind_product", resource_type="product", resource_id=product_id)
        return product
