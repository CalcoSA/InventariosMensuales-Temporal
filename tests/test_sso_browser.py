"""Real browser, RSA-signed test login and Flask test client; no server sockets."""
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
import pytest
from playwright.sync_api import expect
from app import create_app
from tests.conftest import make_container
from tests.test_frontend import browser, select_category
from tests.test_sso import auth_config, clock, private_key, token
from tests.test_sso import apache_app, APACHE_HOST, APACHE_EXTERNAL_URL


@pytest.fixture
def signed_ui(browser, auth_config, clock, tmp_path, token):
    c=make_container(tmp_path)
    app=create_app(auth_config,container=c)
    client=app.test_client(use_cookies=False)
    context=browser.new_context(viewport={"width":1280,"height":1000},locale="es-CO",timezone_id="America/Bogota")
    calls=[]
    def handle(route):
        request=route.request
        url=urlsplit(request.url)
        if url.hostname!="localhost":
            route.abort();return
        response=client.open(url.path+("?" + url.query if url.query else ""),method=request.method,
                             data=request.post_data,headers=request.all_headers())
        calls.append((url.path,response.status_code))
        route.fulfill(status=response.status_code,headers=dict(response.headers),body=response.data)
    context.route("**/*",handle)
    page=context.new_page()
    page.clock.install(time=datetime.fromtimestamp(clock.value,tz=timezone.utc))
    page.goto("http://localhost/auth/expired")
    def login():
        # Transport the real cookie issued by /auth/sso into Chromium; the Flask
        # tests separately verify the 303. No listening HTTP server is required.
        response=client.post("/auth/sso",data={"token":token()})
        assert response.status_code==303 and response.location=="/"
        issued=SimpleCookie(response.headers["Set-Cookie"])["inventario_mensual_session"]
        context.add_cookies([{"name":issued.key,"value":issued.value,"url":"http://localhost",
                              "httpOnly":bool(issued["httponly"]),"sameSite":issued["samesite"],
                              "secure":bool(issued["secure"])}])
        page.goto("http://localhost/")
        expect(page.locator("#puntoVenta option")).to_have_count(2)
    yield page,c,context,calls,login
    context.close()


@pytest.mark.parametrize("trigger",["timer","api"])
def test_expired_session_preserves_and_recovers_monthly_draft(signed_ui,clock,trigger):
    page,c,context,calls,login=signed_ui
    login()
    expect(page.locator("#botonAdministracion")).to_be_hidden()
    cookies=context.cookies()
    cookie=next(x for x in cookies if x["name"]=="inventario_mensual_session")
    assert cookie["httpOnly"] and cookie["sameSite"]=="Lax"
    assert "inventario_mensual_session" not in page.evaluate("document.cookie")
    select_category(page)
    page.fill("#cerrado-0","9")
    page.fill("#abierto-0","1.5")
    if trigger=="timer":
        # Timers alone never renew. Reaching 1200 seconds must close the session.
        clock.advance(1200)
        page.clock.fast_forward(1200000)
    else:
        # Expiry can also arrive while a debounced draft save is still pending.
        clock.advance(1200)
        page.evaluate("fetch('/api/obtenerPuntosVenta',{method:'POST',headers:{'Content-Type':'application/json'},body:'{\"args\":[]}'}).catch(()=>{})")
    expect(page).to_have_url("http://localhost/auth/expired")
    key="inventario-mensual-v1-BR00 - PDV 0-2026-09-18-Bebidas"
    saved=page.evaluate("key=>JSON.parse(localStorage.getItem(key))",key)
    assert saved[0]==dict(item="000123",cerrado="9",abierto="1.5")
    assert c.sheets.writes==0
    login()
    select_category(page)
    assert page.input_value("#cerrado-0")=="9"
    assert page.input_value("#abierto-0")=="1.5"
    assert c.sheets.writes==0


