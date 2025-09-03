import re, datetime
from zoneinfo import ZoneInfo
from .adapters import llm_openai

def word_range(duration: str):
    return {"15s": (60,75), "30s": (90,120), "60s": (150,180)}.get(duration, (90,120))

def llm_chat(system, user, temp=0.5):
    return llm_openai.chat(system, user, temp)

def count_words(t): return len(re.findall(r"\b[\w’']+\b", t))
def first_sentence(t):
    parts = re.split(r"(?<=[.!?])\s+", t.strip(), 1)
    return parts[0] if parts else t.strip()

def qc_local(text: str, lo: int, hi: int):
    wc = count_words(text)
    fs_wc = count_words(first_sentence(text))
    hook_ok = fs_wc <= 18
    punct_ok = ("—" not in text) and ("–" not in text) and not re.search(r"[😀-🙏]", text)
    risk = []
    if not punct_ok: risk.append("punctuation")
    if not hook_ok: risk.append("hook_long")
    if wc < lo or wc > hi: risk.append("length_out_of_range")
    has_six = hook_ok and (lo <= wc <= hi)
    return {"word_count": wc,"first_sentence_word_count": fs_wc,"hook_ok": hook_ok,
            "has_six_beats": has_six,"punctuation_rules_ok": punct_ok,
            "risk_flags": risk,"fix_needed": bool(risk) or not has_six,"suggested_edit": ""}

def next_post_slot(brand_timezone: str, post_windows_csv: str):
    tz = ZoneInfo(brand_timezone or "America/New_York")
    now = datetime.datetime.now(tz)
    windows = [w.strip() for w in post_windows_csv.split(",") if w.strip()]
    today_slots = []
    for w in windows:
        h, m = map(int, w.split(":"))
        slot = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if slot > now:
            today_slots.append(slot)
    if today_slots:
        slot = min(today_slots)
    else:
        h, m = map(int, windows[0].split(":"))
        slot = (now + datetime.timedelta(days=1)).replace(hour=h, minute=m, second=0, microsecond=0)
    return slot.strftime("%H:%M"), slot
