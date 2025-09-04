from django.shortcuts import render, get_object_or_404, redirect
from core.utils import generate_heritage_paragraph, call_openai_for_ssml
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

# def request_detail(request, pk):
#     sr = get_object_or_404(ScriptRequest, pk=pk)
#     return render(request, "request_detail.html", {"sr": sr})


# class ScriptGenerateAPI(APIView):
#     def post(self, req):
#         ser = ScriptRequestSerializer(data=req.data)
#         ser.is_valid(raise_exception=True)
#         sr = ser.save(status="New")
#         task_generate_script.delay(sr.id)
#         return Response({"id": sr.id, "status": "queued"}, status=status.HTTP_201_CREATED)

# class ScriptGetAPI(APIView):
#     def get(self, req, pk):
#         sr = get_object_or_404(ScriptRequest, pk=pk)
#         return Response(ScriptRequestSerializer(sr).data)

# class RenderAvatarAPI(APIView):
#     def post(self, req, pk):
#         sr = get_object_or_404(ScriptRequest, pk=pk)
#         task_render_avatar.delay(sr.id)
#         return Response({"id": sr.id, "render": "queued"}, status=status.HTTP_202_ACCEPTED)

# class AssembleAPI(APIView):
#     def post(self, req, pk):
#         sr = get_object_or_404(ScriptRequest, pk=pk)
#         task_assemble_template.delay(sr.id)
#         return Response({"id": sr.id, "assemble": "queued"}, status=status.HTTP_202_ACCEPTED)

# class DriveAPI(APIView):
#     def post(self, req, pk):
#         sr = get_object_or_404(ScriptRequest, pk=pk)
#         task_push_drive.delay(sr.id)
#         return Response({"id": sr.id, "drive": "queued"}, status=status.HTTP_202_ACCEPTED)

# class CaptionsAPI(APIView):
#     def post(self, req, pk):
#         sr = get_object_or_404(ScriptRequest, pk=pk)
#         task_generate_captions.delay(sr.id)
#         return Response({"id": sr.id, "captions": "queued"}, status=status.HTTP_202_ACCEPTED)

# class AirtableSyncAPI(APIView):
#     def post(self, req, pk):
#         sr = get_object_or_404(ScriptRequest, pk=pk)
#         task_sync_airtable.delay(sr.id)
#         return Response({"id": sr.id, "airtable": "queued"}, status=status.HTTP_202_ACCEPTED)

# class ScheduleAPI(APIView):
#     def post(self, req, pk):
#         sr = get_object_or_404(ScriptRequest, pk=pk)
#         task_schedule.delay(sr.id)
#         return Response({"id": sr.id, "schedule": "queued"}, status=status.HTTP_202_ACCEPTED)

# class PublishAPI(APIView):
#     def post(self, req, pk):
#         sr = get_object_or_404(ScriptRequest, pk=pk)
#         task_publish.delay(sr.id)
#         return Response({"id": sr.id, "publish": "queued"}, status=status.HTTP_202_ACCEPTED)

# class MetricsAPI(APIView):
#     def post(self, req, pk):
#         sr = get_object_or_404(ScriptRequest, pk=pk)
#         task_metrics_24h.delay(sr.id)
#         return Response({"id": sr.id, "metrics24h": "queued"}, status=status.HTTP_202_ACCEPTED)

# def avatar_quick_create(request):
#     brands = Brand.objects.all()
#     ctx = {"brands": brands}
#     if request.method == "POST":
#         brand_id = request.POST["brand"]
#         avatar_name = request.POST["avatar_name"]
#         voice_name = request.POST.get("voice_name","")
#         eleven_id = request.POST.get("eleven_id","")
#         img = request.FILES.get("photo")

#         image_path = None
#         if img:
#             image_path = default_storage.save(f"avatars/{img.name}", ContentFile(img.read()))
#             # Try optional HeyGen photo-avatar API (stub returns "")
#             avatar_id = avatar_heygen.create_photo_avatar(open(default_storage.path(image_path),"rb").read(), avatar_name)
#         else:
#             avatar_id = ""

#         ap = AvatarProfile.objects.create(
#             brand_id=brand_id,
#             avatar_name=avatar_name,
#             voice_name=voice_name,
#             elevenlabs_voice_id=eleven_id,
#             heygen_avatar_id=avatar_id,
#             image=image_path
#         )
#         return redirect("script-form")
#     return render(request, "avatar_form.html", ctx)


