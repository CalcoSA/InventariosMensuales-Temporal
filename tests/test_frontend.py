"""Real Chromium DOM tests. All HTTP is intercepted into Flask's test client.
No listening server and no Google connection are created.
"""
from pathlib import Path
import base64
import re
import pytest
from playwright.sync_api import sync_playwright, expect
from app import create_app
from app.models.errors import GoogleUnavailable, WriteUncertain
from app.services.retry import GoogleExecutor
from tests.test_cache_retry import HttpFailure
from tests.conftest import make_container
from tests.fakes import payload, seed_factors

ROOT=Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        executable=Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
        browser=p.chromium.launch(executable_path=str(executable) if executable.exists() else None,headless=True)
        yield browser
        browser.close()


@pytest.fixture
def ui(browser,tmp_path):
    c=make_container(tmp_path)
    app=create_app({"TESTING":True},container=c)
    client=app.test_client()
    context=browser.new_context(viewport={"width":1280,"height":1000},locale="es-CO",timezone_id="America/Bogota")
    calls=[]
    def route_handler(route):
        request=route.request
        from urllib.parse import urlsplit
        parsed=urlsplit(request.url)
        if parsed.hostname!="localhost":
            route.abort();return
        calls.append(parsed.path)
        if parsed.path=="/original":
            html=(ROOT/"legacy/index_original.html").read_text(encoding="utf-8")
            shim='<script src="/static/js/api.js"></script><script>window.google={script:{run:monthlyApi}};</script>'
            route.fulfill(status=200,content_type="text/html",body=html.replace("<script>",shim+"<script>",1));return
        response=client.open(parsed.path,method=request.method,data=request.post_data,headers=dict(request.headers))
        route.fulfill(status=response.status_code,headers=dict(response.headers),body=response.data)
    context.route("**/*",route_handler)
    page=context.new_page()
    page.on("dialog",lambda dialog:dialog.accept())
    page.goto("http://localhost/")
    expect(page.locator("#puntoVenta option")).to_have_count(2)
    yield page,c,context,calls
    context.close()


def select_category(page):
    page.select_option("#puntoVenta","BR00 - PDV 0")
    page.fill("#fechaInventario","2026-09-18")
    expect(page.locator("#categoriaInventario option")).to_have_count(3)
    page.select_option("#categoriaInventario","Bebidas")
    page.click("#botonComenzar")
    expect(page.locator(".producto")).to_have_count(2)


def test_inventory_draft_progress_search_restore_and_finalize(ui):
    page,c,context,calls=ui
    assert page.input_value("#fechaInventario")==page.evaluate("new Date().toLocaleDateString('en-CA')")
    select_category(page)
    page.click("#botonFinalizar")
    expect(page.locator("#mensajeInventario")).to_contain_text("Faltan 2 productos")
    page.fill("#cerrado-0","4")
    page.fill("#abierto-0","2.5")
    expect(page.locator("#textoProgreso")).to_have_text("1 de 2 (50%)")
    page.fill("#buscador","Café")
    expect(page.locator(".producto")).to_have_count(1)
    page.fill("#buscador","")
    expect(page.locator(".producto")).to_have_count(2)
    writes=c.sheets.writes
    page.click("#botonGuardarProceso")
    expect(page.locator("#mensajeInicio")).to_contain_text('quedó guardado')
    expect(page.locator("#listaEstadosCategorias")).to_contain_text("En proceso")
    assert c.sheets.writes==writes==0
    assert "/api/guardarInventario" not in calls
    stored=page.evaluate("leerBorradorPara('BR00 - PDV 0','2026-09-18','Bebidas')")
    assert list(stored[0])==["item","cerrado","abierto"]
    page.reload()
    select_category(page)
    assert page.input_value("#cerrado-0")=="4"
    page.get_by_role("button",name="Completar vacíos con 0",exact=True).click()
    expect(page.locator("#textoProgreso")).to_have_text("2 de 2 (100%)")
    page.click("#botonGuardarProceso")
    expect(page.locator("#listaEstadosCategorias")).to_contain_text("En proceso")
    page.select_option("#categoriaInventario","Bebidas");page.click("#botonComenzar")
    expect(page.locator(".producto")).to_have_count(2)
    page.click("#botonFinalizar")
    expect(page.locator("#pantallaExito")).to_be_visible()
    assert c.sheets.writes==1
    assert page.evaluate("localStorage.getItem('inventario-mensual-v1-BR00 - PDV 0-2026-09-18-Bebidas')") is None
    assert page.evaluate("localStorage.length")==0
    page.click("#botonVolverCategorias")
    expect(page.locator("#categoriaInventario option[value='Bebidas']")).to_be_disabled()
    expect(page.locator("#listaEstadosCategorias")).to_contain_text("Ya guardada")
    # Original success screen owns the change-PDV action.
    page.evaluate("nuevoInventario()")
    assert page.input_value("#puntoVenta")==""


