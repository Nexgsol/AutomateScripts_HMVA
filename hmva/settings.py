# settings.py
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- Core env ----------
# Prefer SECRET_KEY (Railway), fallback to DJANGO_SECRET_KEY for convenience
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("DJANGO_SECRET_KEY") or "change-me-in-prod"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Comma-separated envs are easiest to maintain on Railway
ALLOWED_HOSTS = [h for h in os.getenv("ALLOWED_HOSTS", "automatescriptshmva-production.up.railway.app,localhost,127.0.0.1").split(",") if h]
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv("CSRF_TRUSTED_ORIGINS", "https://automatescriptshmva-production.up.railway.app").split(",") if o]

# Behind Railway proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# ---------- Security toggled by DEBUG ----------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS: only enable if you will stay HTTPS. Values overridable via env.
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
    "django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
    "django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles",
    "rest_framework","core",
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
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "core" / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "hmva.wsgi.application"

# ---------- SQLite on Railway Volume ----------
# Create a Railway Volume and set: SQLITE_PATH=/data/db.sqlite3
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
    }
}

# ---------- i18n ----------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIMEZONE", "UTC")
USE_I18N = True
USE_TZ = True

# ---------- Static / Media (point to Volume via env) ----------
STATIC_URL = "/static/"
STATIC_ROOT = os.getenv("STATIC_ROOT", str(BASE_DIR / "staticfiles"))
MEDIA_URL = "/media/"
MEDIA_ROOT = os.getenv("MEDIA_ROOT", str(BASE_DIR / "media"))

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- Celery / Redis (Railway plugin exposes REDIS_URL) ----------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

CELERY_TASK_ROUTES = {
    "core.tasks.process_row_task": {"queue": "openai"},
    "core.tasks.save_batch_task": {"queue": "io"},
    "core.tasks.orchestrate_paragraphs_job": {"queue": "default"},
}

# ---------- Third-party keys ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
GDRIVE_SERVICE_ACCOUNT_JSON = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON", "")
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "")
AIRTABLE_TABLE = os.getenv("AIRTABLE_TABLE", "Requests")

# ---------- Optional: simple logging to stdout ----------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
