# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn whitenoise

COPY . .

# Railway sets $PORT dynamically
ENV PORT=8080
EXPOSE 8080

# Start: migrate -> collectstatic -> Celery worker + beat (background) -> Gunicorn (foreground)
# Key differences: bind on IPv4 and IPv6; use sh; log to stdout/stderr
CMD sh -lc "\
  python manage.py migrate --noinput && \
  python manage.py collectstatic --noinput || true && \
  celery -A hmva worker -l INFO -Q default,openai,io,celery,celery.chord_unlock \
         --concurrency=4 --prefetch-multiplier=1 --max-tasks-per-child=200 & \
  celery -A hmva beat -l INFO & \
  exec gunicorn hmva.wsgi:application \
       --bind 0.0.0.0:${PORT} \
       --bind [::]:${PORT} \
       --workers 2 --timeout 120 \
       --access-logfile - --error-logfile - \
"
