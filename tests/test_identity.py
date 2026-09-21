"""Fake identities exist only in tests; every fake-identity app uses TESTING."""
import pytest
from app import create_app
from app.constants import ADMIN_EMAIL
from tests.conftest import make_container, rpc
from tests.fakes import payload

ADMIN_METHODS = (
    "obtenerConteoConsolidadoPDV",
    "generarDescargaConteosMensuales",
    "generarPlanoSiesaMensual",
)


@pytest.mark.parametrize("email,allowed", [
    ("empleado@crepesywafflesantioquia.com", False),
    (ADMIN_EMAIL, True),
    (" INFO.COSTOS@CREPESYWAFFLESANTIOQUIA.COM ", True),
    ("", False),
    ("   ", False),
    (None, False),
])
def test_authenticated_identity_authorizes_each_operation(email, allowed, client, container):
    assert client.application.testing
    container.inventory.finalize(payload())
    container.identity.provider = lambda: email
    state = rpc(client, "obtenerEstadoAdministrador")
    assert state.json["result"] == {"esAdministrador": allowed}
    filters = dict(fecha="2026-09-18", puntoVenta="BR00 - PDV 0", bodega="BR03", consecutivo="897")
    before = container.drive.calls + container.sheets.reads
    for method in ADMIN_METHODS:
        response = rpc(client, method, filters)
        assert response.status_code == (200 if allowed else 403)
    if not allowed:
        assert container.drive.calls + container.sheets.reads == before


@pytest.mark.parametrize("email", [None, "empleado@crepesywafflesantioquia.com"])
def test_browser_cannot_forge_identity(email, client, container):
    container.identity.provider = lambda: email
    headers = {
        "X-Monthly-Request": "1", "Origin": "http://localhost",
        "X-User-Email": ADMIN_EMAIL, "X-Forwarded-Email": ADMIN_EMAIL,
        "X-Auth-Request-Email": ADMIN_EMAIL,
        "Authorization": "Basic aW5mby5jb3N0b3NAY3JlcGVzeXdhZmZsZXNhbnRpb3F1aWEuY29tOg==",
    }
    for method in ADMIN_METHODS:
        response = client.post("/api/" + method + "?email=" + ADMIN_EMAIL,
                               json={"args": [{"email": ADMIN_EMAIL}], "email": ADMIN_EMAIL},
                               headers=headers)
        assert response.status_code == 403
    assert container.drive.calls == container.sheets.reads == container.sheets.writes == 0


def test_default_identity_never_uses_google_oauth(tmp_path, monkeypatch):
    c = make_container(tmp_path, admin=False)
    monkeypatch.setattr(c.auth, "credentials", lambda: pytest.fail("OAuth is not browser identity"))
    client = create_app({"TESTING": False}, container=c).test_client()
    assert rpc(client, "obtenerEstadoAdministrador").json["result"] == {"esAdministrador": False}
    for method in ADMIN_METHODS:
        assert rpc(client, method, {}).status_code == 403


def test_identity_is_checked_again_for_each_request(client, container):
    assert rpc(client, "obtenerEstadoAdministrador").json["result"]["esAdministrador"]
    container.identity.provider = lambda: "empleado@crepesywafflesantioquia.com"
    for method in ADMIN_METHODS:
        assert rpc(client, method, {}).status_code == 403
