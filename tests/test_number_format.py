"""Decimal point and thousands comma through capture, storage and exports."""
import base64
import csv
from copy import deepcopy
from decimal import Decimal
from io import StringIO

import pytest

from app.constants import COUNTS_HEADERS
from tests.fakes import payload, seed_factors, sheet
from tests.test_siesa_factors import FILTERS, lines


def csv_rows(result):
    content = base64.b64decode(result["contenidoBase64"]).decode("utf-8-sig")
    return list(csv.reader(StringIO(content), delimiter=";"))


@pytest.mark.parametrize("closed,opened,factor,stored,converted,display", [
    ("1", "5.145", 1, [1, 5.145, 6.145], "6.145", ["1", "5.145", "6.145"]),
    ("1", "5,145", 1, [1, 5145, 5146], "5146", ["1", "5,145", "5,146"]),
    ("1", "5,145.25", 1, [1, 5145.25, 5146.25], "5146.25", ["1", "5,145.25", "5,146.25"]),
    ("1,234.5", ".75", 24, [1234.5, .75, 1235.25], "29628.75", ["1,234.5", "0.75", "1,235.25"]),
    ("0.1", "0.2", 3, [.1, .2, .3], "0.5", ["0.1", "0.2", "0.3"]),
    ("2", "0.3", 375, [2, .3, 2.3], "750.3", ["2", "0.3", "2.3"]),
])
def test_quantities_keep_their_value_through_all_outputs(container, closed, opened, factor, stored, converted, display):
    seed_factors(container, [[123, "P", "", factor], [2345, "Q", "", 1]])
    data = payload()
    data["conteos"][0].update(cerrado=closed, abierto=opened)
    container.inventory.finalize(data)
    assert container.sheets.books["pdv-0"][1]["values"][1][8:11] == stored
    before = deepcopy(container.sheets.books)
    view = container.admin.consolidated(FILTERS)["registros"][0]
    assert [view["cerrado"], view["abierto"], view["total"]] == stored[:2] + [float(converted)]
    assert csv_rows(container.admin.csv(FILTERS))[1][6:9] == display
    detail = lines(container.admin.flat(FILTERS))[1]
    assert Decimal(detail[148:179]) == Decimal(converted)
    assert len(detail) == 333 and "," not in detail
    assert detail[81:85] == "BR03" and detail[212:223] == "00000000123"
    assert container.sheets.books == before
    assert container.sheets.writes == 1 and container.drive.writes == 0


def test_existing_numeric_counts_ignore_google_display_locale(container):
    seed_factors(container)
    row = ["id", "", FILTERS["fecha"], FILTERS["puntoVenta"], "Bebidas", "000123", "Jugo", "ML", 1, 5145.25, 5146.25]
    counts = sheet("Conteos Mensuales", [COUNTS_HEADERS, row], 1)
    counts["display"][1][8:11] = ["1", "5.145,25", "5.146,25"]
    container.sheets.books["pdv-0"].append(counts)
    before = deepcopy(container.sheets.books)
    assert csv_rows(container.admin.csv(FILTERS))[1][6:9] == ["1", "5,145.25", "5,146.25"]
    assert container.admin.consolidated(FILTERS)["registros"][0]["total"] == 5146.25
    assert Decimal(lines(container.admin.flat(FILTERS))[1][148:179]) == Decimal("5146.25")
    assert container.sheets.books == before
    assert container.sheets.writes == container.drive.writes == 0
