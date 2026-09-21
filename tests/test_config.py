"""Host allowlist configuration and HTTP enforcement without server sockets."""
import pytest

from app import create_app
from app.config import settings
from tests.conftest import make_container


DOMAIN = "inventarios-mensuales.calcoweb.net"


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    # Never depend on, or change, the operator's local .env.
    monkeypatch.setattr("app.config.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("TRUSTED_HOSTS", raising=False)


@pytest.mark.parametrize("value", [None, "", " , \t , "])
def test_empty_or_missing_hosts_keep_local_protection(monkeypatch, tmp_path, value):
    if value is not None:
        monkeypatch.setenv("TRUSTED_HOSTS", value)
    app = create_app({"TESTING": True, "APP_ENV": "testing", "AUTH_ENABLED": False},
                     container=make_container(tmp_path))
    assert set(app.config["TRUSTED_HOSTS"]) == {"localhost", "127.0.0.1"}
    client = app.test_client()
    assert client.get("/healthz", headers={"Host": "localhost"}).status_code == 200
    assert client.get("/healthz", headers={"Host": "127.0.0.1"}).status_code == 200
    assert client.get("/healthz", headers={"Host": DOMAIN}).status_code == 400


def test_hosts_split_trim_and_keep_local_hosts(monkeypatch):
    monkeypatch.setenv("TRUSTED_HOSTS", f"  {DOMAIN} , , extra.example.test , {DOMAIN}  ")
    hosts = settings()["TRUSTED_HOSTS"]
    assert set(hosts) == {"localhost", "127.0.0.1", DOMAIN, "extra.example.test"}
    assert len(hosts) == 4


@pytest.mark.parametrize("value", [
    "*", "localhost, *", "*.calcoweb.net", "inventarios-*.calcoweb.net",
    " .calcoweb.net ", f"{DOMAIN},*",
])
def test_host_wildcards_are_rejected(monkeypatch, value):
    monkeypatch.setenv("TRUSTED_HOSTS", value)
    with pytest.raises(ValueError, match="TRUSTED_HOSTS"):
        settings()


@pytest.mark.parametrize("host,status", [
    ("localhost", 200),
    ("127.0.0.1", 200),
    ("127.0.0.1:8089", 200),
    (DOMAIN, 200),
    (f"{DOMAIN}:443", 200),
    ("unauthorized.example", 400),
    (f"sub.{DOMAIN}", 400),
    (f"{DOMAIN}.unauthorized.example", 400),
    ("inventarios-uno-a-uno.calcoweb.net", 400),
])
def test_configured_hosts_are_enforced(monkeypatch, tmp_path, host, status):
    monkeypatch.setenv("TRUSTED_HOSTS", f" localhost , 127.0.0.1 , {DOMAIN} ")
    container = make_container(tmp_path)
    app = create_app({"TESTING": True, "APP_ENV": "testing", "AUTH_ENABLED": False},
                     container=container)
    response = app.test_client().get("/healthz", headers={"Host": host})
    assert response.status_code == status
    if status == 200:
        assert response.json == {"status": "ok"}
    assert container.drive.calls == container.sheets.reads == container.sheets.writes == 0
