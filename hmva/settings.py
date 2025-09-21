from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- Core env ----------
# Prefer SECRET_KEY (Railway), fallback to DJANGO_SECRET_KEY for convenience
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("DJANGO_SECRET_KEY") or "change-me"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# Proxy / HTTPS awareness (Railway)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# ---------- Security (toggled by DEBUG) ----------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
    SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "false").lower() == "true"
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# ---------- Apps / Middleware ----------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "hmva.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "core" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "hmva.wsgi.application"

# ---------- Database (SQLite on Railway Volume) ----------
# Add a Railway Volume and set SQLITE_PATH=/data/db.sqlite3
DATABASES = {}
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL:
    # Ensure postgresql:// scheme (Railway may still give postgres://)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    try:
        import dj_database_url
        DATABASES["default"] = dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", "600")),  # persistent conns
            ssl_require=True,  # add sslmode=require
        )
    except Exception:
        # Safe fallback if dj_database_url isn't installed for some reason
        from urllib.parse import urlparse
        parsed = urlparse(DATABASE_URL)
        DATABASES["default"] = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username,
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname,
            "PORT": str(parsed.port or "5432"),
            "OPTIONS": {"sslmode": "require"},
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "600")),
        }
else:
    # Local/dev fallback
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
    }

# ---------- Internationalization ----------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIMEZONE", "UTC")
USE_I18N = True
USE_TZ = True

# ---------- Static / Media (point both to Volume via env) ----------
STATIC_URL = "/static/"
STATIC_ROOT = os.getenv("STATIC_ROOT", str(BASE_DIR / "staticfiles"))
MEDIA_URL = os.getenv("MEDIA_URL", "/media/")
MEDIA_ROOT = os.getenv("MEDIA_ROOT", str(BASE_DIR / "media"))

# Whitenoise for static files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- Celery / Redis ----------
# Railway’s Redis plugin exposes REDIS_URL; we accept either CELERY_* or REDIS_URL.
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]


# Route CPU/API heavy tasks to dedicated queues (matches your workers)
CELERY_TASK_ROUTES = {
    "core.tasks.process_row_task": {"queue": "openai"},
    "core.tasks.save_batch_task": {"queue": "io"},
    "core.tasks.orchestrate_paragraphs_job": {"queue": "default"},
}

# ---------- Third-party API keys ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# Google Drive service account: either raw JSON in env or a file path on disk
GDRIVE_SERVICE_ACCOUNT_JSON = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON", "")
GOOGLE_SA_JSON = os.getenv("GOOGLE_SA_JSON", "")  # optional file path if you prefer
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "")

# Airtable
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "")
AIRTABLE_TABLE = os.getenv("AIRTABLE_TABLE", "Requests")

# ---------- Data backend defaults (optional convenience) ----------
DATA_BACKEND = os.getenv("DATA_BACKEND", "local")           # "sheet" or "local"
SHEET_PUBLIC_URL = os.getenv("SHEET_PUBLIC_URL", "")
SHEET_ID = os.getenv("SHEET_ID", "")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")
DATA_FILE = os.getenv("DATA_FILE", "data.xlsx")

COL_ICON = os.getenv("COL_ICON", "Icon Name")
COL_CATEGORY = os.getenv("COL_CATEGORY", "Category")
COL_NOTES = os.getenv("COL_NOTES", "Notes")
COL_DURATION = os.getenv("COL_DURATION", "Duration")
COL_PARAGRAPH = os.getenv("COL_PARAGRAPH", "Paragraph")
COL_SSML = os.getenv("COL_SSML", "SSML")

# ---------- Logging to stdout (helps on Railway) ----------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
