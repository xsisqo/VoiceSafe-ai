from flask import Flask, request, jsonify
from flask_cors import CORS
import datetime

app = Flask(__name__)

# väčší upload limit (napr. 50MB)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

CORS(app)

@app.get("/")
def root():
    return "VoiceSafe AI OK ✅", 200

@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "voicesafe-ai"}), 200

@app.post("/analyze")
def analyze():
    if "file" not in request.files:
        return jsonify({"status":"error","message":"No file field 'file' provided"}), 400

    f = request.files["file"]
    filename = f.filename or "unknown"

    # PROTOTYPE odpoveď (teraz je to dummy)
    out = {
        "status": "success",
        "message": "File received",
        "filename": filename,
        "uploaded_at": datetime.datetime.utcnow().isoformat() + "Z",
        "ai_voice_prob": 15,
        "scam_score": 42,
        "stress_level": 25,
        "flags": [],
        "summary": "No strong red flags detected in this sample, but stay cautious."
    }
    return jsonify(out), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)