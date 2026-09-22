"""Odd-one-out exercise generation and its pre-generated queue."""

import random
import threading
import time
from collections import deque

from config import MIN_WORDS, QUEUE_FILL_PACING_SECONDS, QUEUE_SIZE
from gemini_client import generate_content
from vocab import clamp_word_limit, is_in_vocab, vocab_for


def _selection_system_prompt(word_limit: int) -> str:
    vocab = vocab_for(word_limit)
    return (
        "You pick words for an odd-one-out vocabulary game, for a German "
        f"learner who only knows the {word_limit} most common German words.\n\n"
        "ALLOWED VOCABULARY (base dictionary forms / lemmas):\n"
        f"{vocab}\n\n"
        "Task: choose exactly 4 words FROM THE ALLOWED VOCABULARY LIST ABOVE, "
        "copied exactly as they appear in the list.\n"
        "- Three of the words must clearly share one obvious semantic category "
        "(e.g. all animals, all colors, all family members, all foods, all "
        "body parts, all weather words, all means of transport, etc.).\n"
        "- The fourth word must be a clear, unambiguous outlier: it must NOT "
        "belong to that category.\n"
        "- All 4 words must be common, concrete content words. Do not use "
        "function words (articles, pronouns, prepositions, conjunctions, "
        "auxiliary/modal verbs like 'der', 'und', 'sein', 'haben', 'nicht', "
        "'sehr', 'ich', 'mit', etc.) as any of the 4 options.\n"
        "- The 4 words must all be different from each other.\n\n"
        "Output EXACTLY 4 lines and nothing else: the 3 category words first "
        "(any order), then the odd one out on the 4th line. No numbering, no "
        "bullets, no punctuation, no blank lines, no explanation, no category name."
    )


def _translation_system_prompt() -> str:
    return (
        "Translate each of the given German words into a single short English "
        "word or phrase. Output exactly one translation per line, in the same "
        "order as the input, and nothing else - no numbering, no German word "
        "repeated, no notes."
    )


def _parse_word_lines(text: str, expected_count: int) -> list | None:
    lines = [line.strip(" \t-•.").strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    if len(lines) != expected_count:
        return None
    return lines


def build_item(word_limit: int) -> dict | None:
    for _ in range(3):  # a malformed/invalid response or a transient API error - retry a bit
        try:
            raw = generate_content(_selection_system_prompt(word_limit), "Choose the 4 words now.")
        except Exception:
            continue
        words = _parse_word_lines(raw, 4)
        if not words:
            continue
        if len(set(w.lower() for w in words)) != 4:
            continue  # duplicate word - the group isn't well-formed
        if not all(is_in_vocab(w, word_limit) for w in words):
            continue  # model didn't stick to the allowed vocabulary

        odd_word = words[3]

        try:
            translations_raw = generate_content(_translation_system_prompt(), "\n".join(words))
            glosses = _parse_word_lines(translations_raw, 4)
        except Exception:
            glosses = None
        if not glosses:
            glosses = [""] * 4

        options = [{"word": w, "gloss": g} for w, g in zip(words, glosses)]
        random.shuffle(options)

        return {"options": options, "answer": odd_word}

    return None


# --- Background item queue --------------------------------------------------
#
# Each odd-one-out round is standalone, so - like the cloze exercise - the
# fill loop just keeps QUEUE_SIZE items ready and refills one at a time in
# the background whenever one is popped.

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
            item = build_item(word_limit)
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
        item = build_item(word_limit)

    with state_lock:
        _ensure_filling()

    return item


def reset(word_limit) -> None:
    word_limit = clamp_word_limit(word_limit)
    with state_lock:
        state["word_limit"] = word_limit
        _invalidate()
        _ensure_filling()
