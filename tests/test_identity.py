"""Fake identities exist only in tests; every fake-identity app uses TESTING."""
import pytest
from app import create_app
from app.services.identity import IdentityService
from tests.conftest import make_container, rpc
from tests.fakes import ADMIN_LOGIN, SECOND_ADMIN_LOGIN, payload, seed_factors

ADMIN_METHODS = (
    "obtenerConteoConsolidadoPDV",
    "generarDescargaConteosMensuales",
    "generarPlanoSiesaMensual",
)


@pytest.mark.parametrize("username,allowed", [
    ("empleado.pruebas", False),
    (ADMIN_LOGIN, True),
    (" " + ADMIN_LOGIN.upper() + " ", True),
    (SECOND_ADMIN_LOGIN, True),
    (" " + SECOND_ADMIN_LOGIN.upper() + " ", True),
    ("empleado@example.test", False),
    ("", False),
    ("   ", False),
    (None, False),
])
def test_authenticated_identity_authorizes_each_operation(username, allowed, client, container):
    assert client.application.testing
    seed_factors(container)
    container.inventory.finalize(payload())
    container.identity.provider = lambda: username
    state = rpc(client, "obtenerEstadoAdministrador")
    assert state.json["result"] == {"esAdministrador": allowed}
    filters = dict(fecha="2026-09-18", puntoVenta="BR00 - PDV 0", bodega="BR03", consecutivo="897")
    before = container.drive.calls + container.sheets.reads
    for method in ADMIN_METHODS:
        response = rpc(client, method, filters)
        assert response.status_code == (200 if allowed else 403)
    if not allowed:
        assert container.drive.calls + container.sheets.reads == before


@pytest.mark.parametrize("username", [None, "empleado.pruebas"])
def test_browser_cannot_forge_identity(username, client, container):
    container.identity.provider = lambda: username
    headers = {
        "X-Monthly-Request": "1", "Origin": "http://localhost",
        "X-User-Login": ADMIN_LOGIN, "X-Forwarded-User": ADMIN_LOGIN,
        "X-Auth-Request-User": ADMIN_LOGIN, "X-User-Email": ADMIN_LOGIN,
        "Authorization": "Basic aW5mby5jb3N0b3NAY3JlcGVzeXdhZmZsZXNhbnRpb3F1aWEuY29tOg==",
    }
    for method in ADMIN_METHODS:
        response = client.post("/api/" + method + "?usuario=" + ADMIN_LOGIN,
                               json={"args": [{"usuario": ADMIN_LOGIN}], "sub": ADMIN_LOGIN},
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
    container.identity.provider = lambda: "empleado.pruebas"
    for method in ADMIN_METHODS:
        assert rpc(client, method, {}).status_code == 403


@pytest.mark.parametrize("configured", ["", " , , "])
def test_empty_admin_list_has_no_implicit_admins(configured):
    for username in (ADMIN_LOGIN, SECOND_ADMIN_LOGIN, "info.costos@crepesywafflesantioquia.com",
                     "juan.zapata@crepesywaffles.com", "juan.zapata"):
        assert not IdentityService(lambda: username, admin_logins=configured).is_admin()


def test_admin_list_normalizes_and_uses_exact_logins():
    service = IdentityService(lambda: " ADMIN.PRUEBAS ", admin_logins=" admin.pruebas, , SUPERVISOR.PRUEBAS,admin.pruebas ")
    assert service.admin_logins == {ADMIN_LOGIN, SECOND_ADMIN_LOGIN}
    assert service.is_admin()
    service.provider = lambda: "admin.pruebas@example.test"
    assert not service.is_admin()


@pytest.mark.parametrize("configured", ["*", "admin.*", "admin\nforged", "x" * 257, None])
def test_invalid_admin_list_is_rejected(configured):
    with pytest.raises(ValueError, match="ADMIN_USER_LOGINS"):
        IdentityService(admin_logins=configured)
