from copy import copy
from pathlib import Path
from threading import RLock
import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from app.constants import SCOPES
from app.models.errors import ConfigurationError


class GoogleAuthService:
    def __init__(self, client_file, token_file):
        self.client_file, self.token_file = Path(client_file), Path(token_file)
        self._lock = RLock()
        self._credentials = None

    def authorize(self):
        """Explicit CLI OAuth only; never start a browser from a web request."""
        if not self.client_file.is_file():
            raise ConfigurationError("Falta el cliente OAuth en credentials/credentials.json.")
        try:
            flow = InstalledAppFlow.from_client_secrets_file(str(self.client_file), SCOPES)
            credentials = flow.run_local_server(
                port=0, timeout_seconds=180,
                authorization_prompt_message="Autorice la cuenta corporativa en el navegador.",
                success_message="Autorización completada. Puede cerrar esta ventana.",
            )
        except Exception:
            raise ConfigurationError("No se pudo completar la autorización OAuth.") from None
        with self._lock:
            self._credentials = credentials
            self._save(credentials)

    def _save(self, credentials):
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.token_file.with_suffix(".json.tmp")
        temporary.write_text(credentials.to_json(), encoding="utf-8")
        temporary.replace(self.token_file)

    def credentials(self):
        with self._lock:
            try:
                if self._credentials is None:
                    if not self.token_file.is_file():
                        raise ConfigurationError(
                            "Falta autorizar Google. Ejecute scripts/verify_google_access.py --authorize."
                        )
                    self._credentials = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
                if not self._credentials.valid:
                    if not self._credentials.refresh_token:
                        raise ConfigurationError("La autorización Google debe renovarse.")
                    self._credentials.refresh(Request())
                    self._save(self._credentials)
                if not self._credentials.has_scopes(SCOPES):
                    raise ConfigurationError("Autorice los permisos de Sheets y Drive requeridos.")
                return copy(self._credentials)
            except ConfigurationError:
                raise
            except Exception:
                raise ConfigurationError("No fue posible renovar la autorización Google.") from None

    def client(self, api, version):
        # Each operation gets its own httplib2 transport. Credentials refresh is serialized.
        http = AuthorizedHttp(self.credentials(), http=httplib2.Http(timeout=60))
        return build(api, version, http=http, cache_discovery=False, static_discovery=True)
