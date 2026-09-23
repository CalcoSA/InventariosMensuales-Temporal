import base64
from copy import deepcopy
from decimal import Decimal

import pytest

from app.constants import COUNTS_HEADERS
from app.models.errors import DomainError
from app.services.monthly_admin import flat_file, quantity_flat
from tests.fakes import seed_factors, sheet
from tests.test_siesa_factors import FILTERS, lines


@pytest.mark.parametrize("value,expected", [
    (750.3, "000000000000750.300000000000000."),
    (17.8, "000000000000017.800000000000000."),
    (0.1, "000000000000000.100000000000000."),
    ("1.234", "000000000000001.234000000000000."),
    ("1,234.56", "000000000001234.560000000000000."),
    (" 1,234 ", "000000000001234.000000000000000."),
    ("0.0000000000000005", "000000000000000.000000000000001."),
    ("0.0000000000000004", "000000000000000.000000000000000."),
    ("999999999999999.123456789012345", "999999999999999.123456789012345."),
    (-0.0, "000000000000000.000000000000000."),
])
def test_decimal_encoding_has_no_binary_residue_and_keeps_width(value, expected):
    encoded = quantity_flat(value, "00000002427")
    assert encoded["valor"] == expected
    assert len(encoded["valor"]) == 32
    assert encoded["cerosIniciales"] == encoded["cerosFinales"] == "000000000000000." * 2


@pytest.mark.parametrize("value", ["", None, True, "abc", "1_000", "NaN", "Infinity", float("nan"),
                                   float("inf"), -0.1, "2,5", "1.234,56", "1 234,56", "12,34", "1,23,456",
                                   10**15, "999999999999999.9999999999999995"])
def test_invalid_or_overflowing_quantity_cannot_shift_following_fields(value):
    with pytest.raises(DomainError):
        quantity_flat(value, "00000002427")


def test_lllanogrande_regression_852_lines_and_reported_positions():
    rows = [["id", "", "2026-09-23", "BR10 - Lllanogrande", "Bodega", str(10000+i), "P", "UNID", 0, 0, 0]
            for i in range(850)]
    failures = [
        (60, "2427", Decimal("750.3"), "000000000000750.299999999999955."),
        (61, "2425", Decimal("750.3"), "000000000000750.299999999999955."),
        (123, "2461", Decimal("17.8"), "000000000000017.800000000000001."),
    ]
    for number, item, value, _ in failures:
        rows[number-2][5], rows[number-2][10] = item, value
    result = flat_file(rows, "BR10 - Lllanogrande", "BR10", "00000981")
    content = base64.b64decode(result["contenidoBase64"])
    output = lines(result)
    assert len(output) == 852 and content.count(b"\r\n") == 851
    assert result["nombre"] == "LLLANOGRANDE-Mensual-00000981-PlanosPDV.txt"
    assert result["tipo"] == "text/plain;charset=us-ascii"
    assert output[0] == "000000100000001009" and output[-1] == "000085299990001009"
    assert all(len(line) == 333 for line in output[1:-1])
    for number, item, value, previous in failures:
        line = output[number-1]
        assert line[:7] == str(number).zfill(7)
        assert line[18:26] == "00000981" and line[81:85] == "BR10"
        assert line[212:223] == line[262:273] == item.zfill(11)
        assert Decimal(line[148:179]) == value
        assert line[165:179] == "0" * 14
        assert line[273:] == " " * 60
        # Removing 13 fractional positions reproduces the screenshot: 320
        # characters and two decimal points in the indicated 153..169 field.
        old = line[:148] + previous + line[180:]
        shortened = old[:166] + old[179:]
        assert len(shortened) == 320 and shortened[152:169].count(".") == 2
        assert len(line[152:169]) == 17 and line[152:169].count(".") == 1
        assert line[:148] == old[:148] and line[180:] == old[180:]


def test_converted_consolidation_groups_categories_but_preserves_saved_totals(container):
    seed_factors(container, [[123, "P", "", 24], [2345, "P", "", 1]])
    stored = [
        ["id", "", FILTERS["fecha"], FILTERS["puntoVenta"], "Bebidas", "000123", "P", "KG", 2, 5, 999],
        ["id2", "", FILTERS["fecha"], FILTERS["puntoVenta"], "Cocina", "000123", "P", "KG", 1, 0.3, 1.3],
        ["id3", "", FILTERS["fecha"], FILTERS["puntoVenta"], "Cocina", "002345", "Q", "KG", 1.2, 0.3, 1.5],
    ]
    container.sheets.books["pdv-0"].append(sheet("Conteos Mensuales", [COUNTS_HEADERS] + stored, 1))
    before = deepcopy(container.sheets.books)
    csv_before = container.admin.csv(FILTERS)
    view = container.admin.consolidated(FILTERS)["registros"]
    assert view[0] == dict(item="00000123", producto="P", udm="KG", categoria="Bebidas, Cocina",
                           cerrado=3, abierto=5.3, total=77.3)
    assert view[1]["total"] == 1.5
    exported = lines(container.admin.flat(FILTERS))[1:-1]
    assert sum(Decimal(line[148:179]) for line in exported) == Decimal("78.8")
    assert container.admin.csv(FILTERS) == csv_before
    assert container.sheets.books == before
    assert container.sheets.writes == container.drive.writes == 0


def test_decimal_factor_is_not_rounded_through_float(container):
    seed_factors(container, [[123, "P", "", "1.123456789012345"]])
    stored = [["id", "", FILTERS["fecha"], FILTERS["puntoVenta"], "Bebidas", "123", "P", "KG", 1, 0, 1]]
    container.sheets.books["pdv-0"].append(sheet("Conteos Mensuales", [COUNTS_HEADERS] + stored, 1))
    assert lines(container.admin.flat(FILTERS))[1][148:180] == "000000000000001.123456789012345."
