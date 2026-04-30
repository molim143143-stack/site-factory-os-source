from sqlalchemy.orm import Session

from core.cms_engine import CmsEngine
from core.deploy_engine import DeployEngine
from core.models import Article, ArticleTranslation, Product, ProductTranslation
from core.task_engine import TaskEngine
from core.utils import model_dict


class PublishEngine:
    def __init__(self) -> None:
        self.cms = CmsEngine()
        self.deploy = DeployEngine()
        self.tasks = TaskEngine()

    def publish_article(self, db: Session, *, task, article_id: str) -> dict:
        before = db.get(Article, article_id)
        if before and before.status == "published":
            self.tasks.add_log(db, task.task_id, "PublishEngine", "success", "article already published, deploy skipped")
            return {"article": model_dict(before), "deployment": None, "no_op": True}
        article = self.cms.publish_article(db, article_id=article_id, trace_id=task.trace_id, request_id=task.request_id, task_id=task.task_id)
        t = db.query(ArticleTranslation).filter(ArticleTranslation.article_id == article_id).first()
        html = f"<html><body><article><h1>{t.title}</h1><div>{t.content}</div></article></body></html>"
        deployment = self.deploy.deploy(db, site_id=article.site_id, task_id=task.task_id, trace_id=task.trace_id, request_id=task.request_id, deploy_type="publish_article", files={f"articles/{t.slug}.html": html, "index.html": html})
        return {"article": model_dict(article), "deployment": model_dict(deployment)}

    def publish_product(self, db: Session, *, task, product_id: str) -> dict:
        before = db.get(Product, product_id)
        if before and before.status == "active":
            self.tasks.add_log(db, task.task_id, "PublishEngine", "success", "product already active, deploy skipped")
            return {"product": model_dict(before), "deployment": None, "no_op": True}
        product = self.cms.publish_product(db, product_id=product_id, trace_id=task.trace_id, request_id=task.request_id, task_id=task.task_id)
        t = db.query(ProductTranslation).filter(ProductTranslation.product_id == product_id).first()
        html = f"<html><body><h1>{t.name}</h1><p>{t.description or ''}</p><strong>{product.price} {product.currency}</strong></body></html>"
        deployment = self.deploy.deploy(db, site_id=product.site_id, task_id=task.task_id, trace_id=task.trace_id, request_id=task.request_id, deploy_type="publish_product", files={f"products/{t.slug}.html": html, "index.html": html})
        return {"product": model_dict(product), "deployment": model_dict(deployment)}
