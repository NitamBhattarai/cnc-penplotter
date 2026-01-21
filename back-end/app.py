# app.py
from collections import deque
from flask import Flask, request, jsonify
from flask_cors import CORS
from gcode import text_to_hershey_gcode
import os
import threading

app = Flask(__name__)
CORS(app)

# ---- simple in-memory FIFO queue ----
_lock = threading.Lock()
_job_queue = deque()   # each item is a text string
MAX_QUEUE = 25         # prevent unlimited memory growth

@app.route("/submit", methods=["POST"])
def submit_job():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Missing text"}), 400

    with _lock:
        if len(_job_queue) >= MAX_QUEUE:
            return jsonify({"ok": False, "error": "Queue full"}), 429
        _job_queue.append(text)
        position = len(_job_queue)

    return jsonify({"ok": True, "queued": text, "position": position}), 200

@app.route("/gcode", methods=["GET", "POST"])
def gcode():

    # UI: generate gcode for preview
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        text = (data.get("text") or "").strip()
        if not text:
            return "Missing text", 400, {"Content-Type": "text/plain"}
        gcode = text_to_hershey_gcode(text)
        return gcode, 200, {"Content-Type": "text/plain"}

    # ESP32: poll next queued job
    with _lock:
        if not _job_queue:
            return "NOJOB", 200, {"Content-Type": "text/plain"}

        text = _job_queue.popleft()  # consume oldest job

    gcode = text_to_hershey_gcode(text)
    return gcode, 200, {"Content-Type": "text/plain"}

@app.route("/status", methods=["GET"])
def status():
    with _lock:
        qlen = len(_job_queue)
    return jsonify({"ok": True, "queue_length": qlen}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)