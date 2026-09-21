import _bootstrap
from _cli import container, execute, parser


def main():
    cli = parser("Limpieza de conteos: simulación de solo lectura por defecto.")
    mode = cli.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    cli.add_argument("--confirm", action="store_true", help="Confirma eliminación real de conteos vencidos.")
    args = cli.parse_args()
    if args.execute and not args.confirm:
        cli.error("--execute requiere --confirm.")
    return execute(lambda: container(writes=args.execute).cleanup.run(dry_run=not args.execute))


if __name__ == "__main__":
    raise SystemExit(main())
