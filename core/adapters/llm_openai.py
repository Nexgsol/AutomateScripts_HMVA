import os, json, re, requests
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")
OPENAI_MODEL = os.getenv("OPENAI_MODEL","gpt-4o-mini")

def chat(system: str, user: str, temperature: float = 0.5) -> str:
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
        "model": OPENAI_MODEL,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"}
    }

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json=payload,
        timeout=120
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"].strip()
    return content
