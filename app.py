from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# IMPORTANT FOR RENDER UPLOADS
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024 # 200MB

@app.route("/")
def home():
    return "VoiceSafe AI running"

@app.route("/analyze", methods=["POST"])
def analyze():

    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files["file"]

    filename = file.filename
    save_path = f"/tmp/{filename}"
    file.save(save_path)

    # --- DEMO AI RESULT ---
    result = {
        "summary": "No strong red flags detected.",
        "ai_probability": 15,
        "stress_level": 25,
        "scam_score": 10,
        "flags": [],
        "voice_match": "Unknown"
    }

    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)