@pytest.fixture
def production_ui(browser, apache_app, clock, token, request):
    """Intercept every URL: a simulated intranet POST, Apache and Google fakes."""
    email, intranet_host = request.param
    client = apache_app.test_client(use_cookies=False)
    context = browser.new_context(viewport={'width': 1280, 'height': 1000}, locale='es-CO',
                                  timezone_id='America/Bogota', service_workers='block', offline=True)
    calls = []
    context.add_init_script("""(() => {
      const nativeFetch = window.fetch;
      window.testFetchOptions = [];
      window.fetch = (input, options = {}) => {
        window.testFetchOptions.push({url: String(input), credentials: options.credentials,
          marker: new Headers(options.headers).get('X-Monthly-Request')});
        return nativeFetch.call(window, input, options);
      };
    })();""")

    def handle(route):
        browser_request = route.request
        url = urlsplit(browser_request.url)
        if url.hostname == intranet_host:
            # Ephemeral signed JWT only; no production cookies, keys or WordPress calls.
            encoded = token({'email': email})
            route.fulfill(content_type='text/html', body=(
                f'<form method="post" action="{APACHE_EXTERNAL_URL}/auth/sso">'
                f'<input type="hidden" name="token" value="{encoded}">'
                '<button>Entrar</button></form>'))
            return
        if url.hostname != APACHE_HOST:
            route.abort()
            return
        headers = browser_request.all_headers()
        upstream = {**headers, 'Host': url.netloc,
                    'X-Forwarded-Proto': 'https', 'X-Forwarded-Port': '443'}
        response = client.open(url.path, base_url='http://127.0.0.1:8089',
                               method=browser_request.method, data=browser_request.post_data,
                               headers=upstream)
        # Store only the diagnostic headers; never Cookie or the SSO POST body.
        calls.append({'path': url.path, 'status': response.status_code,
                      'origin': headers.get('origin'), 'site': headers.get('sec-fetch-site'),
                      'marker': headers.get('x-monthly-request')})
        route.fulfill(status=response.status_code, headers=dict(response.headers), body=response.data)

    context.route('**/*', handle)
    page = context.new_page()
    page.set_default_timeout(5000)
    page.on('dialog', lambda dialog: dialog.accept())
    page.clock.install(time=datetime.fromtimestamp(clock.value, tz=timezone.utc))
    try:
        page.goto('https://' + intranet_host + '/')
        page.get_by_role('button', name='Entrar', exact=True).click()
        expect(page).to_have_url(APACHE_EXTERNAL_URL + '/')
        expect(page.locator('#puntoVenta option')).to_have_count(2)
        yield page, apache_app.extensions['monthly'], calls, email
    finally:
        context.close()


@pytest.mark.parametrize('production_ui', [
    (email, intranet) for email in ('empleado@crepesywaffles.com',
                                    'juan.zapata@crepesywaffles.com',
                                    'info.costos@crepesywafflesantioquia.com')
    for intranet in ('intranet.example.test', 'intranet.calcoweb.net')
], indirect=True)
def test_production_sso_browser_inventory_and_request_headers(production_ui):
    page, c, calls, email = production_ui
    if email == 'empleado@crepesywaffles.com':
        expect(page.locator('#botonAdministracion')).to_be_hidden()
    else:
        expect(page.locator('#botonAdministracion')).to_be_visible()
    select_category(page)
    page.fill('#cerrado-0', '4')
    page.fill('#abierto-0', '2.5')
    page.click('#botonGuardarProceso')
    expect(page.locator('#mensajeInicio')).to_contain_text('quedó guardado')
    assert c.sheets.writes == 0
    assert not any(call['path'] == '/api/guardarInventario' for call in calls)
    page.reload()
    select_category(page)
    assert page.input_value('#cerrado-0') == '4'
    assert page.input_value('#abierto-0') == '2.5'
    page.get_by_role('button', name='Completar vacíos con 0', exact=True).click()
    page.click('#botonFinalizar')
    expect(page.locator('#pantallaExito')).to_be_visible()
    assert c.sheets.writes == 1
    paths = {'/api/obtenerPuntosVenta', '/api/obtenerEstadoAdministrador', '/auth/activity',
             '/api/obtenerEstadoCategoriasMensuales', '/api/obtenerProductos', '/api/guardarInventario'}
    assert paths <= {call['path'] for call in calls}
    for call in calls:
        if call['path'] in paths:
            assert call['status'] in {200, 204}, call
            assert call['origin'] == APACHE_EXTERNAL_URL, call
            # Chromium may add Fetch Metadata after interception. Explicit HTTP
            # tests cover same-origin/same-site/cross-site without inventing it here.
            assert call['site'] in {None, 'same-origin'}, call
            assert call['marker'] == '1', call
    for options in page.evaluate('window.testFetchOptions'):
        assert options['credentials'] == 'same-origin'
        assert options['marker'] == '1'
