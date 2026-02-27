# file: AI/app.py

import os
import json
import time
import uuid
import shutil
from typing import Any, Dict, Optional

from fastapi import FastAPI, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from job_queue import (
    set_job,
    get_job,
    set_audio,
    enqueue,
    rate_limit_allow,
)

from db import db_init, list_cases


APP_NAME = "voicesafe-ai"
VERSION = os.environ.get("APP_VERSION", "4.0.0-async")

MAX_MB = int(os.environ.get("MAX_UPLOAD_MB", "25"))
MAX_BYTES = MAX_MB * 1024 * 1024

RL_WINDOW_S = int(os.environ.get("RL_WINDOW_S", "60"))
RL_MAX_REQ = int(os.environ.get("RL_MAX_REQ", "30"))

API_KEY = os.environ.get("API_KEY", "").strip()

UPLOAD_DIR = "uploads_ai"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title=APP_NAME, version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_init()


# =========================
# Health
# =========================
@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": VERSION,
        "timestamp": int(time.time()),
    }


# =========================
# Analyze endpoint
# =========================
@app.post("/analyze")
async def analyze(request: Request, file: UploadFile):

    # Optional API key protection
    if API_KEY:
        header_key = request.headers.get("x-api-key", "")
        if header_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")

    # Rate limit
    client_ip = request.client.host
    if not rate_limit_allow(client_ip, RL_WINDOW_S, RL_MAX_REQ):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Validate size
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {MAX_MB}MB allowed.",
        )

    job_id = str(uuid.uuid4())
    filename = f"{job_id}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(content)

    set_audio(job_id, path)
    set_job(job_id, {"status": "queued", "created": int(time.time())})

    enqueue(job_id)

    return {
        "job_id": job_id,
        "status": "queued",
    }


# =========================
# Job status
# =========================
@app.get("/job/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# =========================
# Cases list
# =========================
@app.get("/cases")
def cases():
    return list_cases()


# =========================
# Root
# =========================
@app.get("/")
def root():
    return {
        "message": "VoiceSafe AI is running",
        "version": VERSION,
    }