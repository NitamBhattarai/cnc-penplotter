# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from gcode import text_to_gcode
import os
import threading

app = Flask(__name__)
CORS(app)

# ---- simple in-memory "one job" queue ----
_lock = threading.Lock()
_pending_job_text = None   # holds the next text to plot

@app.route("/submit", methods=["POST"])
def submit_job():
    global _pending_job_text
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Missing text"}), 400

    with _lock:
        if _pending_job_text is not None:
            return jsonify({"ok": False, "error": "Busy"}), 409
        _pending_job_text = text

    return jsonify({"ok": True, "queued": text}), 200

@app.route("/gcode", methods=["GET", "POST"])
def gcode():
    global _pending_job_text

    # UI: generate gcode for preview
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        text = (data.get("text") or "").strip()
        if not text:
            return "Missing text", 400, {"Content-Type": "text/plain"}
        gcode = text_to_gcode(text)
        return gcode, 200, {"Content-Type": "text/plain"}

    # ESP32: poll next queued job
    with _lock:
        if _pending_job_text is None:
            return "NOJOB", 200, {"Content-Type": "text/plain"}

        text = _pending_job_text
        _pending_job_text = None  # consume once

    gcode = text_to_gcode(text)
    return gcode, 200, {"Content-Type": "text/plain"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)