@pytest.mark.parametrize("statuses",[[429,200],[429,429,200],[429,429,429,429]])
def test_finalizar_read_retries_and_draft_confirmation(ui,monkeypatch,statuses):
    page,c,context,calls=ui
    select_category(page)
    page.get_by_role("button",name="Completar vacíos con 0",exact=True).click()
    responses=iter(statuses)
    sleeps=[]
    executor=GoogleExecutor(sleep=sleeps.append,jitter=lambda:0)
    snapshot=c.inventory_repository.snapshot
    def attempt(file_id):
        status=next(responses)
        if status!=200:raise HttpFailure(status)
        return snapshot(file_id)
    monkeypatch.setattr(c.inventory_repository,"snapshot",lambda file_id:executor.execute(lambda:attempt(file_id)))
    page.click("#botonFinalizar")
    if statuses[-1]==200:
        expect(page.locator("#pantallaExito")).to_be_visible()
        assert page.evaluate("localStorage.length")==0
        assert c.sheets.writes==1
    else:
        expect(page.locator("#mensajeInventario")).to_contain_text("demasiadas solicitudes")
        expect(page.locator("#botonFinalizar")).to_be_enabled()
        expect(page.locator("#pantallaInventario")).to_be_visible()
        expect(page.locator("#pantallaExito")).to_be_hidden()
        assert page.evaluate("localStorage.length")==1
        assert c.sheets.writes==0
    assert executor.calls==len(statuses)
    assert sleeps==[2**i for i in range(len(statuses)-1)]


def test_visibility_and_beforeunload_flush(ui):
    page,*_=ui
    select_category(page)
    page.fill("#cerrado-0","12")
    page.evaluate("window.dispatchEvent(new Event('beforeunload'))")
    assert page.evaluate("JSON.parse(localStorage.getItem(obtenerClaveBorrador()))[0].cerrado")=="12"
    page.fill("#abierto-0","3")
    page.evaluate("Object.defineProperty(document,'hidden',{get:()=>true,configurable:true});document.dispatchEvent(new Event('visibilitychange'));")
    assert page.evaluate("JSON.parse(localStorage.getItem(obtenerClaveBorrador()))[0].abierto")=="3"


def test_unconfirmed_write_preserves_draft_and_never_shows_success(ui):
    page,c,context,calls=ui
    select_category(page)
    page.get_by_role("button",name="Completar vacíos con 0",exact=True).click()
    c.sheets.fail_write=WriteUncertain("Google no confirmó el guardado. Su borrador se conserva.")
    page.click("#botonFinalizar")
    expect(page.locator("#mensajeInventario")).to_contain_text("no confirmó")
    expect(page.locator("#botonFinalizar")).to_be_enabled()
    expect(page.locator("#pantallaExito")).to_be_hidden()
    assert page.evaluate("localStorage.length")==1
    assert c.sheets.writes==1


def test_admin_consolidated_filters_and_downloads(ui):
    page,c,context,calls=ui
    seed_factors(c, [[123,"Jugo","ML",24], [2345,"Café","KG",1]])
    c.cache.clear()
    c.inventory.finalize(payload())
    expect(page.locator("#botonAdministracion")).to_be_visible()
    page.click("#botonAdministracion")
    page.fill("#adminFecha","2026-09-18")
    page.select_option("#adminPuntoVenta","BR00 - PDV 0")
    page.fill("#adminBodega","BR03")
    page.fill("#adminConsecutivo","897")
    with page.expect_download() as download:
        page.click("#botonDescargarPlano")
    assert download.value.suggested_filename=="PDV_0-Mensual-00000897-PlanosPDV.txt"
    page.click("#botonVerConteo")
    expect(page.locator("#pantallaConsolidado")).to_be_visible()
    expect(page.locator("#resumenProductos")).to_have_text("2")
    expect(page.locator("#resumenCerrado")).to_have_text("8")
    expect(page.locator("#resumenAbierto")).to_have_text("5")
    expect(page.locator("#resumenTotal")).to_have_text("105")
    expect(page.locator("#cuerpoConteoConsolidado tr").first.locator("td").last).to_have_text("98.5")
    assert c.sheets.books["pdv-0"][1]["values"][1][10] == 6.5
    page.fill("#buscadorConteo","cafe")
    expect(page.locator("#cuerpoConteoConsolidado tr")).to_have_count(1)
    expect(page.locator("#resumenTotal")).to_have_text("105")
    with page.expect_download() as download:
        page.click("#botonDescargarConteos")
    assert download.value.suggested_filename.endswith(".csv")
    page.get_by_role("button",name="Volver",exact=True).click()
    page.get_by_role("button",name="Volver al inventario",exact=True).click()
    expect(page.locator("#pantallaInicio")).to_be_visible()


