from celery import shared_task
from django.utils import timezone
from django.conf import settings

from core.services.tts_service import fetch_or_create_tts_audio, load_audio_bytes
from .models import ScriptRequest, PublishTarget
from .prompts import GENERATOR_SYSTEM, gen_user, finalize_user, CAPTION_SYSTEM, captions_user
from . import utils
from .adapters import tts_elevenlabs, avatar_heygen, renderer_shotstack, renderer_cloudinary, airtable, drive_google
from .adapters import publish_youtube, publish_instagram, publish_facebook, publish_tiktok
import datetime, json
from celery import chain

@shared_task
def task_generate_script(sr_id: int):
    sr = ScriptRequest.objects.get(id=sr_id)
    lo, hi = utils.word_range(sr.duration)
    draft = utils.llm_chat(GENERATOR_SYSTEM, gen_user(sr.icon_or_topic, sr.notes, lo, hi), 0.5)
    qc = utils.qc_local(draft, lo, hi)
    sr.draft_script = draft
    sr.qc_json = qc
    if qc["fix_needed"]:
        final_text = utils.llm_chat("You are a precise editor.",
                                    finalize_user(sr.icon_or_topic, sr.notes, lo, hi, draft), 0.4)
        sr.final_script = final_text
        sr.qc_json = utils.qc_local(final_text, lo, hi)
        sr.status = "Drafted" if not sr.qc_json["fix_needed"] else "NeedsFix"
    else:
        sr.final_script = draft
        sr.status = "Drafted"
    sr.updated_at = timezone.now()
    sr.save()
    return sr.id


@shared_task
def task_render_avatar(sr_id: int):
    sr = ScriptRequest.objects.get(id=sr_id)
    if not sr.final_script:
        task_generate_script(sr.id)
        sr.refresh_from_db()

    if not (sr.avatar and sr.avatar.heygen_avatar_id and sr.avatar.elevenlabs_voice_id):
        raise ValueError("Avatar profile with HeyGen avatar id and ElevenLabs voice id is required.")

    # Fetch or create (re-use) the TTS asset and get its bytes
    tts_rec = fetch_or_create_tts_audio(
        voice_id=sr.avatar.elevenlabs_voice_id,
        text=sr.final_script,
        settings={"stability": 0.5, "similarity_boost": 0.75},
        attach_history=True,
    )
    mp3 = load_audio_bytes(tts_rec)

    # Continue with HeyGen upload/render (unchanged) ...
    res = avatar_heygen.generate_from_audio_bytes(
        sr.avatar.heygen_avatar_id, mp3, title=f"{sr.icon_or_topic} · req#{sr.id}"
    )
    if res.get("status") != "completed":
        sr.status = "Assembling"
        sr.qc_json = {**(sr.qc_json or {}), "heygen_status": res}
        sr.save()
        return res

    sr.asset_url = res.get("video_url","") or sr.asset_url
    sr.edit_url  = res.get("share_url","") or sr.edit_url
    sr.status = "Rendered"
    sr.save()
    return {"video_url": sr.asset_url, "share_url": sr.edit_url, "eleven_history_id": tts_rec.eleven_history_id}


@shared_task
def task_assemble_template(sr_id: int):
    sr = ScriptRequest.objects.get(id=sr_id)
    if not sr.asset_url:
        raise ValueError("No avatar asset_url to assemble")
    if sr.template and sr.template.engine == "cloudinary":
        res = renderer_cloudinary.assemble(sr.template.payload_json, sr.asset_url)
    else:
        res = renderer_shotstack.assemble(sr.template.payload_json if sr.template else {}, sr.asset_url)
    sr.asset_url = res.get("asset_url", sr.asset_url)
    sr.edit_url = res.get("edit_url", sr.edit_url)
    today = datetime.datetime.utcnow().strftime("%Y%m%d")
    content_type = {"15s":"15sStory","30s":"30sReel","60s":"60sReel"}.get(sr.duration,"30sReel")
    sr.file_name = f"{sr.icon_or_topic.replace(' ','_')}_{today}_9x16_{content_type}.mp4"
    sr.status = "Rendered"
    sr.updated_at = timezone.now()
    sr.save()
    return sr.file_name

