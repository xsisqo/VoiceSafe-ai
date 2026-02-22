from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "VoiceSafe AI running"

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "voicesafe-ai"})

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file"}), 400

        file = request.files["file"]

        # Fake AI analysis (prototype)
        result = {
            "status": "success",
            "message": "File received",
            "filename": file.filename,
            "uploaded_at": datetime.utcnow().isoformat(),
            "ai_voice_prob": 15,
            "scam_score": 42,
            "stress_level": 25,
            "flags": [],
            "summary": "No strong red flags detected in this sample, but stay cautious."
        }

        return jsonify(result)

    except Exception as e:
        print("AI ERROR:", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# 🔥 VERY IMPORTANT FOR RENDER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)