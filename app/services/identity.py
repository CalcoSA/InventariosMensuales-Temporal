from app.constants import ADMIN_EMAIL
from app.models.errors import AccessDenied


class IdentityService:
    """Production injects a verified identity provider; browser input is never identity."""
    def __init__(self, provider=None):
        self.provider = provider or (lambda: None)

    def email(self):
        value = self.provider()
        return value.strip().lower() if isinstance(value, str) else ""

    def is_admin(self):
        return self.email() == ADMIN_EMAIL

    def require_admin(self):
        if not self.is_admin():
            raise AccessDenied(
                "No tiene autorización para acceder a la administración ni descargar archivos."
            )
