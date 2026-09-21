"""Names and defaults copied from the two original Apps Script projects."""
MONTHLY_FOLDER_ID = "1DwPotMtT1Y-V4qIuob3TXmWjfAc2tbWm"
FORMATS_FOLDER_ID = "1nzHsP8GAnkWDMWpMJpQPI4pLP0k6DUjk"
BASES_FOLDER_NAME = "Bases Google - Inventarios Mensuales"
SHEET_MIME = "application/vnd.google-apps.spreadsheet"
FOLDER_MIME = "application/vnd.google-apps.folder"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
COUNTS_SHEET = "Conteos Mensuales"
COUNTS_HEADERS = [
    "ID Registro", "Fecha y hora", "Fecha inventario", "Punto de venta",
    "Categoría", "Item", "Nombre Producto", "Desc. U.M.", "Cerrado", "Abierto", "Total",
]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CACHE_PDV_SECONDS = 600
CACHE_FILE_SECONDS = 21600
CACHE_PRODUCTS_SECONDS = 600
RETENTION_DAYS = 5
CLEANUP_HOUR = 2
