# core/adapters/avatar_heygen.py
import os
import time
import requests
from typing import Dict, Any, Optional

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
API_BASE = "https://api.heygen.com"
UPLOAD_BASE = "https://upload.heygen.com"

class HeyGenError(Exception):
    pass

def _require_key():
    if not HEYGEN_API_KEY:
        raise HeyGenError("HEYGEN_API_KEY is not set.")

def _json_post(url: str, payload: Dict[str, Any], timeout: int = 180) -> Dict[str, Any]:
    _require_key()
    r = requests.post(
        url,
        headers={"X-Api-Key": HEYGEN_API_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        raise HeyGenError(f"POST {url} failed: {e} | body={r.text[:500]}") from e
    data = r.json() if r.content else {}
    return data

def _bin_post(url: str, data: bytes, content_type: str, timeout: int = 180) -> Dict[str, Any]:
    _require_key()
    r = requests.post(
        url,
        headers={"X-Api-Key": HEYGEN_API_KEY, "Content-Type": content_type},
        data=data,
        timeout=timeout,
    )
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        raise HeyGenError(f"POST {url} (binary) failed: {e} | body={r.text[:500]}") from e
    return r.json() if r.content else {}

def _json_get(url: str, params: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    _require_key()
    r = requests.get(url, headers={"X-Api-Key": HEYGEN_API_KEY}, params=params, timeout=timeout)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        raise HeyGenError(f"GET {url} failed: {e} | body={r.text[:500]}") from e
    return r.json() if r.content else {}

# ---------- Public API ----------

def upload_audio_asset(mp3_bytes: bytes) -> str:
    """
    Upload an MP3 to HeyGen's asset store. Returns asset_id.
    """
    res = _bin_post(f"{UPLOAD_BASE}/v1/asset", mp3_bytes, content_type="audio/mpeg", timeout=180)
    asset_id = (res.get("data") or {}).get("id", "")
    if not asset_id:
        raise HeyGenError(f"Upload returned no asset_id: {res}")
    return asset_id

def create_avatar_video(
    avatar_id: str,
    audio_asset_id: str,
    title: str = "",
    width: int = 1080,
    height: int = 1920,
    background_color: str = "#000000",
) -> str:
    """
    Start an avatar render job. Returns video_id.
    """
    payload = {
        "title": title or "Heritage Reel",
        "video_inputs": [
            {
                "character": {"type": "avatar", "avatar_id": avatar_id, "avatar_style": "normal"},
                "voice": {"type": "audio", "audio_asset_id": audio_asset_id},
                "background": {"type": "color", "value": background_color},
            }
        ],
        "dimension": {"width": width, "height": height},
    }
    res = _json_post(f"{API_BASE}/v2/video/generate", payload, timeout=180)
    video_id = (res.get("data") or {}).get("video_id", "")
    if not video_id:
        raise HeyGenError(f"Generate returned no video_id: {res}")
    return video_id

def get_video_status(video_id: str) -> Dict[str, Any]:
    """
    Query job status. Returns dict with at least 'status' and optionally 'video_url'.
    """
    res = _json_get(f"{API_BASE}/v1/video_status.get", params={"video_id": video_id}, timeout=60)
    data = res.get("data") or {}
    if not data:
        # some responses put fields at root; handle gracefully
        data = res
    return data

def wait_for_video(video_id: str, timeout_sec: int = 900, poll_sec: int = 10) -> Dict[str, Any]:
    """
    Poll until 'completed' or 'failed' or timeout.
    Returns the final status dict.
    """
    start = time.time()
    while time.time() - start < timeout_sec:
        data = get_video_status(video_id)
        status = str(data.get("status", "")).lower()
        if status in ("completed", "failed"):
            return data
        time.sleep(poll_sec)
    return {"status": "timeout", "video_id": video_id}

def get_share_url(video_id: str) -> str:
    """
    Request a public share URL for the rendered video.
    """
    res = _json_post(f"{API_BASE}/v1/video/share", {"video_id": video_id}, timeout=60)
    return (res.get("data") or {}).get("share_url", "")

# ---------- Convenience: one-call flow ----------

def generate_from_audio_bytes(
    avatar_id: str,
    mp3_bytes: bytes,
    *,
    title: Optional[str] = None,
    width: int = 1080,
    height: int = 1920,
    background_color: str = "#000000",
    wait_timeout_sec: int = 900,
    poll_sec: int = 10,
) -> Dict[str, Any]:
    """
    Convenience function:
    1) Upload MP3 bytes to Assets -> audio_asset_id
    2) create_avatar_video(...)
    3) wait_for_video(...)
    4) request share URL
    Returns: {"video_id","status","video_url","share_url"}
    """
    asset_id = upload_audio_asset(mp3_bytes)
    video_id = create_avatar_video(
        avatar_id=avatar_id,
        audio_asset_id=asset_id,
        title=title or "Heritage Reel",
        width=width,
        height=height,
        background_color=background_color,
    )
    final = wait_for_video(video_id, timeout_sec=wait_timeout_sec, poll_sec=poll_sec)
    out = {"video_id": video_id, "status": final.get("status", "")}
    if final.get("status") == "completed":
        out["video_url"] = final.get("video_url", "")
        # best-effort share URL (optional)
        try:
            out["share_url"] = get_share_url(video_id)
        except Exception:
            out["share_url"] = ""
    else:
        out["video_url"] = ""
        out["share_url"] = ""
    return out
