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
