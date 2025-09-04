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



# core/prompts.py

BASE_SCRIPT_SYSTEM = """You are a precise, concise scriptwriter for 30-second mini-documentaries about heritage menswear icons. 
Follow instructions exactly. Never use emojis or em dashes. Use standard punctuation only. Output one single flowing paragraph with no headings or lists.
Match a confident, cinematic cadence. Keep brand and item names accurate; if uncertain, prefer conservative phrasing like 'often associated' or 'widely linked'. 
Do not invent specific model numbers unless widely documented."""

def base_script_user(icon_name: str, notes: str) -> str:
    style_ref = (
        'When it comes to timeless American style, look no further than Paul Newman. '
        'His approach to fashion was very simple: use the basics, wear them well, and never look absurd. '
        'When he was not in racing gear, you would often see him in denim, whether a shirt, jeans, jacket, or sometimes all at once. '
        'He wore his Rolex Daytona so consistently that collectors nicknamed it the Paul Newman Daytona, now the most expensive Rolex ever sold. '
        'From western ruggedness to preppy cool to sharp suits, he showed that timeless pieces do the heavy lifting. '
        'His signature racing glasses underlined that style is also about originality, securing his place as a blueprint for masculine American style.'
    )
    return f"""You are a scriptwriter who creates 30 second documentary style reel scripts about heritage mens fashion icons.

Write ONE paragraph of 100 to 130 words that follows this six-beat arc:
1) Intro and hook that establishes why the icon matters.
2) Style philosophy in one sentence.
3) Signature looks with specific garments.
4) One iconic accessory with cultural impact.
5) Range of style across settings.
6) Closing legacy line that names their influence on menswear.

Rules:
- One flowing paragraph. No headings or lists in the output.
- No emojis. No em dashes. Use standard punctuation only.
- Be concise, authoritative, and cinematic.
- Keep brand and item names accurate. If uncertain, use conservative phrasing such as 'often associated' or 'widely linked'.
- Do not invent specific model numbers unless well known.

Style reference for cadence and density only (do NOT copy wording): "{style_ref}"

Icon: {icon_name}
Notes to guide specificity: {notes or "none"}
Output: Return only the final paragraph. No titles, no labels, no extra commentary."""
