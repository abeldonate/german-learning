import os
from datetime import date

from flask import Flask, jsonify, render_template, request

import cloze_engine
import config
import diary_engine
import diary_store
import odd_one_out_engine
import story_engine
import vocab

# templates/ and static/ live at the project root, one level up from src/.
app = Flask(
    __name__,
    template_folder=str(config.PROJECT_ROOT / "templates"),
    static_folder=str(config.PROJECT_ROOT / "static"),
)

diary_store.init_db()


def _parse_date(value) -> str | None:
    """Validate a YYYY-MM-DD string, returning it unchanged or None if invalid."""
    if not value:
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/sentences")
def sentences_page():
    story_engine.warm_up()
    return render_template(
        "sentences.html",
        min_words=config.MIN_WORDS,
        max_words=config.MAX_WORDS,
        step=config.STEP,
        generate_key=config.GENERATE_KEY,
        translate_key=config.TRANSLATE_KEY,
        initial_coverage=vocab.COVERAGE_BY_WORD_LIMIT[config.MIN_WORDS],
        coverage_by_word_limit=vocab.COVERAGE_BY_WORD_LIMIT,
        tone_style_axis=config.TONE_STYLE_AXIS,
        tone_seriousness_axis=config.TONE_SERIOUSNESS_AXIS,
        tone_default_x=config.TONE_DEFAULT_X,
        tone_default_y=config.TONE_DEFAULT_Y,
    )


@app.route("/api/sentences/next", methods=["POST"])
def sentences_next():
    data = request.get_json(force=True) or {}
    item = story_engine.get_next_sentence(
        data.get("wordLimit", config.MIN_WORDS),
        data.get("toneX", config.TONE_DEFAULT_X),
        data.get("toneY", config.TONE_DEFAULT_Y),
    )
    return jsonify(item)


@app.route("/api/sentences/reset", methods=["POST"])
def sentences_reset():
    data = request.get_json(force=True) or {}
    story_engine.reset_story(
        data.get("wordLimit", config.MIN_WORDS),
        data.get("toneX", config.TONE_DEFAULT_X),
        data.get("toneY", config.TONE_DEFAULT_Y),
    )
    return jsonify({"ok": True})


@app.route("/cloze")
def cloze_page():
    cloze_engine.warm_up()
    return render_template(
        "cloze.html",
        min_words=config.MIN_WORDS,
        max_words=config.MAX_WORDS,
        step=config.STEP,
        generate_key=config.GENERATE_KEY,
        translate_key=config.TRANSLATE_KEY,
        initial_coverage=vocab.COVERAGE_BY_WORD_LIMIT[config.MIN_WORDS],
        coverage_by_word_limit=vocab.COVERAGE_BY_WORD_LIMIT,
    )


@app.route("/api/cloze/next", methods=["POST"])
def cloze_next():
    data = request.get_json(force=True) or {}
    item = cloze_engine.get_next_item(data.get("wordLimit", config.MIN_WORDS))
    if item is None:
        return jsonify({"error": "Could not generate a valid sentence. Please try again."}), 502
    return jsonify(item)


@app.route("/api/cloze/reset", methods=["POST"])
def cloze_reset():
    data = request.get_json(force=True) or {}
    cloze_engine.reset(data.get("wordLimit", config.MIN_WORDS))
    return jsonify({"ok": True})


@app.route("/odd-one-out")
def odd_one_out_page():
    odd_one_out_engine.warm_up()
    return render_template(
        "odd-one-out.html",
        min_words=config.MIN_WORDS,
        max_words=config.MAX_WORDS,
        step=config.STEP,
        generate_key=config.GENERATE_KEY,
        translate_key=config.TRANSLATE_KEY,
        initial_coverage=vocab.COVERAGE_BY_WORD_LIMIT[config.MIN_WORDS],
        coverage_by_word_limit=vocab.COVERAGE_BY_WORD_LIMIT,
    )


@app.route("/api/odd-one-out/next", methods=["POST"])
def odd_one_out_next():
    data = request.get_json(force=True) or {}
    item = odd_one_out_engine.get_next_item(data.get("wordLimit", config.MIN_WORDS))
    if item is None:
        return jsonify({"error": "Could not generate a valid word group. Please try again."}), 502
    return jsonify(item)


@app.route("/api/odd-one-out/reset", methods=["POST"])
def odd_one_out_reset():
    data = request.get_json(force=True) or {}
    odd_one_out_engine.reset(data.get("wordLimit", config.MIN_WORDS))
    return jsonify({"ok": True})


@app.route("/diary")
def diary_page():
    return render_template("diary.html", today=date.today().isoformat())


@app.route("/api/diary/correct", methods=["POST"])
def diary_correct():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Please write something first."}), 400

    entry_date = _parse_date(data.get("date")) or date.today().isoformat()

    result = diary_engine.correct_entry(text)
    if result is None:
        return jsonify({"error": "Could not correct the text. Please try again."}), 502

    diary_store.save_entry(entry_date, text, result["corrected"], result["explanation"])
    return jsonify(result)


@app.route("/api/diary/entry", methods=["GET"])
def diary_entry():
    entry_date = _parse_date(request.args.get("date"))
    if entry_date is None:
        return jsonify({"error": "Invalid or missing date."}), 400

    entry = diary_store.get_entry(entry_date)
    if entry is None:
        return jsonify({"date": entry_date, "exists": False})
    return jsonify({**entry, "exists": True})


@app.route("/api/diary/dates", methods=["GET"])
def diary_dates():
    return jsonify({"dates": diary_store.list_dates()})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=debug, threaded=True)
