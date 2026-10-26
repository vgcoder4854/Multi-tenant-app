"""Unit tests for the tenant-safe helpers, using two organizations."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.errors import NotFoundError
import app.models.registry  # noqa: F401  (register all tables)
from app.models.enums import ProjectStatus
from app.models.identity import Organization
from app.models.work import Project
from app.services.tenant import assert_same_org, get_in_org, list_query


@pytest.fixture()
def db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    session = maker()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _org(db: Session, name: str) -> Organization:
    org = Organization(name=name, slug=name.lower())
    db.add(org)
    db.flush()
    return org


def test_get_in_org_returns_own_row(db: Session):
    org_a = _org(db, "Alpha")
    project = Project(org_id=org_a.id, name="P1", status=ProjectStatus.active)
    db.add(project)
    db.flush()

    assert get_in_org(db, Project, project.id, org_a.id).id == project.id


def test_get_in_org_hides_other_org_row_as_404(db: Session):
    org_a, org_b = _org(db, "Alpha"), _org(db, "Beta")
    project_b = Project(org_id=org_b.id, name="P1", status=ProjectStatus.active)
    db.add(project_b)
    db.flush()

    # Org A asking for Org B's project must get 404, not 403/200.
    with pytest.raises(NotFoundError):
        get_in_org(db, Project, project_b.id, org_a.id)


def test_get_in_org_missing_row_is_404(db: Session):
    org_a = _org(db, "Alpha")
    with pytest.raises(NotFoundError):
        get_in_org(db, Project, uuid.uuid4(), org_a.id)


def test_list_query_only_returns_own_org(db: Session):
    org_a, org_b = _org(db, "Alpha"), _org(db, "Beta")
    db.add_all([
        Project(org_id=org_a.id, name="A1", status=ProjectStatus.active),
        Project(org_id=org_a.id, name="A2", status=ProjectStatus.active),
        Project(org_id=org_b.id, name="B1", status=ProjectStatus.active),
    ])
    db.flush()

    names = {p.name for p in db.execute(list_query(Project, org_a.id)).scalars()}
    assert names == {"A1", "A2"}


def test_assert_same_org_raises_for_foreign_object(db: Session):
    org_a, org_b = _org(db, "Alpha"), _org(db, "Beta")
    project_b = Project(org_id=org_b.id, name="P1", status=ProjectStatus.active)
    db.add(project_b)
    db.flush()

    assert_same_org(org_a.id, None)  # None is ignored
    with pytest.raises(NotFoundError):
        assert_same_org(org_a.id, project_b)
