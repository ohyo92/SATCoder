#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any, Mapping

from flask import Flask, Response, jsonify, render_template_string, request

import sat_question_generator as sat


app = Flask(__name__)

VALID_SECTIONS = {"mixed", "math", "verbal"}
VALID_ORDERS = {"hardest", "easiest"}
VALID_FORMATS = {"text", "json"}

DEFAULT_FORM_VALUES = {
    "count": "5",
    "section": "mixed",
    "order": "hardest",
    "format": "text",
    "seed": "",
}

PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SAT Question Generator</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; max-width: 980px; }
      h1 { margin-bottom: 0.5rem; }
      form { display: grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap: 0.9rem 1rem; margin-top: 1rem; }
      label { display: block; font-size: 0.95rem; margin-bottom: 0.35rem; }
      input, select, button { width: 100%; padding: 0.55rem; box-sizing: border-box; font-size: 0.95rem; }
      .actions { grid-column: 1 / -1; }
      .errors { margin-top: 1rem; color: #a11; }
      pre { background: #111; color: #eee; padding: 1rem; border-radius: 8px; overflow: auto; white-space: pre-wrap; }
      .hint { margin-top: 0.6rem; color: #444; font-size: 0.92rem; }
    </style>
  </head>
  <body>
    <h1>SAT Question Generator</h1>
    <p>Generate SAT-style questions and view them in text or JSON.</p>
    <form method="get" action="/">
      <div>
        <label for="count">Question count</label>
        <input id="count" name="count" type="number" min="1" value="{{ form_values['count'] }}" required />
      </div>
      <div>
        <label for="seed">Seed (optional)</label>
        <input id="seed" name="seed" type="number" value="{{ form_values['seed'] }}" />
      </div>
      <div>
        <label for="section">Section</label>
        <select id="section" name="section">
          <option value="mixed" {% if form_values['section'] == 'mixed' %}selected{% endif %}>mixed</option>
          <option value="math" {% if form_values['section'] == 'math' %}selected{% endif %}>math</option>
          <option value="verbal" {% if form_values['section'] == 'verbal' %}selected{% endif %}>verbal</option>
        </select>
      </div>
      <div>
        <label for="order">Order</label>
        <select id="order" name="order">
          <option value="hardest" {% if form_values['order'] == 'hardest' %}selected{% endif %}>hardest</option>
          <option value="easiest" {% if form_values['order'] == 'easiest' %}selected{% endif %}>easiest</option>
        </select>
      </div>
      <div>
        <label for="format">Format</label>
        <select id="format" name="format">
          <option value="text" {% if form_values['format'] == 'text' %}selected{% endif %}>text</option>
          <option value="json" {% if form_values['format'] == 'json' %}selected{% endif %}>json</option>
        </select>
      </div>
      <div class="actions">
        <button type="submit">Generate</button>
      </div>
    </form>

    <div class="hint">
      API endpoint: <code>/generate?count=5&section=mixed&order=hardest&format=json</code>
    </div>

    {% if errors %}
      <div class="errors">
        <strong>Please fix the following:</strong>
        <ul>
          {% for error in errors %}
            <li>{{ error }}</li>
          {% endfor %}
        </ul>
      </div>
    {% endif %}

    {% if output %}
      <h2>Output</h2>
      <pre>{{ output }}</pre>
    {% endif %}
  </body>
</html>
"""


def parse_generation_params(values: Mapping[str, str]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []

    count_raw = values.get("count", DEFAULT_FORM_VALUES["count"]).strip()
    section = values.get("section", DEFAULT_FORM_VALUES["section"]).strip().lower()
    order = values.get("order", DEFAULT_FORM_VALUES["order"]).strip().lower()
    output_format = values.get("format", DEFAULT_FORM_VALUES["format"]).strip().lower()
    seed_raw = values.get("seed", DEFAULT_FORM_VALUES["seed"]).strip()

    count = 0
    seed: int | None = None

    try:
        count = int(count_raw)
        if count < 1:
            raise ValueError
    except ValueError:
        errors.append("count must be an integer greater than or equal to 1.")

    if section not in VALID_SECTIONS:
        errors.append(f"section must be one of: {', '.join(sorted(VALID_SECTIONS))}.")
    if order not in VALID_ORDERS:
        errors.append(f"order must be one of: {', '.join(sorted(VALID_ORDERS))}.")
    if output_format not in VALID_FORMATS:
        errors.append(f"format must be one of: {', '.join(sorted(VALID_FORMATS))}.")

    if seed_raw:
        try:
            seed = int(seed_raw)
        except ValueError:
            errors.append("seed must be an integer when provided.")

    params = {
        "count": count,
        "section": section,
        "order": order,
        "format": output_format,
        "seed": seed,
    }
    return params, errors


def generate_questions(params: Mapping[str, Any]) -> list[sat.SATQuestion]:
    generator = sat.SATQuestionGenerator(seed=params["seed"])
    generated = generator.generate(count=params["count"], section=params["section"])
    return sat.rank_questions(generated, order=params["order"])


@app.get("/")
def index() -> str:
    incoming_values = request.args.to_dict()
    form_values = {**DEFAULT_FORM_VALUES, **incoming_values}
    errors: list[str] = []
    output = ""

    if incoming_values:
        params, errors = parse_generation_params(incoming_values)
        if not errors:
            questions = generate_questions(params)
            if params["format"] == "json":
                output = json.dumps([question.to_dict() for question in questions], indent=2)
            else:
                output = sat.render_text(questions)

    return render_template_string(
        PAGE_TEMPLATE,
        form_values=form_values,
        errors=errors,
        output=output,
    )


@app.get("/generate")
def generate_endpoint() -> Response:
    params, errors = parse_generation_params(request.args.to_dict())
    if errors:
        return jsonify({"errors": errors}), 400

    questions = generate_questions(params)
    if params["format"] == "json":
        return jsonify([question.to_dict() for question in questions])
    return Response(sat.render_text(questions), mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
