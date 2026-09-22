"""Reading-practice sentence generation and its pre-generated queue."""

import threading
import time
from collections import deque

from config import (
    MIN_WORDS,
    QUEUE_FILL_PACING_SECONDS,
    QUEUE_SIZE,
    TONE_DEFAULT_X,
    TONE_DEFAULT_Y,
    TONE_SERIOUSNESS_AXIS,
    TONE_STYLE_AXIS,
)
from gemini_client import generate_content, translate_text
from vocab import clamp_tone, clamp_word_limit, vocab_for


def generation_system_prompt(word_limit: int, tone_x: int, tone_y: int) -> str:
    vocab = vocab_for(word_limit)
    style_desc = TONE_STYLE_AXIS[tone_x]["prompt"]
    mood_desc = TONE_SERIOUSNESS_AXIS[tone_y]["prompt"]
    return (
        "You write extremely simple German reading practice text for a language "
        f"learner who only knows the {word_limit} most common German words.\n\n"
        "ALLOWED VOCABULARY (base dictionary forms / lemmas):\n"
        f"{vocab}\n\n"
        "Rules:\n"
        "- Every content word you use must belong to the word family of one of the "
        "lemmas above (i.e. any grammatically correct inflected, conjugated, or "
        "declined form of one of those lemmas - e.g. if 'gehen' is allowed you may "
        "write 'gehe', 'gehst', 'ging', 'gegangen', etc.).\n"
        "- Do not use any word whose lemma is outside the allowed list.\n"
        "- Names of people and places may be used freely when needed.\n"
        f"- Style: write {style_desc}.\n"
        f"- Tone: the writing should be {mood_desc}.\n"
        "- Write exactly ONE new German sentence that continues the text so far "
        "(or starts it, if there is none yet), consistent with that style and tone.\n"
        "- Keep the sentence short, natural, and grammatically correct.\n"
        "- Output ONLY the German sentence. No quotes, no translation, no notes."
    )


def call_gemini_sentence(word_limit: int, tone_x: int, tone_y: int, context_sentences: list) -> str:
    story_text = " ".join(context_sentences)
    user_content = (
        f"Text so far:\n{story_text}" if story_text else "There is no text yet. Start it."
    )
    return generate_content(generation_system_prompt(word_limit, tone_x, tone_y), user_content)


# --- Background sentence queue ---------------------------------------------
#
# Generating a sentence (and its translation) takes a couple of seconds, so
# up to QUEUE_SIZE {sentence, translation} pairs are kept pre-generated in
# the background. Each queued sentence is generated as a continuation of
# (displayed story + sentences already queued ahead of it), so the story
# stays coherent even though it's prepared before the click that reveals it.
# "epoch" is bumped whenever the displayed story or word limit changes from
# under a running background fill, so a now-stale in-flight generation gets
# discarded instead of appended.

state_lock = threading.Lock()
state = {
    "word_limit": MIN_WORDS,
    "tone_x": TONE_DEFAULT_X,
    "tone_y": TONE_DEFAULT_Y,
    "displayed": [],
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
            tone_x = state["tone_x"]
            tone_y = state["tone_y"]
            epoch = state["epoch"]
            context = state["displayed"] + [item["sentence"] for item in state["queue"]]

        try:
            sentence = call_gemini_sentence(word_limit, tone_x, tone_y, context)
            translation = translate_text(sentence)
        except Exception:
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
                continue  # story, vocabulary, or tone changed while this was generating
            if sentence:
                state["queue"].append({"sentence": sentence, "translation": translation})

        # Pace successful fills too, so this queue alone can't burst through
        # the whole per-minute quota (shared with the other exercises' queues).
        time.sleep(QUEUE_FILL_PACING_SECONDS)


def warm_up():
    """Start the background queue filling. Safe to call repeatedly."""
    with state_lock:
        _ensure_filling()


def get_next_sentence(word_limit, tone_x, tone_y) -> dict:
    word_limit = clamp_word_limit(word_limit)
    tone_x = clamp_tone(tone_x)
    tone_y = clamp_tone(tone_y)

    with state_lock:
        if (word_limit, tone_x, tone_y) != (state["word_limit"], state["tone_x"], state["tone_y"]):
            state["word_limit"] = word_limit
            state["tone_x"] = tone_x
            state["tone_y"] = tone_y
            _invalidate()
        item = state["queue"].popleft() if state["queue"] else None
        context = list(state["displayed"])

    if item is None:
        # Nothing pre-generated yet (cold start, or vocabulary/tone just changed).
        sentence = call_gemini_sentence(word_limit, tone_x, tone_y, context)
        item = {"sentence": sentence, "translation": translate_text(sentence)}

    with state_lock:
        state["displayed"].append(item["sentence"])
        _ensure_filling()

    return item


def reset_story(word_limit, tone_x, tone_y) -> None:
    word_limit = clamp_word_limit(word_limit)
    tone_x = clamp_tone(tone_x)
    tone_y = clamp_tone(tone_y)

    with state_lock:
        state["word_limit"] = word_limit
        state["tone_x"] = tone_x
        state["tone_y"] = tone_y
        state["displayed"] = []
        _invalidate()
        _ensure_filling()
