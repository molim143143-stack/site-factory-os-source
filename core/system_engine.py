from sqlalchemy.orm import Session

from config import APP_VERSION
from core.models import AuditLog, Deployment, Domain, ErrorLog, I18nLanguage, Site, Task
from core.utils import model_dict


class SystemEngine:
    def status(self, db: Session) -> dict:
        return {
            "sites": db.query(Site).count(),
            "sites_active": db.query(Site).filter(Site.status == "active").count(),
            "deployments": db.query(Deployment).count(),
            "errors": db.query(ErrorLog).count(),
            "dns_issues": db.query(Domain).filter(Domain.status.notin_(["ns_verified", "active", "github_bound"])).count(),
            "language_gaps": db.query(I18nLanguage).filter(I18nLanguage.enabled == 1, I18nLanguage.completion < 100).count(),
            "tasks_running": db.query(Task).filter(Task.status == "running").count(),
            "tasks_failed": db.query(Task).filter(Task.status == "failed").count(),
        }

    def version(self) -> dict:
        return {"version": APP_VERSION}

    def logs(self, db: Session) -> dict:
        return {
            "errors": [model_dict(r) for r in db.query(ErrorLog).order_by(ErrorLog.created_at.desc()).limit(50).all()],
            "audit_logs": [model_dict(r) for r in db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(50).all()],
        }
