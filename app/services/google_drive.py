from io import BytesIO
from googleapiclient.http import MediaIoBaseUpload
from app.constants import FOLDER_MIME, SHEET_MIME, XLSX_MIME
from app.models.errors import ConfigurationError


def quote_query(value):
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


class GoogleDriveService:
    def __init__(self, auth, executor, writes=False):
        self.auth, self.executor, self.writes = auth, executor, writes

    def allow_write(self):
        if not self.writes:
            raise ConfigurationError("Las escrituras reales a Google están deshabilitadas.")

    def _call(self, builder, *, idempotent=True):
        # Credential failures retain their useful, secret-free message.
        client = self.auth.client("drive", "v3")
        try:
            return self.executor.execute(
                lambda: builder(client.files()).execute(num_retries=0), idempotent=idempotent)
        finally:
            client.close()

    def list(self, parent, *, name=None, mime=None):
        query = f"'{quote_query(parent)}' in parents and trashed = false"
        if name is not None:
            query += f" and name = '{quote_query(name)}'"
        if mime:
            query += f" and mimeType = '{quote_query(mime)}'"
        result, token = [], None
        while True:
            page = self._call(lambda files: files.list(
                q=query, pageSize=1000, pageToken=token, supportsAllDrives=True,
                includeItemsFromAllDrives=True, fields="nextPageToken,files(id,name,mimeType,modifiedTime,webViewLink)",
            ))
            result.extend(page.get("files", []))
            token = page.get("nextPageToken")
            if not token:
                return result

    def metadata(self, file_id):
        return self._call(lambda files: files.get(fileId=file_id, fields="id,name,mimeType,webViewLink", supportsAllDrives=True))

    def download(self, file_id):
        return self._call(lambda files: files.get_media(fileId=file_id, supportsAllDrives=True))

    def create_folder(self, parent, name):
        self.allow_write()
        return self._call(lambda files: files.create(
            body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent]},
            fields="id,name,webViewLink", supportsAllDrives=True), idempotent=False)

    def upload(self, parent, name, content, mime, *, convert=False, file_id=None):
        self.allow_write()
        body = {"name": name, "mimeType": SHEET_MIME if convert else mime}
        media = MediaIoBaseUpload(BytesIO(content), mimetype=mime, resumable=False)
        if file_id:
            return self._call(lambda files: files.update(fileId=file_id, body=body, media_body=media,
                              fields="id,name,webViewLink", supportsAllDrives=True), idempotent=False)
        if parent:
            body["parents"] = [parent]
        return self._call(lambda files: files.create(body=body, media_body=media,
                          fields="id,name,webViewLink", supportsAllDrives=True), idempotent=False)

    def trash(self, file_id):
        self.allow_write()
        return self._call(lambda files: files.update(fileId=file_id, body={"trashed": True}, fields="id", supportsAllDrives=True))
