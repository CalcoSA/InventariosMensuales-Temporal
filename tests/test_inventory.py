from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import base64
import pytest
from app.constants import COUNTS_HEADERS, ADMIN_EMAIL
from app.models.errors import DomainError, DuplicateInventory, WriteUncertain
from app.models.text import valid_date
from app.models.sheets import decode_book, cell_data
from app.services.monthly_inventory import validate_payload, validate_integrity
from app.services.monthly_cleanup import partition_counts
from tests.fakes import payload, sheet
from tests.conftest import rpc


def test_finalize_exact_rows_and_states(container):
    data = payload()
    result = container.inventory.finalize(data)
    assert result["registros"] == 2
    counts = container.sheets.books["pdv-0"][1]["values"]
    assert counts[0] == COUNTS_HEADERS
    assert len(counts[1]) == 11
    assert counts[1][0] == counts[2][0]
    assert counts[1][5] == "000123"
    assert counts[1][8:] == [4, 2.5, 6.5]
    assert isinstance(counts[1][1], datetime)
    assert container.sheets.writes == 1
    assert container.inventory.states(data["puntoVenta"], data["fecha"])[0]["guardada"]
    with pytest.raises(DuplicateInventory):
        container.inventory.finalize(data)
    assert container.sheets.writes == 1


def test_google_calls_by_user_flow(client,container):
    """Whole flows stay batched; technical OAuth and pagination are excluded."""
    c=container
    def count():return c.drive.calls+c.sheets.reads+c.sheets.writes
    def measured(expected,action):
        before=count()
        result=action()
        assert count()-before==expected
        return result
    pdv="BR00 - PDV 0"
    filters=dict(fecha="2026-09-18",puntoVenta=pdv,bodega="BR03",consecutivo="897")
    measured(0,lambda:client.get("/"))
    measured(0,lambda:rpc(client,"obtenerEstadoAdministrador"))
    measured(2,c.inventory.points)
    measured(0,c.inventory.points)
    measured(2,lambda:c.inventory.categories(pdv))
    measured(0,lambda:c.inventory.products(pdv,"Bebidas"))
    measured(0,lambda:c.inventory.products(pdv,"Cocina"))
    measured(1,lambda:c.inventory.states(pdv,"2026-09-18"))
    measured(2,lambda:c.inventory.finalize(payload()))
    measured(1,lambda:c.admin.consolidated(filters))
    measured(2,lambda:c.admin.csv(filters))
    measured(1,lambda:c.admin.flat(filters))


def test_distinct_categories_same_sheet(container):
    container.inventory.finalize(payload())
    container.inventory.finalize(payload(category="Cocina"))
    assert len(container.sheets.books["pdv-0"][1]["values"]) == 4
    assert not any("repeatCell" in r for r in container.sheets.history[1])


def test_small_empty_counts_grid_expands_before_header_format(container):
    target=sheet("Conteos Mensuales",[],1)
    target.update(rows=1,columns=2)
    container.sheets.books["pdv-0"].append(target)
    container.inventory.finalize(payload())
    requests=container.sheets.history[0]
    assert "appendDimension" in requests[0] and "appendDimension" in requests[1]
    assert "repeatCell" in requests[2]


@pytest.mark.parametrize("value", ["", " ", None, -1, "-0.01", "NaN", "Infinity", float("inf"), True, [], {}, "1,2,3", "abc"])
@pytest.mark.parametrize("field", ["cerrado", "abierto"])
def test_invalid_quantities(value, field, container):
    data = payload()
    data["conteos"][0][field] = value
    with pytest.raises(DomainError):
        container.inventory.finalize(data)
    assert container.sheets.writes == 0


@pytest.mark.parametrize("field,value", [("item","999"),("producto","Otro"),("udm","OTRA")])
def test_tampered_catalog(field,value,container):
    data=payload()
    data["conteos"][0][field]=value
    with pytest.raises(DomainError):
        container.inventory.finalize(data)
    assert container.sheets.writes==0


def test_missing_extra_repeated_products(container):
    for mode in ("missing","extra","repeated"):
        data=payload()
        if mode=="missing": data["conteos"].pop()
        elif mode=="extra": data["conteos"].append(deepcopy(data["conteos"][0]))
        else: data["conteos"][1]=deepcopy(data["conteos"][0])
        with pytest.raises(DomainError): container.inventory.finalize(data)
    assert container.sheets.writes==0


def test_finalize_revalidates_catalog_after_cache(container):
    container.inventory.products("BR00 - PDV 0")
    container.sheets.books["pdv-0"][0]["display"][1][2]="Producto cambiado"
    with pytest.raises(DomainError):
        container.inventory.finalize(payload())
    assert container.sheets.writes==0


@pytest.mark.parametrize("date", ["2026-02-30","invalid","2026-9-18","","0000-01-01"])
def test_invalid_dates(date):
    with pytest.raises(DomainError): valid_date(date)