@pytest.mark.parametrize("width,height",[(1280,1000),(390,844)])
def test_original_visual_parity_except_quantity_controls(ui,width,height):
    page,c,context,calls=ui
    page.set_viewport_size({"width":width,"height":height})
    select_category(page)
    page.locator("#buscador").blur()
    expect(page.locator("#ayudaCantidades")).to_contain_text("1,234.5")
    # Quantity controls now accept grouping commas instead of native spin buttons.
    # Their behavior is tested above/below; compare the rest of the original UI.
    migrated=page.screenshot(full_page=True,animations="disabled",mask=[page.locator(".cantidad input")],
                             style="#ayudaCantidades { display: none; }")
    original=context.new_page()
    original.set_viewport_size({"width":width,"height":height})
    original.goto("http://localhost/original")
    expect(original.locator("#puntoVenta option")).to_have_count(2)
    select_category(original)
    original.locator("#buscador").blur()
    baseline=original.screenshot(full_page=True,animations="disabled",mask=[original.locator(".cantidad input")])
    # Exact rendered-pixel comparison; PNG byte identity in the same browser engine.
    assert migrated==baseline
    original.close()


@pytest.mark.parametrize("email",[None,"empleado@crepesywafflesantioquia.com"])
def test_non_admin_and_no_browser_console_errors(ui,email):
    page,c,context,calls=ui
    c.identity.provider=lambda:email
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.reload()
    expect(page.locator("#botonAdministracion")).to_be_hidden()
    select_category(page)
    page.fill("#cerrado-0","1")
    assert not errors


def test_admin_status_error_keeps_button_hidden(ui):
    page,c,context,calls=ui
    def unavailable():raise GoogleUnavailable("Identidad no disponible.")
    c.identity.provider=unavailable
    with page.expect_response("**/api/obtenerEstadoAdministrador") as response:
        page.reload()
    assert response.value.status==503
    expect(page.locator("#botonAdministracion")).to_be_hidden()


def test_opened_decimal_point_and_comma_survive_draft_in_spanish_browser(ui):
    page,c,context,calls=ui
    seed_factors(c)
    c.cache.clear()
    select_category(page)
    page.fill("#cerrado-0", "1")
    page.fill("#abierto-0", "5.145")
    page.fill("#cerrado-1", "1")
    page.fill("#abierto-1", "5,145")
    expect(page.locator("#textoProgreso")).to_have_text("2 de 2 (100%)")
    page.click("#botonGuardarProceso")
    expect(page.locator("#listaEstadosCategorias")).to_contain_text("En proceso")
    assert c.sheets.writes == 0
    page.reload()
    select_category(page)
    assert page.input_value("#abierto-0") == "5.145"
    assert page.input_value("#abierto-1") == "5,145"
    page.click("#botonFinalizar")
    expect(page.locator("#pantallaExito")).to_be_visible()
    assert [r[8:11] for r in c.sheets.books["pdv-0"][1]["values"][1:]] == [[1, 5.145, 6.145], [1, 5.145, 6.145]]
    page.click("#botonAdministracion")
    page.fill("#adminFecha", "2026-09-18")
    page.select_option("#adminPuntoVenta", "BR00 - PDV 0")
    page.fill("#adminBodega", "BR03")
    page.fill("#adminConsecutivo", "897")
    with page.expect_download() as download:
        page.click("#botonDescargarPlano")
    detail = Path(download.value.path()).read_bytes().decode("ascii").split("\r\n")[1:-1]
    assert all(len(line) == 333 and "," not in line for line in detail)
    assert [line[148:180] for line in detail] == ["000000000000006.145000000000000."] * 2
    page.click("#botonVerConteo")
    expect(page.locator("#pantallaConsolidado")).to_be_visible()
    rows = page.locator("#cuerpoConteoConsolidado tr")
    expect(rows.nth(0).locator("td").last).to_have_text("6.145")
    expect(rows.nth(1).locator("td").last).to_have_text("6.145")
    expect(page.locator("#resumenAbierto")).to_have_text("10.29")
    expect(page.locator("#resumenTotal")).to_have_text("12.29")


