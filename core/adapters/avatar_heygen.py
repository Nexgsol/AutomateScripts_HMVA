# core/adapters/avatar_heygen.py
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import os
import time
import requests

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
API_BASE = "https://api.heygen.com"
UPLOAD_BASE = "https://upload.heygen.com"


# -------------------- Errors & Headers --------------------

class HeyGenError(Exception):
    pass


def _headers(as_json: bool = False) -> Dict[str, str]:
    h = {"X-Api-Key": HEYGEN_API_KEY}
    if as_json:
        h["Content-Type"] = "application/json"
    return h


# -------------------- HTTP helpers --------------------

def _json_get(url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 60) -> Dict[str, Any]:
    if not HEYGEN_API_KEY:
        return {}
    r = requests.get(url, headers=_headers(False), params=params or {}, timeout=timeout)
    r.raise_for_status()
    try:
        return r.json() or {}
    except Exception:
        return {}


def _json_post(url: str, payload: Dict[str, Any], timeout: int = 180) -> Dict[str, Any]:
    if not HEYGEN_API_KEY:
        return {}
    r = requests.post(url, headers=_headers(True), json=payload, timeout=timeout)
    if r.status_code >= 400:
        try:
            body = r.json()
        except Exception:
            body = r.text
        print("[HeyGen ERROR]", r.status_code, url)
        print("[HeyGen ERROR body]", body)
        print("[HeyGen ERROR payload]", payload)
        r.raise_for_status()
    return r.json() or {}


# -------------------- Voices & Avatars --------------------

def list_voices() -> List[Dict[str, Any]]:
    """
    Normalized voice list for the UI.
    """
    if not HEYGEN_API_KEY:
        return []
    url = f"{API_BASE}/v2/voices"
    j = _json_get(url) or {}
    data = j.get("data") or {}
    raw = data.get("voices") or j.get("voices") or []
    out: List[Dict[str, Any]] = []
    for v in raw:
        vid = v.get("voice_id") or v.get("id") or ""
        out.append({
            "id": vid,
            "voice_id": vid,
            "name": v.get("name", ""),
            "language": (v.get("language") or "") or "",
            "gender": (v.get("gender") or "") or "",
            "preview_audio": v.get("preview_audio"),
            "support_pause": bool(v.get("support_pause")),
            "emotion_support": bool(v.get("emotion_support")),
            "support_interactive_avatar": bool(v.get("support_interactive_avatar")),
            "support_locale": bool(v.get("support_locale")),
        })
    return out


def list_group_looks(group_id: str) -> List[Dict[str, Any]]:
    """
    GET /v2/avatar_group/<group_id>/avatars
    Normalizes each look:
    {
      "avatar_id": "...",
      "name": "...",
      "preview_image": "...",
      "group_id": "...",
      "is_motion": bool,
      "default_voice_id": "..."
    }
    """
    if not HEYGEN_API_KEY:
        return []
    url = f"{API_BASE}/v2/avatar_group/{group_id}/avatars"
    try:
        j = _json_get(url)
    except Exception:
        return []
    items = (j.get("data") or {}).get("avatar_list") or []
    out: List[Dict[str, Any]] = []
    for a in items:
        out.append({
            "avatar_id": a.get("id", ""),
            "name": a.get("name", ""),
            "preview_image": a.get("motion_preview_url") or a.get("image_url") or "",
            "group_id": a.get("group_id", group_id),
            "is_motion": bool(a.get("is_motion")),
            "default_voice_id": a.get("default_voice_id", ""),
        })
    return out