def test_csv_consolidated_and_flat(container):
    data=payload()
    container.inventory.finalize(data)
    filters=dict(fecha=data["fecha"],puntoVenta=data["puntoVenta"],bodega="BR03",consecutivo="897")
    csv=container.admin.csv(filters)
    content=base64.b64decode(csv["contenidoBase64"]).decode("utf-8")
    assert content.startswith('\ufeff"Fecha inventario";')
    assert '"00000123"' in content
    flat=container.admin.flat(filters)
    lines=base64.b64decode(flat["contenidoBase64"]).decode("ascii").split("\r\n")
    assert lines[0]=="000000100000001009"
    assert all(len(line)==333 for line in lines[1:-1])
    assert lines[-1]=="000000499990001009"
    assert container.admin.consolidated(filters)["registros"][0]["total"]==6.5


def test_cleanup_preserves_invalid_exact_boundary_and_catalog(container):
    now=datetime(2026,9,18,12,tzinfo=ZoneInfo("America/Bogota"))
    cutoff=now-timedelta(days=5)
    counts=[["id",v,"2026-09-18","BR00 - PDV 0","Bebidas","1","P","KG",1,1,2]
            for v in (cutoff-timedelta(seconds=1),cutoff,now,"2020-01-01",None)]
    container.sheets.books["pdv-0"].append(sheet("Conteos Mensuales",[COUNTS_HEADERS]+counts,1))
    catalog=deepcopy(container.sheets.books["pdv-0"][0])
    container.cleanup.now=lambda:now
    dry=container.cleanup.run()
    assert dry["registrosEliminados"]==1
    assert container.sheets.writes==0
    result=container.cleanup.run(dry_run=False)
    assert result["registrosEliminados"]==1
    assert len(container.sheets.books["pdv-0"][1]["values"])==5
    assert container.sheets.books["pdv-0"][0]==catalog
    assert container.sheets.writes==1


def test_failed_write_never_reports_success(container):
    container.sheets.fail_write=WriteUncertain("Google no confirmó el guardado.")
    with pytest.raises(WriteUncertain): container.inventory.finalize(payload())
    assert len(container.sheets.books["pdv-0"])==1


def test_decode_values_dates_zeros_and_literal_formulas():
    payload={"properties":{"timeZone":"America/Bogota"},"sheets":[{
        "properties":{"sheetId":1,"title":"Mensual","gridProperties":{"rowCount":20,"columnCount":4}},
        "data":[{"rowData":[{"values":[
            {"effectiveValue":{"numberValue":123},"formattedValue":"000123"},
            {"effectiveValue":{"numberValue":46283.5},"formattedValue":"18/09/2026 12:00","effectiveFormat":{"numberFormat":{"type":"DATE_TIME"}}},
            {"effectiveValue":{"numberValue":0},"formattedValue":"0"}
        ]}]}],"merges":[{"startRowIndex":0,"startColumnIndex":0,"endColumnIndex":2,"endRowIndex":1}]}]}
    result=decode_book(payload)[0]
    assert result["display"][0][0]=="000123"
    assert isinstance(result["values"][0][1],datetime)
    assert result["values"][0][2]==0
    assert cell_data("=1+1")=={"userEnteredValue":{"stringValue":"=1+1"}}


def test_http_routes_security_and_errors(client,container):
    assert client.get("/").status_code==200
    assert "script-src 'self';" in client.get("/").headers["Content-Security-Policy"]
    assert rpc(client,"obtenerPuntosVenta").json["result"]==["BR00 - PDV 0"]
    assert rpc(client,"obtenerCategorias","BR00 - PDV 0").json["result"]==["Bebidas","Cocina"]
    assert rpc(client,"guardarInventario",payload()).status_code==200
    assert rpc(client,"guardarInventario",payload()).status_code==409
    assert rpc(client,"noExiste").status_code==404
    assert client.post("/api/guardarInventario",json={"args":[payload()]}).status_code==403
    assert client.post("/api/guardarInventario",json={"args":[payload()]},headers={"X-Monthly-Request":"1","Origin":"https://evil.example"}).status_code==403
    assert client.get("/credentials/token.json").status_code==404
    assert rpc(client,"obtenerProductos",{}).status_code==400
    container.identity.provider=lambda:None
    assert rpc(client,"obtenerEstadoAdministrador").json["result"]=={"esAdministrador":False}
    for method in ("obtenerConteoConsolidadoPDV","generarDescargaConteosMensuales","generarPlanoSiesaMensual"):
        assert rpc(client,method,{}).status_code==403
    assert client.post("/api/generarPlanoSiesaMensual?usuario=abc",json={"args":[{}]},
                       headers={"X-Monthly-Request":"1","X-User-Email":ADMIN_EMAIL}).status_code==403
