import _bootstrap
from _cli import container, execute, output, parser


def main():
    cli = parser("Generador Inventario Mensual. Sin --execute --confirm solo consulta el estado local.")
    cli.add_argument("--execute", action="store_true")
    cli.add_argument("--confirm", action="store_true", help="Confirma creación de archivos reales en Google.")
    cli.add_argument("--limit", type=int, help="Máximo de PDV en esta ejecución; continuar repitiendo el comando.")
    cli.add_argument("--reset-state", action="store_true", help="Borra solo el estado local; no borra resultados de Drive.")
    args = cli.parse_args()
    if args.execute and not args.confirm:
        cli.error("--execute requiere --confirm.")
    if args.limit is not None and args.limit < 1:
        cli.error("--limit debe ser positivo.")
    service = container(writes=args.execute and args.confirm).generator
    if args.reset_state:
        if not args.confirm:
            cli.error("--reset-state requiere --confirm.")
        service.reset()
    return execute(lambda: service.run(limit=args.limit, progress=lambda s: output(
        {"estado": s["ESTADO"], "avance": s["INDICE"], "total": s["TOTAL"]})) if args.execute else service.status())


if __name__ == "__main__":
    raise SystemExit(main())
