"""Cloze (fill-in-the-blank) exercise generation and its pre-generated queue."""

import random
import re
import threading
import time
from collections import deque

from config import CLOZE_MIN_WORD_LENGTH, CLOZE_STOPWORDS, MIN_WORDS, QUEUE_FILL_PACING_SECONDS, QUEUE_SIZE
from gemini_client import generate_content, translate_text
from vocab import clamp_word_limit, vocab_for

_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+")


def cloze_system_prompt(word_limit: int) -> str:
    vocab = vocab_for(word_limit)
    return (
        "You write ONE extremely simple German sentence for a language learner "
        f"who only knows the {word_limit} most common German words.\n\n"
        "ALLOWED VOCABULARY (base dictionary forms / lemmas):\n"
        f"{vocab}\n\n"
        "Rules:\n"
        "- Every content word you use must belong to the word family of one of the "
        "lemmas above (i.e. any grammatically correct inflected, conjugated, or "
        "declined form of one of those lemmas - e.g. if 'gehen' is allowed you may "
        "write 'gehe', 'gehst', 'ging', 'gegangen', etc.).\n"
        "- Do not use any word whose lemma is outside the allowed list.\n"
        "- Names of people and places may be used freely when needed.\n"
        "- The sentence must stand on its own (it does not continue anything).\n"
        "- Keep it short, natural, and grammatically correct.\n"
        "- Output ONLY the German sentence. No quotes, no notes, no translation."
    )


def _generate_sentence(word_limit: int) -> str:
    return generate_content(cloze_system_prompt(word_limit), "Write one new sentence.")


def _pick_blank(sentence: str):
    """Return a regex Match for a content word worth blanking out, or None."""
    candidates = [
        m
        for m in _WORD_RE.finditer(sentence)
        if len(m.group()) >= CLOZE_MIN_WORD_LENGTH and m.group().lower() not in CLOZE_STOPWORDS
    ]
    return random.choice(candidates) if candidates else None


def build_cloze_item(word_limit: int) -> dict | None:
    for _ in range(3):  # no eligible content word, or a transient API error - retry a bit
        try:
            sentence = _generate_sentence(word_limit)
        except Exception:
            continue
        match = _pick_blank(sentence)
        if match:
            break
    else:
        return None

    answer = match.group()
    sentence_with_blank = sentence[: match.start()] + "_____" + sentence[match.end() :]
    try:
        translation = translate_text(sentence)
    except Exception:
        translation = ""
    return {
        "sentenceWithBlank": sentence_with_blank,
        "answer": answer,
        "translation": translation,
    }


# --- Background item queue --------------------------------------------------
#
# Unlike the reading exercise, each cloze item is a standalone sentence with
# no continuation between items - but the fill loop works the same way: keep
# QUEUE_SIZE items ready, and whenever one is popped, refill one more in the
# background so the next click is instant.

state_lock = threading.Lock()
state = {
    "word_limit": MIN_WORDS,
    "queue": deque(),
    "filling": False,
    "epoch": 0,
}


def _invalidate():
    state["epoch"] += 1
    state["queue"].clear()


def _ensure_filling():
    if not state["filling"]:
        state["filling"] = True
        threading.Thread(target=_top_up_queue, daemon=True).start()


def _top_up_queue():
    backoff = 1.0
    while True:
        with state_lock:
            if len(state["queue"]) >= QUEUE_SIZE:
                state["filling"] = False
                return
            word_limit = state["word_limit"]
            epoch = state["epoch"]

        try:
            item = build_cloze_item(word_limit)
        except Exception:
            item = None

        if item is None:
            # Transient errors (rate limits, model overload) shouldn't stall
            # the queue forever - back off and keep retrying instead of
            # giving up, as long as this context is still current.
            with state_lock:
                if state["epoch"] != epoch:
                    continue
            time.sleep(backoff)
            backoff = min(backoff * 2, 20.0)
            continue

        backoff = 1.0
        with state_lock:
            if state["epoch"] != epoch:
                continue  # word limit changed while this was generating
            state["queue"].append(item)

        # Pace successful fills too, so this queue alone can't burst through
        # the whole per-minute quota (shared with the other exercises' queues).
        time.sleep(QUEUE_FILL_PACING_SECONDS)


def warm_up():
    """Start the background queue filling. Safe to call repeatedly."""
    with state_lock:
        _ensure_filling()


def get_next_item(word_limit) -> dict:
    word_limit = clamp_word_limit(word_limit)

    with state_lock:
        if word_limit != state["word_limit"]:
            state["word_limit"] = word_limit
            _invalidate()
        item = state["queue"].popleft() if state["queue"] else None

    if item is None:
        # Nothing pre-generated yet (cold start, or word limit just changed).
        item = build_cloze_item(word_limit)

    with state_lock:
        _ensure_filling()

    return item


def reset(word_limit) -> None:
    word_limit = clamp_word_limit(word_limit)
    with state_lock:
        state["word_limit"] = word_limit
        _invalidate()
        _ensure_filling()
