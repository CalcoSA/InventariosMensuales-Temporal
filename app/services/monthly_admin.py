import base64
import math
import re
from decimal import Decimal, ROUND_HALF_UP, localcontext
from app.models.errors import DomainError
from app.models.text import clean, date_key, valid_date, normalize, safe_filename, parse_number, parse_decimal, rounded_count, spanish_key
from app.services.monthly_inventory import parse_opened


def item_siesa(value):
    text = clean(value)
    return text.zfill(8) if re.fullmatch(r"\d+", text, re.ASCII) else text


def item_flat(value):
    text = re.sub(r"\.0+$", "", clean(value))
    if not re.fullmatch(r"\d{1,11}", text, re.ASCII):
        raise DomainError(f'El ítem "{text}" no es válido para el plano Siesa.')
    return text.zfill(11)


def quantity_flat(value, item):
    number = parse_decimal(value)
    if not number.is_finite() or number < 0:
        raise DomainError(f"La cantidad total del ítem {item} no es válida.")
    if number >= Decimal("1e15"):
        raise DomainError(f"La cantidad del ítem {item} supera el tamaño permitido por Siesa.")
    # Keep the existing 32-character slot and its padding. Quantize the decimal
    # value, not the exact binary64 expansion produced by JavaScript toFixed.
    with localcontext() as context:
        context.prec = 50
        number = number.quantize(Decimal("0.000000000000001"), rounding=ROUND_HALF_UP)
    integer, decimal = format(number.copy_abs(), ".15f").split(".")
    if len(integer) > 15:
        raise DomainError(f"La cantidad del ítem {item} supera el tamaño permitido por Siesa.")
    zeros = "000000000000000." * 2
    return dict(cerosIniciales=zeros, valor=integer.zfill(15) + "." + decimal.ljust(15, "0") + ".", cerosFinales=zeros)


def pdv_flat(value):
    return safe_filename(re.sub(r"^[A-Z]{1,4}\d{1,3}\s*[-–]\s*", "", clean(value), flags=re.I | re.ASCII)).upper() or "PDV"


def csv_field(value):
    return '"' + clean(value).replace('"', '""') + '"' if value is None else '"' + str(value).replace('"', '""') + '"'


