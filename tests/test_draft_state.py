from copy import deepcopy

import pytest
from playwright.sync_api import expect

from app.constants import SHEET_MIME
from tests.fakes import sheet
from tests.test_frontend import browser, ui


def menu(page, pdv, date="2026-09-18"):
    page.select_option("#puntoVenta", pdv)
    page.fill("#fechaInventario", date)
    expect(page.locator("#categoriaInventario option")).to_have_count(3)


def begin(page, category):
    page.select_option("#categoriaInventario", category)
    page.click("#botonComenzar")
    expect(page.locator(".producto")).to_have_count(1)


def state(page, category, label):
    expect(page.locator("#categoriaInventario option").filter(has_text=category)).to_have_text(category + " — " + label)
    expect(page.locator(".estado-categoria").filter(has_text=category)).to_contain_text(label)


def save(page, c, calls, closed):
    page.fill("#cerrado-0", closed)
    page.fill("#abierto-0", "0")
    before = (c.drive.calls, c.sheets.reads, c.sheets.writes, len(calls))
    page.click("#botonGuardarProceso")
    expect(page.locator("#mensajeInicio")).to_contain_text("quedó guardado")
    assert (c.drive.calls, c.sheets.reads, c.sheets.writes, len(calls)) == before


@pytest.mark.parametrize("pdv,cat1,cat2", [
    ("BR01 - Río & Norte", "Café", "Barra de  ensaladas"),
    ("BH02 - HELADERÍA Centro", "Helados Y Postres", "BODEGA"),
    ("BC03 - Cocina   Sur", "ESTACIONES", "Pitas / Plancha"),
])
def test_saved_drafts_survive_reload_reopen_and_switch_without_mixing(ui, pdv, cat1, cat2):
    page, c, context, calls = ui
    next(file for file in c.drive.files if file["id"] == "pdv-0")["name"] = pdv
    pdv2 = "BR99 - Otro PDV"
    c.drive.files.append(dict(id="pdv-1", name=pdv2, mimeType=SHEET_MIME, parents=["bases"]))
    book = [sheet("Mensual", [["Categoría", "Item", "Nombre Producto", "UDM"],
                              [cat1, "00123", "Uno", "UNID"], [cat2, "00456", "Dos", "UNID"]])]
    c.sheets.books.update({"pdv-0": deepcopy(book), "pdv-1": deepcopy(book)})
    c.cache.clear()
    page.reload()
    expect(page.locator("#puntoVenta option")).to_have_count(3)
    menu(page, pdv)
    state(page, cat1, "Pendiente")
    begin(page, cat1)
    save(page, c, calls, "3")
    state(page, cat1, "En proceso")
    state(page, cat2, "Pendiente")
    begin(page, cat2)
    save(page, c, calls, "7")
    state(page, cat1, "En proceso")
    state(page, cat2, "En proceso")
    menu(page, pdv2)
    state(page, cat1, "Pendiente")
    begin(page, cat1)
    save(page, c, calls, "9")
    state(page, cat1, "En proceso")
    state(page, cat2, "Pendiente")
    page.reload()
    expect(page.locator("#puntoVenta option")).to_have_count(3)
    menu(page, pdv)
    state(page, cat1, "En proceso")
    state(page, cat2, "En proceso")
    menu(page, pdv, "2026-09-19")
    state(page, cat1, "Pendiente")
    state(page, cat2, "Pendiente")
    page.close()
    page = context.new_page()
    page.goto("http://localhost/")
    expect(page.locator("#puntoVenta option")).to_have_count(3)
    menu(page, pdv)
    state(page, cat1, "En proceso")
    begin(page, cat1)
    expect(page.locator("#cerrado-0")).to_have_value("3")
    save(page, c, calls, "3")
    menu(page, pdv2)
    begin(page, cat1)
    expect(page.locator("#cerrado-0")).to_have_value("9")
    assert c.sheets.writes == c.drive.writes == 0


def test_legacy_draft_name_variations_restore_and_migrate_locally(ui):
    page, c, context, calls = ui
    old = "inventario-mensual-v1-  br00 - pdv  0  -2026-09-18-  BÉBIDAS  "
    other = "inventario-mensual-v1-BR01 - PDV 1-2026-09-18-Bebidas"
    page.evaluate("""([old, other]) => {
      localStorage.setItem(old, JSON.stringify([{item:'000123', cerrado:'4', abierto:'2'}]));
      localStorage.setItem(other, JSON.stringify([{item:'000123', cerrado:'8', abierto:'1'}]));
    }""", [old, other])
    menu(page, "BR00 - PDV 0")
    state(page, "Bebidas", "En proceso")
    page.select_option("#categoriaInventario", "Bebidas")
    page.click("#botonComenzar")
    expect(page.locator("#cerrado-0")).to_have_value("4")
    expect(page.locator("#abierto-0")).to_have_value("2")
    page.click("#botonGuardarProceso")
    state(page, "Bebidas", "En proceso")
    assert page.evaluate("key => localStorage.getItem(key)", old) is None
    assert page.evaluate("key => JSON.parse(localStorage.getItem(key))[0].cerrado", other) == "8"
    assert page.evaluate("""obtenerClaveBorradorPara(' BR00 - PDV  0 ', '2026-09-18', 'BÉBIDAS') ===
                            obtenerClaveBorradorPara('br00 - pdv 0', '2026-09-18', 'bebidas')""")
    page.reload()
    expect(page.locator("#puntoVenta option")).to_have_count(2)
    menu(page, "BR00 - PDV 0")
    state(page, "Bebidas", "En proceso")
    assert c.sheets.writes == 0


def test_storage_failure_preserves_inputs_and_does_not_claim_saved(ui):
    page, c, context, calls = ui
    menu(page, "BR00 - PDV 0")
    page.select_option("#categoriaInventario", "Bebidas")
    page.click("#botonComenzar")
    expect(page.locator("#cerrado-0")).to_be_visible()
    page.evaluate("() => {Storage.prototype.setItem = () => {throw new DOMException('Full','QuotaExceededError')}}")
    page.fill("#cerrado-0", "4")
    page.click("#botonGuardarProceso")
    expect(page.locator("#mensajeInventario")).to_contain_text("No se pudo guardar el borrador")
    expect(page.locator("#pantallaInventario")).to_be_visible()
    expect(page.locator("#cerrado-0")).to_have_value("4")
    expect(page.locator("#pantallaInicio")).to_be_hidden()
    assert page.evaluate("localStorage.length") == 0
    assert c.sheets.writes == 0


@pytest.mark.parametrize("draft", [[], {}, None, [None], [{}], [{"item":"000123", "cerrado":"", "abierto":""}]])
def test_empty_or_malformed_draft_stays_pending(ui, draft):
    page, *_ = ui
    page.evaluate("draft => localStorage.setItem(obtenerClaveBorradorPara('BR00 - PDV 0','2026-09-18','Bebidas'), JSON.stringify(draft))", draft)
    menu(page, "BR00 - PDV 0")
    state(page, "Bebidas", "Pendiente")
