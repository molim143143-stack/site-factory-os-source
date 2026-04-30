from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.deploy_engine import DeployEngine
from core.errors import require_fields
from core.models import Deployment, DeploymentFile
from core.task_engine import TaskEngine
from core.utils import model_dict

router = APIRouter(prefix="/api/v1")
deploys = DeployEngine()
tasks = TaskEngine()


@router.post("/sites/{site_id}/deployments")
def create_deployment(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)

    def action(task):
        deploy = deploys.deploy(db, site_id=site_id, task_id=task.task_id, trace_id=task.trace_id, request_id=task.request_id, deploy_type=data.get("deploy_type", "site"))
        return {"deployment": model_dict(deploy)}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="deploy", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=action, lock=True)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.get("/sites/{site_id}/deployments")
def list_deployments(site_id: str, db: Session = Depends(get_db)):
    rows = db.query(Deployment).filter(Deployment.site_id == site_id).order_by(Deployment.created_at.desc()).all()
    return {"items": [model_dict(r) for r in rows]}


@router.get("/deployments")
def list_all_deployments(db: Session = Depends(get_db)):
    rows = db.query(Deployment).order_by(Deployment.created_at.desc()).limit(100).all()
    return {"items": [model_dict(r) for r in rows]}


@router.get("/deployments/{deploy_id}")
def get_deployment(deploy_id: str, db: Session = Depends(get_db)):
    return model_dict(db.get(Deployment, deploy_id))


@router.post("/deployments/{deploy_id}/rollback")
def rollback(deploy_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    source = db.get(Deployment, deploy_id)
    site_id = source.site_id if source else None

    def action(task):
        deploy = deploys.rollback(db, deploy_id=deploy_id, task_id=task.task_id, trace_id=task.trace_id, request_id=task.request_id)
        return {"deployment": model_dict(deploy)}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="rollback", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=action, lock=True)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.get("/deployments/{deploy_id}/logs")
def deployment_logs(deploy_id: str, db: Session = Depends(get_db)):
    files = db.query(DeploymentFile).filter(DeploymentFile.deploy_id == deploy_id).all()
    return {"files": [model_dict(f) for f in files]}


@router.post("/deploy/github")
def deploy_github(data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id", "site_id"], data.get("request_id"), request.state.trace_id)
    site_id = data["site_id"]

    def action(task):
        deploy = deploys.deploy(
            db,
            site_id=site_id,
            task_id=task.task_id,
            trace_id=task.trace_id,
            request_id=task.request_id,
            deploy_type="github_pages",
            require_dns=False,
        )
        return {"deployment": model_dict(deploy), "github_pages_url": deploy.repo_name and deploy.live_url, "public_url": deploy.live_url, "dist_path": deploy.dist_path}

    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="deploy_github", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=action, lock=True)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.get("/deploy/status/{site_id}")
def deploy_status(site_id: str, db: Session = Depends(get_db)):
    row = db.query(Deployment).filter(Deployment.site_id == site_id).order_by(Deployment.created_at.desc()).first()
    return {"site_id": site_id, "deployment": model_dict(row) if row else None, "github_pages_url": row.live_url if row else "", "public_url": row.live_url if row else ""}


@router.get("/deploy/logs/{site_id}")
def deploy_logs(site_id: str, db: Session = Depends(get_db)):
    rows = db.query(Deployment).filter(Deployment.site_id == site_id).order_by(Deployment.created_at.desc()).limit(10).all()
    items = []
    for deploy in rows:
        files = db.query(DeploymentFile).filter(DeploymentFile.deploy_id == deploy.deploy_id).all()
        items.append({"deployment": model_dict(deploy), "files": [model_dict(file) for file in files]})
    return {"site_id": site_id, "items": items}
