"""Application configuration.

Everything here is driven by environment variables so the same code runs in
dev (SQLite) and production (Postgres) without changes. No token-based auth is
used anywhere; sessions are signed server-side cookies backed by SECRET_KEY.
"""
import os
os.environ["POSTGRES_USER"] = "postgres"
os.environ["POSTGRES_PASSWORD"] = "123456"
os.environ["POSTGRES_DB"] = "iConcur"
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
postgres_username = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "123456")
postgres_db = os.getenv("POSTGRES_DB", "iConcur")


class Config:
    # Signs the session cookie. Change in production.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me-in-production")

    # SQLite by default (light weight). Point at Postgres for larger installs:
    #   DATABASE_URL=postgresql+psycopg://user:pass@host/dbname

    # switch to sqlite for local development
    # SQLALCHEMY_DATABASE_URI = os.environ.get(
    #     "DATABASE_URL", f"sqlite:///{BASE_DIR / 'iconcur.db'}"
    # )

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"postgresql+psycopg2://{postgres_username}:{postgres_password}@localhost/{postgres_db}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set to True when served over HTTPS
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8 hours

    # File uploads (email attachments, supporting docs)
    # UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))

    @staticmethod
    def get_upload_folder(company_code):
        """Generate the upload folder path based on the company code."""
        base_path = "C:\\Vouchers_Upload"
        return os.path.join(base_path, company_code, "uploads")

    UPLOAD_FOLDER = get_upload_folder("default_company")  # Default path for initialization

    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB per request

    # Inbound email ingestion (IMAP). Optional; only used if configured.
    IMAP_HOST = os.environ.get("IMAP_HOST", "")
    IMAP_USER = os.environ.get("IMAP_USER", "")
    IMAP_PASSWORD = os.environ.get("IMAP_PASSWORD", "")
    IMAP_FOLDER = os.environ.get("IMAP_FOLDER", "INBOX")

    # Shared secret the Outlook/Gmail add-ins present to the inbound webhook.
    # This is NOT a bearer token auth scheme for users; it is a simple plugin key.
    PLUGIN_SHARED_KEY = os.environ.get("PLUGIN_SHARED_KEY", "dev-plugin-key")

    # Claude API key, used to extract request-form fields from uploaded images.
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
