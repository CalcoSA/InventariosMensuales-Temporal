from collections import Counter
from datetime import datetime
import math
from uuid import uuid4
from zoneinfo import ZoneInfo
from app.models.errors import DomainError, DuplicateInventory
from app.models.text import clean, date_key, valid_date, normalize, product_key, spanish_key, parse_number, parse_decimal
from app.repositories.monthly_bases import products_from_book


def is_duplicate(rows, data):
    return any(date_key(r[2]) == date_key(data["fecha"]) and normalize(r[3]) == normalize(data["puntoVenta"])
               and normalize(r[4]) == normalize(data["categoria"]) for r in rows)


def validate_payload(data):
    if not isinstance(data, dict) or any(not isinstance(data.get(k), str) or not data[k].strip() for k in ("puntoVenta", "fecha", "categoria")):
        raise DomainError("Debe seleccionar el PDV, la fecha y la categoría.")
    valid_date(data["fecha"])
    counts = data.get("conteos")
    if not isinstance(counts, list) or not counts:
        raise DomainError("No se recibieron productos.")
    for row in counts:
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) for k in ("item", "producto", "udm")):
            raise DomainError("Los datos de los productos no son válidos.")
        if any(row.get(k) is None or row[k] == "" or (isinstance(row[k], str) and not row[k].strip()) for k in ("cerrado", "abierto")):
            raise DomainError("Debe completar Cerrado y Abierto en todos los productos. Revise el ítem " + row["item"] + ".")
        for key, label in (("cerrado", "cerrada"), ("abierto", "abierta")):
            value = row[key]
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise DomainError(f"La cantidad {label} del ítem {row['item']} no es válida.")
            number = parse_number(value)
            if not math.isfinite(number) or number < 0:
                raise DomainError(f"La cantidad {label} del ítem {row['item']} no es válida. Use punto para decimales y coma para miles (ejemplo: 1,234.5), sin cantidades negativas.")
        total = sum(parse_number(row[k]) for k in ("cerrado", "abierto"))
        if not math.isfinite(total):
            raise DomainError(f"La cantidad total del ítem {row['item']} no es válida.")


def validate_integrity(counts, expected):
    if len(counts) != len(expected):
        raise DomainError("No se guardó el inventario porque la cantidad de productos recibida no coincide con la categoría. Actualice la página y vuelva a intentarlo.")
    if Counter(product_key(p) for p in counts) != Counter(product_key(p) for p in expected):
        raise DomainError("No se guardó el inventario porque falta un producto o se recibió uno diferente. Actualice la página y vuelva a intentarlo.")


class MonthlyInventoryService:
    def __init__(self, bases, inventory, locks, timezone="America/Bogota", now=None):
        self.bases, self.inventory, self.locks = bases, inventory, locks
        self.now = now or (lambda: datetime.now(ZoneInfo(timezone)))

    def points(self):
        return self.bases.points()

    def products(self, pdv, category=None):
        return self.bases.products(pdv, category)

    def categories(self, pdv):
        return sorted({p["categoria"] for p in self.products(pdv) if p["categoria"]}, key=spanish_key)

    def states(self, pdv, date):
        pdv, date = clean(pdv), valid_date(date)
        products = self.products(pdv)
        categories, normalized = {}, {}
        for product in products:
            name = product["categoria"]
            if name not in categories:
                categories[name] = dict(categoria=name, totalProductos=0, guardada=False)
                normalized[normalize(name)] = categories[name]
            categories[name]["totalProductos"] += 1
        rows = self.inventory.counts(self.inventory.read_view(self.bases.resolve(pdv)))
        for row in rows:
            category = normalized.get(normalize(row[4]))
            if date_key(row[2]) == date and normalize(row[3]) == normalize(pdv) and category is not None:
                category["guardada"] = True
        return sorted(categories.values(), key=lambda c: spanish_key(c["categoria"]))

    def finalize(self, data):
        validate_payload(data)
        spreadsheet_id = self.bases.resolve(data["puntoVenta"])
        with self.locks.hold(spreadsheet_id):
            # One fresh read supplies BOTH catalog integrity and duplicate decision.
            book = self.inventory.snapshot(spreadsheet_id)
            expected = [p for p in products_from_book(book, data["puntoVenta"]) if normalize(p["categoria"]) == normalize(data["categoria"])]
            validate_integrity(data["conteos"], expected)
            if is_duplicate(self.inventory.counts(book), data):
                raise DuplicateInventory(f'La categoría "{data["categoria"]}" ya fue guardada para {data["puntoVenta"]} en esta fecha.')
            record_id, timestamp = str(uuid4()), self.now()
            rows = []
            for row in data["conteos"]:
                closed, opened = [parse_decimal(row[k]) for k in ("cerrado", "abierto")]
                rows.append([record_id, timestamp, data["fecha"], data["puntoVenta"], data["categoria"],
                             row["item"], row["producto"], row["udm"], float(closed), float(opened), float(closed + opened)])
            self.inventory.append(spreadsheet_id, book, rows)
        return dict(correcto=True, mensaje="Inventario mensual guardado correctamente.", registros=len(rows))
