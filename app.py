import os
import numpy as np
import librosa
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# ==========================
# ROOT / HEALTH
# ==========================

@app.get("/")
def root():
    return {"ok": True, "service": "voicesafe-ai"}

@app.get("/health")
def health():
    return {"ok": True}


# ==========================
# AUDIO ANALYSIS CORE
# ==========================

def analyze_audio(path):

    # load audio (auto converts mp3/wav)
    y, sr = librosa.load(path, sr=16000, mono=True)

    duration = librosa.get_duration(y=y, sr=sr)

    # ---------- FEATURES ----------
    rms = np.mean(librosa.feature.rms(y=y))
    zcr = np.mean(librosa.feature.zero_crossing_rate(y))
    spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))

    # pitch estimation
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_values = pitches[magnitudes > np.median(magnitudes)]

    if len(pitch_values) > 0:
        pitch_mean = float(np.mean(pitch_values))
        pitch_std = float(np.std(pitch_values))
    else:
        pitch_mean = 0
        pitch_std = 0

    # ==========================
    # AI VOICE HEURISTIC
    # ==========================
    ai_probability = 0

    # synthetic voices often:
    if pitch_std < 20:
        ai_probability += 35

    if zcr < 0.05:
        ai_probability += 25

    if spectral_centroid < 1500:
        ai_probability += 20

    if duration < 2:
        ai_probability += 10

    ai_probability = int(min(ai_probability, 100))

    # ==========================
    # STRESS ESTIMATION
    # ==========================
    stress_level = int(min(pitch_std * 2, 100))

    # ==========================
    # SCAM SCORE
    # ==========================
    scam_score = int(
        min(
            (ai_probability * 0.6) +
            (stress_level * 0.4),
            100
        )
    )

    # FLAGS
    flags = []

    if ai_probability > 70:
        flags.append("Possible AI voice synthesis")

    if stress_level > 60:
        flags.append("Elevated vocal stress")

    if duration < 1.5:
        flags.append("Very short suspicious sample")

    summary = (
        "High probability of synthetic or manipulated voice."
        if ai_probability > 70
        else "Voice appears human with moderate confidence."
    )

    return {
        "summary": summary,
        "ai_probability": ai_probability,
        "stress_level": stress_level,
        "scam_score": scam_score,
        "flags": flags,
    }


# ==========================
# ANALYZE ENDPOINT
# ==========================

@app.post("/analyze")
def analyze():

    if "file" not in request.files:
        return {"error": "Missing file"}, 400

    uploaded = request.files["file"]

    filename = secure_filename(uploaded.filename or "audio.bin")
    save_path = f"/tmp/{filename}"

    data = uploaded.read()

    if not data:
        return {"error": "Empty file"}, 400

    with open(save_path, "wb") as f:
        f.write(data)

    try:
        result = analyze_audio(save_path)
        return jsonify(result)

    except Exception as e:
        print("ANALYZE ERROR:", str(e))
        return jsonify({
            "summary": "Analysis failed",
            "ai_probability": 0,
            "stress_level": 0,
            "scam_score": 0,
            "flags": ["Processing error"]
        })


# ==========================
# START
# ==========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)