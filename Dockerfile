# # Dockerfile
# FROM python:3.11-slim

# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1

# WORKDIR /app
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt \
#     && pip install --no-cache-dir gunicorn whitenoise flower

# COPY . .

# # Railway sets $PORT dynamically; default to 8000 for local
# ENV PORT=8000
# EXPOSE 8000

# # Runtime just runs Gunicorn (migrations/static handled in Pre-Deploy)
# CMD ["bash","-lc","exec gunicorn hmva.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120"]


# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn whitenoise

COPY . .

# Render provides $PORT; default for local
ENV PORT=10000
EXPOSE 10000

# One-liner: migrate, collectstatic, start Celery worker+beat, then Gunicorn (foreground)
CMD bash -lc "\
  python manage.py migrate --noinput && \
  python manage.py collectstatic --noinput || true && \
  celery -A hmva worker -l INFO -Q default,openai,io,celery,celery.chord_unlock \
         --concurrency=4 --prefetch-multiplier=1 --max-tasks-per-child=200 & \
  celery -A hmva beat -l INFO & \
  exec gunicorn hmva.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 \
"

