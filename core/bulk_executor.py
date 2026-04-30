from pathlib import Path

from sqlalchemy.orm import Session

from core.cms_engine import CmsEngine
from core.deploy_engine import DeployEngine
from core.models import BulkItem
from core.utils import model_dict


class BulkExecutor:
    def __init__(self) -> None:
        self.cms = CmsEngine()
        self.deploy = DeployEngine()

    def execute_payload(self, db: Session, *, task, payload: dict, bulk_job_id: str) -> dict:
        config = payload["config"]
        site_id = config["site_id"]
        changed = 0
        article = payload["article"]
        product = payload["product"]
        if article:
            self.cms.create_article(
                db,
                site_id=site_id,
                data={"title": article["title"], "content": article["content"], "language_code": config.get("language_code", "en")},
                trace_id=task.trace_id,
                request_id=task.request_id,
                task_id=task.task_id,
            )
            changed += 1
        if product:
            self.cms.create_product(
                db,
                site_id=site_id,
                data={
                    "name": product["name"],
                    "price": product["price"],
                    "images": product.get("images", []),
                    "description": product.get("desc") or product.get("description"),
                    "language_code": config.get("language_code", "en"),
                },
                trace_id=task.trace_id,
                request_id=task.request_id,
                task_id=task.task_id,
            )
            changed += 1
        items = db.query(BulkItem).filter(BulkItem.bulk_job_id == bulk_job_id, BulkItem.site_id == site_id, BulkItem.status.in_(["ready_execute", "retrying"])).all()
        for item in items:
            item.status = "execute_success" if item.status == "ready_execute" else "retry_success"
        db.commit()
        deployment = None
        if changed > 0:
            deployment = self.deploy.deploy(db, site_id=site_id, task_id=task.task_id, trace_id=task.trace_id, request_id=task.request_id, deploy_type="bulk_import")
        return {"site_id": site_id, "changed": changed, "deployment": model_dict(deployment) if deployment else None}
