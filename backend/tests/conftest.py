from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Resolve to the main repo's sample data (works from worktree too)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
SAMPLE_DIR = os.path.join(_REPO_ROOT, "vanjski-podaci", "primjeri-excel-ponuda")
if not os.path.isdir(SAMPLE_DIR):
    # Fallback: try the main repo root (outside worktree)
    SAMPLE_DIR = "/media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/vanjski-podaci/primjeri-excel-ponuda"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_xlsx_path():
    path = os.path.join(SAMPLE_DIR, "Eurospin_SO_Soboslikarski.xlsx")
    if not os.path.exists(path):
        pytest.skip(f"Sample file not found: {path}")
    return path


@pytest.fixture
def sample_xlsx_bytes(sample_xlsx_path):
    with open(sample_xlsx_path, "rb") as f:
        return f.read()


@pytest.fixture
def second_sample_path():
    path = os.path.join(SAMPLE_DIR, "Eurospin_SO_GK radovi_prijedlog cijena.xlsx")
    if not os.path.exists(path):
        pytest.skip(f"Sample file not found: {path}")
    return path
