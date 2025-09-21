# Dockerfile
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn whitenoise

COPY . .

EXPOSE 8080

# Start Celery worker (bg) + Gunicorn (fg). Keep migrations out of CMD (see Pre-Deploy).
CMD sh -lc "\
  # start Celery only if a real Redis URL is available (Railway plugin exposes REDIS_URL) && \
  if [ -n \"\${CELERY_BROKER_URL:-\${REDIS_URL:-}}\" ]; then \
    export CELERY_BROKER_URL=\"\${CELERY_BROKER_URL:-\${REDIS_URL}}\"; \
    export CELERY_RESULT_BACKEND=\"\${CELERY_RESULT_BACKEND:-\${CELERY_BROKER_URL}}\"; \
    celery -A hmva worker -l INFO \
           -Q default,openai,io,celery,celery.chord_unlock \
           --concurrency=2 --prefetch-multiplier=1 --max-tasks-per-child=200 & \
  else \
    echo \"No Redis URL set; starting web only.\"; \
  fi; \
  # bind ONCE (IPv6 covers IPv4 on Linux) && \
  exec gunicorn hmva.wsgi:application \
       --bind [::]:\${PORT:-8080} \
       --workers 2 --timeout 120 \
       --access-logfile - --error-logfile -"
