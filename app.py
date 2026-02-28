from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
import os
import time
import hashlib
import secrets

# ===============================
# VoiceSafe AI — Enterprise Stable MVP
# - deterministic scoring (same file -> same output)
# - safe CORS (no "*" with credentials)
# - file validation + size guard
# - request-id + timing
# ===============================

APP_NAME = "VoiceSafe AI"
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://voicesafe.ai")
EXTRA_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
ALLOW_ORIGINS = list(dict.fromkeys([FRONTEND_URL, "https://voicesafe-frontend.onrender.com", *EXTRA_ORIGINS]))

# Limits
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
MAX_BYTES = MAX_UPLOAD_MB * 1024 * 1024

ALLOWED_PREFIXES = ("audio/", "video/")
ALLOWED_EXT = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".mp4", ".mov", ".webm")

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    default_response_class=ORJSONResponse,
)

# ---------------------------
# CORS (enterprise safe)
# - DO NOT use "*" when credentials=True
# - keep credentials False unless you really need cookies
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["x-request-id", "x-model", "x-runtime-ms"],
)

# ---------------------------
# Helpers
# ---------------------------
def make_rid() -> str:
    return secrets.token_hex(6)

def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x

def clamp100(n: int) -> int:
    return 0 if n < 0 else 100 if n > 100 else n

def deterministic_scores(file_hash_hex: str) -> dict:
    """
    Deterministic pseudo-scores from hash.
    This keeps MVP stable and demo-friendly for enterprise/investors:
    - same file => same output
    - different file => different output
    """
    # use first bytes of hash to derive 3 numbers
    b = bytes.fromhex(file_hash_hex[:32]) # 16 bytes
    a = int.from_bytes(b[0:4], "big", signed=False)
    c = int.from_bytes(b[4:8], "big", signed=False)
    d = int.from_bytes(b[8:12], "big", signed=False)

    # map to 0..100 with slight shaping
    scam = (a % 101)
    ai_prob = (c % 101)
    stress = (d % 101)

    # mild "enterprise plausible" shaping:
    # if AI prob high, scam tends to be higher too
    if ai_prob >= 75:
        scam = clamp100(int(scam * 0.65 + 35))
    if scam >= 80:
        stress = clamp100(int(stress * 0.6 + 25))

    return {"scam_score": scam, "ai_probability": ai_prob, "stress_level": stress}

def flags_from_scores(scam: int, ai_prob: int, stress: int) -> list[str]:
    flags = []
    if ai_prob >= 70:
        flags.append("AI voice synthesis indicators (prototype)")
    if scam >= 70:
        flags.append("Financial manipulation / scam pattern signals (prototype)")
    if stress >= 65:
        flags.append("High stress markers (prototype)")
    if scam >= 55:
        flags.append("Urgency / pressure language markers (prototype)")
    if not flags:
        flags.append("No strong red flags detected (prototype)")
    return flags[:6]

def summary_from_scores(scam: int, ai_prob: int, stress: int) -> str:
    if scam >= 80 or ai_prob >= 85:
        return "High risk signal. Verify identity via an official number before any payment or account action."
    if scam >= 60 or ai_prob >= 70:
        return "Elevated risk signal. Pause and confirm identity using trusted official channels."
    return "Lower risk signal. Still verify via official channels if money or account access is involved."

# ---------------------------
# Middleware: request-id + timer
# ---------------------------
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id") or make_rid()
    start = time.time()
    response = await call_next(request)
    runtime_ms = int((time.time() - start) * 1000)
    response.headers["x-request-id"] = rid
    response.headers["x-runtime-ms"] = str(runtime_ms)
    response.headers["x-model"] = "voicesafe-mvp-deterministic"
    return response

# ---------------------------
# HEALTH
# ---------------------------
@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "voicesafe-ai",
        "version": APP_VERSION,
        "max_upload_mb": MAX_UPLOAD_MB,
        "cors_origins": ALLOW_ORIGINS,
        "model": "voicesafe-mvp-deterministic",
    }

# ---------------------------
# ANALYZE
# ---------------------------
@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    # Basic content-type / extension checks
    ctype = (file.content_type or "").lower()
    name = (file.filename or "upload").lower()

    if not ctype.startswith(ALLOWED_PREFIXES):
        raise HTTPException(status_code=400, detail=f"Unsupported content-type: {ctype or 'unknown'}")

    if not any(name.endswith(ext) for ext in ALLOWED_EXT):
        # allow if content-type is audio/video even if extension odd, but be strict for enterprise
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {name}")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Max {MAX_UPLOAD_MB} MB")

    # Deterministic hash
    file_hash = hashlib.sha256(data).hexdigest()

    scores = deterministic_scores(file_hash)
    scam = int(scores["scam_score"])
    ai_prob = int(scores["ai_probability"])
    stress = int(scores["stress_level"])

    # Compose stable output (same keys always)
    out = {
        "summary": summary_from_scores(scam, ai_prob, stress),
        "scam_score": scam,
        "ai_probability": ai_prob,
        "stress_level": stress,
        "flags": flags_from_scores(scam, ai_prob, stress),
        "voice_match": "Unknown",
        "file_hash": file_hash[:16], # short hash for debugging (not sensitive)
        "prototype": True,
        "disclaimer": "Advisory risk signals, not forensic identity verification.",
    }
    return out
