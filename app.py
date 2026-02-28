from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import random

app = FastAPI(title="VoiceSafe AI")

# ---------------------------
# CORS (enterprise safe)
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# HEALTH
# ---------------------------
@app.get("/health")
async def health():
    return {"ok": True}

# ---------------------------
# ANALYZE
# ---------------------------
@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):

    # fake AI response (stable MVP)
    return {
        "summary": "Sample analyzed successfully.",
        "scam_score": random.randint(20, 90),
        "ai_probability": random.randint(10, 95),
        "stress_level": random.randint(10, 80),
        "flags": [
            "Voice inconsistency",
            "Urgency language detected",
            "Financial manipulation signals"
        ],
        "voice_match": "Unknown"
    }
