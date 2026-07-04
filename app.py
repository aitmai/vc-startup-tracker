"""
vc-startup-tracker — Flask Backend
====================================
Serves the dashboard and proxies all API calls.
Token stays server-side, never in the browser.

Run locally:  python app.py
Deploy:       Render (see render.yaml)
"""

import os
import json
import requests
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ── Config ──────────────────────────────────────────────
AIRTABLE_TOKEN   = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appWQNv1G6y9m8CM6")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

AIRTABLE_BASE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"
ANTHROPIC_URL     = "https://api.anthropic.com/v1/messages"

AIRTABLE_HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

ANTHROPIC_HEADERS = {
    "x-api-key": ANTHROPIC_API_KEY,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json"
}

# ── Serve dashboard ──────────────────────────────────────
@app.route("/")
def index():
    return render_template("dashboard.html")

# ── Airtable proxy — GET ─────────────────────────────────
@app.route("/api/airtable/<table>", methods=["GET"])
def airtable_get(table):
    params = dict(request.args)
    url = f"{AIRTABLE_BASE_URL}/{table}"
    try:
        resp = requests.get(url, headers=AIRTABLE_HEADERS, params=params, timeout=15)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Airtable proxy — POST ────────────────────────────────
@app.route("/api/airtable/<table>", methods=["POST"])
def airtable_post(table):
    url = f"{AIRTABLE_BASE_URL}/{table}"
    try:
        resp = requests.post(url, headers=AIRTABLE_HEADERS, json=request.json, timeout=15)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Airtable proxy — PATCH ───────────────────────────────
@app.route("/api/airtable/<table>/<record_id>", methods=["PATCH"])
def airtable_patch(table, record_id):
    url = f"{AIRTABLE_BASE_URL}/{table}/{record_id}"
    try:
        resp = requests.patch(url, headers=AIRTABLE_HEADERS, json=request.json, timeout=15)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Airtable proxy — DELETE ──────────────────────────────
@app.route("/api/airtable/<table>/<record_id>", methods=["DELETE"])
def airtable_delete(table, record_id):
    url = f"{AIRTABLE_BASE_URL}/{table}/{record_id}"
    try:
        resp = requests.delete(url, headers=AIRTABLE_HEADERS, timeout=15)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Claude proxy — streaming ─────────────────────────────
@app.route("/api/claude", methods=["POST"])
def claude_proxy():
    payload = request.json
    payload["stream"] = True

    def generate():
        try:
            with requests.post(
                ANTHROPIC_URL,
                headers=ANTHROPIC_HEADERS,
                json=payload,
                stream=True,
                timeout=60
            ) as resp:
                for chunk in resp.iter_lines():
                    if chunk:
                        yield f"{chunk.decode('utf-8')}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

# ── Health check ─────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "airtable": "configured" if AIRTABLE_TOKEN else "missing",
        "claude": "configured" if ANTHROPIC_API_KEY else "missing"
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_ENV") == "development")
