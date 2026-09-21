from app.constants import COUNTS_HEADERS, COUNTS_SHEET
from app.models.sheets import find_sheet, row_data
from app.models.errors import DomainError


class MonthlyInventoryRepository:
    def __init__(self, sheets, cache=None):
        self.sheets, self.cache = sheets, cache

    def snapshot(self, spreadsheet_id):
        return self.sheets.read_book(spreadsheet_id)

    def read_view(self, spreadsheet_id):
        # Coalesce overlapping screen reads only; TTL zero means no stored counts.
        if self.cache:
            return self.cache.get(("counts-view", spreadsheet_id), 0, lambda: self.snapshot(spreadsheet_id))
        return self.snapshot(spreadsheet_id)

    @staticmethod
    def counts(book, *, display=False):
        sheet = find_sheet(book, COUNTS_SHEET, exact=True)
        if not sheet:
            return []
        return [list(row[:11]) + [""] * max(0, 11 - len(row)) for row in sheet["display" if display else "values"][1:]]

    def append(self, spreadsheet_id, book, rows):
        sheet = find_sheet(book, COUNTS_SHEET, exact=True)
        requests = []
        if sheet is None:
            sheet_id = max((s["id"] for s in book), default=-1) + 1
            sheet = dict(id=sheet_id, values=[], rows=max(1000, len(rows) + 1), columns=11)
            requests.append({"addSheet": {"properties": {"sheetId": sheet_id, "title": COUNTS_SHEET,
                            "gridProperties": {"rowCount": sheet["rows"], "columnCount": 11, "frozenRowCount": 1}}}})
        start = len(sheet["values"])
        if start and sheet["values"][0][:11] != COUNTS_HEADERS:
            raise DomainError("Los encabezados de Conteos Mensuales no coinciden con el formato esperado.")
        required_rows = start + len(rows) + (1 if not start else 0)
        if required_rows > sheet["rows"]:
            requests.append({"appendDimension": {"sheetId": sheet["id"], "dimension": "ROWS", "length": required_rows - sheet["rows"]}})
        if sheet["columns"] < 11:
            requests.append({"appendDimension": {"sheetId": sheet["id"], "dimension": "COLUMNS", "length": 11 - sheet["columns"]}})
        if not start:
            rows = [COUNTS_HEADERS] + rows
            requests.append({"repeatCell": {
                "range": {"sheetId": sheet["id"], "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 11},
                "cell": {"userEnteredFormat": {"backgroundColor": {"red": 74/255, "green": 43/255, "blue": 20/255},
                         "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}}},
                "fields": "userEnteredFormat",
            }})
            requests.append({"updateSheetProperties": {"properties": {"sheetId": sheet["id"], "gridProperties": {"frozenRowCount": 1}},
                                                       "fields": "gridProperties.frozenRowCount"}})
        requests.append({"updateCells": {"start": {"sheetId": sheet["id"], "rowIndex": start, "columnIndex": 0},
                         "rows": row_data(rows), "fields": "userEnteredValue,userEnteredFormat.numberFormat"}})
        self.sheets.batch_update(spreadsheet_id, requests)

    def replace_counts(self, spreadsheet_id, sheet, rows):
        # One atomic update sets retained rows and clears the remainder of A:K.
        self.sheets.batch_update(spreadsheet_id, [{"updateCells": {
            "range": {"sheetId": sheet["id"], "startRowIndex": 1, "endRowIndex": len(sheet["values"]),
                      "startColumnIndex": 0, "endColumnIndex": 11},
            "rows": row_data(rows), "fields": "userEnteredValue,userEnteredFormat.numberFormat",
        }}])
