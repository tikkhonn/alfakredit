import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import deps
from app.db import get_session
from app.demo_state import reset_chaos
from app.main import app
from app.seed import build_registry, ensure_demo_queue, seed_if_empty


@pytest.fixture
def client():
    deps.REGISTRY = build_registry()
    reset_chaos()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    with TestingSession() as session:
        seed_if_empty(session)
        ensure_demo_queue(session)

    def override_session():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    reset_chaos()
    deps.REGISTRY = build_registry()
