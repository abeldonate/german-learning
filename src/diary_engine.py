"""Diary correction: free-form German text in, corrected text + a short
explanation of the biggest errors out. Unlike the other exercises, this has
nothing to do with the frequency-ranked word list - the user writes whatever
they want, in whatever vocabulary they want."""

from gemini_client import generate_content

_MARKER_CORRECTED = "###CORRECTED###"
_MARKER_EXPLANATION = "###EXPLANATION###"


def _system_prompt() -> str:
    return (
        "You are an encouraging German writing tutor. The user, a language "
        "learner, wrote a diary entry in German about their day.\n\n"
        "1. Correct the German: fix grammar, spelling, word order, and word "
        "choice mistakes, while keeping the user's original meaning, content, "
        "and personal voice. Keep it natural, conversational diary-style "
        "German - do not make it more formal or add things the user didn't "
        "say.\n"
        "2. Briefly explain the biggest mistakes you fixed, in plain English, "
        "so the learner knows what to watch for next time. Focus on the 2-4 "
        "most significant or recurring issues, not an exhaustive list of "
        "every small fix. Write the explanation as plain text (a short "
        "numbered list is fine) with no markdown formatting - no asterisks, "
        "no bold, no headers.\n\n"
        "Output in EXACTLY this format, with these markers on their own lines:\n"
        f"{_MARKER_CORRECTED}\n"
        "<the corrected German text>\n"
        f"{_MARKER_EXPLANATION}\n"
        "<your explanation of the biggest errors, in English>\n\n"
        "Output nothing else outside this format."
    )


def _parse(raw: str) -> dict | None:
    if _MARKER_CORRECTED not in raw or _MARKER_EXPLANATION not in raw:
        return None
    _, rest = raw.split(_MARKER_CORRECTED, 1)
    corrected, explanation = rest.split(_MARKER_EXPLANATION, 1)
    corrected = corrected.strip()
    explanation = explanation.strip()
    if not corrected:
        return None
    return {"corrected": corrected, "explanation": explanation}


def correct_entry(draft: str) -> dict | None:
    draft = draft.strip()
    if not draft:
        return None

    for _ in range(2):  # a malformed response or a transient API error - retry once
        try:
            raw = generate_content(_system_prompt(), draft)
        except Exception:
            continue
        result = _parse(raw)
        if result:
            return result

    return None
