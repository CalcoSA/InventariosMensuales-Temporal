"""Real Google verification. Only Drive list/get and Sheets get; no mutation methods."""
import _bootstrap
from _cli import container, execute, parser
from app.constants import FOLDER_MIME
from app.models.errors import DomainError
from app.models.sheets import find_sheet
from app.repositories.monthly_bases import products_from_book


def verify(c):
    c.auth.credentials()
    for folder_id in (c.generator.monthly_folder, c.generator.formats_folder):
        if c.drive.metadata(folder_id)["mimeType"] != FOLDER_MIME:
            raise DomainError("Una referencia de carpeta no corresponde a una carpeta Google.")
    folder = c.bases.folder()
    points = c.inventory.points()
    if not points:
        raise DomainError("No se encontraron bases mensuales.")
    book = c.sheets.read_book(c.bases.resolve(points[0]))
    products = products_from_book(book, points[0])
    return dict(correcto=True, soloLectura=True, autenticacion=True, carpetasAccesibles=True,
                carpetaBases=folder, puntosVenta=points, pdvPrueba=points[0],
                hojaMensual=bool(find_sheet(book, "Mensual")),
                categorias=sorted({p["categoria"] for p in products}), productos=len(products),
                llamadasGoogle=c.executor.calls)


def main():
    cli = parser("Verifica acceso Google solo en lectura.")
    cli.add_argument("--authorize", action="store_true", help="Inicia OAuth interactivo y guarda el token propio local.")
    args = cli.parse_args()
    c = container(writes=False)
    def action():
        if args.authorize:
            c.auth.authorize()
        return verify(c)
    return execute(action)


if __name__ == "__main__":
    raise SystemExit(main())
