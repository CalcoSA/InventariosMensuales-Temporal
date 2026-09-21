import base64
import json
from pathlib import Path
import subprocess
import pytest
from app.models import generator_rules as g
from app.models import text as t
from app.models.errors import DomainError
from app.services import monthly_admin as a
from app.repositories.monthly_bases import products_from_book, find_index
from tests.fakes import sheet

ROOT = Path(__file__).resolve().parent.parent


def oracle(cases):
    result = subprocess.run(["node", str(ROOT / "tests/legacy_oracle.cjs")], input=json.dumps(cases, ensure_ascii=False),
                            encoding="utf-8", capture_output=True, check=True)
    return json.loads(result.stdout)


FUNCTIONS = [
    ("generator", "normalizarTexto_", g.norm, [["  Café--Ñandú / % "], ["A.1.xlsx"], [None], [0]]),
    ("generator", "normalizarCodigo_", g.normalize_code, [["' 00123.000 "], ["item"], ["Total"], ["ab 012"], [None]]),
    ("generator", "separarUnidadEmpaque_", g.split_pack, [[v] for v in ["Jugo X 750 ML", "Queso - X 2 KG", "Palitos X 6 UNIDADES", "Café X12", "Salsa x 1,5 L;", "Jugo ML", "A X 12 bolsas", "A X 2.", "X 12", "A X 2\n", "Jugo\u00a0X\u00a0750\u00a0ML"]]),
    ("generator", "normalizarUnidad_", g.normalize_unit, [[" x  2 kg "], [None]]),
    ("generator", "codigosPosiblesEnCelda_", g.possible_codes, [["Ref ABC123 y 00123"], ["TOTAL"], ["0003.00"], ["Ñ123 á234"]]),
    ("generator", "tipoPdv_", g.pdv_type, [[v] for v in ["BH01 Heladería", "H. Envigado", "H2", "BC01", "Cocina Central", "BR03", "HELADERIA Centro"]]),
    ("generator", "claveNombre_", g.name_key, [[v] for v in ["BH01 - Heladería Centro 09.xlsx", "BR 12 Restaurante Norte (2).xlsx", "H. Río TOGO ETAPA", "Árbol 09.xlsm"]]),
    ("generator", "puntajeCoincidencia_", g.match_score, [["BR01 Norte 09.xlsx", "BR01 Norte.xlsx"], ["BH01 Centro.xlsx", "BC01 Centro.xlsx"], ["", ""], ["A", "XYZ"]]),
    ("generator", "crearNombreSalida_", g.output_name, [["BH01 - Río 09.xlsx"], ["a/b:09  .xlsx"], ["Norte.xlsx"]]),
    ("generator", "limpiarNombreArchivo_", g.safe_output_name, [['a/b:c*d?e"f<g>h|i\\j']]),
    ("generator", "limpiarCategoria_", g.clean_category, [[" -- BEBIDAS : "], ["a  b"], ["–Cocina—"]]),
    ("web", "normalizar_", t.normalize, [["  Café.  Ñandú "], [0], [None]]),
    ("web", "limpiarTextoMensual_", t.clean, [[None], [0], ["  ab  cd  "]]),
    ("web", "crearClaveProductoMensual_", t.product_key, [[dict(item="001", producto=" Café  ", udm="KG")], [{}]]),
    ("web", "claveFechaMensual_", t.date_key, [["1/2/2026"], ["2026-09-18"], ["31-12-2025"], ["invalid"]]),
    ("web", "nombreArchivoSeguro_", t.safe_filename, [["Árbol / Ñandú"], ["-- a.b --"]]),
    ("web", "formatearItemSiesa_", a.item_siesa, [["123"], ["000123"], ["123.0"], ["ABC"], [123]]),
    ("web", "formatearItemPlanoSiesa_", a.item_flat, [["123"], ["123.00"], ["00012345678"]]),
    ("web", "convertirNumeroPlanoSiesa_", t.parse_number, [["1.234,5"], ["1,234.5"], [" 1 234,25 "], [0], [""]]),
    ("web", "nombrePDVPlanoSiesa_", a.pdv_flat, [["BR03 - Río Norte"], ["BH1–Heladería"], ["BC1 - Cocina"], [""]]),
    ("web", "redondearConteoMensual_", t.rounded_count, [[0.1+0.2], [2.12345678], [0.0000005], [-0.0000005]]),
    ("web", "formatearCantidadPlanoSiesa_", a.quantity_flat, [[v,"00000000123"] for v in [0, 0.1, 1.005, 2.5, 123456789.125, "1.234,56", 0.000000000000001, 999999999999999]]),
    ("web", "escaparCampoCSV_", a.csv_field, [[' café;"'], [None], [0], [" x \n y "]]),
    ("web", "buscarIndiceMensual_", find_index, [[["x","codigo","item"],["item","codigo"]], [["x"],["categoria"]]]),
]


