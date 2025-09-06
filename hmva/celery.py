import os
from celery import Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE','hmva.settings')
app=Celery('hmva')
app.config_from_object('django.conf:settings',namespace='CELERY')
app.autodiscover_tasks()
app.conf.imports = app.conf.imports + ("core.tasks.video_tasks",)
app.conf.imports = app.conf.imports + ("core.tasks.script_tasks",)