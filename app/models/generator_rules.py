"""Direct port of pure functions from generador_inventario_mensual.gs.

Indices, priority order and even normalization/extension quirks are preserved.
Sheets are plain display-value matrices, with merged-cell ranges supplied separately.
"""
import re
from app.models.text import clean, generator_normalize as norm, spanish_key

CODE_HEADERS = {"CODIGO", "COD", "ITEM", "CODIGO ITEM", "REFERENCIA"}
PRODUCT_HEADERS = {
    "PRODUCTO", "DESCRIPCION", "NOMBRE PRODUCTO", "NOMBRE DEL PRODUCTO",
    "DESCRIPCION PRODUCTO", "DESCRIPCION DEL PRODUCTO", "DESCRIPCION ITEM", "ARTICULO",
}
UNIT_HEADERS = {"UNIDAD", "UM", "U M", "DESC UM", "UNIDAD DE MEDIDA", "UNIDAD DE EMPAQUE", "PRESENTACION"}
FORBIDDEN = [
    "FORMATO", "INVENTARIO", "PUNTO DE VENTA", "FECHA", "RESPONSABLE",
    "FIRMA", "OBSERVACION", "CODIGO", "PRODUCTO", "DESCRIPCION", "UNIDAD",
    "CANTIDAD", "CONTEO", "ABIERTO", "CERRADO", "TOTAL", "MENSUAL",
]
PACK = re.compile(
    r"\s*(?:[-–—]\s*)?(X\s*[0-9]+(?:[.,][0-9]+)?\s*(?:ML|MILILITROS?|L|LT|LTS|LITROS?|G|GR|GRS|GRAMOS?|KG|KILOS?|UND|UNDS|UNID|UNIDS|UNIDADES?|U|OZ|LB|LIBRAS?|CC|PAQ(?:UETE)?S?|BOLSAS?|BOTELLAS?|LATAS?|CAJAS?|CUBETAS?)?)\s*[;,.]?\s*$",
    re.I,
)


def code_header(text):
    return text in CODE_HEADERS or "CODIGO DEL PRODUCTO" in text


def product_header(text):
    return text in PRODUCT_HEADERS


def unit_header(text):
    return text in UNIT_HEADERS or "DESC U M" in text


def detect_columns(values):
    best = None
    for row_index, row in enumerate(values[:60]):
        code = product = unit = None
        for col, value in enumerate(row[:40]):
            text = norm(value)
            if code_header(text):
                code = col
            if product_header(text):
                product = col
            if unit_header(text):
                unit = col
        score = (3 if code is not None else 0) + (3 if product is not None else 0) + (1 if unit is not None else 0)
        if code is not None and product is not None and (best is None or score > best["puntaje"]):
            best = dict(filaEncabezado=row_index + 1, colCodigo=code, colProducto=product, colUnidad=unit, puntaje=score)
    return best


def split_pack(value):
    text = clean(value or "")
    match = PACK.search(text)
    return {"producto": text[:match.start()].strip(), "unidad": re.sub(r"\s+", " ", match[1]).upper()} if match else {"producto": text, "unidad": ""}


def normalize_unit(value):
    return re.sub(r"\s+", " ", clean(value or "")).upper()


def normalize_code(value):
    code = re.sub(r"\.0+$", "", re.sub(r"\s+", "", re.sub("^'", "", clean(value)))).upper()
    return "" if code in {"TOTAL", "CODIGO", "CÓDIGO", "ITEM", "REFERENCIA"} else code


def possible_codes(value):
    text = clean(value)
    result = {}
    exact = normalize_code(text)
    if exact:
        result[exact] = None
    for found in re.findall(r"\b[A-Z]{0,3}\d{3,10}\b", text.upper(), re.ASCII):
        result[normalize_code(found)] = None
    return list(result)


