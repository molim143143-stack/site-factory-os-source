import os

from sqlalchemy.orm import Session

from core.audit_engine import AuditEngine
from core.errors import AppException
from core.models import I18nLanguage, Site, SiteAlias
from core.utils import model_dict, new_id, now_iso


SUPPORTED_LANGUAGES = {
    "en": "English",
    "zh-CN": "中文",
    "es": "Español",
    "pt": "Português",
    "ur-Latn": "Romanized Urdu",
    "hi": "Hindi",
    "de": "Deutsch",
    "vi": "Tiếng Việt",
    "ja": "日本語",
}


class SiteManager:
    def __init__(self) -> None:
        self.audit = AuditEngine()

    def create_site(self, db: Session, *, domain: str, alias: str, site_type: str, template_id: str, trace_id: str, request_id: str, task_id: str) -> Site:
        if db.query(Site).filter(Site.domain == domain).first():
            raise AppException("SITE_ALREADY_EXISTS", details={"domain": domain})
        if db.query(SiteAlias).filter(SiteAlias.alias == alias).first():
            raise AppException("SITE_ALIAS_DUPLICATE", details={"alias": alias})
        now = now_iso()
        site_id = new_id("site")
        repo = f"sfs-{site_id}"
        site = Site(
            site_id=site_id,
            alias=alias,
            site_type=site_type,
            domain=domain,
            repo_name=repo,
            repo_branch="main",
            github_pages_url=f"https://{os.getenv('GITHUB_OWNER', 'github')}.github.io/{repo}/",
            public_url=f"https://{os.getenv('GITHUB_OWNER', 'github')}.github.io/{repo}/",
            template_id=template_id,
            theme_id="default",
            status="dns_pending",
            created_at=now,
            updated_at=now,
        )
        db.add(site)
        db.add(SiteAlias(alias_id=new_id("alias"), site_id=site_id, alias=alias, keywords=alias, created_at=now))
        for code, name in SUPPORTED_LANGUAGES.items():
            db.add(
                I18nLanguage(
                    id=new_id("lang"),
                    site_id=site_id,
                    language_code=code,
                    language_name=name,
                    enabled=1 if code == "en" else 0,
                    is_default=1 if code == "en" else 0,
                    completion=100 if code == "en" else 0,
                    created_at=now,
                    updated_at=now,
                )
            )
        db.commit()
        self.audit.record(
            db,
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            action="site.create",
            resource_type="site",
            resource_id=site_id,
            after=model_dict(site),
        )
        return site

    def get_site(self, db: Session, site_id: str) -> Site:
        site = db.get(Site, site_id)
        if not site:
            raise AppException("SITE_NOT_FOUND", details={"site_id": site_id})
        return site

    def list_sites(self, db: Session) -> list[Site]:
        return db.query(Site).order_by(Site.created_at.desc()).all()

    def update_status(self, db: Session, site_id: str, status: str) -> Site:
        site = self.get_site(db, site_id)
        site.status = status
        site.updated_at = now_iso()
        db.commit()
        return site
