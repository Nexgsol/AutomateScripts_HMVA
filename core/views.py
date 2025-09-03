from django.shortcuts import render, get_object_or_404, redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Brand, ScriptRequest, Template, AvatarProfile
from .serializers import ScriptRequestSerializer

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .adapters import avatar_heygen

from .tasks import (
    task_generate_script, task_kickoff_chain, task_render_avatar, task_assemble_template,
    task_push_drive, task_generate_captions, task_sync_airtable,
    task_schedule, task_publish, task_metrics_24h
)

def script_form(request):
    brands = Brand.objects.all()
    avatars = AvatarProfile.objects.all()
    templates = Template.objects.all()
    ctx = {"brands": brands, "avatars": avatars, "templates": templates}
    if request.method == "POST":
        brand_id = request.POST["brand"]
        icon = request.POST["icon"]
        notes = request.POST.get("notes","")
        duration = request.POST.get("duration","30s")
        avatar_id = request.POST.get("avatar") or None
        template_id = request.POST.get("template") or None
        sr = ScriptRequest.objects.create(
            brand_id=brand_id, icon_or_topic=icon, notes=notes,
            duration=duration, avatar_id=avatar_id, template_id=template_id, status="New"
        )
        if request.POST.get("auto") == "on":
            task_kickoff_chain.delay(sr.id)
            return redirect("request-detail", pk=sr.id)
        task_generate_script.delay(sr.id)
        return redirect("request-detail", pk=sr.id)
    return render(request, "script_form.html", ctx)


class AutoPipelineAPI(APIView):
    def post(self, req, pk):
        task_kickoff_chain.delay(pk)
        return Response({"id": pk, "auto_pipeline": "queued"}, status=status.HTTP_202_ACCEPTED)


def request_detail(request, pk):
    sr = get_object_or_404(ScriptRequest, pk=pk)
    return render(request, "request_detail.html", {"sr": sr})


class ScriptGenerateAPI(APIView):
    def post(self, req):
        ser = ScriptRequestSerializer(data=req.data)
        ser.is_valid(raise_exception=True)
        sr = ser.save(status="New")
        task_generate_script.delay(sr.id)
        return Response({"id": sr.id, "status": "queued"}, status=status.HTTP_201_CREATED)

class ScriptGetAPI(APIView):
    def get(self, req, pk):
        sr = get_object_or_404(ScriptRequest, pk=pk)
        return Response(ScriptRequestSerializer(sr).data)

class RenderAvatarAPI(APIView):
    def post(self, req, pk):
        sr = get_object_or_404(ScriptRequest, pk=pk)
        task_render_avatar.delay(sr.id)
        return Response({"id": sr.id, "render": "queued"}, status=status.HTTP_202_ACCEPTED)

class AssembleAPI(APIView):
    def post(self, req, pk):
        sr = get_object_or_404(ScriptRequest, pk=pk)
        task_assemble_template.delay(sr.id)
        return Response({"id": sr.id, "assemble": "queued"}, status=status.HTTP_202_ACCEPTED)

class DriveAPI(APIView):
    def post(self, req, pk):
        sr = get_object_or_404(ScriptRequest, pk=pk)
        task_push_drive.delay(sr.id)
        return Response({"id": sr.id, "drive": "queued"}, status=status.HTTP_202_ACCEPTED)

class CaptionsAPI(APIView):
    def post(self, req, pk):
        sr = get_object_or_404(ScriptRequest, pk=pk)
        task_generate_captions.delay(sr.id)
        return Response({"id": sr.id, "captions": "queued"}, status=status.HTTP_202_ACCEPTED)

class AirtableSyncAPI(APIView):
    def post(self, req, pk):
        sr = get_object_or_404(ScriptRequest, pk=pk)
        task_sync_airtable.delay(sr.id)
        return Response({"id": sr.id, "airtable": "queued"}, status=status.HTTP_202_ACCEPTED)

class ScheduleAPI(APIView):
    def post(self, req, pk):
        sr = get_object_or_404(ScriptRequest, pk=pk)
        task_schedule.delay(sr.id)
        return Response({"id": sr.id, "schedule": "queued"}, status=status.HTTP_202_ACCEPTED)

class PublishAPI(APIView):
    def post(self, req, pk):
        sr = get_object_or_404(ScriptRequest, pk=pk)
        task_publish.delay(sr.id)
        return Response({"id": sr.id, "publish": "queued"}, status=status.HTTP_202_ACCEPTED)

class MetricsAPI(APIView):
    def post(self, req, pk):
        sr = get_object_or_404(ScriptRequest, pk=pk)
        task_metrics_24h.delay(sr.id)
        return Response({"id": sr.id, "metrics24h": "queued"}, status=status.HTTP_202_ACCEPTED)

def avatar_quick_create(request):
    brands = Brand.objects.all()
    ctx = {"brands": brands}
    if request.method == "POST":
        brand_id = request.POST["brand"]
        avatar_name = request.POST["avatar_name"]
        voice_name = request.POST.get("voice_name","")
        eleven_id = request.POST.get("eleven_id","")
        img = request.FILES.get("photo")

        image_path = None
        if img:
            image_path = default_storage.save(f"avatars/{img.name}", ContentFile(img.read()))
            # Try optional HeyGen photo-avatar API (stub returns "")
            avatar_id = avatar_heygen.create_photo_avatar(open(default_storage.path(image_path),"rb").read(), avatar_name)
        else:
            avatar_id = ""

        ap = AvatarProfile.objects.create(
            brand_id=brand_id,
            avatar_name=avatar_name,
            voice_name=voice_name,
            elevenlabs_voice_id=eleven_id,
            heygen_avatar_id=avatar_id,
            image=image_path
        )
        return redirect("script-form")
    return render(request, "avatar_form.html", ctx)