@pytest.mark.parametrize("value", ["1,234.5", "1.234,56", "1,234,567", "1 234", "-1"])
def test_invalid_number_format_never_saves_or_finalizes(ui, value):
    page,c,context,calls=ui
    select_category(page)
    page.get_by_role("button",name="Completar vacíos con 0",exact=True).click()
    page.fill("#abierto-0", value)
    expect(page.locator("#textoProgreso")).to_have_text("1 de 2 (50%)")
    for button in ("#botonGuardarProceso", "#botonFinalizar"):
        page.click(button)
        expect(page.locator("#mensajeInventario")).to_contain_text("Use punto o coma como separador decimal")
        expect(page.locator("#pantallaInventario")).to_be_visible()
        assert page.input_value("#abierto-0") == value
    assert c.sheets.writes == 0 and "/api/guardarInventario" not in calls


@pytest.mark.parametrize("closed,factor,opened,total", [
    (6, 1, "1.114", "7.114"), (5, 1, "5.335", "10.335"),
    (0, 24, "1.114", "1.114"), (2, 24, "1.114", "49.114"),
    (0, 1, "1.11456789", "1.11456789"), (6, 1, "1", "7"),
    (1, 3100, "1600", "4700"),
])
@pytest.mark.parametrize("separator", [".", ","])
def test_opened_and_converted_total_keep_decimals_in_administration(ui, closed, factor, opened, total, separator):
    page,c,context,calls=ui
    seed_factors(c, [[123, "P", "", factor], [2345, "Q", "", 1]])
    c.cache.clear()
    select_category(page)
    page.get_by_role("button",name="Completar vacíos con 0",exact=True).click()
    page.fill("#cerrado-0", str(closed))
    entered = opened.replace(".", separator)
    page.fill("#abierto-0", entered)
    assert page.evaluate("cantidadValida(productos[0].abierto, 'abierto')")
    expect(page.locator("#textoProgreso")).to_have_text("2 de 2 (100%)")
    page.click("#botonGuardarProceso")
    expect(page.locator("#listaEstadosCategorias")).to_contain_text("En proceso")
    assert page.evaluate("JSON.parse(localStorage.getItem(obtenerClaveBorradorPara("
                         "'BR00 - PDV 0', '2026-09-18', 'Bebidas')))[0].abierto") == entered
    assert c.sheets.writes == 0 and "/api/guardarInventario" not in calls
    page.reload()
    select_category(page)
    assert page.input_value("#cerrado-0") == str(closed)
    assert page.input_value("#abierto-0") == entered
    assert page.evaluate("productos[0].abierto") == entered
    with page.expect_request("**/api/guardarInventario") as request:
        page.click("#botonFinalizar")
    assert request.value.method == "POST"
    sent = request.value.post_data_json["args"][0]["conteos"][0]
    assert sent["cerrado"] == str(closed) and sent["abierto"] == entered
    expect(page.locator("#pantallaExito")).to_be_visible()
    written = next(request["updateCells"]["rows"][1]["values"]
                   for batch in c.sheets.history for request in batch if "updateCells" in request)
    assert written[8]["userEnteredValue"] == {"numberValue": closed}
    assert written[9]["userEnteredValue"] == {"numberValue": float(opened)}
    assert c.sheets.books["pdv-0"][1]["values"][1][9] == float(opened)
    if opened in ("1.114", "5.335"):
        assert written[9]["userEnteredValue"]["numberValue"] != int(opened.replace(".", ""))
    page.click("#botonAdministracion")
    page.fill("#adminFecha", "2026-09-18")
    page.select_option("#adminPuntoVenta", "BR00 - PDV 0")
    page.click("#botonVerConteo")
    expect(page.locator("#pantallaConsolidado")).to_be_visible()
    cells = page.locator("#cuerpoConteoConsolidado tr").first.locator("td")
    expect(cells.nth(4)).to_have_text(str(closed))
    expect(cells.nth(5)).to_have_text(opened)
    expect(cells.nth(6)).to_have_text(total)
    expect(page.locator("#resumenAbierto")).to_have_text(opened)
    expect(page.locator("#resumenTotal")).to_have_text(total)
