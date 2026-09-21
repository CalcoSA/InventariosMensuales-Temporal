from app.models.errors import AccessDenied


class IdentityService:
    """Production injects a verified identity provider; browser input is never identity."""
    def __init__(self, provider=None, *, admin_logins=""):
        self.provider = provider or (lambda: None)
        if not isinstance(admin_logins, str):
            raise ValueError("ADMIN_USER_LOGINS debe ser una lista de usuarios separados por comas.")
        self.admin_logins = frozenset(login.strip().lower() for login in admin_logins.split(",") if login.strip())
        if any("*" in login or len(login) > 256 or any(ord(c) < 32 or ord(c) == 127 for c in login)
               for login in self.admin_logins):
            raise ValueError("ADMIN_USER_LOGINS requiere usuarios exactos, sin comodines ni caracteres de control.")

    def username(self):
        value = self.provider()
        return value.strip().lower() if isinstance(value, str) else ""

    def is_admin(self):
        return self.username() in self.admin_logins

    def require_admin(self):
        if not self.is_admin():
            raise AccessDenied(
                "No tiene autorización para acceder a la administración ni descargar archivos."
            )
