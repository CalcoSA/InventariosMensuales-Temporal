from app.constants import BASES_FOLDER_NAME, FOLDER_MIME, SHEET_MIME, CACHE_PDV_SECONDS, CACHE_FILE_SECONDS, CACHE_PRODUCTS_SECONDS
from app.models.errors import DomainError
from app.models.sheets import find_sheet
from app.models.text import clean, normalize, spanish_key

COLUMN_OPTIONS = [
    ["categoria"], ["item", "codigo", "cod", "id producto"],
    ["nombre producto", "producto", "descripcion", "desc item"],
    ["desc u m", "desc um", "descripcion unidad de medida", "udm", "unidad de medida", "unidad", "um empaque"],
]


def find_index(headers, options):
    options = [normalize(o) for o in options]
    return next((i for i, header in enumerate(headers) if header in options), -1)


def products_from_book(book, pdv):
    sheet = find_sheet(book, "Mensual")
    if not sheet:
        raise DomainError(f"No se encontró la hoja Mensual para {pdv}.")
    rows = sheet["display"]
    if len(rows) < 2 or max(map(len, rows), default=0) < 3:
        return []
    headers = [normalize(value) for value in rows[0]]
    columns = [find_index(headers, options) for options in COLUMN_OPTIONS]
    columns = [i if c == -1 else c for i, c in enumerate(columns)]
    result = []
    for index, row in enumerate(rows[1:], 1):
        product = dict(id=index)
        for name, col in zip(("categoria", "item", "producto", "udm"), columns):
            product[name] = clean(row[col] if col < len(row) else "")
        if product["categoria"] and product["item"] and product["producto"] and normalize(product["producto"]) != "no tiene":
            result.append(product)
    return result


class MonthlyBasesRepository:
    def __init__(self, drive, sheets, cache, formats_folder):
        self.drive, self.sheets, self.cache, self.formats_folder = drive, sheets, cache, formats_folder

    def folder(self):
        def load():
            folders = self.drive.list(self.formats_folder, name=BASES_FOLDER_NAME, mime=FOLDER_MIME)
            if not folders:
                raise DomainError("No se encontró la carpeta Bases Google - Inventarios Mensuales. Ejecute la preparación administrativa.")
            return folders[0]["id"]
        return self.cache.get(("bases-folder",), CACHE_FILE_SECONDS, load)

    def files(self, *, fresh=False):
        loader = lambda: self.drive.list(self.folder(), mime=SHEET_MIME)
        return loader() if fresh else self.cache.get(("pdv-files",), CACHE_PDV_SECONDS, loader)

    def points(self):
        return sorted({f["name"].strip() for f in self.files()}, key=spanish_key)

    def resolve(self, pdv):
        if not isinstance(pdv, str) or not pdv.strip():
            raise DomainError("Seleccione un punto de venta.")
        def load():
            # Name match is deliberately exact as in getFilesByName.
            files = self.drive.list(self.folder(), name=pdv, mime=SHEET_MIME)
            if not files:
                raise DomainError(f"No se encontró la base mensual de {pdv}.")
            return files[0]["id"]
        return self.cache.get(("file", pdv), CACHE_FILE_SECONDS, load)

    def products(self, pdv, category=None):
        file_id = self.resolve(pdv)
        products = self.cache.get(("products", file_id), CACHE_PRODUCTS_SECONDS,
                                  lambda: products_from_book(self.sheets.read_book(file_id), pdv))
        return [p for p in products if not normalize(category) or normalize(p["categoria"]) == normalize(category)]
