from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.cms_engine import CmsEngine
from core.database import get_db
from core.errors import require_fields
from core.models import Article, Product
from core.publish_engine import PublishEngine
from core.task_engine import TaskEngine
from core.utils import model_dict

router = APIRouter(prefix="/api/v1")
cms = CmsEngine()
publish = PublishEngine()
tasks = TaskEngine()


@router.post("/sites/{site_id}/articles")
def create_article(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id", "title", "content"], data.get("request_id"), request.state.trace_id)

    def action(task):
        article = cms.create_article(db, site_id=site_id, data=data, trace_id=task.trace_id, request_id=task.request_id, task_id=task.task_id)
        return {"article": model_dict(article)}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="article_create", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/articles/create")
def create_article_alias(data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["site_id"], data.get("request_id"), request.state.trace_id)
    return create_article(data["site_id"], data, request, db)


@router.get("/sites/{site_id}/articles")
def list_articles(site_id: str, db: Session = Depends(get_db)):
    return {"items": [model_dict(a) for a in db.query(Article).filter(Article.site_id == site_id).all()]}


@router.get("/articles/{article_id}")
def get_article(article_id: str, db: Session = Depends(get_db)):
    return model_dict(db.get(Article, article_id))


@router.patch("/articles/{article_id}")
def patch_article(article_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    article = db.get(Article, article_id)
    site_id = article.site_id if article else None

    def action(task):
        if "status" in data:
            article.status = data["status"]
        db.commit()
        return {"article": model_dict(article)}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="article_update", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/articles/{article_id}/publish")
def publish_article(article_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    article = db.get(Article, article_id)
    site_id = article.site_id if article else None
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="publish_article", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: publish.publish_article(db, task=task, article_id=article_id), lock=True)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/articles/publish")
def publish_article_alias(data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["article_id"], data.get("request_id"), request.state.trace_id)
    return publish_article(data["article_id"], data, request, db)


@router.post("/articles/{article_id}/archive")
def archive_article(article_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    article = db.get(Article, article_id)
    site_id = article.site_id if article else None

    def action(task):
        article.status = "archived"
        db.commit()
        return {"article": model_dict(article)}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="article_archive", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/sites/{site_id}/products")
def create_product(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id", "name"], data.get("request_id"), request.state.trace_id)

    def action(task):
        product = cms.create_product(db, site_id=site_id, data=data, trace_id=task.trace_id, request_id=task.request_id, task_id=task.task_id)
        return {"product": model_dict(product)}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="product_create", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/products/create")
def create_product_alias(data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["site_id"], data.get("request_id"), request.state.trace_id)
    return create_product(data["site_id"], data, request, db)


@router.get("/sites/{site_id}/products")
def list_products(site_id: str, db: Session = Depends(get_db)):
    return {"items": [model_dict(p) for p in db.query(Product).filter(Product.site_id == site_id).all()]}


@router.get("/products/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)):
    return model_dict(db.get(Product, product_id))


@router.patch("/products/{product_id}")
def patch_product(product_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    product = db.get(Product, product_id)
    site_id = product.site_id if product else None

    def action(task):
        if "price" in data:
            product.price = float(data["price"])
        if "status" in data:
            product.status = data["status"]
        db.commit()
        return {"product": model_dict(product)}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="product_update", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/products/{product_id}/publish")
def publish_product(product_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    product = db.get(Product, product_id)
    site_id = product.site_id if product else None
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="publish_product", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: publish.publish_product(db, task=task, product_id=product_id), lock=True)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/products/publish")
def publish_product_alias(data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["product_id"], data.get("request_id"), request.state.trace_id)
    return publish_product(data["product_id"], data, request, db)


@router.post("/products/{product_id}/archive")
def archive_product(product_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    product = db.get(Product, product_id)
    site_id = product.site_id if product else None

    def action(task):
        product.status = "archived"
        db.commit()
        return {"product": model_dict(product)}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="product_archive", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=action, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}