def quantity_csv(value, item):
    number = parse_decimal(value)
    if not number.is_finite() or number < 0:
        raise DomainError(f"El ítem {item} tiene una cantidad inválida para el CSV.")
    text = format(number, ",f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def download(name, mime, content, count, **extra):
    return dict(nombre=name, tipo=mime, contenidoBase64=base64.b64encode(content.encode("utf-8")).decode("ascii"), registros=count, **extra)


def flat_file(rows, pdv, warehouse, sequence):
    if len(rows) > 9999997:
        raise DomainError("El plano supera la cantidad máxima de registros.")
    lines = ["000000100000001009"]
    for index, row in enumerate(rows):
        item = item_flat(row[5])
        quantity = quantity_flat(row[10], item)
        line = (str(index + 2).zfill(7) + "04120002009" + sequence + " " * 55 + warehouse + " " * 26 +
                "00000" + quantity["cerosIniciales"] + quantity["valor"] + quantity["cerosFinales"] +
                item + "0" * 39 + item + " " * 60)
        if len(line) != 333:
            raise DomainError(f"No fue posible formar el registro del ítem {item}.")
        lines.append(line)
    lines.append(str(len(lines) + 1).zfill(7) + "99990001009")
    return download(f"{pdv_flat(pdv)}-Mensual-{sequence}-PlanosPDV.txt", "text/plain;charset=us-ascii", "\r\n".join(lines),
                    len(rows), consecutivo=sequence, bodega=warehouse)


def consolidate(rows):
    grouped = {}
    for row in rows:
        item = item_siesa(row[5])
        key = item + "|" + normalize(row[6]) + "|" + normalize(row[7])
        if key not in grouped:
            grouped[key] = dict(item=item, producto=clean(row[6]), udm=clean(row[7]), categorias=[], cerrado=0, abierto=Decimal(0), total=Decimal(0))
        record = grouped[key]
        category = clean(row[4])
        if category and category not in record["categorias"]:
            record["categorias"].append(category)
        for col, field in ((8, "cerrado"), (9, "abierto"), (10, "total")):
            if field == "cerrado":
                number = parse_number(row[col])
                record[field] += number if math.isfinite(number) else 0
            else:
                number = parse_decimal(row[col])
                record[field] += number if number.is_finite() else Decimal(0)
    records = []
    for record in grouped.values():
        result = {k: v for k, v in record.items() if k != "categorias"}
        result["categoria"] = ", ".join(record["categorias"])
        for field in ("cerrado", "abierto", "total"):
            result[field] = rounded_count(record[field]) if field == "cerrado" else float(record[field])
        records.append(result)
    return sorted(records, key=lambda r: spanish_key(r["item"], numeric=True))


class MonthlyAdminService:
    def __init__(self, bases, inventory, identity, factors):
        self.bases, self.inventory, self.identity, self.factors = bases, inventory, identity, factors

    def _filters(self, data, require_pdv=True):
        self.identity.require_admin()
        if not isinstance(data, dict):
            raise DomainError("Seleccione la fecha del inventario.")
        date, pdv = valid_date(data.get("fecha")), clean(data.get("puntoVenta"))
        if require_pdv and not pdv:
            raise DomainError("Seleccione un punto de venta.")
        return date, pdv

    def _rows(self, date, pdv):
        book = self.inventory.read_view(self.bases.resolve(pdv))
        rows = self.inventory.counts(book)
        if not rows:
            raise DomainError("El PDV seleccionado no tiene conteos mensuales.")
        rows = [r for r in rows if date_key(r[2]) == date and normalize(r[3]) == normalize(pdv)]
        if not rows:
            raise DomainError(f"No se encontraron conteos de {pdv} para la fecha seleccionada.")
        return rows

    def consolidated(self, data):
        date, pdv = self._filters(data)
        records = consolidate(self._converted_rows(date, pdv, decimal_opened=True))
        # Sum decimal columns here so the browser need not add binary floats.
        summary = {field: float(sum((parse_decimal(row[field]) for row in records), Decimal(0)))
                   for field in ("abierto", "total")}
        return dict(puntoVenta=pdv, fecha=date, registros=records, resumen=summary)

    def flat(self, data):
        date, pdv = self._filters(data)
        warehouse, sequence = clean(data.get("bodega")).upper(), clean(data.get("consecutivo"))
        if not re.fullmatch(r"[A-Z0-9]{4}", warehouse):
            raise DomainError("La bodega debe tener 4 caracteres. Ejemplo: BR03.")
        if not re.fullmatch(r"\d{1,8}", sequence, re.ASCII):
            raise DomainError("El consecutivo debe contener solamente números y tener máximo 8 dígitos.")
        return flat_file(self._converted_rows(date, pdv), pdv, warehouse, sequence.zfill(8))

    def _converted_rows(self, date, pdv, *, decimal_opened=False):
        rows = self._rows(date, pdv)
        factors, issues = self.factors.read()
        problems, converted = {}, []
        for row in rows:
            item = item_flat(row[5])
            problem = issues.get(item)
            if not problem and item not in factors:
                problem = "no existe en Base general"
            if problem:
                problems[clean(row[5])] = problem
                continue
            closed = parse_decimal(row[8])
            # The consolidated view follows capture's decimal rule for Abierto.
            # Keep the validated Siesa parsing unchanged by default.
            opened = parse_opened(row[9]) if decimal_opened else parse_decimal(row[9])
            if any(not value.is_finite() or value < 0 for value in (closed, opened)):
                raise DomainError(f"El ítem {clean(row[5])} tiene Cerrado o Abierto inválido.")
            output = list(row)
            if decimal_opened:
                output[9] = opened
            with localcontext() as context:
                context.prec = 50
                output[10] = closed * factors[item] + opened
            converted.append(output)
        if problems:
            detail = "; ".join(f"{item}: {reason}" for item, reason in problems.items())
            raise DomainError(f"No se pudo calcular el total convertido. Revise Base general: {detail}.")
        return converted

    def csv(self, data):
        date, pdv = self._filters(data, require_pdv=False)
        records = []
        for file in self.bases.files(fresh=True):
            if pdv and normalize(file["name"]) != normalize(pdv):
                continue
            book = self.inventory.read_view(file["id"])
            # Keep displayed dates/catalog labels, but never parse quantities
            # from locale-dependent Sheets formatting.
            for row, raw in zip(self.inventory.counts(book, display=True), self.inventory.counts(book)):
                if date_key(row[2]) == date:
                    quantities = [quantity_csv(value, row[5]) for value in raw[8:11]]
                    records.append([row[2], row[3], row[4], item_siesa(row[5]), *row[6:8], *quantities])
        if not records:
            raise DomainError("No se encontraron conteos mensuales para la fecha y el PDV seleccionados.")
        records.sort(key=lambda r: (spanish_key(r[1]), spanish_key(r[2]), spanish_key(r[3])))
        headers = ["Fecha inventario", "Punto de venta", "Categoría", "Item Siesa", "Nombre Producto", "Desc. U.M.", "Cerrado", "Abierto", "Total"]
        content = "\ufeff" + "\r\n".join(";".join(csv_field(v) for v in row) for row in [headers] + records)
        suffix = "_" + safe_filename(pdv) if pdv else "_Todos_los_PDV"
        return download("Conteos_Mensuales_" + date + suffix + ".csv", "text/csv;charset=utf-8", content, len(records))
