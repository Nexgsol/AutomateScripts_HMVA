import os, requests
import json
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVEN_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")


def list_history(page_size: int = 50) -> dict:
    if not ELEVEN_API_KEY:
        return {}
    url = f"https://api.elevenlabs.io/v1/history?per_page={page_size}"
    r = requests.get(url, headers={"xi-api-key": ELEVEN_API_KEY}, timeout=60)
    r.raise_for_status()
    return r.json()


def find_history_item_id(voice_id: str, text: str, page_size: int = 50) -> str:
    """
    Best-effort: scan recent history and try to match by voice_id and text snippet.
    """
    data = list_history(page_size)
    items = data.get("history") or data.get("items") or []
    key = (text or "").strip()[:60]
    for it in items:
        if str(it.get("voice_id")) == str(voice_id):
            t = it.get("text") or ""
            if key and key in t:
                return it.get("history_item_id") or it.get("id") or ""
    return ""