def list_avatars(include_public: bool = False, group_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Always return renderable LOOK avatars (avatar_id), flattened across groups.
    """
    if not HEYGEN_API_KEY:
        return []

    j = _json_get(f"{API_BASE}/v2/avatar_group.list", params={"include_public": str(include_public).lower()})
    data = j.get("data") or {}

    out: List[Dict[str, Any]] = []
    seen: set[str] = set()

    # Some tenants expose looks directly here
    direct = data.get("avatar_list") or []
    for a in direct:
        vid = a.get("id")
        if not vid or vid in seen:
            continue
        out.append({
            "type": "look",
            "id": vid,
            "avatar_id": vid,
            "name": a.get("name", ""),
            "preview_image": a.get("motion_preview_url") or a.get("image_url") or "",
            "group_id": a.get("group_id", ""),
            "is_motion": bool(a.get("is_motion")),
            "default_voice_id": a.get("default_voice_id", ""),
        })
        seen.add(vid)

    # Otherwise expand groups -> looks
    groups_src = group_ids if group_ids is not None else [
        g.get("id", "") for g in (data.get("avatar_group_list") or []) if g.get("id")
    ]
    for gid in groups_src:
        for lk in list_group_looks(gid):
            vid = lk.get("avatar_id", "")
            if not vid or vid in seen:
                continue
            out.append({
                "type": "look",
                "id": vid,
                "avatar_id": vid,
                "name": lk.get("name", ""),
                "preview_image": lk.get("preview_image", ""),
                "group_id": lk.get("group_id", gid),
                "is_motion": bool(lk.get("is_motion")),
                "default_voice_id": lk.get("default_voice_id", ""),
            })
            seen.add(vid)

    return out


# core/adapters/avatar_heygen.py

def get_avatar_info(avatar_id: str) -> Dict[str, Any]:
    """
    Fetch avatar/talking_photo detail.
    Returns a minimal dict: { "avatar_id", "type", "default_voice_id", "name", ... }
    """
    if not HEYGEN_API_KEY:
        # fallback stub
        return {"avatar_id": avatar_id, "type": "avatar", "default_voice_id": None}

    url = f"{API_BASE}/v2/avatar/{avatar_id}/details"
    j = _json_get(url) or {}
    d = (j.get("data") or {}) if isinstance(j, dict) else {}

    # Normalize fields
    return {
        "avatar_id": d.get("id") or avatar_id,
        "type": d.get("type") or "avatar",  # "avatar" | "talking_photo"
        "name": d.get("name"),
        "default_voice_id": d.get("default_voice_id"),
        "preview_image_url": d.get("preview_image_url") or d.get("image_url"),
        "preview_video_url": d.get("preview_video_url") or d.get("motion_preview_url"),
        "is_public": d.get("is_public"),
        "premium": d.get("premium"),
    }


def resolve_avatar_id(avatar_or_group_id: str) -> Tuple[str, Optional[str]]:
    """
    If a group id is provided, resolve to the first look in that group.
    Returns (avatar_id, default_voice_id)
    """
    aid = avatar_or_group_id
    # crude heuristic (many group ids are 32 hex chars)
    if len(aid) == 32:
        looks = list_group_looks(aid)
        if looks:
            first = looks[0]
            return first["avatar_id"], first.get("default_voice_id") or None
    return aid, None


# -------------------- Audio Upload --------------------

def upload_audio_asset(mp3_bytes: bytes, filename: Optional[str] = None, content_type: str = "audio/mpeg") -> str:
    """
    Upload raw audio bytes to HeyGen asset storage.
    Returns: audio asset id (str).
    """
    if not HEYGEN_API_KEY:
        return "asset_stub_audio"
    url = f"{UPLOAD_BASE}/v1/asset"
    headers = {"X-Api-Key": HEYGEN_API_KEY, "Content-Type": content_type}
    if filename:
        headers["Content-Disposition"] = f'inline; filename="{filename}"'
    r = requests.post(url, headers=headers, data=mp3_bytes, timeout=180)
    if r.status_code >= 400:
        try:
            body = r.json()
        except Exception:
            body = r.text
        print("[HeyGen AUDIO ERROR]", r.status_code, url)
        print("[HeyGen AUDIO body]", body)
        r.raise_for_status()
    return (r.json().get("data") or {}).get("id", "")


def upload_audio_asset_from_url(audio_url: str, filename: Optional[str] = None, timeout: int = 180) -> str:
    """
    Downloads audio from a URL and uploads it as an asset.
    Returns: audio asset id (str).
    """
    if not HEYGEN_API_KEY:
        return "asset_stub_audio"

    dr = requests.get(audio_url, stream=True, timeout=timeout)
    dr.raise_for_status()
    chunks = []
    for chunk in dr.iter_content(8192):
        if chunk:
            chunks.append(chunk)
    data = b"".join(chunks)

    ct = dr.headers.get("Content-Type", "audio/mpeg")
    if not filename:
        try:
            filename = os.path.basename(audio_url.split("?", 1)[0]) or "audio.mp3"
        except Exception:
            filename = "audio.mp3"

    return upload_audio_asset(data, filename=filename, content_type=ct)


# -------------------- Video Creation (avatar/talking_photo) --------------------

def create_avatar_video(
    avatar_id: str,
    *,
    audio_asset_id: Optional[str] = None,   # provide for "audio" mode
    input_text: Optional[str] = None,       # provide for "TTS" mode
    voice_id: Optional[str] = None,         # optional TTS voice
    title: str = "Heritage Reel",
    width: int = 1080,
    height: int = 1920,
    background_color: str = "#000000",
    background_image_url: Optional[str] = None,
    avatar_style: str = "normal",
    accept_group_id: bool = True,           # resolve group → first look
) -> str:
    """
    Create a HeyGen avatar video using either uploaded audio or text-to-speech.
    Returns video_id (str).
    """
    if not HEYGEN_API_KEY:
        return "video_stub_123"
    if not avatar_id:
        raise ValueError("avatar_id (or group id) is required")
    if not (audio_asset_id or input_text):
        raise ValueError("Provide either audio_asset_id (audio mode) or input_text (TTS mode).")

    final_avatar_id, default_voice = resolve_avatar_id(avatar_id) if accept_group_id else (avatar_id, None)

    if audio_asset_id:
        voice_block: Dict[str, Any] = {"type": "audio", "audio_asset_id": audio_asset_id}
    else:
        voice_block = {"type": "text", "input_text": input_text}
        if voice_id or default_voice:
            voice_block["voice_id"] = voice_id or default_voice

    background = {"type": "image", "image_url": background_image_url} if background_image_url else {"type": "color", "value": background_color}

    payload = {
        "title": title or "Heritage Reel",
        "video_inputs": [{
            "character": {"type": "avatar", "avatar_id": final_avatar_id, "avatar_style": avatar_style},
            "voice": voice_block,
            "background": background,
        }],
        "dimension": {"width": width, "height": height},
        "test": False,
        "callback_id": None,
        "aspect_ratio": None,
    }

    url = f"{API_BASE}/v2/video/generate"
    j = _json_post(url, payload, timeout=180)
    return (j.get("data") or {}).get("video_id", "")


def create_avatar_video_from_audio(
    avatar_id: str,
    audio_asset_id: str,
    **kwargs
) -> str:
    return create_avatar_video(avatar_id, audio_asset_id=audio_asset_id, **kwargs)


def create_avatar_video_from_text(
    avatar_id: str,
    input_text: str,
    voice_id: Optional[str] = None,
    **kwargs
) -> str:
    return create_avatar_video(avatar_id, input_text=input_text, voice_id=voice_id, **kwargs)


def create_talking_photo_video_from_text(
    *,
    talking_photo_id: str,
    input_text: str,
    voice_id: Optional[str] = None,
    title: str = "Heritage Reel",
    width: int = 1080,
    height: int = 1920,
    background_color: str = "#000000",
) -> str:
    payload = {
        "title": title or "Heritage Reel",
        "video_inputs": [
            {
                "character": {"type": "talking_photo", "talking_photo_id": talking_photo_id},
                "voice": {"type": "text", "input_text": input_text, "voice_id": voice_id},
                "background": {"type": "color", "value": background_color},
            }
        ],
        "dimension": {"width": width, "height": height},
        "test": False,
        "callback_id": None,
        "aspect_ratio": None,
    }
    j = _json_post(f"{API_BASE}/v2/video/generate", payload, timeout=180)
    return (j.get("data") or {}).get("video_id", "")


def create_talking_photo_video_from_audio(
    *,
    talking_photo_id: str,
    audio_asset_id: str,
    title: str = "Heritage Reel",
    width: int = 1080,
    height: int = 1920,
    background_color: str = "#00FF00",
) -> str:
    payload = {
        "title": title or "Heritage Reel",
        "video_inputs": [
            {
                "character": {"type": "talking_photo", "talking_photo_id": talking_photo_id},
                "voice": {"type": "audio", "audio_asset_id": audio_asset_id},
                "background": {"type": "color", "value": background_color},
            }
        ],
        "dimension": {"width": width, "height": height},
        "test": False,
        "callback_id": None,
        "aspect_ratio": None,
    }
    j = _json_post(f"{API_BASE}/v2/video/generate", payload, timeout=180)
    return (j.get("data") or {}).get("video_id", "")


# -------------------- Status & Share --------------------

def get_video_status(video_id: str) -> dict:
    """
    v1 status endpoint remains widely used and stable in tenants.
    """
    if not HEYGEN_API_KEY:
        return {"status": "completed", "video_url": "https://example.com/video/avatar.mp4"}
    url = f"{API_BASE}/v1/video_status.get"
    r = requests.get(url, headers=_headers(False), params={"video_id": video_id}, timeout=60)
    r.raise_for_status()
    return r.json().get("data") or {}


def wait_for_video(video_id: str, timeout_sec: int = 900, poll_sec: int = 10) -> dict:
    start = time.time()
    while time.time() - start < timeout_sec:
        data = get_video_status(video_id)
        if data.get("status") in ("completed", "failed"):
            return data
        time.sleep(poll_sec)
    return {"status": "timeout"}


def get_share_url(video_id: str) -> str:
    if not HEYGEN_API_KEY:
        return "https://example.com/share/video_stub_123"
    url = f"{API_BASE}/v1/video/share"
    j = _json_post(url, {"video_id": video_id}, timeout=60)
    return (j.get("data") or {}).get("share_url", "")