@pytest.mark.parametrize("project,name,python,cases", FUNCTIONS, ids=[row[1] for row in FUNCTIONS])
def test_pure_functions(project, name, python, cases):
    expected = oracle([dict(project=project, function=name, args=args) for args in cases])
    for args, result in zip(cases, expected):
        assert "error" not in result, (name, args, result)
        actual = python(*args)
        assert actual == result["result"], (name, args, actual, result)


@pytest.mark.parametrize("value", ["abc", "123456789012", "-1", "", "12,0"])
def test_invalid_flat_items(value):
    expected = oracle([dict(project="web", function="formatearItemPlanoSiesa_", args=[value])])[0]
    with pytest.raises(DomainError) as caught:
        a.item_flat(value)
    assert str(caught.value) == expected["error"]


def test_spanish_collation():
    values = ["nube", "Ñandú", "Norte", "ñandu", "arbol", "Árbol", "A", "a", "z", "PDV 2", "PDV 10"]
    source = "process.stdout.write(JSON.stringify(JSON.parse(process.argv[1]).sort((a,b)=>a.localeCompare(b,'es'))))"
    expected = json.loads(subprocess.check_output(["node", "-e", source, json.dumps(values)], encoding="utf-8"))
    assert sorted(values, key=t.spanish_key) == expected


def test_generator_tables_anchors_and_categories():
    values = [["Inventario Mensual", "", "", ""], ["BEBIDAS", "", "", ""],
              ["Código", "Producto", "Categoría", ""], ["00123", "Jugo X 12", "Bebidas", ""],
              ["00456", "Café", "", ""], ["COCINA", "", "", ""], ["00789", "Queso", "", ""]]
    products = {code: dict(codigo=code, producto="P", unidad="") for code in ("00123", "00456", "00789")}
    merged = [dict(texto="BEBIDAS", fila=2, columnaInicio=1, columnaFin=4)]
    book = [dict(name="Mensual", display=values, merged=merged)]
    cases = [
        dict(project="generator", function="detectarColumnas_", args=[values]),
        dict(project="generator", function="detectarTablaCategorias_", args=[values]),
        dict(project="generator", function="detectarAnclasCategorias_", args=[values,list(products),merged]),
        dict(project="generator", function="obtenerCategoriasPorCodigo_", args=["id",products], book=book),
    ]
    result = oracle(cases)
    assert g.detect_columns(values) == result[0]["result"]
    assert g.detect_category_table(values) == result[1]["result"]
    anchors = g.detect_anchors(values, products, merged)
    assert anchors == result[2]["result"]
    assert {k:list(v) for k,v in g.categories_by_code(book,products).items()} == result[3]["result"]
    positions = [(1,1),(2,1),(5,3),(152,4),(153,9),(12,10)]
    expected = oracle([dict(project="generator",function="categoriaParaCelda_",args=[anchors,r,c]) for r,c in positions])
    assert [g.category_for_cell(anchors,r,c) for r,c in positions] == [x["result"] for x in expected]


@pytest.mark.parametrize("value", ["BEBIDAS", "No contiene producto", "123", "ABIERTO", "00123", "A", "A B C D E F G", "--- Cocina --", "ÁREA"])
def test_category_candidate(value):
    expected = oracle([dict(project="generator",function="esCategoriaCandidata_",args=[value,["00123"]])])[0]
    assert g.category_candidate(value, {"00123": {}}) == expected["result"]


def test_matching_and_duplicates():
    files = [dict(id=str(i),nombre=n,actualizado=i,mimeType="x") for i,n in enumerate(
        ["BR01 Norte.xlsx", "BR01 Norte.xlsx", "BR01 Norte (1).xlsx", "BH02 Sur.xls", "BC01 Cocina.xlsx"])]
    expected = oracle([
        dict(project="generator",function="quitarDuplicadosFormatos_",args=[files]),
        dict(project="generator",function="buscarMejorFormato_",args=["BR01 Norte 09.xlsx",files]),
    ])
    assert g.deduplicate_templates(files) == expected[0]["result"]
    assert g.best_template("BR01 Norte 09.xlsx",files) == expected[1]["result"]


