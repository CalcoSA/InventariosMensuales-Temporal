import os
from pathlib import Path
from dotenv import load_dotenv
from .constants import MONTHLY_FOLDER_ID, FORMATS_FOLDER_ID

ROOT = Path(__file__).resolve().parent.parent


def settings():
    load_dotenv(ROOT / ".env")
    app_env = os.getenv("APP_ENV", "development")
    trusted_hosts = ["127.0.0.1", "localhost"]
    for value in os.getenv("TRUSTED_HOSTS", "").split(","):
        host = value.strip()
        # A leading dot also matches every subdomain in Werkzeug.
        if "*" in host or host.startswith("."):
            raise ValueError("TRUSTED_HOSTS solo admite hosts exactos, sin comodines.")
        if host and host not in trusted_hosts:
            trusted_hosts.append(host)
    return {
        "APP_ENV": app_env,
        # Validated strictly by session_auth_service, including production guards.
        "AUTH_ENABLED": os.getenv("AUTH_ENABLED", "false"),
        "SSO_ISSUER": os.getenv("SSO_ISSUER", "calco-intranet"),
        "SSO_AUDIENCE": os.getenv("SSO_AUDIENCE", "inventarios-mensuales"),
        "SSO_PUBLIC_KEY_PATH": os.getenv("SSO_PUBLIC_KEY_PATH", ""),
        "SSO_TOKEN_MAX_AGE_SECONDS": os.getenv("SSO_TOKEN_MAX_AGE_SECONDS", "60"),
        "SSO_CLOCK_SKEW_SECONDS": os.getenv("SSO_CLOCK_SKEW_SECONDS", "10"),
        "SESSION_JWT_SECRET": os.getenv("SESSION_JWT_SECRET", ""),
        "SESSION_JWT_ISSUER": os.getenv("SESSION_JWT_ISSUER", "inventarios-mensuales"),
        "SESSION_JWT_AUDIENCE": os.getenv("SESSION_JWT_AUDIENCE", "inventarios-mensuales-session"),
        "SESSION_JWT_COOKIE_NAME": os.getenv("SESSION_JWT_COOKIE_NAME", "inventario_mensual_session"),
        "SESSION_IDLE_TIMEOUT_SECONDS": os.getenv("SESSION_IDLE_TIMEOUT_SECONDS", "1200"),
        "SESSION_COOKIE_SECURE": os.getenv("SESSION_COOKIE_SECURE", "true" if app_env == "production" else "false"),
        "INTRANET_URL": os.getenv("INTRANET_URL", ""),
        "MONTHLY_FOLDER_ID": os.getenv("MONTHLY_FOLDER_ID", MONTHLY_FOLDER_ID),
        "FORMATS_FOLDER_ID": os.getenv("FORMATS_FOLDER_ID", FORMATS_FOLDER_ID),
        "GOOGLE_CLIENT_FILE": ROOT / "credentials" / "credentials.json",
        "GOOGLE_TOKEN_FILE": ROOT / "credentials" / "token.json",
        "RUNTIME_DIR": ROOT / ".runtime",
        "TIMEZONE": os.getenv("APP_TIMEZONE", "America/Bogota"),
        # Deliberate local-development guard. Enabling is an operator action.
        "GOOGLE_WRITES_ENABLED": os.getenv("GOOGLE_WRITES_ENABLED", "false").lower() == "true",
        "MAX_CONTENT_LENGTH": 4 * 1024 * 1024,
        "TRUSTED_HOSTS": trusted_hosts,
    }
