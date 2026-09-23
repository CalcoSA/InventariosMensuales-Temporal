import base64
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier

import pytest

from app.constants import SHEET_MIME
from app.models.errors import DomainError
from app.repositories.monthly_factors import factors_from_book
from app.services.monthly_admin import flat_file
from tests.conftest import make_container, rpc
from tests.fakes import payload, seed_factors, sheet


FILTERS = dict(fecha="2026-09-18", puntoVenta="BR00 - PDV 0", bodega="BR03", consecutivo="897")


def lines(result):
    return base64.b64decode(result["contenidoBase64"]).decode("ascii").split("\r\n")


@pytest.mark.parametrize("closed,factor,opened,total", [
    (2, 24, 5, 53), (0, 24, 5, 5), (2, 24, 0, 48), (1, 1, 3, 4),
    (1, 12, 3, 15), (2, 2.5, 3, 8), (1.5, "24", 0.5, 36.5), (2, "2,5", 0, 5),
])
def test_siesa_factor_only_changes_output_quantity(container, closed, factor, opened, total):
    seed_factors(container, [[123, "Nombre distinto", "Otra presentación", factor, "OTRA"],
                             [2345, "Café", "KG", 1, "KG"]])
    data = payload()
    data["conteos"][0].update(cerrado=closed, abierto=opened)
    container.inventory.finalize(data)
    rows = container.sheets.books["pdv-0"][1]["values"][1:]
    assert rows[0][8:] == [closed, opened, closed + opened]
    before = deepcopy(container.sheets.books)
    csv_before = container.admin.csv(FILTERS)
    consolidated_before = container.admin.consolidated(FILTERS)
    original = flat_file(rows, FILTERS["puntoVenta"], "BR03", "00000897")
    result = container.admin.flat(FILTERS)
    old, new = lines(original), lines(result)
    assert new[0] == "000000100000001009"
    assert new[-1] == "000000499990001009"
    assert all(len(line) == 333 for line in new[1:-1])
    assert new[1][148:180] == f"{total:031.15f}."
    assert new[1][:148] == old[1][:148] and new[1][180:] == old[1][180:]
    assert new[2:] == old[2:]
    assert {k:v for k,v in result.items() if k != "contenidoBase64"} == {
        k:v for k,v in original.items() if k != "contenidoBase64"}
    assert container.sheets.books == before
    assert container.admin.csv(FILTERS) == csv_before
    assert container.admin.consolidated(FILTERS) == consolidated_before
    assert container.sheets.writes == 1 and container.drive.writes == 0


def test_historical_total_is_not_used_or_rewritten(container):
    seed_factors(container, [[123, "P", "", 24], [2345, "P", "", 12]])
    container.inventory.finalize(payload())
    container.sheets.books["pdv-0"][1]["values"][1][10] = 999
    before = deepcopy(container.sheets.books)
    assert lines(container.admin.flat(FILTERS))[1][148:180] == "000000000000098.500000000000000."
    assert container.sheets.books == before
    assert container.admin.consolidated(FILTERS)["registros"][0]["total"] == 999


@pytest.mark.parametrize("factor", ["", None, "abc", "24 unidades", "1,2,3", 0, -1, True, float("nan"), float("inf")])
def test_invalid_factor_blocks_complete_export_with_item_list(container, client, factor):
    seed_factors(container, [[123, "P", "", factor]])
    container.inventory.finalize(payload())
    before = deepcopy(container.sheets.books)
    response = rpc(client, "generarPlanoSiesaMensual", FILTERS)
    assert response.status_code == 400
    assert "000123" in response.text and "002345" in response.text
    assert "Base general" in response.text and "contenidoBase64" not in response.text
    assert container.sheets.books == before and container.sheets.writes == 1


