# core/jobs.py
from typing import Optional
from django.utils import timezone
from django.db import transaction
from django.core.files.storage import default_storage
from .models import JobRun


def job_get_or_create(job_id, **kwargs) -> JobRun:
    with transaction.atomic():
        obj, _ = JobRun.objects.get_or_create(job_id=job_id, defaults=kwargs)
        # Backfill useful fields if provided
        update = {}
        for k, v in kwargs.items():
            if v and getattr(obj, k, None) != v:
                update[k] = v
        if update:
            JobRun.objects.filter(pk=obj.pk).update(**update, updated_at=timezone.now())
            for k, v in update.items():
                setattr(obj, k, v)
    return obj


def job_set_state(job_id, state: str, error: str = "", download_url: str = "", results_path: str = "") -> None:
    update = {"state": state, "updated_at": timezone.now()}
    if error:
        update["error"] = error
    if download_url:
        update["download_url"] = download_url
    if results_path:
        update["results_path"] = results_path
    JobRun.objects.filter(job_id=job_id).update(**update)


def job_touch(job_id, **kwargs) -> None:
    kwargs["updated_at"] = timezone.now()
    JobRun.objects.filter(job_id=job_id).update(**kwargs)