def pdv_type(name):
    text = norm(name)
    if re.search(r"^BH\s*\d+|^H(?:\.|\s|\d)", text):
        return "HELADERIA"
    if re.search(r"^BC\s*\d+|\bCOCINA\b", text):
        return "COCINA"
    return "RESTAURANTE"


def name_key(name):
    text = norm(name)
    for pattern, replacement in [
        (r"\.(XLSX|XLS|XLSM)$", " "), (r"\(\d+\)$", " "), (r"\b09\b", " "),
        (r"^B[RHCD]?\s*\d+\s*[-.]?\s*", " "), (r"^H\s*\d+\s*", " "),
        (r"\bHELADERIA\b", " "), (r"\bRESTAURANTE\b", " "), (r"^H\b", " "),
        (r"\bETAPA\b", " "), (r"\bTOGO\b", "TO GO"), (r"[^A-Z0-9]+", " "),
        (r"\s+", " "),
    ]:
        text = re.sub(pattern, replacement, text)
    return text.strip().lower()


def match_score(monthly, template):
    left, right = name_key(monthly), name_key(template)
    score = 2 if left == right else 0.8 if left in right or right in left else 0
    a, b = set(left.split()), set(right.split())
    if a | b:
        score += len(a & b) / len(a | b)
    return score + (0.35 if pdv_type(monthly) == pdv_type(template) else -0.35)


def best_template(name, templates):
    best, score = None, -float("inf")
    for template in templates:
        candidate = match_score(name, template["nombre"])
        if candidate > score:
            best, score = template, candidate
    return best if score >= 0.45 else None


def deduplicate_templates(files):
    result = {}
    for file in files:
        key = re.sub(r"\(\d+\)$", "", re.sub(r"\.(XLSX|XLS|XLSM)$", "", norm(file["nombre"]))).strip()
        if key not in result or file["actualizado"] > result[key]["actualizado"]:
            result[key] = file
    return list(result.values())


def clean_category(value):
    return re.sub(r"^[-–—:]+|[-–—:]+$", "", re.sub(r"\s+", " ", clean(value or ""))).strip()


def category_candidate(value, products):
    original, text = clean(value or ""), norm(value or "")
    if not text or not 3 <= len(text) <= 55 or re.fullmatch(r"\d+(?:[.,]\d+)?", original, re.ASCII):
        return False
    if any(word in text for word in FORBIDDEN) or any(code in products for code in possible_codes(original)):
        return False
    return len(text.split()) <= 6


def detect_category_table(values):
    for index, row in enumerate(values[:100]):
        item = category = None
        for col, value in enumerate(row):
            text = norm(value)
            if code_header(text):
                item = col
            if text in {"CATEGORIA", "SECCION", "AREA", "UBICACION", "CATEGORIA INVENTARIO"}:
                category = col
        if item is not None and category is not None:
            return dict(filaEncabezado=index, colItem=item, colCategoria=category)
    return None


def cell(row, index):
    return row[index] if index is not None and index < len(row) else ""


def assign_table(values, structure, products, categories):
    current = ""
    for row in values[structure["filaEncabezado"] + 1:]:
        category = clean(cell(row, structure["colCategoria"]) or "")
        if category_candidate(category, products):
            current = clean_category(category)
        code = normalize_code(cell(row, structure["colItem"]))
        if code in products and current:
            categories[code][current] = None


def add_anchor(anchors, keys, anchor):
    key = "|".join(map(str, [norm(anchor["categoria"]), anchor["fila"], anchor["columnaInicio"], anchor["columnaFin"]]))
    if key not in keys:
        keys.add(key)
        anchors.append(anchor)


