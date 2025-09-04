import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def build_prompt(content, niche, tone, target_audience, duration_sec, language):
    return f"""
You are a social media growth director specialized in short-form video.

TASK:
Given the user's CONTENT, craft:
1) High-signal TAGS (topic labels, not hashtags).
2) Popular HASHTAGS (≤15, prefixed with #).
3) A FULL REEL SCRIPT with hook, beats, CTA, captions, posting tips.

OUTPUT JSON schema:
{{
  "meta": {{
    "language": "string",
    "niche": "string",
    "tone": "string",
    "targetAudience": "string",
    "estimatedDurationSec": number
  }},
  "tags": ["string"],
  "hashtags": ["#string"],
  "script": {{
    "title": "string",
    "beats": [
      {{
        "t": "0-2s",
        "role": "hook|setup|value|demo|proof|reframe|cta|outro",
        "voiceover": "string",
        "onScreenText": "string",
        "shotIdea": "string",
        "brollIdeas": ["string"],
        "patternBreak": "string",
        "sfxOrMusic": "string"
      }}
    ],
    "cta": "string",
    "caption": "string",
    "postingTips": ["string"]
  }}
}}

RULES:
- Keep writing in {language or 'en'}.
- Hook must be thumb-stopping.
- Beats should cover ~{duration_sec} seconds.
- No fluff.

USER CONTENT: \"\"\"{content}\"\"\"
NICHE: \"\"\"{niche}\"\"\"
TONE: \"\"\"{tone}\"\"\"
AUDIENCE: \"\"\"{target_audience}\"\"\"
"""

@app.post("/generate-reel")
async def generate_reel(req: Request):
    body = await req.json()
    content = body.get("content")
    if not content or not content.strip():
        return JSONResponse({"error": "Provide non-empty content"}, status_code=400)
    niche = body.get("niche", "")
    tone = body.get("tone", "energetic")
    target_audience = body.get("targetAudience", "")
    duration_sec = body.get("durationSec", 30)
    language = body.get("language", "en")
    prompt = build_prompt(content, niche, tone, target_audience, duration_sec, language)
    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
        temperature=0.7,
        max_output_tokens=1200,
        response_format={"type": "json_object"}
    )
    text = response.output_text or response.output[0].content[0].text
    try:
        data = json.loads(text)
    except:
        match = None
        import re
        m = re.search(r"\{[\s\S]*\}$", text)
        if m:
            data = json.loads(m.group(0))
        else:
            return JSONResponse({"error": "Invalid JSON"}, status_code=500)
    return {"ok": True, "data": data}

@app.get("/")
async def root():
    return {"status": "Reels generator running"}