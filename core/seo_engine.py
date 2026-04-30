from sqlalchemy.orm import Session

from core.models import SeoRecord
from core.site_manager import SiteManager
from core.utils import model_dict, new_id, now_iso


class SeoEngine:
    def __init__(self) -> None:
        self.sites = SiteManager()

    def update_site_seo(self, db: Session, site_id: str, data: dict) -> SeoRecord:
        self.sites.get_site(db, site_id)
        language_code = data.get("language_code", "en")
        row = (
            db.query(SeoRecord)
            .filter(SeoRecord.site_id == site_id, SeoRecord.entity_type == "site", SeoRecord.entity_id == site_id, SeoRecord.language_code == language_code)
            .first()
        )
        now = now_iso()
        if not row:
            row = SeoRecord(
                seo_id=new_id("seo"),
                site_id=site_id,
                entity_type="site",
                entity_id=site_id,
                language_code=language_code,
                title=data["title"],
                description=data.get("description"),
                slug=data.get("slug", "/"),
                created_at=now,
                updated_at=now,
            )
            db.add(row)
        else:
            row.title = data.get("title", row.title)
            row.description = data.get("description", row.description)
            row.slug = data.get("slug", row.slug)
            row.updated_at = now
        db.commit()
        return row

    def sitemap(self, db: Session, site_id: str) -> dict:
        rows = db.query(SeoRecord).filter(SeoRecord.site_id == site_id).all()
        return {
            "site_id": site_id,
            "sitemap": [model_dict(r) for r in rows],
            "hreflang": [{"language_code": r.language_code, "slug": r.slug} for r in rows],
        }
