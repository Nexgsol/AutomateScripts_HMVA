from celery import shared_task
from django.utils import timezone
from django.conf import settings
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
    mp3 = tts_elevenlabs.synthesize_bytes(sr.final_script, sr.avatar.elevenlabs_voice_id)
    audio_asset_id = avatar_heygen.upload_audio_asset(mp3)
    video_id = avatar_heygen.create_avatar_video(sr.avatar.heygen_avatar_id, audio_asset_id,
                                                 title=f"{sr.icon_or_topic} · req#{sr.id}", width=1080, height=1920)
    status = avatar_heygen.wait_for_video(video_id, timeout_sec=900, poll_sec=10)
    if status.get("status") != "completed":
        sr.status = "Assembling"
        sr.qc_json = {**(sr.qc_json or {}), "heygen_status": status}
        sr.save()
        return status
    video_url = status.get("video_url","")
    share_url = avatar_heygen.get_share_url(video_id) or ""
    sr.asset_url = video_url
    sr.edit_url = share_url
    sr.status = "Rendered"
    sr.updated_at = timezone.now()
    sr.save()
    return {"video_url": video_url, "share_url": share_url}

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


@shared_task
def task_kickoff_chain(sr_id: int):
    """
    Full auto pipeline: script -> avatar -> assemble -> Drive -> captions -> Airtable -> schedule
    """
    flow = chain(
        task_generate_script.s(sr_id),
        task_render_avatar.s(sr_id),
        task_assemble_template.s(sr_id),
        task_push_drive.s(sr_id),
        task_generate_captions.s(sr_id),
        task_sync_airtable.s(sr_id),
        task_schedule.s(sr_id),
    )
    flow.delay()
    return {"pipeline": "queued", "sr_id": sr_id}