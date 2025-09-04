# core/adapters/tts_elevenlabs.py
from __future__ import annotations
import os, requests
from typing import Optional, Dict, Any

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_DEFAULT_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # public sample voice
DEFAULT_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_monolingual_v1")

def _headers() -> Dict[str, str]:
    if not ELEVENLABS_API_KEY:
        return {}
    return {
        "xi-api-key": ELEVENLABS_API_KEY,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }

def synthesize_bytes(
    text: str,
    voice_id: Optional[str] = None,
    *,
    model_id: Optional[str] = None,
    stability: float = 0.35,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    use_speaker_boost: bool = True,
) -> bytes:
    """
    Returns MP3 bytes from ElevenLabs TTS. Raises on error.
    """
    if not text:
        raise ValueError("text is required")
    vid = voice_id or DEFAULT_VOICE_ID
    mid = model_id or DEFAULT_MODEL_ID

    if not ELEVENLABS_API_KEY:
        # Dev stub: small silent mp3 blob would be ideal; instead, fail loudly
        raise RuntimeError("ELEVENLABS_API_KEY not set")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
    payload = {
        "text": text,
        "model_id": mid,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost,
        },
    }
    r = requests.post(url, headers=_headers(), json=payload, timeout=180)
    if r.status_code >= 400:
        try:
            body = r.json()
        except Exception:
            body = r.text
        print("[ElevenLabs ERROR]", r.status_code, url)
        print("[ElevenLabs ERROR body]", body)
        r.raise_for_status()
    return r.content


def synthesize_tts_bytes(text: str, voice_id: str | None) -> bytes:
    """
    Return MP3 bytes for the provided text with ElevenLabs.
    Your previous function was likely named `synthesize_bytes`; rename or alias it.
    """
    mp3_bytes = synthesize_bytes(text, voice_id=voice_id)
    return mp3_bytes
  