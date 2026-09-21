from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import shutil
import subprocess
import uuid
from unittest.mock import Mock

import jwt
import pytest
from flask import request
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec

from app import create_app
from app.constants import ADMIN_EMAIL
from tests.conftest import make_container, rpc
from tests.fakes import payload as inventory_payload
from app.services.session_auth_service import ReplayCache, SessionAuthService

HEADERS = {'X-Monthly-Request': '1', 'Origin': 'http://localhost'}


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        value = 1800000000

        def advance(self, seconds):
            self.value += seconds

    clock = Clock()

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromtimestamp(clock.value, tz=tz or timezone.utc)

    monkeypatch.setattr(jwt.api_jwt, 'datetime', FrozenDateTime)
    monkeypatch.setattr(SessionAuthService, 'now', staticmethod(lambda: clock.value))
    return clock


@pytest.fixture(scope='module')
def private_key():
    # Ephemeral test key in RAM; never saved or used by application configuration.
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def auth_config(tmp_path, private_key):
    public = tmp_path / 'public.pem'
    public.write_bytes(private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return {'TESTING': True, 'APP_ENV': 'testing', 'DEBUG': False, 'AUTH_ENABLED': True,
            'SSO_PUBLIC_KEY_PATH': str(public), 'SESSION_COOKIE_SECURE': False,
            'SESSION_JWT_SECRET': 'test-only-0123456789-ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            'SESSION_IDLE_TIMEOUT_SECONDS': 1200}


@pytest.fixture
def app(auth_config, clock, tmp_path):
    return create_app(auth_config, container=make_container(tmp_path))


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def token(private_key, clock):
    def make(changes=None, omit=(), key=None, algorithm='RS256', headers=None):
        claims = {'iss': 'calco-intranet', 'aud': 'inventarios-mensuales', 'sub': 'wp.usuario', 'usuario': 'wp.usuario', 'email': 'empleado@crepesywafflesantioquia.com',
                  'iat': clock.value, 'nbf': clock.value, 'exp': clock.value + 60, 'jti': uuid.uuid4().hex}
        claims.update(changes or {})
        for field in omit:
            claims.pop(field)
        return jwt.encode(claims, key if key is not None else private_key, algorithm=algorithm, headers=headers)
    return make


def login(client, token):
    response = client.post('/auth/sso', data={'token': token()})
    assert response.status_code == 303
    return response


def claims(app, client):
    return app.extensions['session_auth'].read_session(client.get_cookie(app.config['SESSION_JWT_COOKIE_NAME']).value)


def test_valid_sso_cookie_and_protected_inventory(app, client, token, clock):
    sso = token()
    response = client.post('/auth/sso', data={'token': sso})
    assert response.status_code == 303 and response.location == '/'
    cookie = response.headers['Set-Cookie']
    assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie and 'Path=/' in cookie
    assert 'Max-Age=1200' in cookie and 'Domain=' not in cookie
    assert sso not in cookie and sso not in response.text and sso not in response.location
    session = claims(app, client)
    assert session['sub'] == 'wp.usuario'
    assert session['exp'] == clock.value + 1200
    assert jwt.get_unverified_header(client.get_cookie('inventario_mensual_session').value)['alg'] == 'HS256'
    assert client.get('/').status_code == 200
    assert rpc(client,'obtenerPuntosVenta').json['result'] == ['BR00 - PDV 0']
    assert rpc(client,'guardarInventario',inventory_payload()).json['result']['correcto']


@pytest.mark.parametrize('changes', [
    {'iss': 'wrong'}, {'aud': 'wrong'}, {'aud': ['inventarios-mensuales']},
    {'sub': ''}, {'sub': '   '}, {'sub': 1}, {'jti': ''}, {'jti': 7},
    {'iat': 1800000011}, {'nbf': 1800000011},
    {'iat': 1799999800, 'nbf': 1799999800, 'exp': 1799999860},
    {'exp': 1800000061}, {'iat': '1800000000'}, {'nbf': True}, {'exp': 1800000060.5},
    {'nbf': 1799999999}, {'exp': 1800000000},
])
def test_invalid_sso_claims(client, token, changes):
    response = client.post('/auth/sso', data={'token': token(changes)})
    assert response.status_code == 401
    assert not client.get_cookie('inventario_mensual_session')


@pytest.mark.parametrize('field', ['iss', 'aud', 'sub', 'email', 'iat', 'nbf', 'exp', 'jti'])
def test_missing_sso_claim(client, token, field):
    assert client.post('/auth/sso', data={'token': token(omit=[field])}).status_code == 401


def test_invalid_signature(client, token):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert client.post('/auth/sso', data={'token': token(key=other_key)}).status_code == 401


@pytest.mark.parametrize('algorithm,key', [('HS256', 'test-only-other-secret-0123456789abcdef'), ('none', '')])
def test_wrong_sso_algorithm(client, token, algorithm, key):
    assert client.post('/auth/sso', data={'token': token(key=key, algorithm=algorithm)}).status_code == 401


@pytest.mark.parametrize('headers', [{'typ': 'OTHER'}, {'crit': ['unknown']}])
def test_invalid_sso_header(client, token, headers):
    assert client.post('/auth/sso', data={'token': token(headers=headers)}).status_code == 401


def test_replay_single_use_across_clients(app, token):
    encoded = token()
    assert app.test_client().post('/auth/sso', data={'token': encoded}).status_code == 303
    assert app.test_client().post('/auth/sso', data={'token': encoded}).status_code == 401


def test_replay_atomic_and_ttl():
    cache = ReplayCache()
    def consume(_):
        try:
            cache.consume('same-jti', 150, 100)
            return True
        except jwt.InvalidTokenError:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(consume, range(32))) == 1
    with pytest.raises(jwt.InvalidTokenError):
        cache.consume('same-jti', 150, 189)
    cache.consume('same-jti', 250, 190)


def test_clock_skew_at_most_ten_seconds(client, token, clock):
    encoded = token()
    clock.advance(69)
    assert client.post('/auth/sso', data={'token': encoded}).status_code == 303
    encoded = token()
    clock.advance(70)
    assert client.post('/auth/sso', data={'token': encoded}).status_code == 401


def test_sso_never_accepts_query_or_json_identity(client, token):
    encoded = token()
    assert client.get('/auth/sso', query_string={'token': encoded}).status_code in {401, 405}
    assert client.post('/auth/sso', query_string={'token': encoded}).status_code == 401
    assert client.post('/auth/sso?usuario=ZmFrZQ==', data={'token': encoded}).status_code == 401
    assert client.post('/auth/sso', json={'token': encoded}).status_code == 401
    assert client.get('/?usuario=ZmFrZQ==').status_code == 401


@pytest.mark.parametrize('path,method', [('/', 'get'), ('/api/obtenerPuntosVenta', 'post'),
    ('/api/obtenerCategorias', 'post'), ('/api/obtenerProductos', 'post'), ('/api/guardarInventario', 'post'),
    ('/auth/activity', 'post'), ('/auth/logout', 'post'), ('/auth/status', 'post'),
    ('/static/js/monthly.js', 'get'), ('/unknown', 'get')])
def test_routes_require_session(client, path, method):
    response = getattr(client, method)(path)
    assert response.status_code == 401
    if path.startswith(('/api/', '/auth/')):
        assert response.json == {'error': 'Sesión expirada. Ingrese nuevamente desde la intranet.'}
    else:
        assert 'Acceso requerido.' in response.text


def test_health_and_access_screen_are_public(app, client):
    assert client.get('/healthz').status_code == 200
    assert client.get('/healthz').json == {'status': 'ok'}
    expired = client.get('/auth/expired')
    assert expired.status_code == 401 and 'Sesión cerrada por inactividad.' in expired.text
    assert 'href=' not in expired.text
    app.config['INTRANET_URL'] = 'https://intranet.example.test/'
    assert 'href="https://intranet.example.test/"' in client.get('/').text


def test_sliding_activity_and_exact_idle_expiration(app, client, token, clock):
    login(client, token)
    sid = claims(app, client)['sid']
    for elapsed in [600, 900, 1140]:
        clock.advance(elapsed)
        response = client.post('/auth/activity', headers=HEADERS)
        assert response.status_code == 204
        assert claims(app, client)['sid'] == sid
        assert claims(app, client)['exp'] == clock.value + 1200
    clock.advance(1199)
    assert rpc(client,'obtenerPuntosVenta').status_code == 200
    clock.advance(1)
    assert rpc(client,'obtenerPuntosVenta').status_code == 401
    response = client.post('/auth/activity', headers=HEADERS)
    assert response.status_code == 401 and 'Set-Cookie' not in response.headers


def test_delayed_heartbeat_uses_last_event_time(app, client, token, clock):
    login(client, token)
    clock.advance(100)
    response = client.post('/auth/activity', json={'idle_seconds': 30}, headers=HEADERS)
    assert response.status_code == 204
    assert claims(app, client)['exp'] == clock.value - 30 + 1200
    clock.advance(1170)
    assert client.post('/auth/activity', headers=HEADERS).status_code == 401


def test_status_and_background_reads_do_not_renew(app, client, token, clock):
    login(client, token)
    original = claims(app, client)['exp']
    clock.advance(1199)
    for path, method in [('/auth/status', 'post'), ('/healthz', 'get'), ('/', 'get')]:
        response = getattr(client, method)(path, headers=HEADERS)
        assert response.status_code in {200, 204}
        assert 'Set-Cookie' not in response.headers
        assert claims(app, client)['exp'] == original
    clock.advance(1)
    assert client.post('/auth/status', headers=HEADERS).status_code == 401


@pytest.mark.parametrize('idle', [-1, 1200, '30', True, None, float('inf')])
def test_invalid_activity(client, token, idle):
    login(client, token)
    assert client.post('/auth/activity', json={'idle_seconds': idle}, headers=HEADERS).status_code == 400


def test_logout_deletes_cookie(client, token):
    login(client, token)
    response = client.post('/auth/logout', headers=HEADERS)
    assert response.status_code == 204 and 'Max-Age=0' in response.headers['Set-Cookie']
    assert client.get_cookie('inventario_mensual_session') is None
    assert client.get('/').status_code == 401


def test_expired_tab_never_deletes_new_shared_cookie(app, client, token, clock):
    login(client, token)
    old = client.get_cookie('inventario_mensual_session').value
    clock.advance(600)
    client.post('/auth/activity', headers=HEADERS)
    active_cookie = client.get_cookie('inventario_mensual_session').value
    clock.advance(600)
    stale = app.test_client()
    stale.set_cookie('inventario_mensual_session', old)
    response = stale.post('/auth/status', headers=HEADERS)
    assert response.status_code == 401 and 'Set-Cookie' not in response.headers
    assert client.get('/').status_code == 200
    assert client.get_cookie('inventario_mensual_session').value == active_cookie
    assert 'Set-Cookie' not in client.get('/auth/expired').headers


@pytest.mark.parametrize('headers', [{}, {'X-Monthly-Request': '1', 'Origin': 'https://evil.test'},
    {'X-Monthly-Request': '1', 'Origin': 'null'},
    {'X-Monthly-Request': '1', 'Sec-Fetch-Site': 'cross-site'}])
def test_csrf_for_mutations(client, token, headers):
    login(client, token)
    assert client.post('/auth/activity', headers=headers).status_code == 403
    assert client.post('/auth/logout', headers=headers).status_code == 403
    assert client.post('/api/guardarInventario', json={}, headers=headers).status_code == 403


def test_session_signature_and_algorithm(client, token, app):
    login(client, token)
    original = claims(app, client)
    for encoded in [jwt.encode(original, 'incorrect-secret-for-tests-0123456789', algorithm='HS256'),
                    jwt.encode(original, '', algorithm='none')]:
        client.set_cookie('inventario_mensual_session', encoded)
        assert rpc(client,'obtenerPuntosVenta').status_code == 401


@pytest.mark.parametrize('changes', [{'iss': 'calco-intranet'}, {'aud': 'inventarios-mensuales'},
    {'sub': ''}, {'sid': ''}, {'exp': 1800009999}, {'act': 1800000100}])
def test_session_claims_are_validated(client, token, app, changes):
    login(client, token)
    invalid = {**claims(app, client), **changes}
    encoded = jwt.encode(invalid, app.config['SESSION_JWT_SECRET'], algorithm='HS256')
    client.set_cookie('inventario_mensual_session', encoded)
    assert client.post('/auth/activity', headers=HEADERS).status_code == 401


def test_internal_jwt_is_not_exposed_to_page(client, token):
    login(client, token)
    cookie = client.get_cookie('inventario_mensual_session').value
    page = client.get('/')
    assert 'js/auth.js' in page.text
    assert cookie not in page.text
    assert cookie not in str(dict(page.headers))
    assert page.headers['Cache-Control'] == 'no-store'
    assert page.headers['Referrer-Policy'] == 'no-referrer'


def test_local_development_remains_available_without_identity():
    app = create_app({'APP_ENV': 'development', 'AUTH_ENABLED': False})
    client = app.test_client()
    page = client.get('/?usuario=ignored')
    assert page.status_code == 200 and 'js/auth.js' not in page.text
    assert 'Set-Cookie' not in page.headers
    assert client.post('/auth/sso', data={'token': 'fake'}).status_code == 404


def test_production_secure_cookie(auth_config, clock, token):
    app = create_app({**auth_config, 'APP_ENV': 'production', 'SESSION_COOKIE_SECURE': True})
    client = app.test_client()
    response = client.post('/auth/sso', data={'token': token()}, base_url='https://localhost')
    assert response.status_code == 303 and 'Secure' in response.headers['Set-Cookie']


@pytest.mark.parametrize('changes', [
    {'AUTH_ENABLED': False}, {'SESSION_JWT_SECRET': ''}, {'SESSION_JWT_SECRET': 'short'},
    {'SESSION_JWT_SECRET': '0123456789abcdef0123456789abcdef'},
    {'SSO_PUBLIC_KEY_PATH': ''}, {'SSO_PUBLIC_KEY_PATH': '/does/not/exist.pem'},
    {'SSO_CLOCK_SKEW_SECONDS': 11}, {'SSO_CLOCK_SKEW_SECONDS': -1},
    {'SSO_TOKEN_MAX_AGE_SECONDS': 0}, {'SSO_TOKEN_MAX_AGE_SECONDS': 'no'},
    {'SESSION_IDLE_TIMEOUT_SECONDS': 0}, {'SESSION_IDLE_TIMEOUT_SECONDS': 1200.5},
    {'SESSION_COOKIE_SECURE': False}, {'DEBUG': True}, {'SSO_ISSUER': ''}, {'SSO_AUDIENCE': ''},
    {'SESSION_JWT_ISSUER': ''}, {'SESSION_JWT_AUDIENCE': ''},
    {'SESSION_JWT_COOKIE_NAME': 'bad;cookie'}, {'AUTH_ENABLED': 'yes'}, {'APP_ENV': 'prod'},
    {'INTRANET_URL': 'javascript:alert(1)'}, {'INTRANET_URL': 'http://intranet.test'},
])
def test_production_rejects_bad_config(auth_config, changes):
    with pytest.raises(ValueError):
        create_app({**auth_config, 'APP_ENV': 'production', 'SESSION_COOKIE_SECURE': True, **changes})


def test_rejects_private_or_non_rsa_key(auth_config, tmp_path, private_key):
    # Private-key rejection tested without writing a private PEM onto disk.
    from unittest.mock import patch
    private = private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    for material in [private, b'not a public key', ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)]:
        with patch('app.services.session_auth_service.Path.read_bytes', return_value=material):
            with pytest.raises(ValueError):
                create_app(auth_config)


