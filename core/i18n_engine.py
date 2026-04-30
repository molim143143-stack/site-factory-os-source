from sqlalchemy.orm import Session

from core.errors import AppException
from core.models import I18nLanguage
from core.site_manager import SUPPORTED_LANGUAGES, SiteManager
from core.utils import model_dict, now_iso


class I18nEngine:
    def __init__(self) -> None:
        self.sites = SiteManager()

    def get_site_i18n(self, db: Session, site_id: str) -> dict:
        self.sites.get_site(db, site_id)
        rows = db.query(I18nLanguage).filter(I18nLanguage.site_id == site_id).all()
        return {"site_id": site_id, "languages": [model_dict(r) for r in rows]}

    def enable(self, db: Session, site_id: str, language_code: str) -> I18nLanguage:
        self.sites.get_site(db, site_id)
        if language_code not in SUPPORTED_LANGUAGES:
            raise AppException("I18N_LANGUAGE_NOT_SUPPORTED", details={"language_code": language_code})
        row = db.query(I18nLanguage).filter(I18nLanguage.site_id == site_id, I18nLanguage.language_code == language_code).first()
        if not row:
            raise AppException("I18N_LANGUAGE_NOT_SUPPORTED", details={"language_code": language_code})
        row.enabled = 1
        row.completion = 100
        row.updated_at = now_iso()
        db.commit()
        return row

    def status(self, db: Session, site_id: str) -> dict:
        rows = db.query(I18nLanguage).filter(I18nLanguage.site_id == site_id).all()
        completion = {r.language_code: r.completion for r in rows if r.enabled}
        missing = {r.language_code: ["content.translation"] for r in rows if r.enabled and r.completion < 100}
        return {"site_id": site_id, "default_language": "en", "completion": completion, "missing_fields": missing}
