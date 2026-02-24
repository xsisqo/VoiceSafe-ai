# ai/app.py

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

@app.get("/")
def root():
    return jsonify({"ok": True, "service": "voicesafe-ai"})

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.post("/analyze")
def analyze():
    # Expect multipart/form-data with "file"
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400

    uploaded = request.files["file"]
    filename = secure_filename(uploaded.filename or "audio.bin")
    save_path = os.path.join("/tmp", filename)

    # IMPORTANT (Render fix): read fully first, then write
    data = uploaded.read()
    if not data:
        return jsonify({"error": "Empty file"}), 400

    with open(save_path, "wb") as f:
        f.write(data)

    # DEMO RESULT (stable)
    result = {
        "summary": "No strong red flags detected in this sample, but stay cautious.",
        "ai_probability": 15,
        "stress_level": 25,
        "scam_score": 10,
        "flags": [],
        "voice_match": "Unknown",
        "meta": {
            "filename": filename,
            "bytes": len(data)
        }
    }

    return jsonify(result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)