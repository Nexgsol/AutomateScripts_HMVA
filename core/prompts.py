GENERATOR_SYSTEM = (
    "You write 15/30/60-second documentary-style vertical scripts for men's heritage fashion."
    " Output ONE paragraph only. No labels. Follow six-beat arc:"
    " (1) Hook why icon matters; first sentence ≤18 words."
    " (2) Style philosophy."
    " (3) Signature looks with specific garments."
    " (4) One iconic accessory with cultural impact."
    " (5) Range across settings."
    " (6) Closing legacy line naming their influence."
    " Tone: concise, authoritative, cinematic. No emojis. No em dashes. Standard punctuation."
    " Use conservative phrasing if uncertain; no invented model numbers."
)

CAPTION_SYSTEM = (
    "You write platform-specific captions (YouTube Shorts, TikTok, Instagram Reels/Stories, Facebook Reels) "
    "for short vertical videos. Return concise, engaging copy using supplied hashtags where relevant. "
    "Respect platform character norms and avoid clickbait claims."
)

def gen_user(icon, notes, lo, hi):
    return (f"Icon/Topic: {icon}\nNotes: {notes}\n"
            f"Word target: {lo}–{hi} words.\nReturn only the single paragraph.")

def finalize_user(icon, notes, lo, hi, original):
    return ("Correct to satisfy rules. Keep one paragraph; hook first sentence ≤18 words;"
            f" target {lo}–{hi} words. Remove emojis/em-dashes; soften risky claims;"
            f" preserve factual notes.\nIcon: {icon}\nNotes:{notes}\nOriginal:{original}\n"
            "Return only the corrected paragraph.")

def captions_user(topic, hashtags_csv):
    return (f"Topic: {topic}\nHashtags: {hashtags_csv}\n"
            "Return JSON with fields: caption_yt, caption_tt, caption_ig_reels, caption_ig_stories, caption_fb_reels.")


def word_range_for_duration(duration: str) -> tuple[int, int]:
    duration_map = {
        "15": (40, 55),
        "30": (90, 120),
        "60": (180, 230),
    }
    return duration_map.get(str(duration), (100, 130))  # fallback


# core/prompts.py

BASE_SCRIPT_SYSTEM = """You are a precise, concise scriptwriter for 30-second mini-documentaries about heritage menswear icons. 
Follow instructions exactly. Never use emojis or em dashes. Use standard punctuation only. Return ONLY a single JSON object (no extra commentary, no markdown).
Match a confident, cinematic cadence. Keep brand and item names accurate; if uncertain, prefer conservative phrasing like 'often associated' or 'widely linked'. 
Do not invent specific model numbers unless widely documented.

IMPORTANT: You must return your answer as a valid JSON object, containing keys "paragraph" and "ssml". 
"""

def base_script_user(icon_name: str, notes: str, duration: str) -> str:
    lo, hi = word_range_for_duration(duration)
    style_ref = (
        'When it comes to timeless American style, look no further than Paul Newman. '
        'His approach to fashion was very simple: use the basics, wear them well, and never look absurd. '
        'When he was not in racing gear, you would often see him in denim, whether a shirt, jeans, jacket, or sometimes all at once. '
        'He wore his Rolex Daytona so consistently that collectors nicknamed it the Paul Newman Daytona, now the most expensive Rolex ever sold. '
        'From western ruggedness to preppy cool to sharp suits, he showed that timeless pieces do the heavy lifting. '
        'His signature racing glasses underlined that style is also about originality, securing his place as a blueprint for masculine American style.'
    )
    return f"""
You are a senior fashion copywriter AND an SSML engineer.
GOAL
1) Write ONE documentary-style brand paragraph ({lo}–{hi} words) about {icon_name}.
- Weave in these notes naturally: {notes}
- Concrete visuals (fit, fabric, color mood, scene); present tense; no hype, emojis, or markdown.
- Include one subtle styling suggestion.
- End with a calm, confident closing line.

2) Convert that paragraph into VALID, production-ready SSML (ElevenLabs-compatible).

SSML RULES
- Output ONE <speak> block only (no XML declaration, no code fences, no comments).
- Wrap content in <prosody rate="medium"> … </prosody>.
- Use <break> between 120–500ms at natural beats.
- Use <emphasis level="moderate"> on up to 3 short phrases.
- Convert years to <say-as interpret-as="date" format="y">YYYY</say-as>.
- Convert standalone integers to <say-as interpret-as="cardinal">N</say-as> when helpful.
- Escape special characters (&, <, >, ").
- End with <mark name="END"/> right before </speak>.
- No vendor-specific or <audio> tags.

OUTPUT FORMAT
Return ONLY a single JSON object (no extra text, no markdown), strictly valid and double-quoted:
{{
  "paragraph": "string — the plain text paragraph ({lo}–{hi} words).",
  "ssml": "<speak>…</speak>"
}}
"""

PROMPT_TEMPLATE = """
You are a senior fashion copywriter AND an SSML engineer.
GOAL
1) Write ONE documentary-style brand paragraph ({lo}–{hi} words) about {icon}.
- Weave in these notes naturally: {notes}
- Concrete visuals (fit, fabric, color mood, scene); present tense; no hype, emojis, or markdown.
- Include one subtle styling suggestion.
- End with a calm, confident closing line.

2) Convert that paragraph into VALID, production-ready SSML (ElevenLabs-compatible).

SSML RULES
- Output ONE <speak> block only (no XML declaration, no code fences, no comments).
- Wrap content in <prosody rate="medium"> … </prosody>.
- Use <break> between 120–500ms at natural beats.
- Use <emphasis level="moderate"> on up to 3 short phrases.
- Convert years to <say-as interpret-as="date" format="y">YYYY</say-as>.
- Convert standalone integers to <say-as interpret-as="cardinal">N</say-as> when helpful.
- Escape special characters (&, <, >, ").
- End with <mark name="END"/> right before </speak>.
- No vendor-specific or <audio> tags.

OUTPUT FORMAT
Return ONLY a single JSON object (no extra text, no markdown), strictly valid and double-quoted:
{{
  "paragraph": "string — the plain text paragraph ({lo}–{hi} words).",
  "ssml": "<speak>…</speak>"
}}
"""