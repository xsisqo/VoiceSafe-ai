import os
import traceback
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MAX_MB = int(os.environ.get("MAX_UPLOAD_MB", "25"))
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024

@app.get("/")
def root():
    return "VoiceSafe AI OK ✅"

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "voicesafe-ai",
        "max_upload_mb": MAX_MB,
        "time": datetime.utcnow().isoformat() + "Z"
    })

def _error(msg, code=500, extra=None):
    payload = {"status": "error", "message": msg}
    if extra is not None:
        payload["detail"] = extra
    return jsonify(payload), code

@app.post("/analyze")
def analyze():
    try:
        # Accept both "file" and "audio"
        f = request.files.get("file") or request.files.get("audio")
        if not f:
            return _error("No file provided. Use multipart/form-data field name: file (or audio).", 400)

        filename = f.filename or "unknown"
        # Optional: you can inspect mimetype
        mimetype = f.mimetype or ""

        # Read bytes safely (some hosts need it)
        data = f.read()
        if not data or len(data) < 10:
            return _error("Uploaded file is empty or too small.", 400, {"filename": filename, "mimetype": mimetype})

        # ---- PROTOTYPE ANALYSIS (placeholder) ----
        # Here you will later put real detection / embeddings etc.
        # For now return stable demo numbers
        result = {
            "status": "success",
            "message": "File received",
            "filename": filename,
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
            "ai_voice_prob": 15,
            "scam_score": 42,
            "stress_level": 25,
            "flags": [],
            "summary": "No strong red flags detected in this sample, but stay cautious."
        }
        return jsonify(result)

    except Exception as e:
        # ALWAYS return a JSON detail so backend doesn't show detail:null
        tb = traceback.format_exc()
        return _error("AI analyze crashed.", 500, {"error": str(e), "trace": tb})

if __name__ == "__main__":
    # Local run
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)