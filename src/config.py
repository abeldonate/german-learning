import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Project root (one level up from src/), where config.yml, .env, the word
# list, templates/, and static/ all live.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yml"

load_dotenv(PROJECT_ROOT / ".env")

with open(CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

WORDLIST_PATH = PROJECT_ROOT / CONFIG["paths"]["wordlist"]
DIARY_DB_PATH = PROJECT_ROOT / CONFIG["paths"]["diary_db"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = os.environ.get("GEMINI_MODEL", CONFIG["model"])

QUEUE_SIZE = CONFIG["queue_size"]
QUEUE_FILL_PACING_SECONDS = CONFIG["queue_fill_pacing_seconds"]
GENERATE_KEY = CONFIG["keys"]["generate"]
TRANSLATE_KEY = CONFIG["keys"]["translate"]

MIN_WORDS = CONFIG["slider"]["min"]
MAX_WORDS = CONFIG["slider"]["max"]
STEP = CONFIG["slider"]["step"]

TONE_STYLE_AXIS = CONFIG["tone"]["style_axis"]
TONE_SERIOUSNESS_AXIS = CONFIG["tone"]["seriousness_axis"]
TONE_DEFAULT_X = CONFIG["tone"]["default"]["x"]
TONE_DEFAULT_Y = CONFIG["tone"]["default"]["y"]
assert len(TONE_STYLE_AXIS) == len(TONE_SERIOUSNESS_AXIS), "tone axes must be the same length"

CLOZE_MIN_WORD_LENGTH = CONFIG["cloze"]["min_word_length"]
CLOZE_STOPWORDS = {w.lower() for w in CONFIG["cloze"]["stopwords"]}
