import os, json, requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# (Optional) keep a tiny allowlist to avoid typos in env
_ALLOWED_MODELS = {
    "gpt-4o-mini",
    "gpt-4o",           # if you use the larger model
    "gpt-4.1-mini",     # if enabled for your account
}

def _pick_model(name: str) -> str:
    return name if name in _ALLOWED_MODELS else "gpt-4o-mini"

def chat(system: str, user: str, temperature: float = 0.5) -> str:
    """
    Returns the assistant message content (expected JSON string because of response_format).
    Raises a RuntimeError that includes the API's error message on 4xx/5xx.
    """
    # Local fallback when no key present (your original stub)
    if not OPENAI_API_KEY:
        return json.dumps({
            "paragraph": (
                "This icon shaped menswear with rugged simplicity. Signature pieces included a Harrington jacket, "
                "slim chinos, desert boots, and often Persol sunglasses. Across film sets and city streets, "
                "his wardrobe adapted without losing its edge. His legacy anchors modern heritage style."
            ),
            "ssml": (
                '<speak><prosody rate="medium">'
                'This icon shaped menswear with rugged simplicity. '
                '<break time="300ms"/> Signature pieces included a Harrington jacket, slim chinos, desert boots, '
                'and often Persol sunglasses. <break time="240ms"/> Across film sets and city streets, his wardrobe '
                'adapted without losing its edge. His legacy anchors modern heritage style.'
                '<mark name="END"/></prosody></speak>'
            )
        })

    payload = {
        "model": _pick_model(OPENAI_MODEL),
        "temperature": float(temperature),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "response_format": {"type": "json_object"},
    }

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Network error calling OpenAI: {e}") from e

    # If it fails, show the API's message so you know exactly what's wrong
    if r.status_code >= 400:
        try:
            err = r.json().get("error", {})
            msg = err.get("message") or r.text
        except Exception:
            msg = r.text
        raise RuntimeError(f"OpenAI API error {r.status_code}: {msg}")

    data = r.json()
    # Defensive: ensure choices/message/content exist
    try:
        content = (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"Unexpected OpenAI response shape: {json.dumps(data)[:500]}")

    return content
