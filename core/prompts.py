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
