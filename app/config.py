from datetime import timedelta
import os
from dotenv import load_dotenv

# Resolve .env from the project root (one level above app/).
_ENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=_ENV_PATH, override=False)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-key")

    USE_SQLITE = os.environ.get("DB_USE_SQLITE", "true").lower() == "true"

    if USE_SQLITE:
        # Default development database.
        SQLALCHEMY_DATABASE_URI = (
            "sqlite:///" + os.path.join(BASE_DIR, "..", "instance", "smartqualihome.db")
        )
        SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        DB_HOST = os.environ.get("DB_HOST", "localhost")
        DB_PORT = os.environ.get("DB_PORT", "3306")
        DB_USER = os.environ.get("DB_USER", "root")
        DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
        DB_NAME = os.environ.get("DB_NAME", "smartqualihome")
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
            "?charset=utf8mb4"
        )

        engine_options = {
            "pool_pre_ping": True,
            "pool_recycle": 180,
        }

        # Aiven (and most managed MySQL providers) require TLS connections.
        # DB_SSL_CA should point to a CA cert file path, e.g. Render's
        # "Secret File" mount at /etc/secrets/aiven-ca.pem, or a local path
        # such as instance/aiven-ca.pem for XAMPP/dev use.
        DB_SSL_CA = os.environ.get("DB_SSL_CA", "")
        if DB_SSL_CA:
            engine_options["connect_args"] = {"ssl": {"ca": DB_SSL_CA}}

        SQLALCHEMY_ENGINE_OPTIONS = engine_options

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    # File uploads
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "instance", "uploads")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

    # Session cookie security
    _IS_PRODUCTION = os.environ.get("FLASK_ENV", "development").lower() == "production"

    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = "Lax"
    # True when FLASK_ENV=production (Render serves over HTTPS).
    # Stays False for local http://localhost development.
    SESSION_COOKIE_SECURE    = _IS_PRODUCTION
    # Session lifetime (used when session.permanent = True)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    # Inactivity timeout in minutes (enforced in app.before_request).
    SESSION_TIMEOUT_MINS     = 60

    # Remember Me: keep session alive for 30 days
    REMEMBER_COOKIE_DURATION  = timedelta(days=30)
    REMEMBER_COOKIE_HTTPONLY  = True
    REMEMBER_COOKIE_SAMESITE  = "Lax"
    REMEMBER_COOKIE_SECURE    = _IS_PRODUCTION

    # SMTP mail settings (used by forgot/reset password)
    MAIL_SERVER    = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT      = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USERNAME  = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD  = os.environ.get("MAIL_PASSWORD", "")
    MAIL_USE_TLS   = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL   = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_FROM      = os.environ.get("MAIL_FROM", MAIL_USERNAME or "no-reply@qualihome.local")