@pytest.mark.parametrize("duplicates,error", [([24,24], False), ([24,"24"], False), ([24,12], True), ([24,""], True)])
def test_duplicate_reference_requires_same_valid_factor(container, duplicates, error):
    seed_factors(container, [[item, "P", "", factor] for item, factor in
                             zip([123, "000123"], duplicates)] + [[2345, "P", "", 1]])
    container.inventory.finalize(payload())
    if error:
        with pytest.raises(DomainError, match="000123"):
            container.admin.flat(FILTERS)
    else:
        assert lines(container.admin.flat(FILTERS))[1][148:180] == "000000000000098.500000000000000."


def test_missing_item_blocks_even_when_closed_is_zero(container):
    seed_factors(container, [[123, "P", "", 24]])
    data = payload()
    data["conteos"][1]["cerrado"] = 0
    container.inventory.finalize(data)
    with pytest.raises(DomainError, match="002345: no existe en Base general"):
        container.admin.flat(FILTERS)


def test_invalid_factors_for_unexported_items_do_not_block(container):
    seed_factors(container, [[123, "P", "", 24], [2345, "P", "", 1], [1922, "P", "", 0],
                             [999, "P", "", 12], [999, "P", "", 24]])
    container.inventory.finalize(payload())
    assert len(lines(container.admin.flat(FILTERS))) == 4


def test_master_excluded_from_points_csv_cleanup_and_cannot_be_saved(container):
    seed_factors(container)
    assert container.bases.points() == [FILTERS["puntoVenta"]]
    assert [f["id"] for f in container.bases.files(fresh=True)] == ["pdv-0"]
    with pytest.raises(DomainError, match="maestro"):
        container.bases.resolve(" Base GENERAL ")
    before = deepcopy(container.sheets.books["factors"])
    container.cleanup.run(dry_run=False)
    assert container.sheets.books["factors"] == before


@pytest.mark.parametrize("masters", [0,2])
def test_source_must_be_unique(container, masters):
    container.inventory.finalize(payload())
    if masters:
        seed_factors(container)
        container.drive.files.append(dict(id="other", name="BASE GENERAL", mimeType=SHEET_MIME, parents=["bases"]))
    with pytest.raises(DomainError, match="único archivo"):
        container.admin.flat(FILTERS)


def test_headers_locate_columns_and_schema_changes_fail_safely():
    assert factors_from_book([sheet("Hoja 1", [["Factor U.M.", "Referencia"], [24, 123]])]) == ({"00000000123":24}, {})
    for book in ([], [sheet("Mensual", [["Referencia", "Factor U.M."], [123,24]])],
                 [sheet("Hoja 1", [["Referencia", "Factor"], [123,24]])],
                 [sheet("Hoja 1", [["Referencia", "Factor U.M."], ["ABC",24]])]):
        with pytest.raises(DomainError):
            factors_from_book(book)


def test_grouped_factors_refresh_between_exports(container):
    seed_factors(container)
    container.inventory.finalize(payload())
    container.bases.points()  # warm folder and file metadata
    before = (container.drive.calls, container.sheets.reads, container.sheets.writes)
    container.admin.flat(FILTERS)
    assert (container.drive.calls, container.sheets.reads, container.sheets.writes) == (before[0], before[1]+2, before[2])
    container.sheets.books["factors"][0]["values"][1][3] = 24
    assert lines(container.admin.flat(FILTERS))[1][148:180] == "000000000000098.500000000000000."
    assert container.sheets.reads == before[1]+4


@pytest.mark.parametrize("users", [10,20,36,40])
def test_concurrent_siesa_exports_share_reads(tmp_path, users):
    c = make_container(tmp_path, delay=.05)
    seed_factors(c)
    c.inventory.finalize(payload())
    c.bases.points()
    before = (c.drive.calls, c.sheets.reads, c.sheets.writes)
    gate = Barrier(users)
    def export(_):
        gate.wait()
        return c.admin.flat(FILTERS)
    with ThreadPoolExecutor(users) as pool:
        results = list(pool.map(export, range(users)))
    assert all(result == results[0] for result in results)
    assert (c.drive.calls, c.sheets.reads, c.sheets.writes) == (before[0], before[1]+2, before[2])
