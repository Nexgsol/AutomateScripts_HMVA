# core/services/tts_service.py
import hashlib, json
from django.core.files.base import ContentFile
from django.db import transaction
from ..models import TTSAudio
from ..adapters import tts_elevenlabs

def _hash_text(text: str, voice_id: str, settings: dict | None) -> str:
    key = json.dumps({"text": text, "voice": voice_id, "settings": settings or {}}, sort_keys=True)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

@transaction.atomic
def fetch_or_create_tts_audio(*, voice_id: str, text: str, settings: dict | None = None, attach_history: bool = True) -> TTSAudio:
    """
    Returns a TTSAudio row. If the same (voice,text,settings) exists, re-uses it.
    Otherwise generates MP3 via ElevenLabs and stores it, then (optionally) links to a history item.
    """
    settings = settings or {}
    thash = _hash_text(text, voice_id, settings)

    try:
        return TTSAudio.objects.select_for_update().get(text_hash=thash, voice_id=voice_id)
    except TTSAudio.DoesNotExist:
        pass

    # Generate MP3 bytes via ElevenLabs
    mp3 = tts_elevenlabs.synthesize_bytes(
        text=text,
        voice_id=voice_id,
        stability=settings.get("stability", 0.5),
        similarity_boost=settings.get("similarity_boost", 0.75),
    )

    rec = TTSAudio.objects.create(
        voice_id=voice_id,
        text_hash=thash,
        text_excerpt=text[:200],
        settings=settings,
    )
    rec.file.save(f"{thash[:16]}.mp3", ContentFile(mp3))
    rec.save()

    if attach_history:
        hid = tts_elevenlabs.find_history_item_id(voice_id, text)
        if hid:
            rec.eleven_history_id = hid
            rec.save(update_fields=["eleven_history_id"])

    return rec

def load_audio_bytes(rec: TTSAudio) -> bytes:
    rec.file.open("rb")
    try:
        return rec.file.read()
    finally:
        rec.file.close()
