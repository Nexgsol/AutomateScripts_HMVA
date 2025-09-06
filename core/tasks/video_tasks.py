# tasks.py
from __future__ import annotations
import os
import requests
from celery import shared_task
from requests import HTTPError
from django.utils import timezone

from core.models import ScriptRequest
from core.adapters import avatar_heygen
from core.adapters import tts_elevenlabs  # your existing 11L wrapper


def _resolve_character_and_voice(avatar_id: str, heygen_voice_id: str | None):
    """
    Use /v2/avatar/{id}/details to determine:
      - character_type: "avatar" or "talking_photo"
      - look_id: same avatar_id you passed
      - picked_voice: explicit heygen_voice_id or default from avatar
    """
    info = avatar_heygen.get_avatar_info(avatar_id)
    ctype = "avatar" if info.get("type") == "avatar" else "talking_photo"
    picked = heygen_voice_id or info.get("default_voice_id") or None
    return ctype, avatar_id, picked


@shared_task
def task_render_heygen_tts(
    sr_id: int,
    avatar_or_group_id: str,
    heygen_voice_id: str | None = None,
    audio_url: str | None = None,          # already-generated audio URL (MP3/WAV)
    audio_path: str | None = None,         # already-generated audio local file
    transcript: str | None = None,         # captions (defaults to final_script)
):
    """
    Render via HeyGen:
    - If audio provided: upload → render from audio.
    - Else try HeyGen TTS → render from text.
    - On HTTPError from HeyGen TTS, fallback to ElevenLabs → upload → render.
    """
    sr = ScriptRequest.objects.get(id=sr_id)

    # Ensure we have a script
    if not sr.final_script:
        # OPTIONAL: generate a script here if your pipeline requires
        sr.final_script = sr.draft_script or ""
        sr.status = "Drafted"
        sr.save()

    transcript_text = transcript or sr.final_script

    # Decide character & voice
    character_type, look_id, picked_voice = _resolve_character_and_voice(avatar_or_group_id, heygen_voice_id)

    # --------------------------
    # PATH A: PRE-GENERATED AUDIO
    # --------------------------
    try:
        audio_asset_id = None
        if audio_path and os.path.exists(audio_path):
            with open(audio_path, "rb") as f:
                audio_asset_id = avatar_heygen.upload_audio_asset(
                    f.read(), filename=os.path.basename(audio_path)
                )
        elif audio_url:
            # keep as a secondary option if you truly need URL fetching
            audio_asset_id = avatar_heygen.upload_audio_asset_from_url(audio_url)

        if audio_asset_id:
            if character_type == "avatar":
                video_id = avatar_heygen.create_avatar_video_from_audio(
                    avatar_id=look_id,
                    audio_asset_id=audio_asset_id,
                    title=f"{sr.icon_or_topic} · req#{sr.id}",
                    width=1080, height=1920,
                    accept_group_id=False,
                )
            else:
                video_id = avatar_heygen.create_talking_photo_video_from_audio(
                    talking_photo_id=look_id,
                    audio_asset_id=audio_asset_id,
                    title=f"{sr.icon_or_topic} · req#{sr.id}",
                    width=1080, height=1920,
                )
            sr.status = "Queued"
            sr.qc_json = {**(sr.qc_json or {}), "heygen_video_id": video_id}
            sr.updated_at = timezone.now()
            sr.save()
            return {"status": "queued", "video_id": video_id}
    except Exception as e:
        sr.qc_json = {**(sr.qc_json or {}), "audio_pipeline_error": str(e)}
        sr.save()

    # ----------------------------------
    # PATH B: HEYGEN TTS (TEXT -> VOICE)
    # ----------------------------------
    try:
        if character_type == "avatar":
            video_id = avatar_heygen.create_avatar_video_from_text(
                avatar_id=look_id,
                input_text=sr.final_script,  # plain text
                voice_id=picked_voice,       # HeyGen voice id (can be ElevenLabs-backed)
                title=f"{sr.icon_or_topic} · req#{sr.id}",
                width=1080, height=1920,
                accept_group_id=False,
            )
        else:
            video_id = avatar_heygen.create_talking_photo_video_from_text(
                talking_photo_id=look_id,
                input_text=sr.final_script,
                voice_id=picked_voice,
                title=f"{sr.icon_or_topic} · req#{sr.id}",
                width=1080, height=1920,
            )
    except HTTPError:
        # -------------------------------------------------------------
        # PATH C: FALLBACK ElevenLabs TTS -> upload audio -> render
        # -------------------------------------------------------------
        el_voice = getattr(getattr(sr, "avatar", None), "elevenlabs_voice_id", None) or getattr(sr, "elevenlabs_voice_id", None)

        # synthesize bytes from TEXT (or support SSML if your wrapper allows)
        mp3_bytes = tts_elevenlabs.synthesize_tts_bytes(
            text_or_ssml=sr.final_script,
            voice_id=el_voice,
            input_format="text",           # use "ssml" if you pass SSML
            output_format="mp3_44100_128",
        )
        audio_asset_id = avatar_heygen.upload_audio_asset(mp3_bytes, filename=f"sr_{sr.id}.mp3")

        if character_type == "avatar":
            video_id = avatar_heygen.create_avatar_video_from_audio(
                avatar_id=look_id,
                audio_asset_id=audio_asset_id,
                title=f"{sr.icon_or_topic} · req#{sr.id}",
                width=1080, height=1920,
                accept_group_id=False,
            )
        else:
            video_id = avatar_heygen.create_talking_photo_video_from_audio(
                talking_photo_id=look_id,
                audio_asset_id=audio_asset_id,
                title=f"{sr.icon_or_topic} · req#{sr.id}",
                width=1080, height=1920,
            )

    # --------------------------
    # Wait + persist (shared)
    # --------------------------
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
