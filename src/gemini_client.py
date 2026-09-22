"""All direct calls to the Gemini API live here."""

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, MODEL

if not GEMINI_API_KEY:
    raise SystemExit(
        "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/apikey "
        "and put it in a .env file (see .env.example), or run: "
        "export GEMINI_API_KEY=your-key-here"
    )

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_content(system_prompt: str, user_content: str) -> str:
    response = client.models.generate_content(
        model=MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )
    return (response.text or "").strip()


def translate_text(text: str) -> str:
    if not text:
        return ""
    return generate_content(
        "Translate the given German text into natural, fluent English. "
        "Output ONLY the translation, nothing else.",
        text,
    )
