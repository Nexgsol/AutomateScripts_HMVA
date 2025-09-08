FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn whitenoise

COPY . .

# Long-lived server, bind to $PORT
CMD ["bash","-lc","python manage.py migrate --noinput && python manage.py collectstatic --noinput && exec gunicorn hmva.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120"]
