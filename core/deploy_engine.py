from pathlib import Path

from sqlalchemy.orm import Session

from config import GENERATED_DIR
from core.audit_engine import AuditEngine
from core.domain_engine import DomainEngine
from core.errors import AppException
from core.models import Deployment, DeploymentFile, I18nLanguage, Site
from core.public_url import resolve_public_url
from core.template_engine import TemplateEngine
from core.utils import model_dict, new_id, now_iso, sha256_text, to_json
from integrations.github import GitHubIntegration


class DeployEngine:
    def __init__(self) -> None:
        self.audit = AuditEngine()
        self.domain = DomainEngine()
        self.templates = TemplateEngine()
        self.github = GitHubIntegration()

    def _previous_commit(self, db: Session, site_id: str) -> str | None:
        row = (
            db.query(Deployment)
            .filter(Deployment.site_id == site_id, Deployment.status.in_(["success", "rollback_success"]))
            .order_by(Deployment.created_at.desc())
            .first()
        )
        return row.commit_id if row else None

    def deploy(self, db: Session, *, site_id: str, task_id: str, trace_id: str, request_id: str, deploy_type: str = "site", files: dict[str, str] | None = None, require_dns: bool = True) -> Deployment:
        site = db.get(Site, site_id)
        if not site:
            raise AppException("SITE_NOT_FOUND", details={"site_id": site_id})
        if require_dns:
            self.domain.require_ready_for_deploy(db, site_id)
        if deploy_type != "rollback":
            incomplete = (
                db.query(I18nLanguage)
                .filter(I18nLanguage.site_id == site_id, I18nLanguage.enabled == 1, I18nLanguage.completion < 100)
                .all()
            )
            if incomplete:
                raise AppException(
                    "I18N_MISSING_TRANSLATION",
                    details={"languages": [row.language_code for row in incomplete]},
                )
        content = files or self.templates.render_site(db, site_id)
        if not content:
            raise AppException("DEPLOY_PAGE_NOT_READY", details={"site_id": site_id, "reason": "no rendered files"})
        dist = GENERATED_DIR / site_id / "dist"
        dist.mkdir(parents=True, exist_ok=True)
        manifest = {}
        self.github.create_repo(site.repo_name)
        last_commit_id = None
        for file_path, body in content.items():
            if str(file_path).startswith(str(dist)):
                target = Path(file_path)
                rel_path = target.relative_to(dist).as_posix()
            else:
                rel_path = str(file_path).lstrip("/")
                target = dist / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
            manifest[rel_path] = sha256_text(body)
            result = self.github.put_file(site.repo_name, rel_path, body, f"Deploy {site.site_id} {now_iso()}")
            last_commit_id = result.get("commit", {}).get("sha") or result.get("commit_id") or last_commit_id
        index_path = dist / "index.html"
        if not index_path.exists() or index_path.stat().st_size == 0:
            raise AppException("DEPLOY_PAGE_NOT_READY", details={"site_id": site_id, "missing": "dist/index.html"})
        self.github.enable_pages(site.repo_name)
        pages_status = self.github.pages_status(site.repo_name)
        previous_commit_id = self._previous_commit(db, site_id)
        commit_id = last_commit_id or new_id("commit")
        live_url = pages_status.get("html_url") or pages_status.get("url")
        if self.github.mode == "real":
            default_pages_url = f"https://{self.github.owner}.github.io/{site.repo_name}/"
            if not live_url or ".github.io/" not in live_url:
                live_url = default_pages_url
            site.github_pages_url = default_pages_url
        if not live_url:
            owner = self.github.owner or "mock"
            live_url = f"https://{owner}.github.io/{site.repo_name}/" if self.github.mode == "real" else f"https://mock.local/{site.domain or site_id}"
        site.public_url = resolve_public_url(db, site, self.github.owner) or live_url
        live_url = site.public_url
        now = now_iso()
        deploy = Deployment(
            deploy_id=new_id("deploy"),
            site_id=site_id,
            task_id=task_id,
            trace_id=trace_id,
            request_id=request_id,
            deploy_type=deploy_type,
            status="success",
            commit_id=commit_id,
            previous_commit_id=previous_commit_id,
            repo_name=site.repo_name,
            repo_branch=site.repo_branch,
            manifest_hash=sha256_text(to_json(manifest)),
            dist_path=str(dist),
            live_url=live_url,
            created_at=now,
            finished_at=now,
        )
        db.add(deploy)
        for path, content_hash in manifest.items():
            db.add(
                DeploymentFile(
                    file_id=new_id("dfile"),
                    deploy_id=deploy.deploy_id,
                    file_path=path,
                    content_hash=content_hash,
                    file_size=len((dist / path).read_text(encoding="utf-8").encode("utf-8")),
                    action="modified" if previous_commit_id else "added",
                    created_at=now,
                )
            )
        site.status = "active"
        site.last_deploy_at = now
        if self.github.mode != "real":
            site.github_pages_url = deploy.live_url
        site.public_url = deploy.live_url
        site.updated_at = now
        db.commit()
        self.audit.record(
            db,
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            action="deploy.create",
            resource_type="deployment",
            resource_id=deploy.deploy_id,
            after=model_dict(deploy),
        )
        return deploy

    def rollback(self, db: Session, *, deploy_id: str, task_id: str, trace_id: str, request_id: str) -> Deployment:
        source = db.get(Deployment, deploy_id)
        if not source or not source.previous_commit_id:
            raise AppException("DEPLOY_ROLLBACK_FAILED", details={"deploy_id": deploy_id})
        rollback = self.deploy(
            db,
            site_id=source.site_id,
            task_id=task_id,
            trace_id=trace_id,
            request_id=request_id,
            deploy_type="rollback",
            files={"index.html": f"<html><body><h1>Rollback to {source.previous_commit_id}</h1></body></html>"},
        )
        rollback.rollback_from_deploy_id = deploy_id
        rollback.status = "rollback_success"
        db.commit()
        return rollback
