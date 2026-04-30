from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.env_loader import load_env_file

load_env_file()

from api.bulk_api import router as bulk_router
from api.builder_api import router as builder_router
from api.cms_api import router as cms_router
from api.deploy_api import router as deploy_router
from api.domain_api import router as domain_router
from api.i18n_api import router as i18n_router
from api.membership_api import router as membership_router
from api.payment_api import router as payment_router
from api.seo_api import router as seo_router
from api.site_api import router as site_router
from api.system_api import router as system_router
from api.task_api import router as task_router
from core.database import SessionLocal, init_db
from core.error_engine import ErrorEngine
from core.errors import AppException
from core.utils import new_id
from integrations.github import GitHubIntegration


app = FastAPI(title="Site Factory OS", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    GitHubIntegration().startup_check()


@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    request.state.trace_id = request.headers.get("x-trace-id") or new_id("trace")
    return await call_next(request)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    exc.trace_id = exc.trace_id or getattr(request.state, "trace_id", None)
    payload = exc.payload()
    db = SessionLocal()
    try:
        ErrorEngine().record(
            db,
            payload["error"]["error_code"],
            payload["error"]["message"],
            trace_id=payload["error"]["trace_id"],
            request_id=payload["error"]["request_id"],
            task_id=exc.task_id,
            site_id=exc.site_id,
            details=payload["error"]["details"],
        )
    finally:
        db.close()
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(Exception)
async def unknown_exception_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", None)
    db = SessionLocal()
    try:
        ErrorEngine().record(db, "SYSTEM_INTERNAL_EXCEPTION", str(exc), trace_id=trace_id)
    finally:
        db.close()
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "error_code": "SYSTEM_INTERNAL_EXCEPTION",
                "message": str(exc),
                "severity": "CRITICAL",
                "retryable": False,
                "user_action_required": False,
                "details": {},
                "trace_id": trace_id,
                "request_id": None,
            }
        },
    )


@app.get("/")
def root():
    return {"status": "running", "api": "/api/v1"}


app.include_router(system_router)
app.include_router(site_router)
app.include_router(domain_router)
app.include_router(deploy_router)
app.include_router(task_router)
app.include_router(membership_router)
app.include_router(cms_router)
app.include_router(payment_router)
app.include_router(bulk_router)
app.include_router(i18n_router)
app.include_router(seo_router)
app.include_router(builder_router)
