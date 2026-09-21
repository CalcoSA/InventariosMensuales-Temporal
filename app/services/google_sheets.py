from app.models.errors import ConfigurationError
from app.models.sheets import decode_book


class GoogleSheetsService:
    def __init__(self, auth, executor, writes=False, timezone="America/Bogota"):
        self.auth, self.executor, self.writes, self.timezone = auth, executor, writes, timezone

    def read_book(self, spreadsheet_id):
        client = self.auth.client("sheets", "v4")
        try:
            payload = self.executor.execute(lambda: client.spreadsheets().get(
                spreadsheetId=spreadsheet_id, includeGridData=True,
                fields="properties(timeZone),sheets(properties,merges,data(startRow,startColumn,rowData(values(formattedValue,effectiveValue,userEnteredValue,effectiveFormat(numberFormat)))))",
            ).execute(num_retries=0))
            return decode_book(payload, self.timezone)
        finally:
            client.close()

    def batch_update(self, spreadsheet_id, requests):
        if not self.writes:
            raise ConfigurationError("Las escrituras reales a Google están deshabilitadas.")
        client = self.auth.client("sheets", "v4")
        try:
            return self.executor.execute(lambda: client.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body={"requests": requests},
            ).execute(num_retries=0), idempotent=False)
        finally:
            client.close()
