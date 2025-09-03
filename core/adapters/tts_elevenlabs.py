import os, requests
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVEN_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

def synthesize_bytes(text: str, voice_id: str, stability: float=0.5, similarity_boost: float=0.75) -> bytes:
    if not ELEVEN_API_KEY:
        return b"ID3\x03\x00\x00\x00\x00\x00\x21"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVEN_API_KEY, "accept": "audio/mpeg", "Content-Type": "application/json"}
    payload = {"text": text, "model_id": ELEVEN_MODEL,
               "voice_settings":{"stability": stability, "similarity_boost": similarity_boost}}
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    r.raise_for_status()
    return r.content
