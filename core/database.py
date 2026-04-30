from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> None:
    from core import models  # noqa: F401
    from core.models import Membership, User
    from core.utils import now_iso, sha256_text

    Base.metadata.create_all(bind=engine)
    ensure_schema_columns()
    db = SessionLocal()
    try:
        now = now_iso()
        user = db.get(User, "user_candy2000")
        if not user:
            user = User(
                user_id="user_candy2000",
                username="candy2000",
                email="candy2000@example.com",
                password_hash=sha256_text("candy2000"),
                role="super_admin",
                status="active",
                created_at=now,
                updated_at=now,
            )
            db.add(user)
        membership = db.query(Membership).filter(Membership.user_id == "user_candy2000").first()
        if not membership:
            membership = Membership(
                membership_id="mem_candy2000",
                user_id="user_candy2000",
                plan="enterprise",
                status="active",
                started_at=now,
                expires_at="2099-01-01T00:00:00+00:00",
                site_limit=999999,
                deploy_limit_per_day=999999,
                device_limit=999999,
                can_use_bulk_import=1,
                can_use_telegram=1,
                can_use_diy_builder=1,
                can_use_i18n=1,
                can_use_payment_links=1,
                can_use_roles=1,
                can_use_advanced_audit=1,
                created_at=now,
                updated_at=now,
            )
            db.add(membership)
        db.commit()
    finally:
        db.close()


def ensure_schema_columns() -> None:
    additions = {
        "sites": {
            "public_url": "TEXT",
        },
        "domains": {
            "owner_user_id": "TEXT",
            "is_public_pool": "INTEGER DEFAULT 0",
            "domain_mode": "TEXT DEFAULT 'custom_domain'",
            "parent_domain": "TEXT",
            "full_domain": "TEXT",
        },
    }
    with engine.begin() as conn:
        for table, columns in additions.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()}
            for column, definition in columns.items():
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
