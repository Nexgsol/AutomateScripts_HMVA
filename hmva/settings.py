from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-key")
DEBUG = True
ALLOWED_HOSTS = "ALLOWED_HOSTS", "automatescriptshmva-production.up.railway.app, localhost,127.0.0.1"
CSRF_TRUSTED_ORIGINS = "CSRF_TRUSTED_ORIGINS", "https://automatescriptshmva-production.up.railway.app/"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # behind Render proxy

# redirect http->https at Django level (safe behind Railway)
SECURE_SSL_REDIRECT = True

# secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS (enable once you’re sure HTTPS is permanent!)
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "false").lower() == "true"

# extra hardening (optional)
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

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

DATABASES = {"default": {"ENGINE":"django.db.backends.sqlite3","NAME": BASE_DIR/"db.sqlite3"}}

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIMEZONE", "America/New_York")
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # ✅ you already fixed the missing quote

# Recommended for prod (serves gzip/brotli of hashed files)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

CELERY_BROKER_URL = os.getenv("REDIS_URL") or "redis://redis:6379/0"
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Make delivery robust
CELERY_TASK_ACKS_LATE = True                 # re-queue if worker dies mid-task
CELERY_WORKER_PREFETCH_MULTIPLIER = 1        # smoother flow; better with rate limits
CELERY_TASK_TRACK_STARTED = True

# Keep content simple/compatible
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

# Route noisy API calls away from I/O and orchestration
CELERY_TASK_ROUTES = {
    "core.tasks.process_row_task": {"queue": "openai"},
    "core.tasks.save_batch_task": {"queue": "io"},
    "core.tasks.orchestrate_paragraphs_job": {"queue": "default"},
}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
GDRIVE_SERVICE_ACCOUNT_JSON = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON", "")
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "")
AIRTABLE_TABLE = os.getenv("AIRTABLE_TABLE", "Requests")
