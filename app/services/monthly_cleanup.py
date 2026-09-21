from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.constants import COUNTS_SHEET, RETENTION_DAYS
from app.models.errors import DomainError
from app.models.sheets import find_sheet


def partition_counts(rows, cutoff):
    kept, removed = [], 0
    for row in rows:
        timestamp = row[1]
        if isinstance(timestamp, datetime) and timestamp.tzinfo is not None and timestamp < cutoff:
            removed += 1
        else:
            kept.append(row)
    return kept, removed


class MonthlyCleanupService:
    def __init__(self, bases, inventory, locks, timezone="America/Bogota", now=None):
        self.bases, self.inventory, self.locks = bases, inventory, locks
        self.now = now or (lambda: datetime.now(ZoneInfo(timezone)))

    def run(self, dry_run=True):
        cutoff = self.now() - timedelta(days=RETENTION_DAYS)
        result = dict(correcto=True, puntosRevisados=0, puntosLimpiados=0, registrosEliminados=0,
                      antiguedadDias=RETENTION_DAYS, errores=[], simulacion=dry_run)
        for file in self.bases.files(fresh=True):
            result["puntosRevisados"] += 1
            try:
                with self.locks.hold(file["id"]):
                    book = self.inventory.snapshot(file["id"])
                    kept, removed = partition_counts(self.inventory.counts(book), cutoff)
                    if not removed:
                        continue
                    if not dry_run:
                        self.inventory.replace_counts(file["id"], find_sheet(book, COUNTS_SHEET, exact=True), kept)
                    result["puntosLimpiados"] += 1
                    result["registrosEliminados"] += removed
            except DomainError as error:
                result["errores"].append(file["name"] + ": " + str(error))
        result["correcto"] = not result["errores"]
        return result
