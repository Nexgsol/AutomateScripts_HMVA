# core/views_jobs.py
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_GET
from core.models import JobRun
from celery.result import AsyncResult


def _with_backend_state(job: JobRun):
    # If we have the final callback, use that state first
    if job.handoff_id:
        try:
            ar = AsyncResult(job.handoff_id)
            if ar.successful():
                return "SUCCESS"
            if ar.failed():
                return "FAILURE"
            if ar.status in ("PENDING", "RECEIVED", "STARTED", "RETRY"):
                return "RUNNING"
        except Exception:
            pass

    # Otherwise peek the orchestrator
    try:
        ar = AsyncResult(str(job.job_id))
        if ar.successful():
            return "SUCCESS"
        if ar.failed():
            return "FAILURE"
        if ar.status in ("PENDING", "RECEIVED", "STARTED", "RETRY"):
            return "RUNNING"
    except Exception:
        pass
    return job.state


@require_GET
def api_jobs_list(request):
    limit = int(request.GET.get("limit", 25))
    qs = JobRun.objects.order_by("-created_at")[:max(1, min(limit, 100))]
    data = []
    for j in qs:
        state = _with_backend_state(j)
        data.append({
            "job_id": str(j.job_id),
            "state": state,
            "mode": j.mode,
            "file": j.file_path,
            "sheet_name": j.sheet_name,
            "results": j.results_path,
            "download_url": j.download_url,
            "batches": j.batches,
            "created_at": j.created_at.isoformat(),
            "updated_at": j.updated_at.isoformat(),
            "error": j.error,
        })
        if state != j.state:
            JobRun.objects.filter(pk=j.pk).update(state=state)
    return JsonResponse({"jobs": data})


@require_GET
def api_jobs_detail(request, job_id: str):
    try:
        j = JobRun.objects.get(job_id=job_id)
    except JobRun.DoesNotExist:
        raise Http404("job not found")
    return JsonResponse({
        "job_id": str(j.job_id),
        "state": _with_backend_state(j),
        "mode": j.mode,
        "file": j.file_path,
        "sheet_name": j.sheet_name,
        "results": j.results_path,
        "download_url": j.download_url,
        "batches": j.batches,
        "created_at": j.created_at.isoformat(),
        "updated_at": j.updated_at.isoformat(),
        "error": j.error,
    })
