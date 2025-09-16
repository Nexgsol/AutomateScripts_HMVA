# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn whitenoise flower

COPY . .

# Railway sets $PORT dynamically; default to 8000 for local
ENV PORT=8000
EXPOSE 8000

# Runtime just runs Gunicorn (migrations/static handled in Pre-Deploy)
CMD ["bash","-lc","exec gunicorn hmva.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120"]
