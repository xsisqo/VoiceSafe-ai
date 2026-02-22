import os
import uuid
import traceback
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Upload folder (works on Windows + Render)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Max upload size 25MB
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


@app.get("/")
def root():
    return "VoiceSafe AI OK ✅"


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "voicesafe-ai"})


def _safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default


@app.post("/analyze")
def analyze():
    try:
        if "file" not in request.files:
            return jsonify({
                "status": "error",
                "message": "Missing file field. Use multipart/form-data with field name 'file'."
            }), 400

        f = request.files["file"]
        if not f or f.filename == "":
            return jsonify({"status": "error", "message": "Empty filename"}), 400

        # Save file
        ext = os.path.splitext(f.filename)[1].lower()
        safe_name = f"{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(UPLOAD_DIR, safe_name)
        f.save(save_path)

        # ✅ PROTOTYPE scoring (placeholder)
        # Tu neskôr doplníme reálnu detekciu / porovnanie hlasu / podobnosť
        result = {
            "status": "success",
            "message": "File received",
            "filename": f.filename,
            "uploaded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "ai_voice_prob": 15,
            "scam_score": 42,
            "stress_level": 25,
            "summary": "No strong red flags detected in this sample, but stay cautious.",
            "flags": []
        }

        return jsonify(result), 200

    except Exception as e:
        # Toto ti dá reálny dôvod 500 aj do odpovede (na debug)
        tb = traceback.format_exc()
        print("AI ERROR:", str(e))
        print(tb)
        return jsonify({
            "status": "error",
            "message": "AI analyze crashed",
            "detail": str(e)
        }), 500


if __name__ == "__main__":
    # LOCAL run
    app.run(host="127.0.0.1", port=5000, debug=True)