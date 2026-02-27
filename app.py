import os
import numpy as np
import librosa
import soundfile as sf

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)


# ---------------------------
# HEALTH
# ---------------------------
@app.get("/")
def root():
    return jsonify({"ok": True, "service": "voicesafe-ai"})


@app.get("/health")
def health():
    return jsonify({"ok": True})


# ---------------------------
# AUDIO FEATURE ANALYSIS
# ---------------------------
def analyze_audio(path):

    # load audio
    y, sr = librosa.load(path, sr=16000, mono=True)

    duration = librosa.get_duration(y=y, sr=sr)

    # basic features
    rms = np.mean(librosa.feature.rms(y=y))
    zcr = np.mean(librosa.feature.zero_crossing_rate(y))
    spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))

    # pitch stability (AI voices often too stable)
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_values = pitches[magnitudes > np.median(magnitudes)]

    if len(pitch_values) > 0:
        pitch_std = np.std(pitch_values)
    else:
        pitch_std = 0

    # ---------------------------
    # HEURISTIC SCORING
    # ---------------------------

    # AI voice tends to:
    # - lower pitch variance
    # - stable energy
    # - smoother waveform

    ai_probability = 100 - min(100, pitch_std * 10)

    stress_level = min(100, zcr * 1000)

    scam_score = min(
        100,
        (ai_probability * 0.6 + stress_level * 0.4)
    )

    flags = []

    if ai_probability > 70:
        flags.append("Synthetic voice characteristics")

    if stress_level > 50:
        flags.append("High vocal stress detected")

    return {
        "summary": "Audio analyzed using acoustic signal heuristics.",
        "ai_probability": round(float(ai_probability), 1),
        "stress_level": round(float(stress_level), 1),
        "scam_score": round(float(scam_score), 1),
        "flags": flags,
    }


# ---------------------------
# ANALYZE ENDPOINT
# ---------------------------
@app.post("/analyze")
def analyze():

    if "file" not in request.files:
        return jsonify({"error": "Missing file"}), 400

    uploaded = request.files["file"]

    filename = secure_filename(uploaded.filename or "audio.wav")
    path = os.path.join("/tmp", filename)

    uploaded.save(path)

    try:
        result = analyze_audio(path)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            "error": "analysis_failed",
            "message": str(e)
        }), 500


# ---------------------------
# START
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