@shared_task
def task_push_drive(sr_id: int):
    sr = ScriptRequest.objects.get(id=sr_id)
    if not sr.asset_url:
        raise ValueError("No asset_url to push to Drive")
    folder_id = settings.GDRIVE_FOLDER_ID or ""
    try:
        meta = drive_google.upload_from_url(sr.asset_url, sr.file_name or "Heritage_Reel.mp4", folder_id)
        sr.edit_url = meta.get("webViewLink","") or sr.edit_url
    except Exception as e:
        sr.qc_json = {**(sr.qc_json or {}), "drive_error": str(e)}
    sr.updated_at = timezone.now()
    sr.save()
    return True

@shared_task
def task_generate_captions(sr_id: int):
    sr = ScriptRequest.objects.get(id=sr_id)
    hashtags = (sr.brand.hashtags or "").strip()
    hashtags_csv = hashtags if hashtags else ""
    resp = utils.llm_chat(CAPTION_SYSTEM, captions_user(sr.icon_or_topic, hashtags_csv), 0.2)
    import json
    try:
        data = json.loads(resp)
    except Exception:
        data = {"caption_yt": resp[:180], "caption_tt": resp[:180],
                "caption_ig_reels": resp[:180], "caption_ig_stories": resp[:180], "caption_fb_reels": resp[:180]}
    sr.caption_yt = data.get("caption_yt","")
    sr.caption_tt = data.get("caption_tt","")
    sr.caption_ig_reels = data.get("caption_ig_reels","")
    sr.caption_ig_stories = data.get("caption_ig_stories","")
    sr.caption_fb_reels = data.get("caption_fb_reels","")
    sr.updated_at = timezone.now()
    sr.save()
    return True

@shared_task
def task_sync_airtable(sr_id: int):
    sr = ScriptRequest.objects.get(id=sr_id)
    fields = {
        "RequestID": sr.id, "Brand": sr.brand.name, "IconOrTopic": sr.icon_or_topic,
        "Duration": sr.duration, "Status": sr.status, "AssetURL": sr.asset_url,
        "FileName": sr.file_name, "CaptionYT": sr.caption_yt, "CaptionTikTok": sr.caption_tt,
        "CaptionIGReels": sr.caption_ig_reels, "CaptionIGStories": sr.caption_ig_stories,
        "CaptionFBReels": sr.caption_fb_reels,
    }
    rid = airtable.push_record(fields)
    return rid

@shared_task
def task_schedule(sr_id: int):
    sr = ScriptRequest.objects.get(id=sr_id)
    slot_label, slot_dt = utils.next_post_slot(sr.brand.timezone, sr.brand.post_windows)
    sr.scheduled_slot = slot_label
    sr.publish_at = slot_dt.astimezone(timezone.utc)
    sr.status = "Scheduled"
    sr.updated_at = timezone.now()
    sr.save()
    return sr.publish_at.isoformat()

@shared_task
def task_publish(sr_id: int):
    sr = ScriptRequest.objects.get(id=sr_id)
    posts = {}
    for t in PublishTarget.objects.filter(brand=sr.brand, enabled=True):
        if t.platform == "yt":
            posts["yt"] = publish_youtube.schedule_upload(sr.asset_url, sr.icon_or_topic, sr.publish_at.isoformat())
        elif t.platform == "ig":
            posts["ig"] = publish_instagram.schedule_upload(sr.asset_url, sr.caption_ig_reels, sr.publish_at.isoformat())
        elif t.platform == "fb":
            posts["fb"] = publish_facebook.schedule_upload(sr.asset_url, sr.caption_fb_reels, sr.publish_at.isoformat())
        elif t.platform == "tt":
            posts["tt"] = publish_tiktok.schedule_upload(sr.asset_url, sr.caption_tt, sr.publish_at.isoformat())
    sr.post_ids = posts
    sr.status = "Posted"
    sr.updated_at = timezone.now()
    sr.save()
    return posts

