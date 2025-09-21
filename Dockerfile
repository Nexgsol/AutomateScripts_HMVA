FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir gunicorn whitenoise
COPY . .

EXPOSE 8080
CMD sh -lc '\
  # start Celery worker in background (listens to chord queues too)
  celery -A hmva worker -l INFO -Q default,openai,io,celery,celery.chord_unlock \
         --concurrency=2 --prefetch-multiplier=1 --max-tasks-per-child=200 & \
  # now start Gunicorn immediately (foreground)
  exec gunicorn hmva.wsgi:application \
    --bind 0.0.0.0:${PORT:-8080} --bind [::]:${PORT:-8080} \
    --workers 2 --timeout 120 --access-logfile - --error-logfile -'
