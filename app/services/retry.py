import random
import time
from threading import Lock
from app.models.errors import GoogleUnavailable, WriteUncertain

RETRY_STATUSES = {429, 500, 502, 503, 504}


class GoogleExecutor:
    def __init__(self, attempts=4, sleep=time.sleep, jitter=random.random):
        self.attempts, self.sleep, self.jitter = attempts, sleep, jitter
        self.calls = self.retries = self.rate_limits = 0
        self._lock = Lock()

    def execute(self, operation, *, idempotent=True):
        for attempt in range(self.attempts):
            with self._lock:
                self.calls += 1
            try:
                return operation()
            except Exception as error:
                status = getattr(getattr(error, "resp", None), "status", None)
                if status == 429:
                    with self._lock:
                        self.rate_limits += 1
                if idempotent and status in RETRY_STATUSES and attempt + 1 < self.attempts:
                    with self._lock:
                        self.retries += 1
                    self.sleep(2 ** attempt + self.jitter())
                    continue
                if not idempotent:
                    raise WriteUncertain(
                        "Google no confirmó el guardado. Su borrador se conserva. "
                        "Actualice el estado de la categoría antes de volver a finalizar."
                    ) from None
                if status == 429:
                    raise GoogleUnavailable(
                        "Google está recibiendo demasiadas solicitudes. Espere un momento e intente nuevamente."
                    ) from None
                raise GoogleUnavailable("No fue posible consultar Google. Intente nuevamente.") from None
