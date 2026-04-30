import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config import BASE_DIR
from core.builder_engine import BLOCK_LIBRARY, BLOCK_SCHEMAS, BuilderEngine
from core.database import get_db
from core.errors import require_fields
from core.models import Page
from core.task_engine import TaskEngine
from core.utils import model_dict

router = APIRouter(prefix="/api/v1")
builder = BuilderEngine()
tasks = TaskEngine()


def _template_items() -> list[dict]:
    index_path = BASE_DIR / "template_library" / "meta" / "templates.index.json"
    if not index_path.exists():
        return []
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    items = data.get("templates", data if isinstance(data, list) else [])
    available = []
    for item in items:
        if item.get("status") != "available" or not item.get("can_use_in_builder"):
            continue
        if not item.get("page_schema") and item.get("normalized_path"):
            schema_path = BASE_DIR / item["normalized_path"] / "page.schema.json"
            if schema_path.exists():
                try:
                    item["page_schema"] = json.loads(schema_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    item["page_schema"] = {"blocks": []}
        if item.get("id"):
            item["preview_image_url"] = f"/api/v1/builder/templates/{item['id']}/preview.png"
        available.append(item)
    return available


@router.post("/sites/{site_id}/pages")
def create_page(site_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="page_create", payload=data, site_id=site_id, trace_id=request.state.trace_id, action=lambda task: {"page": model_dict(builder.create_page(db, site_id, data))}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.get("/sites/{site_id}/pages")
def list_pages(site_id: str, db: Session = Depends(get_db)):
    return {"items": [model_dict(p) for p in db.query(Page).filter(Page.site_id == site_id).all()]}


@router.get("/pages/{page_id}")
def get_page(page_id: str, db: Session = Depends(get_db)):
    return model_dict(db.get(Page, page_id))


@router.patch("/pages/{page_id}")
def patch_page(page_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    row = db.get(Page, page_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="page_update", payload=data, site_id=row.site_id if row else None, trace_id=request.state.trace_id, action=lambda task: {"page": model_dict(builder.update_page(db, page_id, data))}, lock=False)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/pages/{page_id}/preview")
def preview_page(page_id: str, data: dict | None = None, db: Session = Depends(get_db)):
    page = db.get(Page, page_id)
    return {"page_id": page_id, "html": f"<html><body>{page.layout_json if page else ''}</body></html>"}


@router.post("/pages/{page_id}/publish")
def publish_page(page_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    page = db.get(Page, page_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="diy_publish", payload=data, site_id=page.site_id if page else None, trace_id=request.state.trace_id, action=lambda task: builder.publish_page(db, task=task, page_id=page_id), lock=True)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/pages/{page_id}/rollback")
def rollback_page(page_id: str, data: dict, request: Request, db: Session = Depends(get_db)):
    require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    page = db.get(Page, page_id)
    task, result, created = tasks.run(db, request_id=data["request_id"], task_type="page_rollback", payload=data, site_id=page.site_id if page else None, trace_id=request.state.trace_id, action=lambda task: {"page_id": page_id, "status": "rolled_back"}, lock=True)
    return {"task_id": task.task_id, "trace_id": task.trace_id, "idempotent": not created, **result}


@router.post("/pages/{page_id}/blocks")
@router.patch("/blocks/{page_id}")
@router.delete("/blocks/{page_id}")
@router.post("/pages/{page_id}/blocks/reorder")
def block_ops(page_id: str, data: dict | None = None, request: Request = None, db: Session = Depends(get_db)):
    data = data or {}
    if request and request.method != "GET":
        require_fields(data, ["request_id"], data.get("request_id"), request.state.trace_id)
    return {"page_id": page_id, "operation": "recorded", "request_id": data.get("request_id")}


@router.get("/builder/block-library")
def block_library():
    return {"items": [{"type": item, "schema": BLOCK_SCHEMAS[item]} for item in BLOCK_LIBRARY]}


@router.get("/builder/themes")
def themes():
    return {"items": ["default", "shop", "blog", "landing"]}


@router.get("/builder/templates")
def template_library():
    return {"items": _template_items()}


@router.get("/builder/templates/{template_id}/preview.png")
def template_preview(template_id: str):
    for item in _template_items():
        if item.get("id") != template_id:
            continue
        normalized = (BASE_DIR / item.get("normalized_path", "")).resolve()
        library_root = (BASE_DIR / "template_library" / "normalized").resolve()
        if library_root not in normalized.parents and normalized != library_root:
            break
        preview = normalized / "preview.png"
        if preview.exists():
            return FileResponse(preview, media_type="image/png")
        break
    raise HTTPException(status_code=404, detail="template preview not found")
