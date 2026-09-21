from app.constants import ADMIN_EMAIL
from app.models.errors import AccessDenied

# Temporary additional administrator while the original account regains intranet access.
ADMIN_EMAILS = frozenset({ADMIN_EMAIL, "juan.zapata@crepesywaffles.com"})


class IdentityService:
    """Production injects a verified identity provider; browser input is never identity."""
    def __init__(self, provider=None):
        self.provider = provider or (lambda: None)

    def email(self):
        value = self.provider()
        return value.strip().lower() if isinstance(value, str) else ""

    def is_admin(self):
        return self.email() in ADMIN_EMAILS

    def require_admin(self):
        if not self.is_admin():
            raise AccessDenied(
                "No tiene autorización para acceder a la administración ni descargar archivos."
            )
