from sqlalchemy.orm import Session

from core.audit_engine import AuditEngine
from core.errors import AppException
from core.models import Article, ArticleTranslation, Product, ProductTranslation
from core.site_manager import SiteManager
from core.utils import model_dict, new_id, now_iso, slugify, to_json


class CmsEngine:
    def __init__(self) -> None:
        self.audit = AuditEngine()
        self.sites = SiteManager()

    def create_article(self, db: Session, *, site_id: str, data: dict, trace_id: str, request_id: str, task_id: str) -> Article:
        self.sites.get_site(db, site_id)
        title = data.get("title")
        content = data.get("content")
        if not title or not content:
            raise AppException("CMS_ARTICLE_INVALID", details={"required": ["title", "content"]})
        now = now_iso()
        article = Article(
            article_id=new_id("article"),
            site_id=site_id,
            cover_image=data.get("cover_image"),
            tags_json=to_json(data.get("tags", [])),
            category=data.get("category"),
            status="draft",
            created_at=now,
            updated_at=now,
        )
        db.add(article)
        db.add(
            ArticleTranslation(
                translation_id=new_id("atr"),
                article_id=article.article_id,
                language_code=data.get("language_code", "en"),
                title=title,
                content=content,
                seo_title=data.get("seo_title", title),
                seo_description=data.get("seo_description"),
                slug=data.get("slug", slugify(title)),
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()
        self.audit.record(db, trace_id=trace_id, request_id=request_id, task_id=task_id, action="article.create", resource_type="article", resource_id=article.article_id, after=model_dict(article))
        return article

    def publish_article(self, db: Session, *, article_id: str, trace_id: str, request_id: str, task_id: str) -> Article:
        article = db.get(Article, article_id)
        if not article:
            raise AppException("CMS_ARTICLE_NOT_FOUND", details={"article_id": article_id})
        translations = db.query(ArticleTranslation).filter(ArticleTranslation.article_id == article_id).all()
        if not translations or any(not t.content for t in translations):
            raise AppException("CMS_ARTICLE_EMPTY_CONTENT", details={"article_id": article_id})
        article.status = "published"
        article.published_at = now_iso()
        article.updated_at = now_iso()
        db.commit()
        self.audit.record(db, trace_id=trace_id, request_id=request_id, task_id=task_id, action="article.publish", resource_type="article", resource_id=article.article_id, after=model_dict(article))
        return article

    def create_product(self, db: Session, *, site_id: str, data: dict, trace_id: str, request_id: str, task_id: str) -> Product:
        self.sites.get_site(db, site_id)
        try:
            price = float(data.get("price"))
        except (TypeError, ValueError):
            raise AppException("CMS_PRODUCT_PRICE_INVALID", details={"field": "price"})
        if price <= 0:
            raise AppException("CMS_PRODUCT_PRICE_INVALID", details={"field": "price", "rule": "> 0"})
        name = data.get("name")
        if not name:
            raise AppException("CMS_PRODUCT_INVALID", details={"required": ["name"]})
        now = now_iso()
        product = Product(
            product_id=new_id("product"),
            site_id=site_id,
            price=price,
            currency=data.get("currency", "USD"),
            images_json=to_json(data.get("images", [])),
            attributes_json=to_json(data.get("attributes", {})),
            status="draft",
            created_at=now,
            updated_at=now,
        )
        db.add(product)
        db.add(
            ProductTranslation(
                translation_id=new_id("ptr"),
                product_id=product.product_id,
                language_code=data.get("language_code", "en"),
                name=name,
                description=data.get("description"),
                seo_title=data.get("seo_title", name),
                seo_description=data.get("seo_description"),
                slug=data.get("slug", slugify(name)),
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()
        self.audit.record(db, trace_id=trace_id, request_id=request_id, task_id=task_id, action="product.create", resource_type="product", resource_id=product.product_id, after=model_dict(product))
        return product

    def publish_product(self, db: Session, *, product_id: str, trace_id: str, request_id: str, task_id: str) -> Product:
        product = db.get(Product, product_id)
        if not product:
            raise AppException("CMS_PRODUCT_NOT_FOUND", details={"product_id": product_id})
        if product.price <= 0:
            raise AppException("CMS_PRODUCT_PRICE_INVALID", details={"product_id": product_id})
        product.status = "active"
        product.published_at = now_iso()
        product.updated_at = now_iso()
        db.commit()
        self.audit.record(db, trace_id=trace_id, request_id=request_id, task_id=task_id, action="product.publish", resource_type="product", resource_id=product.product_id, after=model_dict(product))
        return product
