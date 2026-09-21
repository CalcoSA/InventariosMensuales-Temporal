import os
from pathlib import Path
from dotenv import load_dotenv
from .constants import MONTHLY_FOLDER_ID, FORMATS_FOLDER_ID

ROOT = Path(__file__).resolve().parent.parent


def settings():
    load_dotenv(ROOT / ".env")
    return {
        "MONTHLY_FOLDER_ID": os.getenv("MONTHLY_FOLDER_ID", MONTHLY_FOLDER_ID),
        "FORMATS_FOLDER_ID": os.getenv("FORMATS_FOLDER_ID", FORMATS_FOLDER_ID),
        "GOOGLE_CLIENT_FILE": ROOT / "credentials" / "credentials.json",
        "GOOGLE_TOKEN_FILE": ROOT / "credentials" / "token.json",
        "RUNTIME_DIR": ROOT / ".runtime",
        "TIMEZONE": os.getenv("APP_TIMEZONE", "America/Bogota"),
        # Deliberate local-development guard. Enabling is an operator action.
        "GOOGLE_WRITES_ENABLED": os.getenv("GOOGLE_WRITES_ENABLED", "false").lower() == "true",
        "MAX_CONTENT_LENGTH": 4 * 1024 * 1024,
        "TRUSTED_HOSTS": ["127.0.0.1", "localhost"],
    }
