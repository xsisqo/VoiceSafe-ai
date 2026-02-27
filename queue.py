# file: AI/queue.py
import os
import time
from typing import Any, Dict, Optional, Tuple

import redis as redis_lib

APP_NAME = "voicesafe-ai"

REDIS_URL = os.environ.get("REDIS_URL", "").strip()
JOB_TTL_S = int(os.environ.get("JOB_TTL_S", "3600")) # job status/result TTL (1h)
AUDIO_TTL_S = int(os.environ.get("AUDIO_TTL_S", "900")) # audio bytes TTL (15m)
QUEUE_NAME = os.environ.get("QUEUE_NAME", "voicesafe:jobs")

if not REDIS_URL:
    raise RuntimeError("REDIS_URL is required for async jobs architecture")

r = redis_lib.from_url(REDIS_URL, decode_responses=False)


def qkey_job(job_id: str) -> str:
    return f"job:{job_id}"


def qkey_audio(job_id: str) -> str:
    return f"audio:{job_id}"


def set_job(job_id: str, payload_json: bytes) -> None:
    r.setex(qkey_job(job_id), JOB_TTL_S, payload_json)


def get_job(job_id: str) -> Optional[bytes]:
    return r.get(qkey_job(job_id))


def set_audio(job_id: str, audio_bytes: bytes) -> None:
    r.setex(qkey_audio(job_id), AUDIO_TTL_S, audio_bytes)


def get_audio(job_id: str) -> Optional[bytes]:
    return r.get(qkey_audio(job_id))


def del_audio(job_id: str) -> None:
    try:
        r.delete(qkey_audio(job_id))
    except Exception:
        pass


def enqueue(job_id: str) -> None:
    # Use LPUSH + worker BLPOP
    r.lpush(QUEUE_NAME, job_id.encode("utf-8"))


def dequeue_block(timeout_s: int = 30) -> Optional[str]:
    # BLPOP returns (queue_name, value)
    item = r.blpop(QUEUE_NAME, timeout=timeout_s)
    if not item:
        return None
    _, val = item
    try:
        return val.decode("utf-8")
    except Exception:
        return None


def rate_limit_allow(ip: str, window_s: int, max_req: int) -> bool:
    """
    Simple Redis rate limit: INCR + EXPIRE, per IP per window.
    """
    key = f"rl:{ip}:{int(time.time() // window_s)}"
    pipe = r.pipeline()
    pipe.incr(key, 1)
    pipe.expire(key, window_s + 5)
    count, _ = pipe.execute()
    return int(count) <= int(max_req)
