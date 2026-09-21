from contextlib import contextmanager
from datetime import datetime
from io import BytesIO
import logging
import re
import zipfile
from app.constants import SHEET_MIME, XLSX_MIME
from app.models.errors import DomainError
from app.models.text import spanish_key


class MonthlyGeneratorRepository:
    def __init__(self, drive, sheets):
        self.drive, self.sheets = drive, sheets

    def files(self, parent):
        files = []
        for file in self.drive.list(parent):
            if not re.search(r"\.(xlsx|xls|xlsm)$", file["name"], re.I) and file["mimeType"] != SHEET_MIME:
                continue
            modified = file.get("modifiedTime", "1970-01-01T00:00:00Z")
            files.append(dict(id=file["id"], nombre=file["name"], mimeType=file["mimeType"],
                              actualizado=int(datetime.fromisoformat(modified.replace("Z", "+00:00")).timestamp() * 1000)))
        return sorted(files, key=lambda f: spanish_key(f["nombre"]))

    @contextmanager
    def open_book(self, file):
        file_id, temporary = file["id"], file["mimeType"] != SHEET_MIME
        if temporary:
            result = self.drive.upload(None, "TEMPORAL_" + str(int(datetime.now().timestamp() * 1000)) + "_" + file["nombre"],
                                       self.drive.download(file_id), file["mimeType"], convert=True)
            file_id = result["id"]
        try:
            yield self.sheets.read_book(file_id)
        finally:
            if temporary:
                try:
                    self.drive.trash(file_id)
                except DomainError:
                    logging.getLogger(__name__).warning("No se pudo enviar a la papelera el temporal %s.", file_id)

    def write_xlsx(self, folder, name, content):
        # Resume uses the existing exact name, never creates a second output.
        existing = self.drive.list(folder, name=name)
        if len(existing) > 1:
            raise DomainError("Hay resultados duplicados con el nombre " + name + ". Revise la carpeta de salida.")
        if existing:
            return existing[0]
        return self.drive.upload(folder, name, content, XLSX_MIME)

    def zip_outputs(self, folder):
        files = [f for f in self.drive.list(folder) if re.search(r"\.xlsx$", f["name"], re.I)]
        if not files:
            raise DomainError("No se generaron archivos para incluir en el ZIP.")
        content = BytesIO()
        with zipfile.ZipFile(content, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in files:
                archive.writestr(file["name"], self.drive.download(file["id"]))
        name = "INVENTARIOS_PDV_GENERADOS.zip"
        existing = self.drive.list(folder, name=name)
        if len(existing) > 1:
            raise DomainError("Hay más de un ZIP de resultados. Revise la carpeta antes de continuar.")
        return self.drive.upload(folder, name, content.getvalue(), "application/zip",
                                 file_id=existing[0]["id"] if existing else None)
