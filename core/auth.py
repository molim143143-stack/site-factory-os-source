import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.errors import AppException
from core.models import User


JWT_SECRET = os.getenv("SFS_JWT_SECRET", "site-factory-os-local-dev-secret")
JWT_ISSUER = "site-factory-os"
ACCESS_TTL_SECONDS = int(os.getenv("SFS_ACCESS_TTL_SECONDS", "3600"))
REFRESH_TTL_SECONDS = int(os.getenv("SFS_REFRESH_TTL_SECONDS", "604800"))


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _sign(message: str) -> str:
    return _b64url(hmac.new(JWT_SECRET.encode("utf-8"), message.encode("ascii"), hashlib.sha256).digest())


def create_token(user: User, *, token_type: str = "access", ttl_seconds: int | None = None) -> str:
    ttl = ttl_seconds if ttl_seconds is not None else (ACCESS_TTL_SECONDS if token_type == "access" else REFRESH_TTL_SECONDS)
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": JWT_ISSUER,
        "sub": user.user_id,
        "username": user.username,
        "role": user.role,
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
    }
    head = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(f"{head}.{body}")
    return f"{head}.{body}.{signature}"


def decode_token(token: str, *, expected_type: str = "access") -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise AppException("AUTH_TOKEN_INVALID", status_code=401)
    head, body, signature = parts
    if not hmac.compare_digest(_sign(f"{head}.{body}"), signature):
        raise AppException("AUTH_TOKEN_INVALID", status_code=401)
    try:
        payload = json.loads(_b64url_decode(body))
    except Exception as exc:
        raise AppException("AUTH_TOKEN_INVALID", status_code=401) from exc
    if payload.get("iss") != JWT_ISSUER or payload.get("type") != expected_type:
        raise AppException("AUTH_TOKEN_INVALID", status_code=401)
    if int(payload.get("exp", 0)) < int(time.time()):
        raise AppException("AUTH_TOKEN_EXPIRED", status_code=401)
    return payload


def get_current_user(authorization: str | None = Header(default=None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppException("AUTH_UNAUTHORIZED", status_code=401)
    payload = decode_token(authorization.split(" ", 1)[1].strip(), expected_type="access")
    user_id = payload.get("sub")
    db: Session = SessionLocal()
    try:
        user = db.get(User, user_id)
        if not user or user.status != "active":
            raise AppException("AUTH_TOKEN_INVALID", status_code=401)
        db.expunge(user)
        return user
    finally:
        db.close()


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in {"admin", "super_admin"}:
        raise AppException("AUTH_FORBIDDEN", details={"required_role": "admin"}, status_code=403)
    return user
