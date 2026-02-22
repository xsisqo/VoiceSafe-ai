from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # allow calls from your frontend/backend

@app.get("/")
def root():
    return "AI OK ✅"

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "voicesafe-ai",
        "time": datetime.utcnow().isoformat() + "Z"
    })

@app.post("/analyze")
def analyze():
    """
    Accepts multipart/form-data with field name: file
    Returns consistent demo analysis (we'll improve model later).
    """
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "Missing file field"}), 400

    f = request.files["file"]
    filename = f.filename or "unknown"

    # Read bytes (optional, for future features)
    _ = f.read()

    # Demo output (stable, predictable)
    result = {
        "status": "success",
        "message": "File received",
        "filename": filename,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",

        # These are the fields your backend expects:
        "ai_voice_prob": 15,
        "scam_score": 42,
        "stress_level": 25,

        # Optional extras
        "summary": "No strong red flags detected in this sample, but stay cautious.",
        "flags": []
    }
    return jsonify(result), 200

if __name__ == "__main__":
    # local dev only
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=True)