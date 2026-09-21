import _bootstrap
from _cli import container, execute, parser


def main():
    cli = parser("Preparar bases mensuales: requiere --execute --confirm para convertir en Google.")
    cli.add_argument("--execute", action="store_true")
    cli.add_argument("--confirm", action="store_true")
    cli.add_argument("--limit", type=int, default=5)
    args = cli.parse_args()
    if args.limit < 1:
        cli.error("--limit debe ser positivo.")
    if not args.execute:
        print("Simulación: no se convirtió ningún archivo. Use --execute --confirm para autorizar la preparación.")
        return 0
    if not args.confirm:
        cli.error("--execute requiere --confirm.")
    return execute(lambda: container(writes=True).preparation.run(args.limit))


if __name__ == "__main__":
    raise SystemExit(main())
