from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import hashlib
import os

app = FastAPI(title="VoiceSafe AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_MB = 50
MAX_BYTES = MAX_MB * 1024 * 1024

ALLOWED_PREFIX = ("audio/", "video/")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.content_type.startswith(ALLOWED_PREFIX):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    data = await file.read()

    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    file_hash = hashlib.sha256(data).hexdigest()

    scam = int(file_hash[:2], 16) % 100
    ai_prob = int(file_hash[2:4], 16) % 100
    stress = int(file_hash[4:6], 16) % 100

    risk = "LOW"
    if scam > 70 or ai_prob > 80:
        risk = "HIGH"
    elif scam > 40:
        risk = "MEDIUM"

    return {
        "summary": "Enterprise demo analysis completed.",
        "scam_score": scam,
        "ai_probability": ai_prob,
        "stress_level": stress,
        "risk_level": risk,
        "confidence": 78,
        "flags": ["Prototype scoring"],
    }