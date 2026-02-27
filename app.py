# file: AI/app.py
import os
import json
import time
import uuid
import shutil
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from queue import (
    set_job, get_job, set_audio, enqueue,
    rate_limit_allow,
)
from db import db_init, list_cases

APP_NAME = "voicesafe-ai"
VERSION = os.environ.get("APP_VERSION", "4.0.0-async")

MAX_MB = int(os.environ.get("MAX_UPLOAD_MB", "25"))
MAX_BYTES = MAX_MB * 1024 * 1024

# TTL & queue settings are in queue.py via env
RL_WINDOW_S = int(os.environ.get("RL_WINDOW_S", "60"))
RL_MAX_REQ = int(os.environ.get("RL_MAX_REQ", "30"))

API_KEY = os.environ.get("API_KEY", "").strip() # optional auth (x-api-key header)

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").strip()
ALLOWED_ORIGINS = ["*"] if CORS_ORIGINS == "*" else [x.strip() for x in CORS_ORIGINS.split(",") if x.strip()]

START_TIME = time.time()


def _check_api_key(request: Request) -> None:
    if not API_KEY:
        return
    got = request.headers.get("x-api-key", "").strip()
    if got != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")


def _get_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "").strip()
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


app = FastAPI(title=APP_NAME, version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# init DB if present
try:
    db_init()
except Exception:
    pass


@app.get("/")
def root() -> Dict[str, Any]:
    return {"ok": True, "service": APP_NAME, "version": VERSION}


@app.get("/health")
def health() -> Dict[str, Any]:
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    return {
        "ok": True,
        "service": APP_NAME,
        "version": VERSION,
        "ffmpeg": ffmpeg_ok,
        "max_upload_mb": MAX_MB,
    }


@app.post("/jobs")
async def create_job(request: Request, file: UploadFile = File(...)) -> Dict[str, Any]:
    _check_api_key(request)
    ip = _get_ip(request)

    # Redis rate-limit (per IP)
    if not rate_limit_allow(ip, RL_WINDOW_S, RL_MAX_REQ):
        raise HTTPException(status_code=429, detail="rate_limited")

    if not file:
        raise HTTPException(status_code=400, detail="missing_file")

    job_id = str(uuid.uuid4())
    filename = (file.filename or "audio.bin").replace("\\", "_").replace("/", "_").strip() or "audio.bin"

    # Stream upload into memory bytes (bounded) then store to Redis with TTL
    size = 0
    buf = bytearray()
    while True:
        chunk = await file.read(1024 * 1024) # 1MB
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_BYTES:
            raise HTTPException(status_code=413, detail=f"file_too_large (max {MAX_MB}MB)")
        buf.extend(chunk)

    if size <= 0:
        raise HTTPException(status_code=400, detail="empty_file")

    # Store audio bytes in Redis for worker (TTL)
    set_audio(job_id, bytes(buf))

    # Create job record
    payload = {
        "id": job_id,
        "status": "queued",
        "created_at": int(time.time()),
        "ip": ip,
        "filename": filename,
        "bytes": size,
    }
    set_job(job_id, json.dumps(payload).encode("utf-8"))

    # Enqueue for worker
    enqueue(job_id)

    return {"ok": True, "job_id": job_id, "status": "queued"}


@app.get("/jobs/{job_id}")
def get_job_status(request: Request, job_id: str) -> Dict[str, Any]:
    _check_api_key(request)

    raw = get_job(job_id)
    if not raw:
        raise HTTPException(status_code=404, detail="job_not_found")

    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {"id": job_id, "status": "unknown", "raw": raw[:200].decode("utf-8", "ignore")}


@app.get("/cases")
def cases(request: Request, limit: int = 50) -> Dict[str, Any]:
    _check_api_key(request)

    try:
        items = list_cases(limit=limit)
        return {"ok": True, "items": items}
    except Exception:
        # If DB not configured, just return empty
        return {"ok": True, "items": [], "note": "DATABASE_URL not configured or DB unavailable"}
