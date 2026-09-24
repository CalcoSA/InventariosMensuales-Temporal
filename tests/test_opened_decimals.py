"""Abierto stays decimal from capture to Administration, with Siesa unchanged."""
import base64
from copy import deepcopy
from decimal import Decimal
import hashlib

import pytest

from app.constants import COUNTS_HEADERS
from app.models.sheets import decode_book, row_data
from tests.conftest import rpc
from tests.fakes import payload, seed_factors, sheet
from tests.test_siesa_factors import FILTERS, lines


CASES = [(6, 1, "1.114", "7.114"), (5, 1, "5.335", "10.335"),
         (0, 24, "1.114", "1.114"), (2, 24, "1.114", "49.114"),
         (1, 3100, "1600", "4700")]


@pytest.mark.parametrize("closed,factor,opened,total", CASES)
@pytest.mark.parametrize("separator", [".", ","])
def test_required_decimal_cases_through_save_and_admin_api(container, client, closed, factor, opened, total, separator):
    seed_factors(container, [[123, "P", "", factor], [2345, "Q", "", 1]])
    data = payload()
    data["conteos"][0].update(cerrado=str(closed), abierto=opened.replace(".", separator))
    data["conteos"][1].update(cerrado="0", abierto="0")
    assert rpc(client, "guardarInventario", data).status_code == 200
    stored = container.sheets.books["pdv-0"][1]["values"][1]
    assert stored[8] == closed and stored[9] == float(opened)
    if "." in opened:
        assert stored[9] != int(opened.replace(".", ""))  # 1.114 != 1114; 5.335 != 5335.
    before = deepcopy(container.sheets.books)
    plano_before = container.admin.flat(FILTERS)
    response = rpc(client, "obtenerConteoConsolidadoPDV", FILTERS)
    assert response.status_code == 200
    result = response.json["result"]
    assert result["registros"][0]["abierto"] == float(opened)
    assert result["registros"][0]["total"] == float(total)
    assert result["resumen"] == {"abierto": float(opened), "total": float(total)}
    assert container.admin.flat(FILTERS) == plano_before
    assert Decimal(lines(plano_before)[1][148:179]) == Decimal(total)
    assert container.sheets.books == before and container.sheets.writes == 1


@pytest.mark.parametrize("closed,factor,opened,total", CASES)
@pytest.mark.parametrize("representation", ["number", "point", "comma"])
def test_existing_sheet_values_keep_opened_decimal_when_read(container, client, closed, factor, opened, total, representation):
    seed_factors(container, [[123, "P", "", factor]])
    raw = float(opened) if representation == "number" else opened.replace(".", "," if representation == "comma" else ".")
    rows = row_data([COUNTS_HEADERS, ["id", "", FILTERS["fecha"], FILTERS["puntoVenta"],
                                    "Bebidas", "123", "P", "KG", closed, raw, 0]])
    for row in rows:
        for cell in row["values"]:
            cell["effectiveValue"] = cell["userEnteredValue"]
    # Read real Sheets cell shapes, including a locale-specific displayed number.
    rows[1]["values"][9]["formattedValue"] = opened.replace(".", ",")
    book = decode_book({"sheets": [{"properties": {"sheetId": 1, "title": "Conteos Mensuales"},
                                    "data": [{"rowData": rows}]}]})
    assert book[0]["values"][1][9] == raw
    container.sheets.books["pdv-0"].extend(book)
    before = deepcopy(container.sheets.books)
    response = rpc(client, "obtenerConteoConsolidadoPDV", FILTERS)
    assert response.status_code == 200
    result = response.json["result"]
    assert result["registros"][0]["abierto"] == float(opened)
    assert result["registros"][0]["total"] == float(total)
    assert result["resumen"] == {"abierto": float(opened), "total": float(total)}
    assert container.sheets.books == before
    assert container.sheets.writes == container.drive.writes == 0


def test_siesa_bytes_match_pre_fix_baseline_for_numeric_and_text_opened(container):
    seed_factors(container)
    rows = [["id", "", FILTERS["fecha"], FILTERS["puntoVenta"], "Bebidas", "123", "P", "KG", 6, opened, 0]
            for opened in ["1.114", "1,114", "5.335", "5,335", 1600, 1114, 1.114, 5.335]]
    container.sheets.books["pdv-0"].append(sheet("Conteos Mensuales", [COUNTS_HEADERS] + rows, 1))
    before = deepcopy(container.sheets.books)
    container.admin.consolidated(FILTERS)
    content = base64.b64decode(container.admin.flat(FILTERS)["contenidoBase64"])
    # Full ASCII/CRLF artifact captured from c3c3692 before this reading fix.
    assert hashlib.sha256(content).hexdigest() == "7ab3180afe7221af590343b596136ea473c1034770f00bdff99febce4585c13e"
    assert container.sheets.books == before
    assert container.sheets.writes == container.drive.writes == 0


@pytest.mark.parametrize("field,value", [
    ("cerrado", "2,5"), ("cerrado", "12,34"), ("cerrado", "1234,567"),
    ("abierto", "1,234.5"), ("abierto", "1.234,5"), ("abierto", "1,234,567"),
])
def test_field_specific_invalid_separators_are_rejected_before_google(container, client, field, value):
    data = payload()
    data["conteos"][0][field] = value
    assert rpc(client, "guardarInventario", data).status_code == 400
    assert container.sheets.reads == container.sheets.writes == container.drive.calls == 0


def test_closed_keeps_thousands_while_opened_uses_decimal_comma(container):
    data = payload()
    data["conteos"][0].update(cerrado="1,114", abierto="1,114")
    container.inventory.finalize(data)
    assert container.sheets.books["pdv-0"][1]["values"][1][8:11] == [1114, 1.114, 1115.114]


@pytest.mark.parametrize("opened,expected", [("0.500", .5), ("2.250", 2.25), ("1.11456789", 1.11456789)])
def test_opened_precision_is_not_limited_to_six_decimals(container, opened, expected):
    seed_factors(container)
    data = payload()
    data["conteos"][0].update(cerrado="0", abierto=opened)
    container.inventory.finalize(data)
    record = container.admin.consolidated(FILTERS)["registros"][0]
    assert record["abierto"] == record["total"] == expected


def test_admin_decimal_sums_and_existing_integers_do_not_change_saved_data_or_siesa(container):
    seed_factors(container)
    rows = [["id", "", FILTERS["fecha"], FILTERS["puntoVenta"], category, item, "P", "KG", closed, opened, closed + opened]
            for category, item, closed, opened in [
                ("Bebidas", "123", 0, .1), ("Cocina", "123", 0, .2),
                ("Cocina", "2345", 6, 1114)]]
    container.sheets.books["pdv-0"].append(sheet("Conteos Mensuales", [COUNTS_HEADERS] + rows, 1))
    before = deepcopy(container.sheets.books)
    plano_before = container.admin.flat(FILTERS)
    result = container.admin.consolidated(FILTERS)
    assert result["registros"][0]["abierto"] == result["registros"][0]["total"] == .3
    # Do not guess that an already saved integer should be divided by 1000.
    assert result["registros"][1]["abierto"] == 1114
    assert result["registros"][1]["total"] == 1120
    assert result["resumen"] == {"abierto": 1114.3, "total": 1120.3}
    assert container.admin.flat(FILTERS) == plano_before
    assert container.sheets.books == before and container.sheets.writes == 0
