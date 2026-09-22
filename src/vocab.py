"""Word list, frequency-based coverage, and clamping helpers shared by every exercise."""

import json

from config import MAX_WORDS, MIN_WORDS, STEP, TONE_STYLE_AXIS, WORDLIST_PATH

with open(WORDLIST_PATH, encoding="utf-8") as f:
    WORD_ENTRIES = sorted(json.load(f), key=lambda e: e["position"])
LEMMAS = [entry["lemma"] for entry in WORD_ENTRIES]
_LOWER_LEMMAS = [w.lower() for w in LEMMAS]

# occurrence_per_million is each lemma's frequency per million running words of
# the corpus this list was built from, so it sums to ~1,000,000 across the full
# vocabulary. The cumulative sum over the top N words is therefore the real,
# corpus-measured percentage of everyday German text/conversation you'd
# recognize knowing only those N words.
_CUMULATIVE_OCCURRENCE = []
_running = 0.0
for entry in WORD_ENTRIES:
    _running += entry["occurrence_per_million"]
    _CUMULATIVE_OCCURRENCE.append(_running)


def coverage_percent(word_limit: int) -> float:
    word_limit = max(1, min(len(_CUMULATIVE_OCCURRENCE), word_limit))
    return round(_CUMULATIVE_OCCURRENCE[word_limit - 1] / 1_000_000 * 100, 1)


COVERAGE_BY_WORD_LIMIT = {n: coverage_percent(n) for n in range(MIN_WORDS, MAX_WORDS + 1, STEP)}


def vocab_for(word_limit: int) -> str:
    word_limit = max(MIN_WORDS, min(MAX_WORDS, word_limit))
    return ", ".join(LEMMAS[:word_limit])


def is_in_vocab(word: str, word_limit: int) -> bool:
    """Case-insensitive membership check against the top word_limit lemmas."""
    word_limit = max(MIN_WORDS, min(MAX_WORDS, word_limit))
    return word.strip().lower() in _LOWER_LEMMAS[:word_limit]


def clamp_word_limit(n) -> int:
    return max(MIN_WORDS, min(MAX_WORDS, int(n)))


def clamp_tone(n) -> int:
    return max(0, min(len(TONE_STYLE_AXIS) - 1, int(n)))
