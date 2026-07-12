import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sfplatform.db import SessionLocal

_BACKEND_DIR = Path(__file__).resolve().parent.parent  # tests/ -> backend/


def _alembic(*args: str, check: bool) -> None:
    env = {**os.environ, "PYTHONPATH": str(_BACKEND_DIR / "src")}
    subprocess.run([sys.executable, "-m", "alembic", *args],
                   cwd=_BACKEND_DIR, env=env, check=check)


@pytest.fixture(scope="session", autouse=True)
def _migrate():
    _alembic("downgrade", "base", check=False)
    _alembic("upgrade", "head", check=True)

    from sfplatform.seed import seed
    seed()


@pytest.fixture()
def db_session():
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def client():
    from sfplatform.app import app
    return TestClient(app, headers={"X-Tenant-Id": "1"})
