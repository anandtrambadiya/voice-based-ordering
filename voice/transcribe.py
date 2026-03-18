"""
voice/transcribe.py — Whisper (tiny) + robust NLP parser
Uses ffmpeg (now installed) to handle any audio format from browser.
"""
import whisper, re, io, os, tempfile
from difflib import get_close_matches

_model = None

def get_model():
    global _model
    if _model is None:
        print("[Whisper] Loading tiny model...")
        _model = whisper.load_model("tiny")
        print("[Whisper] Ready.")
    return _model


def transcribe_audio(audio_bytes: bytes, ext: str = "webm") -> str:
    """Save to temp file — Whisper uses ffmpeg internally to decode any format."""
    model = get_model()

    with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        print(f"[Whisper] Transcribing {len(audio_bytes)} bytes as .{ext}")
        result = model.transcribe(tmp_path, language=None, task="transcribe",
                                  temperature=0, best_of=1)
        text = result['text'].strip()
        print(f"[Whisper] '{text}'")
        return text
    finally:
        try: os.unlink(tmp_path)
        except: pass


# ── Parser ────────────────────────────────────────────────────────────────────

_NUMS = {
    'zero':0,'one':1,'two':2,'three':3,'four':4,'five':5,
    'six':6,'seven':7,'eight':8,'nine':9,'ten':10,
    'ek':1,'do':2,'teen':3,'char':4,'paanch':5,
    'chhe':6,'saat':7,'aath':8,'nau':9,'das':10,
    'a':1,'an':1,'the':1,
}

_NOISE = {
    'please','aur','and','also','plus','with','some','give','me',
    'lao','dena','chahiye','order','want','i','would','like',
    'can','get','have','do','bhi','hi','na','yaar','bhai',
}


def parse_order(transcript: str, menu_items: list) -> list:
    tokens = _tokenize(transcript)
    print(f"[Parser] Tokens: {tokens}")

    menu_lookup = {}
    for item in menu_items:
        key = _normalize(item['name'])
        menu_lookup[key] = item
        for word in key.split():
            if len(word) >= 4 and word not in menu_lookup:
                menu_lookup[word] = item

    results, seen_ids, used = [], set(), [False] * len(tokens)

    i = 0
    while i < len(tokens):
        if used[i]:
            i += 1
            continue
        matched = False
        for span in range(min(4, len(tokens) - i), 0, -1):
            chunk = ' '.join(tokens[i:i+span])
            item  = _find_item(chunk, menu_lookup, menu_items)
            if item and item['id'] not in seen_ids:
                qty = _grab_qty(tokens, used, i, span)
                seen_ids.add(item['id'])
                results.append({
                    'menu_item_id': item['id'],
                    'name':         item['name'],
                    'price':        item['price'],
                    'quantity':     qty,
                })
                for j in range(i, i + span):
                    used[j] = True
                matched = True
                i += span
                break
        if not matched:
            i += 1

    print(f"[Parser] Matched {len(results)} items: {[r['name'] for r in results]}")
    return results


def _tokenize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", ' ', text)
    return [t for t in text.split() if t not in _NOISE]

def _normalize(name):
    return name.lower().strip()

def _find_item(chunk, menu_lookup, menu_items):
    if chunk in menu_lookup:
        return menu_lookup[chunk]
    close = get_close_matches(chunk, list(menu_lookup.keys()), n=1, cutoff=0.55)
    if close:
        return menu_lookup[close[0]]
    return None

def _grab_qty(tokens, used, item_start, item_span):
    for idx in [item_start - 1, item_start + item_span]:
        if 0 <= idx < len(tokens) and not used[idx]:
            tok = tokens[idx]
            if tok.isdigit():
                used[idx] = True
                return int(tok)
            if tok in _NUMS and _NUMS[tok] > 0:
                used[idx] = True
                return _NUMS[tok]
    return 1