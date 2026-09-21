"""In-memory Google surfaces. Business logic and repositories remain real."""
from copy import deepcopy
from datetime import datetime, timedelta
from io import BytesIO
from threading import Lock
import time
from app.constants import BASES_FOLDER_NAME, COUNTS_HEADERS, FOLDER_MIME, SHEET_MIME

ADMIN_LOGIN = "admin.pruebas"
SECOND_ADMIN_LOGIN = "supervisor.pruebas"
TEST_ADMIN_LOGINS = ADMIN_LOGIN + "," + SECOND_ADMIN_LOGIN


def sheet(name, rows, sheet_id=0, merged=None):
    width = max(map(len, rows), default=0)
    rows = [list(r) + [""] * (width - len(r)) for r in rows]
    def display(value):
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y %H:%M:%S")
        if isinstance(value, float) and value == int(value):
            return str(int(value))
        return str(value)
    return dict(id=sheet_id, name=name, values=deepcopy(rows), display=[[display(v) for v in r] for r in rows],
                rows=1000, columns=26, merged=merged or [])


class FakeDrive:
    def __init__(self, points=1, delay=0):
        self.delay, self.lock = delay, Lock()
        self.calls = self.writes = 0
        self.files = [
            dict(id="monthly", name="Mensuales", mimeType=FOLDER_MIME, parents=[]),
            dict(id="formats", name="Formatos", mimeType=FOLDER_MIME, parents=[]),
            dict(id="bases", name=BASES_FOLDER_NAME, mimeType=FOLDER_MIME, parents=["formats"]),
        ] + [dict(id=f"pdv-{i}", name=f"BR{i:02} - PDV {i}", mimeType=SHEET_MIME, parents=["bases"]) for i in range(points)]
        self.content = {}
        self.on_convert = None

    def _count(self, write=False):
        with self.lock:
            self.calls += 1
            self.writes += int(write)
        time.sleep(self.delay)

    def list(self, parent, *, name=None, mime=None):
        self._count()
        return deepcopy([f for f in self.files if parent in f.get("parents", []) and
                         (name is None or f["name"] == name) and (mime is None or f["mimeType"] == mime) and not f.get("trashed")])

    def metadata(self, file_id):
        self._count()
        return deepcopy(next(f for f in self.files if f["id"] == file_id))

    def create_folder(self, parent, name):
        self._count(True)
        result = dict(id="folder-" + str(len(self.files)), name=name, mimeType=FOLDER_MIME, parents=[parent])
        self.files.append(result)
        return deepcopy(result)

    def download(self, file_id):
        self._count()
        return self.content[file_id]

    def upload(self, parent, name, content, mime, *, convert=False, file_id=None):
        self._count(True)
        if file_id:
            result = next(f for f in self.files if f["id"] == file_id)
            result["name"] = name
        else:
            result = dict(id="file-" + str(len(self.files)), name=name, mimeType=SHEET_MIME if convert else mime, parents=[parent] if parent else [])
            self.files.append(result)
        self.content[result["id"]] = content
        if convert and self.on_convert:
            self.on_convert(result, content)
        return deepcopy(result)

    def trash(self, file_id):
        self._count(True)
        next(f for f in self.files if f["id"] == file_id)["trashed"] = True


class FakeSheets:
    def __init__(self, points=1, delay=0):
        self.delay, self.lock = delay, Lock()
        self.reads = self.writes = 0
        self.books = {f"pdv-{i}": [sheet("Mensual", [
            ["Categoría", "Item", "Nombre Producto", "Desc U M"],
            ["Bebidas", "000123", "Jugo X 750 ML", "X 750 ML"],
            ["Bebidas", "002345", "Café", "KG"],
            ["Cocina", "000456", "Queso", "KG"],
        ])] for i in range(points)}
        self.history = []
        self.fail_write = None

    def read_book(self, file_id):
        with self.lock:
            self.reads += 1
        time.sleep(self.delay)
        with self.lock:
            return deepcopy(self.books[file_id])

    def batch_update(self, file_id, requests):
        with self.lock:
            self.writes += 1
            if self.fail_write:
                raise self.fail_write
            self.history.append(deepcopy(requests))
            book = self.books[file_id]
            for request in requests:
                if "addSheet" in request:
                    props = request["addSheet"]["properties"]
                    book.append(sheet(props["title"], [], props["sheetId"]))
                elif "appendDimension" in request:
                    area = request["appendDimension"]
                    target = next(s for s in book if s["id"] == area["sheetId"])
                    target["rows" if area["dimension"] == "ROWS" else "columns"] += area["length"]
                elif "updateCells" in request:
                    update = request["updateCells"]
                    area = update.get("start", update.get("range"))
                    target = next(s for s in book if s["id"] == area["sheetId"])
                    start = area.get("rowIndex", area.get("startRowIndex", 0))
                    values = []
                    for row in update.get("rows", []):
                        values.append([])
                        for cell in row["values"]:
                            value = cell.get("userEnteredValue", {})
                            raw = value.get("stringValue", value.get("numberValue", value.get("boolValue", "")))
                            if cell.get("userEnteredFormat", {}).get("numberFormat", {}).get("type") == "DATE_TIME":
                                from zoneinfo import ZoneInfo
                                raw = (datetime(1899, 12, 30) + timedelta(days=raw)).replace(tzinfo=ZoneInfo("America/Bogota"))
                            values[-1].append(raw)
                    current = target["values"]
                    while len(current) < start:
                        current.append([""] * 11)
                    end = area.get("endRowIndex", start + len(values))
                    current[start:end] = values
                    target.update(sheet(target["name"], current, target["id"]))
        time.sleep(self.delay)
        return {}


def payload(pdv="BR00 - PDV 0", category="Bebidas", date="2026-09-18"):
    products = [dict(item="000123", producto="Jugo X 750 ML", udm="X 750 ML"),
                dict(item="002345", producto="Café", udm="KG")] if category == "Bebidas" else [
                dict(item="000456", producto="Queso", udm="KG")]
    return dict(puntoVenta=pdv, fecha=date, categoria=category,
                conteos=[dict(**p, cerrado="4", abierto="2.5") for p in products])