# class ParagraphAPI(APIView):
#     def post(self, request):
#         icon = request.data.get("icon") or request.POST.get("icon")
#         notes = request.data.get("notes") or request.POST.get("notes", "")
#         if not icon:
#             return Response({"error": "icon is required"}, status=status.HTTP_400_BAD_REQUEST)
#         paragraph = generate_heritage_paragraph(
#             icon, notes
#         )
#         return Response({"icon": icon, "paragraph": paragraph}, status=status.HTTP_200_OK)
    




    from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from .forms import ScriptAvatarForm
from .models import Icon, ScriptRequest
from .utils import generate_heritage_paragraph
from .adapters import avatar_heygen
from .tasks import task_render_heygen_tts

@require_http_methods(["GET", "POST"])
def script_avatar_page(request):
    paragraph = ""
    if request.method == "POST":
        form = ScriptAvatarForm(request.POST)
        action = request.POST.get("action", "")
        if form.is_valid():
            icon_obj = form.cleaned_data["icon"]
            brand = form.cleaned_data["brand"]
            duration = form.cleaned_data["duration"]
            category = form.cleaned_data["category"] or (icon_obj.category if hasattr(icon_obj, "category") else "")
            notes = form.cleaned_data["notes"] or (getattr(icon_obj, "short_cues", "") or "")

            # Always refresh paragraph so both actions work
            paragraph = generate_heritage_paragraph(icon_obj.name, notes)

            if action == "generate_video":
                heygen_avatar_id = form.cleaned_data["heygen_avatar_id"]
                heygen_voice_id  = form.cleaned_data["heygen_voice_id"] or None
                if not heygen_avatar_id:
                    messages.error(request, "Please select a HeyGen avatar.")
                else:
                    sr = ScriptRequest.objects.create(
                        brand=brand, mode="Single",
                        icon_or_topic=icon_obj.name,
                        notes=notes,
                        duration=duration,
                        draft_script=paragraph,
                        final_script=paragraph,
                        status="Drafted",
                    )
                    task_render_heygen_tts.delay(sr.id, heygen_avatar_id, heygen_voice_id)
                    messages.success(request, f"Video render queued for {icon_obj.name}.")
                    # change 'request-detail' to your actual detail route name if different
                    return redirect("request-detail", pk=sr.id)
    else:
        form = ScriptAvatarForm()

    return render(request, "script_avatar_page.html", {"form": form, "paragraph": paragraph})


# AJAX helpers
# def heygen_avatars_api(request):
#     return JsonResponse({"avatars": avatar_heygen.list_avatars()})


# def heygen_voices_api(request):
#     return JsonResponse({"voices": avatar_heygen.list_voices()})


# def icon_meta_api(request, pk: int):
#     icon = get_object_or_404(Icon, pk=pk)
#     return JsonResponse({"category": getattr(icon, "category", ""), "notes": getattr(icon, "short_cues", "")})


# Paragraph generator API (used by the left-side button)


class ParagraphAPI(APIView):
    def post(self, request):
        icon = request.data.get("icon", "")
        notes = request.data.get("notes", "")
        if not icon:
            return Response({"error": "No icon provided"}, status=status.HTTP_400_BAD_REQUEST)
        # Compose a prompt that asks for both plain paragraph and SSML
        prompt = f"""
            You are a senior fashion copywriter AND an SSML engineer.
            GOAL
            1) Write ONE documentary-style brand paragraph (120–180 words) about {icon}.
            - Weave in these notes naturally: {notes}
            - Concrete visuals (fit, fabric, color mood, scene); present tense; no hype, emojis, or markdown.
            - Include one subtle styling suggestion.
            - End with a calm, confident closing line.

            2) Convert that paragraph into VALID, production-ready SSML (ElevenLabs-compatible).

            SSML RULES
            - Output ONE <speak> block only (no XML declaration, no code fences, no comments).
            - Wrap content in <prosody rate="medium"> … </prosody>.
            - Use <break> between 120–500ms at natural beats.
            - Use <emphasis level="moderate"> on up to 3 short phrases.
            - Convert years to <say-as interpret-as="date" format="y">YYYY</say-as>.
            - Convert standalone integers to <say-as interpret-as="cardinal">N</say-as> when helpful.
            - Escape special characters (&, <, >, ").
            - End with <mark name="END"/> right before </speak>.
            - No vendor-specific or <audio> tags.

            OUTPUT FORMAT
            Return ONLY a single JSON object (no extra text, no markdown), strictly valid and double-quoted:
            {{
            "paragraph": "string — the plain text paragraph (120–180 words).",
            "ssml": "<speak>…</speak>"
            }}
            """

        # Call OpenAI once
        import json
        response = call_openai_for_ssml(prompt)
        try:
            data = json.loads(response)
            return Response({"paragraph": data.get("paragraph", ""), "ssml": data.get("ssml", "")})
        except Exception:
            # fallback: just return the text as paragraph
            return Response({"paragraph": response, "ssml": ""})

