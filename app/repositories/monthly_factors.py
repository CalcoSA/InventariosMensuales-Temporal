"""Factors for converted views and Siesa; never used when saving counts."""
from decimal import Decimal
import re

from app.models.errors import DomainError
from app.models.sheets import find_sheet
from app.models.text import clean, normalize


def reference_key(value):
    text = re.sub(r"\.0+$", "", clean(value))
    if not re.fullmatch(r"[0-9]{1,11}", text):
        raise DomainError(f"Referencia inválida en Base general: {clean(value) or '(vacía)'}.")
    return text.zfill(11)


def factor_value(value):
    # Sheets returns effective numeric values (including 2.5), without scaling.
    # Accept decimal text too, but not guessed thousands separators or units.
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+(?:[.,][0-9]+)?", clean(value)):
        return None
    number = Decimal(clean(value).replace(",", "."))
    return number if number.is_finite() and number > 0 else None


def factors_from_book(book):
    sheet = find_sheet(book, "Hoja 1")
    rows = sheet["values"] if sheet else []
    if not rows:
        raise DomainError("Base general no contiene datos en Hoja 1.")
    headers = [normalize(value) for value in rows[0]]
    required = ["referencia", "factor u.m."]
    if any(headers.count(name) != 1 for name in required):
        raise DomainError("Base general debe tener una columna Referencia y una columna Factor U.M. en Hoja 1.")
    item_col, factor_col = (headers.index(name) for name in required)
    factors, issues = {}, {}
    for line, row in enumerate(rows[1:], 2):
        if not any(clean(value) for value in row):
            continue
        try:
            key = reference_key(row[item_col] if item_col < len(row) else "")
        except DomainError as error:
            raise DomainError(f"{error} Revise la fila {line}.") from error
        value = factor_value(row[factor_col] if factor_col < len(row) else "")
        if value is None:
            issues[key] = "factor vacío o inválido (debe ser numérico y mayor que cero)"
        elif key in factors and factors[key] != value:
            issues[key] = "factores distintos para la misma referencia"
        else:
            factors[key] = value
    return factors, issues


class MonthlyFactorsRepository:
    def __init__(self, bases):
        self.bases = bases

    def read(self):
        files = [file for file in self.bases.all_files() if normalize(file["name"]) == "base general"]
        if len(files) != 1:
            raise DomainError("Debe existir un único archivo Base general en Bases Google - Inventarios Mensuales.")
        file_id = files[0]["id"]
        # No stale factors: share overlapping reads, refresh on the next export.
        return self.bases.cache.get(("siesa-factors", file_id), 0,
                                    lambda: factors_from_book(self.bases.sheets.read_book(file_id)))
