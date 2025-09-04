# core/adapters/avatar_heygen.py

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import os
import time
import requests

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
API_BASE = "https://api.heygen.com"
UPLOAD_BASE = "https://upload.heygen.com"


# -------------------- helpers --------------------

class HeyGenError(Exception):
    pass


def _headers(as_json: bool = False) -> Dict[str, str]:
    h = {"X-Api-Key": HEYGEN_API_KEY}
    if as_json:
        h["Content-Type"] = "application/json"
    return h


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
        # dump helpful info to worker logs
        print("[HeyGen ERROR]", r.status_code, url)
        print("[HeyGen ERROR body]", body)
        print("[HeyGen ERROR payload]", payload)
        r.raise_for_status()
    return r.json() or {}


# -------------------- list avatars (looks & groups) --------------------

def list_group_looks(group_id: str) -> List[Dict[str, Any]]:
    """
    GET /v2/avatar_group/{group_id}/avatars
    Normalizes to items that have a concrete renderable avatar_id.
    """
    if not (HEYGEN_API_KEY and group_id):
        return []
    url = f"{API_BASE}/v2/avatar_group/{group_id}/avatars"
    j = _json_get(url)
    data = j.get("data") or {}
    looks = data.get("avatar_list") or []
    out: List[Dict[str, Any]] = []
    for a in looks:
        out.append({
            "avatar_id": a.get("id", ""),
            "name": a.get("name", ""),
            "preview_image": a.get("motion_preview_url") or a.get("image_url") or "",
            "image_url": a.get("image_url", ""),
            "motion_preview_url": a.get("motion_preview_url", ""),
            "group_id": a.get("group_id", group_id),
            "is_motion": bool(a.get("is_motion")),
            "default_voice_id": a.get("default_voice_id", ""),
            "created_at": a.get("created_at"),
        })
    return out

def list_avatars(include_public: bool = False, group_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Always return renderable LOOK avatars (avatar_id), flattened across groups.

    [
      {
        "type": "look",
        "id": "<avatar_id>",
        "avatar_id": "<avatar_id>",
        "name": "...",
        "preview_image": "...",
        "group_id": "<group_id>",
        "is_motion": true/false,
        "default_voice_id": "..."
      }, ...
    ]
    """
    if not HEYGEN_API_KEY:
        return []

    # First call: list groups (and capture any tenants that already include avatar_list at top level)
    j = _json_get(f"{API_BASE}/v2/avatar_group.list", params={"include_public": str(include_public).lower()})
    data = j.get("data") or {}

    def _norm_from_direct(a: Dict[str, Any]) -> Dict[str, Any]:
        # Some tenants place looks directly on avatar_group.list -> data.avatar_list
        return {
            "type": "look",
            "id": a.get("id", ""),
            "avatar_id": a.get("id", ""),
            "name": a.get("name", ""),
            "preview_image": a.get("motion_preview_url") or a.get("image_url") or "",
            "group_id": a.get("group_id", ""),
            "is_motion": bool(a.get("is_motion")),
            "default_voice_id": a.get("default_voice_id", ""),
        }

    out: List[Dict[str, Any]] = []
    seen: set = set()

    # If direct looks are present, include them
    direct_looks = data.get("avatar_list") or []
    for a in direct_looks:
        vid = a.get("id", "")
        if vid and vid not in seen:
            out.append(_norm_from_direct(a))
            seen.add(vid)

    # Determine which groups to expand
    groups_src = group_ids if group_ids is not None else [
        g.get("id", "") for g in (data.get("avatar_group_list") or []) if g.get("id")
    ]

    # Expand each group into its looks and append
    for gid in groups_src:
        looks = list_group_looks(gid)
        for lk in looks:
            vid = lk.get("avatar_id", "")
            if not vid or vid in seen:
                continue
            out.append({
                "type": "look",
                "id": vid,
                "avatar_id": vid,
                "name": lk.get("name", ""),
                "preview_image": lk.get("preview_image", "") or lk.get("image_url", ""),
                "group_id": lk.get("group_id", gid),
                "is_motion": bool(lk.get("is_motion")),
                "default_voice_id": lk.get("default_voice_id", ""),
            })
            seen.add(vid)

    return out
# -------------------- list voices --------------------

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


# -------------------- group → looks (renderable avatar_id) --------------------

def get_avatar_group(group_id: str) -> Dict[str, Any]:
    """
    Builds a lightweight group summary by filtering /v2/avatar_group.list (look-level).
    """
    if not HEYGEN_API_KEY:
        return {}

    url = f"{API_BASE}/v2/avatar_group.list"
    j = _json_get(url, params={"include_public": "false"}) or {}
    data = j.get("data") or {}
    all_looks = data.get("avatar_list") or []

    looks = [a for a in all_looks if a.get("group_id") == group_id]
    if not looks:
        return {"id": group_id, "looks_count": 0}

    first = looks[0]
    preview_image = first.get("motion_preview_url") or first.get("image_url") or ""
    # Prefer the first look’s default voice (simple, predictable)
    default_voice_id = first.get("default_voice_id") or None

    return {
        "id": group_id,
        "looks_count": len(looks),
        "preview_image": preview_image,
        "default_voice_id": default_voice_id,
        "name": first.get("name", ""),
    }




def resolve_avatar_id(group_or_avatar_id: str) -> Tuple[str, Optional[str]]:
    """
    Accepts either a look avatar_id (returns it) OR a group_id (returns first look's avatar_id).
    Returns (avatar_id, default_voice_id).
    """
    if not group_or_avatar_id:
        return "", None
    looks = list_group_looks(group_or_avatar_id)
    if looks:
        first = looks[0]
        return first.get("avatar_id", ""), first.get("default_voice_id") or None
    # assume already a look id
    return group_or_avatar_id, None


# -------------------- audio upload --------------------

def upload_audio_asset(mp3_bytes: bytes) -> str:
    if not HEYGEN_API_KEY:
        return "asset_stub_audio"
    url = f"{UPLOAD_BASE}/v1/asset"
    headers = {"X-Api-Key": HEYGEN_API_KEY, "Content-Type": "audio/mpeg"}
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


# -------------------- video creation (audio OR text) --------------------

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

    # Resolve group → look id if allowed
    final_avatar_id, default_voice = resolve_avatar_id(avatar_id) if accept_group_id else (avatar_id, None)

    # Voice block
    if audio_asset_id:
        voice_block: Dict[str, Any] = {"type": "audio", "audio_asset_id": audio_asset_id}
    else:
        voice_block = {"type": "text", "input_text": input_text}
        if voice_id or default_voice:
            voice_block["voice_id"] = voice_id or default_voice

    # Background
    background = {"type": "image", "image_url": background_image_url} if background_image_url else {"type": "color", "value": background_color}

    payload = {
        "title": title or "Heritage Reel",
        "video_inputs": [{
            "character": {"type": "avatar", "avatar_id": final_avatar_id, "avatar_style": avatar_style},
            "voice": voice_block,
            "background": background,
        }],
        "dimension": {"width": width, "height": height},
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


# -------------------- status & share --------------------

def get_video_status(video_id: str) -> dict:
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