def detect_anchors(values, products, merged=()):
    anchors, keys = [], set()
    for area in merged:
        if category_candidate(area["texto"], products):
            add_anchor(anchors, keys, dict(categoria=clean_category(area["texto"]), fila=area["fila"], columnaInicio=area["columnaInicio"], columnaFin=area["columnaFin"], prioridad=10))
    for index, row in enumerate(values):
        cells = [(col + 1, clean(value or "")) for col, value in enumerate(row) if clean(value or "")]
        if not cells or any(code in products for _, text in cells for code in possible_codes(text)):
            continue
        for col, text in cells:
            few = len(cells) <= 3
            if category_candidate(text, products) and (text == text.upper() or few):
                add_anchor(anchors, keys, dict(categoria=clean_category(text), fila=index + 1, columnaInicio=max(1, col - 2), columnaFin=min(len(row), col + 4), prioridad=6 if few else 4))
    return anchors


def column_distance(anchor, col):
    return max(anchor["columnaInicio"] - col, col - anchor["columnaFin"], 0)


def category_for_cell(anchors, row, col):
    best, best_score = "", -float("inf")
    for anchor in anchors:
        distance = row - anchor["fila"]
        columns = column_distance(anchor, col)
        if distance < 0 or distance > 150 or columns > 5:
            continue
        score = anchor["prioridad"] - distance * 0.08 - columns * 1.5
        if score > best_score:
            best, best_score = anchor["categoria"], score
    return best


def same_row_category(row, code_column, products, anchors, row_number):
    candidates = sorted((a for a in anchors if a["fila"] == row_number), key=lambda a: column_distance(a, code_column + 1))
    if candidates:
        return candidates[0]["categoria"]
    for col in list(range(code_column - 1, -1, -1)) + list(range(code_column + 1, len(row))):
        text = clean(row[col] or "")
        if category_candidate(text, products) and text == text.upper() and len(norm(text).split()) <= 4:
            return clean_category(text)
    return ""


def extract_products(sheets):
    products = {}
    for name in ("Pedido Diario", "Bodega"):
        sheet = next((s for s in sheets if norm(s["name"]) == norm(name)), None)
        structure = detect_columns(sheet["display"]) if sheet else None
        if not structure:
            continue
        for row in sheet["display"][structure["filaEncabezado"]:]:
            code, product = normalize_code(cell(row, structure["colCodigo"])), clean(cell(row, structure["colProducto"]) or "")
            if not code or not product:
                continue
            unit = normalize_unit(split_pack(product)["unidad"])
            if code not in products:
                products[code] = dict(codigo=code, producto=product, unidad=unit)
            elif not products[code]["unidad"] and unit:
                products[code]["unidad"] = unit
    return products


def categories_by_code(sheets, products):
    from app.models.errors import DomainError
    categories = {code: {} for code in products}
    candidates = [s for s in sheets if any(norm(n) in norm(s["name"]) for n in ("Mensual", "Formato de Inventario Mensual"))]
    if not candidates:
        raise DomainError("El formato no contiene la hoja Mensual o Formato de Inventario Mensual.")
    for sheet in candidates:
        values = [row[:40] for row in sheet["display"][:5000]]
        if not values:
            continue
        table = detect_category_table(values)
        if table:
            assign_table(values, table, products, categories)
        anchors = detect_anchors(values, products, sheet.get("merged", []))
        for r, row in enumerate(values):
            for c, value in enumerate(row):
                for code in possible_codes(value):
                    if code in products:
                        category = category_for_cell(anchors, r + 1, c + 1) or same_row_category(row, c, products, anchors, r + 1)
                        if category:
                            categories[code][category] = None
    return categories


def output_rows(products, categories):
    rows = [[p["codigo"], p["producto"], p["unidad"], c] for p in products.values() for c in (categories.get(p["codigo"]) or ["SIN CATEGORÍA"])]
    return sorted(rows, key=lambda r: (spanish_key(r[3]), spanish_key(r[1])))


def safe_output_name(name):
    return re.sub(r'[\\/:*?"<>|]', "-", name)


def output_name(name):
    base = re.sub(r"\s*09\s*$", "", re.sub(r"\.xlsx$", "", name, flags=re.I)).strip()
    return safe_output_name(base + " - BASE INVENTARIO.xlsx")
