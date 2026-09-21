"""Per-spreadsheet locks shared by web/CLI processes on the same host."""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from threading import RLock
from time import monotonic
from filelock import FileLock, Timeout
from app.models.errors import GoogleUnavailable


class SpreadsheetLocks:
    def __init__(self, directory, timeout=30):
        self.directory = Path(directory)
        self.timeout = timeout
        self._guard = RLock()
        self.max_wait = 0.0

    @contextmanager
    def hold(self, spreadsheet_id):
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / (sha256(spreadsheet_id.encode()).hexdigest() + ".lock")
        started = monotonic()
        lock = FileLock(str(path), timeout=self.timeout)
        try:
            lock.acquire()
        except Timeout:
            raise GoogleUnavailable("Hay otro proceso guardando este PDV. Intente nuevamente.") from None
        try:
            with self._guard:
                self.max_wait = max(self.max_wait, monotonic() - started)
            yield
        finally:
            lock.release()
