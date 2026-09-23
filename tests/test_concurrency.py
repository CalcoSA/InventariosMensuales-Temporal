from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import perf_counter
import pytest
from app.models.errors import DuplicateInventory
from tests.conftest import make_container
from tests.fakes import payload, sheet, seed_factors
from app.constants import COUNTS_HEADERS

RESULTS=[]


@pytest.mark.parametrize("users",[10,20,36,40])
@pytest.mark.parametrize("flow",["reads","distinct_saves","duplicate_saves","states","admin"])
def test_load(users,flow,tmp_path):
    c=make_container(tmp_path,points=users if flow=="distinct_saves" else 1,delay=.005)
    pdv="BR00 - PDV 0"
    products=40 if flow in ("distinct_saves","duplicate_saves") else 2
    if products==40:
        catalog=[["Categoría","Item","Nombre Producto","Desc U M"]]+[
            ["Bebidas",f"{i:06}",f"Producto {i}","KG"] for i in range(1,41)]
        for file_id in c.sheets.books:
            c.sheets.books[file_id]=[sheet("Mensual",catalog)]
    def submission(point=pdv):
        data=payload(pdv=point)
        data["conteos"]=[dict(item=f"{i:06}",producto=f"Producto {i}",udm="KG",cerrado="4",abierto="2.5")
                         for i in range(1,41)]
        return data
    if flow=="admin":
        seed_factors(c)
        c.inventory.finalize(payload())
    before=c.drive.calls+c.sheets.reads+c.sheets.writes
    reads_before,writes_before=c.sheets.reads,c.sheets.writes
    c.locks.max_wait=0.0
    gate=Barrier(users)
    def worker(i):
        gate.wait()
        try:
            if flow=="reads":
                assert pdv in c.inventory.points()
                assert c.inventory.categories(pdv)==["Bebidas","Cocina"]
                assert len(c.inventory.products(pdv,"Bebidas"))==2
                assert len(c.inventory.products(pdv,"Cocina"))==1
            elif flow=="distinct_saves":
                c.inventory.finalize(submission(f"BR{i:02} - PDV {i}"))
            elif flow=="duplicate_saves":c.inventory.finalize(submission())
            elif flow=="states":assert len(c.inventory.states(pdv,"2026-09-18"))==2
            else:assert len(c.admin.consolidated(dict(puntoVenta=pdv,fecha="2026-09-18"))["registros"])==2
            return "success"
        except DuplicateInventory:return "duplicate"
    started=perf_counter()
    with ThreadPoolExecutor(users) as pool:outcomes=list(pool.map(worker,range(users)))
    elapsed=perf_counter()-started
    metrics=dict(usuarios=users,flujo=flow,exitos=outcomes.count("success"),duplicadosRechazados=outcomes.count("duplicate"),
                 fallos=0,segundos=round(elapsed,6),maxEspera=round(c.locks.max_wait,6),
                 llamadasGoogle=c.drive.calls+c.sheets.reads+c.sheets.writes-before,
                 lecturasSheets=c.sheets.reads-reads_before,escriturasSheets=c.sheets.writes-writes_before,
                 singleFlightEsperas=c.cache.waits,respuestas429=0,productosPorInventario=products)
    RESULTS.append(metrics)
    assert outcomes.count("success")==(1 if flow=="duplicate_saves" else users)
    assert outcomes.count("duplicate")==(users-1 if flow=="duplicate_saves" else 0)
    if flow=="reads":assert metrics["llamadasGoogle"]==4
    if flow=="distinct_saves":assert c.sheets.writes==users
    if flow=="duplicate_saves":
        assert c.sheets.writes==1
        assert c.sheets.reads==users  # no cached duplicate decisions
    if flow in ("distinct_saves","duplicate_saves"):
        record_ids=set()
        for i,book in enumerate(c.sheets.books.values()):
            counts=next(s["values"] for s in book if s["name"]=="Conteos Mensuales")
            assert counts[0]==COUNTS_HEADERS and len(counts)==41
            ids={r[0] for r in counts[1:]}
            assert len(ids)==1 and not record_ids.intersection(ids)
            record_ids.update(ids)
            assert {r[5] for r in counts[1:]}=={f"{n:06}" for n in range(1,41)}
            assert all(r[3]==f"BR{i:02} - PDV {i}" and r[8:]==[4,2.5,6.5] for r in counts[1:])


@pytest.mark.parametrize("users",[10,20,36,40])
def test_draft_load(users):
    import json, subprocess
    from pathlib import Path
    result=subprocess.run(["node",str(Path(__file__).with_name("frontend_load.cjs")),str(users)],
                          capture_output=True,encoding="utf-8",check=True)
    metrics=json.loads(result.stdout)
    RESULTS.append(metrics)
    assert metrics["exitos"]==users and metrics["llamadasGoogle"]==0