def test_no_tokens_in_logs(app, client, token, caplog):
    encoded = token()
    with caplog.at_level('INFO'):
        response = client.post('/auth/sso', data={'token': encoded})
        client.post('/auth/sso', data={'token': encoded})
        session_token = client.get_cookie('inventario_mensual_session').value
        client.post('/auth/logout', headers=HEADERS)
    assert encoded not in caplog.text and session_token not in caplog.text
    assert app.config['SESSION_JWT_SECRET'] not in caplog.text


def test_frontend_auth_scenarios():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js requerido para las pruebas de pestañas y reloj de JavaScript')
    result = subprocess.run([node, 'tests/auth_frontend.cjs'], capture_output=True, text=True, encoding='utf-8', timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("email,admin", [
    ("empleado@crepesywafflesantioquia.com", False),
    (ADMIN_EMAIL, True),
    (" INFO.COSTOS@CREPESYWAFFLESANTIOQUIA.COM ", True),
])
def test_signed_email_controls_administration(app,client,token,email,admin,monkeypatch):
    c=app.extensions["monthly"]
    monkeypatch.setattr(c.auth,"credentials",lambda:pytest.fail("OAuth is not user identity"))
    c.inventory.finalize(inventory_payload())
    response=client.post("/auth/sso",data={"token":token({"email":email})})
    assert response.status_code==303
    assert claims(app,client)["email"]==email.strip().lower()
    assert rpc(client,"obtenerEstadoAdministrador").json["result"]=={"esAdministrador":admin}
    filters=dict(fecha="2026-09-18",puntoVenta="BR00 - PDV 0",bodega="BR03",consecutivo="897")
    for method in ("obtenerConteoConsolidadoPDV","generarDescargaConteosMensuales","generarPlanoSiesaMensual"):
        assert rpc(client,method,filters).status_code==(200 if admin else 403)
    assert client.get("/").status_code==200


@pytest.mark.parametrize("changes", [
    {"aud":"inventarios-uno-a-uno"}, {"usuario":"otro"},
    {"email":None}, {"email":""}, {"email":" "}, {"email":ADMIN_EMAIL+"\nforged"},
    {"email":[]}, {"email":"sin-arroba"}, {"email":"a@b"}, {"email":7},
])
def test_monthly_rejects_invalid_identity(client,token,changes):
    assert client.post("/auth/sso",data={"token":token(changes)}).status_code==401
    assert client.get_cookie("inventario_mensual_session") is None


def test_usuario_is_optional_and_subject_is_the_login(app,client,token):
    assert client.post("/auth/sso",data={"token":token(omit=["usuario"])}).status_code==303
    assert claims(app,client)["sub"]=="wp.usuario"


def test_unsigned_email_and_provider_cannot_override_signed_identity(app,client,token):
    # The injected fake admin in make_container is replaced by the SSO provider.
    assert client.post("/auth/sso",data={"token":token(),"email":ADMIN_EMAIL,"usuario":ADMIN_EMAIL}).status_code==303
    assert claims(app,client)["email"]=="empleado@crepesywafflesantioquia.com"
    for method in ("obtenerConteoConsolidadoPDV","generarDescargaConteosMensuales","generarPlanoSiesaMensual"):
        response=client.post("/api/"+method+"?email="+ADMIN_EMAIL,
                             json={"args":[{"email":ADMIN_EMAIL}]},
                             headers={**HEADERS,"X-User-Email":ADMIN_EMAIL,"X-Forwarded-Email":ADMIN_EMAIL})
        assert response.status_code==403


def test_api_polling_and_get_status_do_not_extend_session(app,client,token,clock):
    login(client,token)
    original=claims(app,client)["exp"]
    for _ in range(19):
        clock.advance(60)
        for response in (rpc(client,"obtenerPuntosVenta"),client.get("/auth/status")):
            assert response.status_code in {200,204}
            assert "Set-Cookie" not in response.headers
        assert claims(app,client)["exp"]==original
    clock.advance(60)
    assert rpc(client,"obtenerPuntosVenta").status_code==401
    assert client.get("/auth/status").status_code==401


def test_duplicate_sso_form_fields_and_oversized_tokens_rejected(client,token):
    from werkzeug.datastructures import MultiDict
    encoded=token()
    assert client.post("/auth/sso",data=MultiDict([("token",encoded),("token",encoded)])).status_code==401
    assert client.post("/auth/sso",data={"token":"a"*17000}).status_code==401


@pytest.mark.parametrize("body", ["null","[]","{invalid"])
def test_malformed_activity_does_not_renew(client,token,body):
    login(client,token)
    response=client.post("/auth/activity",data=body,content_type="application/json",headers=HEADERS)
    assert response.status_code==400 and "Set-Cookie" not in response.headers


APACHE_HOST = 'inventarios-mensuales.calcoweb.net'
APACHE_INTERNAL_URL = 'http://' + APACHE_HOST
APACHE_EXTERNAL_URL = 'https://' + APACHE_HOST
APACHE_HEADERS = {
    'X-Forwarded-Proto': 'https', 'X-Forwarded-Port': '443',
    'Origin': APACHE_EXTERNAL_URL, 'X-Monthly-Request': '1',
    'Sec-Fetch-Site': 'same-origin',
}


@pytest.fixture
def apache_app(auth_config, clock, tmp_path):
    return create_app({**auth_config, 'APP_ENV': 'production', 'SESSION_COOKIE_SECURE': True,
                       'TRUSTED_HOSTS': ['localhost', '127.0.0.1', APACHE_HOST]},
                      container=make_container(tmp_path))


@pytest.fixture
def apache_client(apache_app, token):
    client = apache_app.test_client()
    response = client.post('/auth/sso', base_url=APACHE_INTERNAL_URL,
                           headers=APACHE_HEADERS, data={'token': token()})
    assert response.status_code == 303 and 'Secure' in response.headers['Set-Cookie']
    return client


def test_apache_https_activity_and_external_host_url(apache_client):
    with apache_client:
        response = apache_client.post('/auth/activity', base_url=APACHE_INTERNAL_URL,
                                      headers=APACHE_HEADERS, json={})
        assert response.status_code == 204
        assert request.environ['werkzeug.proxy_fix.orig']['wsgi.url_scheme'] == 'http'
        assert request.host_url == APACHE_EXTERNAL_URL + '/'
        assert request.is_secure
        assert request.environ['SERVER_PORT'] == '443'


def test_apache_matching_origin_allows_api(apache_client):
    response = apache_client.post('/api/obtenerPuntosVenta', base_url=APACHE_INTERNAL_URL,
                                  headers=APACHE_HEADERS, json={'args': []})
    assert response.status_code == 200
    assert response.json['result'] == ['BR00 - PDV 0']


@pytest.mark.parametrize('path', ['/auth/activity', '/api/guardarInventario'])
@pytest.mark.parametrize('changes', [
    {'Origin': 'https://evil.test'},
    {'Origin': APACHE_INTERNAL_URL},
    {'Origin': APACHE_EXTERNAL_URL + ':8443'},
    {'Sec-Fetch-Site': 'cross-site'},
    {'X-Monthly-Request': None},
])
def test_apache_keeps_origin_and_mutation_protection(apache_client, path, changes):
    headers = {key: value for key, value in {**APACHE_HEADERS, **changes}.items() if value is not None}
    response = apache_client.post(path, base_url=APACHE_INTERNAL_URL, headers=headers, json={})
    assert response.status_code == 403
    assert response.json == {'error': 'Origen de solicitud no permitido.'}
    container = apache_client.application.extensions['monthly']
    assert container.drive.calls == container.sheets.reads == container.sheets.writes == 0


def test_apache_untrusted_host_cannot_be_replaced_by_forwarded_host(apache_client):
    cookie_name = apache_client.application.config['SESSION_JWT_COOKIE_NAME']
    cookie = apache_client.get_cookie(cookie_name, domain=APACHE_HOST)
    # Supply a valid session even for the hostile Host so rejection tests the host check.
    apache_client.set_cookie(cookie_name, cookie.value, domain='evil.test')
    response = apache_client.post('/auth/activity', base_url='http://evil.test', json={},
                                  headers={**APACHE_HEADERS, 'X-Forwarded-Host': APACHE_HOST})
    assert response.status_code == 400


@pytest.mark.parametrize('path', ['/auth/activity', '/api/guardarInventario'])
def test_apache_missing_session_precedes_origin_check(apache_app, path):
    headers = {**APACHE_HEADERS, 'Origin': 'https://evil.test', 'Sec-Fetch-Site': 'cross-site'}
    del headers['X-Monthly-Request']
    response = apache_app.test_client().post(path, base_url=APACHE_INTERNAL_URL,
                                             headers=headers, json={})
    assert response.status_code == 401
    assert response.json == {'error': 'Sesión expirada. Ingrese nuevamente desde la intranet.'}


def test_apache_trusts_only_last_proto_port_and_ignores_other_forwarded_headers(apache_client):
    headers = {**APACHE_HEADERS, 'X-Forwarded-Proto': 'http, https',
               'X-Forwarded-Port': '8089, 443', 'X-Forwarded-Host': 'evil.test',
               'X-Forwarded-For': '203.0.113.10', 'X-Forwarded-Prefix': '/forged'}
    with apache_client:
        response = apache_client.post('/auth/activity', base_url=APACHE_INTERNAL_URL,
                                      headers=headers, json={})
        assert response.status_code == 204
        assert request.host_url == APACHE_EXTERNAL_URL + '/'
        assert request.remote_addr == '127.0.0.1'
        assert request.script_root == ''
