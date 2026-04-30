from sqlalchemy.orm import Session

from core.deploy_engine import DeployEngine
from core.domain_engine import DomainEngine
from core.site_manager import SiteManager
from core.task_engine import TaskEngine
from core.utils import model_dict


class BuildEngine:
    def __init__(self) -> None:
        self.sites = SiteManager()
        self.domains = DomainEngine()
        self.deploys = DeployEngine()
        self.tasks = TaskEngine()

    def create_site_workflow(self, db: Session, *, task, payload: dict) -> dict:
        self.tasks.add_log(db, task.task_id, "ValidateNode", "success", "site create payload validated")
        site = self.sites.create_site(
            db,
            domain=payload["domain"],
            alias=payload["alias"],
            site_type=payload.get("site_type", "landing"),
            template_id=payload.get("template_id", "landing1"),
            trace_id=task.trace_id,
            request_id=task.request_id,
            task_id=task.task_id,
        )
        self.tasks.add_log(db, task.task_id, "CreateGitHubRepoNode", "skipped", "GitHub repo is created during deploy/github only")
        self.tasks.add_log(db, task.task_id, "WriteCNAMENode", "skipped", "CNAME is only written after custom domain verification")
        domain = self.domains.create_zone(
            db,
            site_id=site.site_id,
            domain=payload["domain"],
            trace_id=task.trace_id,
            request_id=task.request_id,
            task_id=task.task_id,
            owner_user_id=payload.get("user_id"),
            domain_mode=payload.get("domain_mode", "custom_domain"),
            parent_domain=payload.get("parent_domain"),
            is_public_pool=int(bool(payload.get("is_public_pool", 0))),
        )
        self.tasks.add_log(db, task.task_id, "ReturnNSNode", "success", "nameservers returned", details={"ns": [domain.ns1, domain.ns2]})
        return {
            "site": model_dict(site),
            "domain": model_dict(domain),
            "next_step": "set NS then POST /api/v1/domains/{domain}/ns-check",
        }
