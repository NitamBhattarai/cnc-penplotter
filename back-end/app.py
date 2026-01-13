# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from gcode import text_to_gcode
import os

app = Flask(__name__)
CORS(app)

@app.route("/gcode", methods=["GET", "POST"])
def generate_gcode():
    if request.method == "POST":
        data = request.get_json()
        text = data.get("text", "")
    else:  # GET
        text = request.args.get("text", "HELLO")

    gcode = text_to_gcode(text)
    return gcode, 200, {'Content-Type': 'text/plain'}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
