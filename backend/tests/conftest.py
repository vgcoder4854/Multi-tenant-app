"""Shared pytest fixtures.

Strategy: point ``DATABASE_URL`` at a dedicated SQLite file *before* importing the
app, run the real Alembic migrations once per session (so triggers/indexes exist),
then give each test an outer transaction that is rolled back at the end. Services
call ``commit()`` which, with ``join_transaction_mode="create_savepoint"``, only
releases a savepoint — the outer rollback still cleans everything up.
"""
from __future__ import annotations

import os
import pathlib

# --- Configure the test database BEFORE importing app modules -------------
BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
TEST_DB_PATH = BACKEND_DIR / "test_app.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ENVIRONMENT"] = "test"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.database import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrated_schema():
    """Create the schema once using the real migrations (includes the trigger)."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")
    yield
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink(missing_ok=True)


@pytest.fixture()
def db() -> Session:
    """A session wrapped in a transaction that is rolled back after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db: Session) -> TestClient:
    """TestClient whose DB dependency uses the rolled-back test session."""

    def _override_get_db():
        try:
            yield db
        except Exception:
            db.rollback()
            raise

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# Convenience auth helpers
# --------------------------------------------------------------------------- #
@pytest.fixture()
def login(client: TestClient):
    """Return a function that logs a user in and (optionally) switches workspace."""

    def _login(email: str, password: str = "Password123!", org_id=None) -> dict[str, str]:
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        if org_id is not None:
            resp = client.post(
                "/api/v1/auth/switch-organization",
                json={"org_id": str(org_id)},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200, resp.text
            token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login
