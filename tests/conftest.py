from pathlib import Path
import pytest
from app.config import settings
from app.container import Container
from app import create_app
from app.constants import ADMIN_EMAIL
from tests.fakes import FakeDrive, FakeSheets


def make_container(tmp_path, points=1, delay=0, admin=True):
    config = settings()
    config.update(TESTING=True, RUNTIME_DIR=tmp_path, FORMATS_FOLDER_ID="formats", MONTHLY_FOLDER_ID="monthly")
    return Container(config, drive=FakeDrive(points, delay), sheets=FakeSheets(points, delay),
                     identity_provider=(lambda: ADMIN_EMAIL) if admin else None)


@pytest.fixture
def container(tmp_path):
    return make_container(tmp_path)


@pytest.fixture
def client(container):
    return create_app({"TESTING": True}, container=container).test_client()


def rpc(client, method, *args):
    return client.post("/api/" + method, json={"args": list(args)},
                       headers={"X-Monthly-Request": "1", "Origin": "http://localhost"})
