import os
import sys
import tempfile
import pathlib
import unittest.mock
from contextlib import asynccontextmanager
import pytest
import uuid
import datetime

_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_db_path = pathlib.Path(_db_file.name).as_posix()
_db_file.close()

os.environ["GIIPS_JWT_SECRET"] = "test-secret-key-for-ci"
os.environ["REDIS_URL"] = ""
os.environ["S3_ENDPOINT_URL"] = ""
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

sys.modules["sentence_transformers"] = unittest.mock.MagicMock()

import database

database.seed_synthetic_data = lambda *a, **kw: None
database.topup_wards = lambda *a, **kw: None
database.backfill_wards_and_incidents = lambda *a, **kw: None
database.backfill_complaint_user_ids = lambda *a, **kw: None
database.migrate_old_departments = lambda *a, **kw: None
database.backfill_officer_departments = lambda *a, **kw: None
database.seed_default_executive = lambda *a, **kw: None

from database import Base, engine, seed_demo_users

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
seed_demo_users()

from app import app
from fastapi.testclient import TestClient
from auth_service import create_access_token
from database import User, SessionLocal


@asynccontextmanager
async def _test_lifespan(app):
    from database import Base, engine
    Base.metadata.create_all(bind=engine)
    yield


app.router.lifespan_context = _test_lifespan


@pytest.fixture(scope="session")
def client():
    c = TestClient(app, headers={"Origin": "http://testserver"})
    yield c


@pytest.fixture(scope="session")
def db_session():
    sess = SessionLocal()
    yield sess
    sess.close()


@pytest.fixture(scope="session")
def demo_citizen(db_session):
    user = db_session.query(User).filter(User.email == "citizen@giips.gov.in").first()
    return user


@pytest.fixture(scope="session")
def demo_officer(db_session):
    user = db_session.query(User).filter(User.email == "officer1@giips.gov.in").first()
    return user


@pytest.fixture(scope="session")
def citizen_token(demo_citizen):
    return create_access_token({"sub": demo_citizen.email, "role": "Citizen"})


@pytest.fixture(scope="session")
def officer_token(demo_officer):
    return create_access_token({"sub": demo_officer.email, "role": "Officer"})


@pytest.fixture(scope="session")
def citizen_auth(citizen_token):
    return {"Authorization": f"Bearer {citizen_token}"}


@pytest.fixture(scope="session")
def officer_auth(officer_token):
    return {"Authorization": f"Bearer {officer_token}"}
