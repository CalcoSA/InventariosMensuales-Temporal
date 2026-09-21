from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.models.text import normalize


def decode_book(payload, timezone="America/Bogota"):
    """Preserve display values for catalogs and typed dates/numbers for counts."""
    zone = ZoneInfo(payload.get("properties", {}).get("timeZone", timezone))
    sheets = []
    for sheet in payload.get("sheets", []):
        props = sheet["properties"]
        cells = {}
        last_row = last_col = 0
        for block in sheet.get("data", []):
            start_row, start_col = block.get("startRow", 0), block.get("startColumn", 0)
            for r, row in enumerate(block.get("rowData", []), start_row):
                for c, value in enumerate(row.get("values", []), start_col):
                    if "effectiveValue" not in value and not value.get("formattedValue") and "userEnteredValue" not in value:
                        continue
                    cells[r, c] = value
                    last_row, last_col = max(last_row, r + 1), max(last_col, c + 1)
        display = [[""] * last_col for _ in range(last_row)]
        typed = [[""] * last_col for _ in range(last_row)]
        for (r, c), value in cells.items():
            effective = value.get("effectiveValue", {})
            raw = effective.get("stringValue", effective.get("numberValue", effective.get("boolValue", "")))
            if isinstance(raw, (int, float)) and not isinstance(raw, bool) and value.get("effectiveFormat", {}).get("numberFormat", {}).get("type") in {"DATE", "DATE_TIME"}:
                raw = (datetime(1899, 12, 30) + timedelta(days=raw)).replace(tzinfo=zone)
            display[r][c] = value.get("formattedValue", str(raw) if raw != "" else "")
            typed[r][c] = raw
        merged = []
        for area in sheet.get("merges", []):
            r, c = area.get("startRowIndex", 0), area.get("startColumnIndex", 0)
            merged.append(dict(
                texto=display[r][c] if r < last_row and c < last_col else "",
                fila=r + 1, columnaInicio=c + 1, columnaFin=area["endColumnIndex"],
            ))
        sheets.append(dict(id=props["sheetId"], name=props["title"], display=display, values=typed,
                           merged=merged, rows=props.get("gridProperties", {}).get("rowCount", 1000),
                           columns=props.get("gridProperties", {}).get("columnCount", 26)))
    return sheets


def find_sheet(sheets, name, exact=False):
    return next((s for s in sheets if (s["name"] == name if exact else normalize(s["name"]) == normalize(name))), None)


def cell_data(value):
    if isinstance(value, datetime):
        naive = value.replace(tzinfo=None)
        serial = (naive - datetime(1899, 12, 30)).total_seconds() / 86400
        return {"userEnteredValue": {"numberValue": serial},
                "userEnteredFormat": {"numberFormat": {"type": "DATE_TIME", "pattern": "dd/MM/yyyy HH:mm:ss"}}}
    if isinstance(value, bool):
        return {"userEnteredValue": {"boolValue": value}}
    if isinstance(value, (int, float)):
        return {"userEnteredValue": {"numberValue": value}}
    # Literal strings, including leading zeros and strings beginning with "=".
    return {"userEnteredValue": {"stringValue": "" if value is None else str(value)}}


def row_data(rows):
    return [{"values": [cell_data(value) for value in row]} for row in rows]