def test_products_and_output_rows():
    rows = [["CATEGORIA","CODIGO","DESCRIPCION","UNIDAD"],["Bebidas","00123","Café","KG"],
            ["Cocina","00456","no tiene",""],["","5","X",""],["Bebidas","3","Jugo","ML"]]
    book = [sheet("Mensual", rows)]
    expected = oracle([dict(project="web",function="obtenerProductos",args=["PDV"],book=book)])[0]
    assert products_from_book(book,"PDV") == expected["result"]
    products = {"001":dict(codigo="001",producto="Árbol",unidad="X 1"),"002":dict(codigo="002",producto="Nube",unidad="")}
    categories = {"001":["Cocina","Bebidas"],"002":[]}
    expected = oracle([dict(project="generator",function="construirFilasSalida_",args=[products,categories])])[0]
    assert g.output_rows(products,categories) == expected["result"]


def test_full_flat_and_consolidated():
    rows = [["id","2026-09-18 12:00","2026-09-18","BR03 - Río","Bebidas","000123","Café","KG",4,2.5,6.5],
            ["id2","2026-09-18 13:00","2026-09-18","BR03 - Río","Cocina","000123","Café","KG",0.1,0.2,0.3]]
    book = [sheet("Conteos Mensuales", [[""]*11]+rows)]
    # Oracle getValues must receive numeric values, not display strings.
    book[0]["display"] = book[0]["values"]
    filters = dict(fecha="2026-09-18",puntoVenta="BR03 - Río",bodega="BR03",consecutivo="897")
    expected = oracle([dict(project="web",function="generarPlanoSiesaMensual",args=[filters],book=book),
                       dict(project="web",function="obtenerConteoConsolidadoPDV",args=[filters],book=book)])
    assert a.flat_file(rows,filters["puntoVenta"],"BR03","00000897") == expected[0]["result"]
    assert a.consolidate(rows) == expected[1]["result"]["registros"]


def test_csv_full_bytes(container):
    from tests.fakes import payload
    container.inventory.finalize(payload())
    filters=dict(fecha="2026-09-18",puntoVenta="BR00 - PDV 0")
    book=[dict(name=s["name"],display=s["display"]) for s in container.sheets.books["pdv-0"]]
    expected=oracle([dict(project="web",function="generarDescargaConteosMensuales",args=[filters],book=book,
                          csvFiles=[dict(id="pdv-0",name="BR00 - PDV 0")])])[0]
    assert container.admin.csv(filters)==expected["result"]


def test_generator_extraction_and_same_row_fallback():
    book=[dict(name="Pedido Diario",display=[["Código","Producto","Unidad"],["001","Jugo X 12","NO USAR"],["002","Café","KG"]]),
          dict(name="Bodega",display=[["Código","Producto"],["002","Café X 2 KG"],["003","No tiene"]])]
    expected=oracle([dict(project="generator",function="extraerProductosActualizados_",args=["id"],book=book)])[0]
    assert g.extract_products(book)==expected["result"]
    rows=[["COCINA","001","X"],["Bebidas","001","BODEGA"],["001","1","PRODUCTO"]]
    expected=oracle([dict(project="generator",function="categoriaEnMismaFila_",args=[r,1,["001"],[],2]) for r in rows])
    assert [g.same_row_category(r,1,{"001":{}},[],2) for r in rows]==[x["result"] for x in expected]


def test_header_scan_priority_and_limits():
    rows=[["Código","Producto"],["Item","Descripción","UDM"],["COD","PRODUCTO","UNIDAD"],
          ["ITEM","NOMBRE PRODUCTO","PRESENTACIÓN"]]
    cases=[rows,[[""]]*60+[["Código","Producto","Unidad"]],[[""]]*99+[["Código","Categoría"]]]
    expected=oracle([dict(project="generator",function="detectarColumnas_",args=[r]) for r in cases])
    assert [g.detect_columns(r) for r in cases]==[x["result"] for x in expected]


def test_generated_siesa_decimal_cases():
    import random
    rng=random.Random(20260918)
    values=[rng.randrange(10**12)/10**rng.randrange(0,12) for _ in range(100)]+[-0.0,0.0000000000000005,9.999999999999999]
    expected=oracle([dict(project="web",function="formatearCantidadPlanoSiesa_",args=[v,"1"]) for v in values])
    assert [a.quantity_flat(v,"1") for v in values]==[x["result"] for x in expected]
