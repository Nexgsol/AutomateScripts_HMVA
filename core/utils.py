import json
import re
<<<<<<< HEAD
import datetime
from typing import Dict
from zoneinfo import ZoneInfo

from core.adapters import llm_openai
from core.prompts import BASE_SCRIPT_SYSTEM, PROMPT_TEMPLATE, base_script_user


=======
from typing import Dict

from .prompts import BASE_SCRIPT_SYSTEM, base_script_user
# If you don't have these helpers elsewhere, keep them here:




import re, datetime
from zoneinfo import ZoneInfo
from .adapters import llm_openai
>>>>>>> main

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


# core/utils.py (append at bottom or near your other llm helpers)
import re

def generate_heritage_paragraph(icon_name: str, notes: str) -> str:
    """
    Generates a single 100–130 word paragraph per the Instructional Notes.
    Uses llm_chat(BASE_SCRIPT_SYSTEM, base_script_user, temperature=0.5).
    Enforces 'single paragraph' and trims stray newlines/spaces.
    """
    from .prompts import BASE_SCRIPT_SYSTEM, base_script_user

    raw = llm_chat(BASE_SCRIPT_SYSTEM, base_script_user(icon_name, notes), temp=0.5)

    # normalize whitespace to keep one paragraph
    text = raw.strip()
    # Replace hard newlines with spaces; collapse multiple spaces
    text = re.sub(r'\s*\n+\s*', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()

    # Guard: if it somehow produced multiple paragraphs, squash to one
    parts = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    if len(parts) > 1:
        text = ' '.join(parts)

    # (Optional) hard length nudge: if outside 100–130 words, ask model to tighten/expand once.
    words = len(text.split())
    if words < 100 or words > 130:
        fix_prompt = (
            f"Rewrite to a single flowing paragraph of 100 to 130 words, keep meaning and all six beats, "
            f"no emojis, no em dashes, standard punctuation only. Icon: {icon_name}. Notes: {notes}. "
            f"ORIGINAL:\n{text}\n\nReturn only the corrected paragraph."
        )
        text = llm_chat("You are a precise editor.", fix_prompt, temp=0.3).strip()
        text = re.sub(r'\s*\n+\s*', ' ', text)
        text = re.sub(r'\s{2,}', ' ', text).strip()
    return text

_WS_NEWLINES = re.compile(r'\s*\n+\s*')
_MULTI_WS = re.compile(r'\s{2,}')

<<<<<<< HEAD

def word_range_for_duration(duration: str) -> tuple[int, int]:
    duration_map = {
        "15": (40, 55),
        "30": (90, 120),
        "60": (180, 230),
    }
    return duration_map.get(str(duration), (100, 130))  # fallback

def build_prompt(icon: str, notes: str = "", category: str | None = None) -> str:
    icon_for_prompt = compose_icon_for_prompt(icon, category)
    duration="30"  # Default duration; modify as needed
    lo, hi = word_range_for_duration(duration)
    return PROMPT_TEMPLATE.format(icon=icon_for_prompt, notes=(notes or "").strip(), lo=lo, hi=hi)
=======
def _normalize_one_paragraph(text: str) -> str:
    text = text.strip()
    text = _WS_NEWLINES.sub(' ', text)
    text = _MULTI_WS.sub(' ', text).strip()
    # squash multiple paragraphs if any slipped in
    parts = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    if len(parts) > 1:
        text = ' '.join(parts)
    return text
>>>>>>> main

def _coerce_json(raw: str) -> Dict:
    """
    Best-effort JSON extraction:
    - Try json.loads
    - If it fails, pull first {...} block and try again
    - Finally, wrap into expected schema if it's just a plain paragraph
    """
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Try to extract the outermost JSON object
    m = re.search(r'\{.*\}', raw, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    # If the model returned only the paragraph, coerce it
    coerced = _normalize_one_paragraph(raw)
    return {"paragraph": coerced, "ssml": ""}

<<<<<<< HEAD
    def _canon(s: str) -> str:
        return (s or "").strip().lower().replace("_", " ").replace("-", " ")

    rows = ws.iter_rows(values_only=True)
    header = next(rows, None)
    if not header:
        wb.close()
        return

    hmap = { _canon(h): i for i, h in enumerate(header or []) if h is not None }

    def _get(row, *cands):

        """
        Return a cell value from `row` by checking candidate column names.

        Args:
            row (tuple): Row values from Excel.
            *cands (str): Possible header names (e.g. "Icon Name", "Icon").

        Returns:
            str: Normalized string from the first matching column,
                or "" if none found.
        """

        for c in cands:
            idx = hmap.get(_canon(c))
            if idx is not None:
                return str(row[idx] or "").strip()
        return ""


    excel_row = 2  # header is row 1
    for r in rows:
        icon = _get(r, "icon name", "icon", "name", "ICon name")
        if icon:
            yield {
                "row": excel_row,
                "icon": icon,
                "category": _get(r, "category", "type"),
                "notes": _get(r, "notes", "note"),
            }
        excel_row += 1

    wb.close()


def batch(iterable, size: int):
    """Yield lists of up to `size` items from an iterator (memory-light)."""
    buf = []
    for item in iterable:
        buf.append(item)
        if len(buf) == size:
            yield buf
            buf = []
    if buf:
        yield buf


def call_openai_for_paragraph_and_ssml(prompt: str) -> str:
=======
def generate_heritage_paragraph_with_ssml(
    icon_name: str,
    notes: str,
    duration: str,
    temp: float = 0.5,
) -> Dict[str, str]:
>>>>>>> main
    """
    Generates a single documentary-style paragraph (120–160 words) AND
    a production-ready SSML version in one call.

    Returns:
        {"paragraph": "...", "ssml": "<speak>...</speak>"}
    """
<<<<<<< HEAD
    system = (
        "You are a senior fashion copywriter AND an SSML engineer.\n"
        "Return ONLY a single JSON object (no extra commentary, no markdown)."
    )
    try:
        raw = llm_openai.chat(system, prompt, temperature=0.2).strip()
        return raw
    except Exception as e:
        return json.dumps({
            "paragraph": "",
            "ssml": "",
            "error": str(e),
        })


_WS_NEWLINES = re.compile(r'\s*\n+\s*')
_MULTI_WS = re.compile(r'\s{2,}')


def _normalize_one_paragraph(text: str) -> str:
    text = text.strip()
    text = _WS_NEWLINES.sub(' ', text)
    text = _MULTI_WS.sub(' ', text).strip()
    # squash multiple paragraphs if any slipped in
    parts = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    if len(parts) > 1:
        text = ' '.join(parts)
    return text


def _coerce_json(raw: str) -> Dict:
    """
    Best-effort JSON extraction:
    - Try json.loads
    - If it fails, pull first {...} block and try again
    - Finally, wrap into expected schema if it's just a plain paragraph
    """
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Try to extract the outermost JSON object
    m = re.search(r'\{.*\}', raw, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    # If the model returned only the paragraph, coerce it
    coerced = _normalize_one_paragraph(raw)
    return {"paragraph": coerced, "ssml": ""}


def generate_heritage_paragraph_with_ssml(
    icon_name: str,
    notes: str,
    duration: str,
    category: str | None = None,
    temp: float = 0.5,
) -> Dict[str, str]:
    """
    Generates a single documentary-style paragraph (120–160 words) AND
    a production-ready SSML version in one call.

    Returns:
        {"paragraph": "...", "ssml": "<speak>...</speak>"}
    """
    # Build user prompt (the base prompt should already ask for JSON with both fields)
    # user_prompt = base_script_user(icon_name, notes, duration)

    # raw = llm_chat(BASE_SCRIPT_SYSTEM, user_prompt, temp=temp)
    prompt = build_prompt(icon=icon_name, notes=notes, category=category)
    raw = call_openai_for_paragraph_and_ssml(prompt)
=======
    # Build user prompt (the base prompt should already ask for JSON with both fields)
    user_prompt = base_script_user(icon_name, notes, duration)

    raw = llm_chat(BASE_SCRIPT_SYSTEM, user_prompt, temp=temp)
>>>>>>> main
    data = _coerce_json(raw)

    # Normalize and guard the paragraph
    paragraph = _normalize_one_paragraph(data.get("paragraph", ""))

    # If length drifts, nudge once
    wc = len(paragraph.split())
    if wc < 120 or wc > 160:
        fix_prompt = (
            "Rewrite into one flowing paragraph of 120–160 words. "
            "Keep meaning and all six beats. "
            "No emojis, no em dashes, standard punctuation only.\n\n"
            f"Icon: {icon_name}\nNotes: {notes or 'none'}\n"
            f"Original:\n{paragraph}\n\n"
            "Return only the corrected paragraph."
        )
        paragraph = llm_chat("You are a precise editor.", fix_prompt, temp=0.3).strip()
        paragraph = _normalize_one_paragraph(paragraph)

    # SSML: accept model output if valid-looking, otherwise convert paragraph-only
    ssml = (data.get("ssml") or "").strip()
    has_speak = ssml.lower().startswith("<speak") and ssml.lower().endswith("</speak>")

    if not has_speak:
        # Fallback: ask model to convert the finalized paragraph to SSML only
        ssml_system = (
            "You convert plain text into VALID, production-ready SSML (ElevenLabs-compatible). "
            "Return ONE <speak> block ONLY. No code fences, no explanations, no XML declaration. "
            'Wrap with <prosody rate="medium">…</prosody>. Use <break time="120ms"–"500ms">, '
            '<emphasis level="moderate"> (≤3 uses), convert years with '
            '<say-as interpret-as="date" format="y">YYYY</say-as> and integers with '
            '<say-as interpret-as="cardinal">N</say-as>. Escape special characters. '
            'End with <mark name="END"/> before </speak>.'
        )
        ssml_user = (
            "Convert the following paragraph to SSML following the rules:\n\n"
            f"{paragraph}"
        )
        ssml = llm_chat(ssml_system, ssml_user, temp=0.2).strip()

    return {"paragraph": paragraph, "ssml": ssml}