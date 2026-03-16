"""
voice/transcribe.py  —  Whisper wrapper + NLP item parser
"""
import whisper
import tempfile
import os
import re
from difflib import get_close_matches

# Load model once at import time (small = fast + good Hindi/Hinglish)
_model = None

def get_model():
    global _model
    if _model is None:
        print("[Whisper] Loading model...")
        _model = whisper.load_model("small")
        print("[Whisper] Model ready.")
    return _model


def transcribe_audio(audio_bytes: bytes, ext: str = "wav") -> str:
    """Save audio bytes to temp file, transcribe with Whisper."""
    model = get_model()
    # Always save as .wav — works on Windows without ffmpeg
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        print(f"[Whisper] Transcribing file: {tmp_path} ({len(audio_bytes)} bytes)")
        result = model.transcribe(tmp_path, language=None, task="transcribe")
        text = result['text'].strip()
        print(f"[Whisper] Transcript: {text}")
        return text
    except Exception as e:
        print(f"[Whisper] ERROR: {e}")
        raise
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


# ── NLP Parser ───────────────────────────────────────────────────────────────

# Hindi/Hinglish number words → int
_NUMBER_WORDS = {
    'ek': 1, 'one': 1, 'do': 2, 'two': 2, 'teen': 3, 'three': 3,
    'char': 4, 'four': 4, 'paanch': 5, 'five': 5, 'chhe': 6, 'six': 6,
    'saat': 7, 'seven': 7, 'aath': 8, 'eight': 8, 'nau': 9, 'nine': 9,
    'das': 10, 'ten': 10,
}


def parse_order(transcript: str, menu_items: list[dict]) -> list[dict]:
    """
    Parse a voice transcript into a list of {menu_item_id, name, quantity}.

    Works for English, Hindi, and Hinglish. Examples:
      "do butter chicken aur ek naan"
      "one biryani and two mango lassi please"
      "paneer tikka teen aur garlic naan do"
    """
    menu_names = [item['name'] for item in menu_items]
    transcript_clean = transcript.lower().strip()

    # Split on common conjunctions (aur, and, also, plus, ,)
    parts = re.split(r'\b(aur|and|also|plus|,|;)\b', transcript_clean)

    results = []
    seen_ids = set()

    for part in parts:
        part = part.strip()
        if not part or part in ('aur', 'and', 'also', 'plus', ',', ';'):
            continue

        qty   = _extract_quantity(part)
        match = _match_menu_item(part, menu_names)

        if match:
            item = next(i for i in menu_items if i['name'] == match)
            if item['id'] not in seen_ids:
                seen_ids.add(item['id'])
                results.append({
                    'menu_item_id': item['id'],
                    'name':         item['name'],
                    'price':        item['price'],
                    'quantity':     qty
                })

    return results


def _extract_quantity(text: str) -> int:
    """Extract numeric quantity from a phrase."""
    # Digit first
    m = re.search(r'\b(\d+)\b', text)
    if m:
        return int(m.group(1))
    # Word numbers
    for word, val in _NUMBER_WORDS.items():
        if re.search(rf'\b{word}\b', text):
            return val
    return 1


def _match_menu_item(text: str, menu_names: list[str]) -> str | None:
    """Fuzzy match text against menu item names."""
    lower_names = [n.lower() for n in menu_names]

    # Try direct substring match first
    for i, name in enumerate(lower_names):
        name_words = name.split()
        if all(w in text for w in name_words):
            return menu_names[i]

    # Fuzzy match
    matches = get_close_matches(text, lower_names, n=1, cutoff=0.45)
    if matches:
        idx = lower_names.index(matches[0])
        return menu_names[idx]

    # Word-level fuzzy: try each word in the text
    words = text.split()
    for word in words:
        if len(word) < 3:
            continue
        matches = get_close_matches(word, lower_names, n=1, cutoff=0.6)
        if matches:
            idx = lower_names.index(matches[0])
            return menu_names[idx]

    return None