@shared_task
def task_metrics_24h(sr_id: int):
    sr = ScriptRequest.objects.get(id=sr_id)
    perf = {"views": 0, "likes": 0, "comments": 0, "shares": 0, "rank_percentile": 50}
    sr.performance_json = perf
    sr.status = "Pulled"
    sr.updated_at = timezone.now()
    sr.save()
    return perf

# core/tasks.py

from celery import shared_task
from requests import HTTPError
from django.utils import timezone
from .models import ScriptRequest
from .utils import generate_heritage_paragraph
from .adapters import avatar_heygen, tts_elevenlabs

@shared_task
def task_render_heygen_tts(sr_id: int, avatar_or_group_id: str, heygen_voice_id: str | None = None):
    """
    Render via HeyGen using TTS first; if HeyGen rejects, fall back to audio pipeline.
    Ensures we always send a LOOK avatar_id (not a group_id).
    """
    sr = ScriptRequest.objects.get(id=sr_id)

    # Ensure we have text
    if not sr.final_script:
        sr.final_script = generate_heritage_paragraph(sr.icon_or_topic, sr.notes or "")
        sr.status = "Drafted"
        sr.save()

    # 1) Resolve group -> first look (renderable) and pick a voice if needed
    look_avatar_id = avatar_or_group_id
    picked_voice = heygen_voice_id
    print("[TASK] incoming avatar_or_group_id:", avatar_or_group_id)
    print("[TASK] resolved look_avatar_id:", look_avatar_id, "picked_voice:", picked_voice)

    # 2) Try TTS path
    try:
        video_id = avatar_heygen.create_avatar_video_from_text(
            avatar_id=look_avatar_id,
            input_text=sr.final_script,
            voice_id=picked_voice,            # may be None; adapter handles omission
            title=f"{sr.icon_or_topic} · req#{sr.id}",
            width=1080, height=1920,
            # accept_group_id False because we've resolved to a look already
            accept_group_id=False,
        )
    except HTTPError as e:
        # 3) Fallback: synthesize audio with ElevenLabs -> upload -> render via audio_asset_id
        print("[TASK] TTS failed, falling back to audio. Reason:", str(e))
        # If your ScriptRequest.avatar has an ElevenLabs id, prefer that; otherwise continue without (ElevenLabs default/mapped)
        el_voice = getattr(sr.avatar, "elevenlabs_voice_id", None)
        mp3_bytes = tts_elevenlabs.synthesize_bytes(sr.final_script, el_voice)
        audio_asset_id = avatar_heygen.upload_audio_asset(mp3_bytes)
        video_id = avatar_heygen.create_avatar_video_from_audio(
            avatar_id=look_avatar_id,
            audio_asset_id=audio_asset_id,
            title=f"{sr.icon_or_topic} · req#{sr.id}",
            width=1080, height=1920,
            accept_group_id=False,
        )

    # 4) Wait and persist
    st = avatar_heygen.wait_for_video(video_id, timeout_sec=900, poll_sec=10)
    if st.get("status") != "completed":
        sr.status = "Assembling"
        sr.qc_json = {**(sr.qc_json or {}), "heygen_status": st}
        sr.save()
        return st

    sr.asset_url = st.get("video_url", "")
    sr.edit_url = avatar_heygen.get_share_url(video_id) or ""
    sr.status = "Rendered"
    sr.updated_at = timezone.now()
    sr.save()
    return {"video_url": sr.asset_url, "share_url": sr.edit_url}


@shared_task
def task_kickoff_chain(sr_id: int):
    flow = chain(
        task_generate_script.si(sr_id),
        task_render_avatar.si(sr_id),
        task_assemble_template.si(sr_id),
        task_push_drive.si(sr_id),
        task_generate_captions.si(sr_id),
        task_sync_airtable.si(sr_id),
        task_schedule.si(sr_id),
    )
    flow.delay()
    return {"pipeline": "queued", "sr_id": sr_id}
