import os

os.environ.setdefault("JWT_SECRET", "test-secret-" + "0" * 32)
os.environ.setdefault("FERNET_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "changeme-admin-123")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.db import get_db  # noqa: E402
from app.core.ratelimit import limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402

limiter.enabled = False
from app.models import Base, Manufacturer, SystemRole, SystemUser  # noqa: E402
from app.seed import seed_manufacturers, seed_profiles  # noqa: E402

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture
def db():
    Base.metadata.create_all(engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def seeded(db):
    mfrs = seed_manufacturers(db)
    seed_profiles(db, mfrs)
    db.add(
        SystemUser(
            username="admin", email="admin@example.com", full_name="Admin",
            role=SystemRole.superadmin, is_active=True,
            password_hash=hash_password("changeme-admin-123"),
        )
    )
    db.commit()
    return db


@pytest.fixture
def client(seeded):
    def _override_db():
        yield seeded

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "changeme-admin-123"})
    assert r.status_code == 200, r.text
    client.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
    return client


def first_manufacturer_id(db) -> int:
    return db.query(Manufacturer).filter_by(name="huawei").one().id
