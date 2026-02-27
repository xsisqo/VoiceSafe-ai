# AI/job_queue.py
import os
import json
import time
import uuid
from typing import Any, Dict, Optional, Tuple

# ============================================================
# VoiceSafe AI - Job Queue
# - Works with Redis if REDIS_URL is set
# - Falls back to in-memory mode if REDIS_URL is missing
# ============================================================

APP_PREFIX = os.getenv("APP_PREFIX", "voicesafe")
REDIS_URL = (os.getenv("REDIS_URL", "") or "").strip()

# Rate limit defaults (can be overridden from env)
RL_WINDOW_S = int(os.getenv("RL_WINDOW_S", "60"))
RL_MAX_REQ = int(os.getenv("RL_MAX_REQ", "30"))

# Redis keys
JOBS_KEY = f"{APP_PREFIX}:jobs" # hash: job_id -> json
AUDIO_KEY = f"{APP_PREFIX}:audio" # hash: job_id -> json (path/meta)
QUEUE_KEY = f"{APP_PREFIX}:queue" # list: job_id
DONE_KEY = f"{APP_PREFIX}:done" # list: job_id (optional)


# ----------------------------
# In-memory fallback storage
# ----------------------------
_mem_jobs: Dict[str, Dict[str, Any]] = {}
_mem_audio: Dict[str, Dict[str, Any]] = {}
_mem_queue: list[str] = []
_mem_done: list[str] = []
_mem_rate: Dict[str, list[float]] = {} # key -> timestamps


# ----------------------------
# Redis client (lazy)
# ----------------------------
_redis = None

def _get_redis():
    """
    Returns a redis client if REDIS_URL is provided and redis is available.
    Otherwise returns None (in-memory fallback).
    """
    global _redis
    if not REDIS_URL:
        return None

    if _redis is not None:
        return _redis

    try:
        import redis # redis==5.x
        _redis = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True, # store strings
            socket_timeout=5,
            socket_connect_timeout=5,
            health_check_interval=30,
        )
        # quick ping to validate
        _redis.ping()
        return _redis
    except Exception as e:
        # If Redis misconfigured/unreachable, fall back to memory
        print(f"⚠️ Redis not available, falling back to memory mode. Reason: {e}")
        _redis = None
        return None


# ============================================================
# Rate limiting
# ============================================================

def rate_limit_allow(
    key: str,
    limit: int = RL_MAX_REQ,
    window_s: int = RL_WINDOW_S,
) -> bool:
    """
    Simple fixed-window limiter:
    - Redis: INCR + EXPIRE
    - Memory: timestamps list in window
    """
    r = _get_redis()
    bucket = f"{APP_PREFIX}:rl:{key}:{int(time.time() // window_s)}"

    if r:
        try:
            val = r.incr(bucket)
            if val == 1:
                r.expire(bucket, window_s + 2)
            return val <= limit
        except Exception as e:
            print(f"⚠️ Redis rate-limit failed, using memory. Reason: {e}")

    # Memory fallback: sliding window timestamps
    now = time.time()
    arr = _mem_rate.get(key, [])
    arr = [t for t in arr if now - t < window_s]
    if len(arr) >= limit:
        _mem_rate[key] = arr
        return False
    arr.append(now)
    _mem_rate[key] = arr
    return True


# ============================================================
# Job storage
# ============================================================

def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def _json_loads(s: str) -> Any:
    return json.loads(s)

def set_job(job_id: str, data: Dict[str, Any]) -> None:
    """
    Store job metadata.
    """
    r = _get_redis()
    if r:
        try:
            r.hset(JOBS_KEY, job_id, _json_dumps(data))
            return
        except Exception as e:
            print(f"⚠️ Redis set_job failed, using memory. Reason: {e}")

    _mem_jobs[job_id] = data


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch job metadata.
    """
    r = _get_redis()
    if r:
        try:
            val = r.hget(JOBS_KEY, job_id)
            if not val:
                return None
            return _json_loads(val)
        except Exception as e:
            print(f"⚠️ Redis get_job failed, using memory. Reason: {e}")

    return _mem_jobs.get(job_id)


def set_audio(job_id: str, audio_path: str, extra: Optional[Dict[str, Any]] = None) -> None:
    """
    Store audio location for a job.
    We store a JSON blob with at least {"path": "..."}.
    """
    payload: Dict[str, Any] = {"path": audio_path}
    if extra:
        payload.update(extra)

    r = _get_redis()
    if r:
        try:
            r.hset(AUDIO_KEY, job_id, _json_dumps(payload))
            return
        except Exception as e:
            print(f"⚠️ Redis set_audio failed, using memory. Reason: {e}")

    _mem_audio[job_id] = payload


def get_audio(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch audio info for a job.
    """
    r = _get_redis()
    if r:
        try:
            val = r.hget(AUDIO_KEY, job_id)
            if not val:
                return None
            return _json_loads(val)
        except Exception as e:
            print(f"⚠️ Redis get_audio failed, using memory. Reason: {e}")

    return _mem_audio.get(job_id)


# ============================================================
# Queue operations
# ============================================================

def enqueue(job_id: str) -> None:
    """
    Enqueue a job id for processing (worker consumes this).
    """
    r = _get_redis()
    if r:
        try:
            r.rpush(QUEUE_KEY, job_id)
            return
        except Exception as e:
            print(f"⚠️ Redis enqueue failed, using memory. Reason: {e}")

    _mem_queue.append(job_id)


def dequeue(block: bool = False, timeout_s: int = 10) -> Optional[str]:
    """
    Pop next job id (for worker).
    - Redis: BLPOP (blocking) or LPOP
    - Memory: pop(0)
    """
    r = _get_redis()
    if r:
        try:
            if block:
                item = r.blpop(QUEUE_KEY, timeout=timeout_s)
                if not item:
                    return None
                _, job_id = item
                return job_id
            return r.lpop(QUEUE_KEY)
        except Exception as e:
            print(f"⚠️ Redis dequeue failed, using memory. Reason: {e}")

    if not _mem_queue:
        return None
    return _mem_queue.pop(0)


def mark_done(job_id: str) -> None:
    """
    Optional: track completed jobs.
    """
    r = _get_redis()
    if r:
        try:
            r.rpush(DONE_KEY, job_id)
            return
        except Exception as e:
            print(f"⚠️ Redis mark_done failed, using memory. Reason: {e}")

    _mem_done.append(job_id)


# ============================================================
# Helpers
# ============================================================

def new_job_id(prefix: str = "job") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def health() -> Dict[str, Any]:
    """
    Small health helper for /health endpoint.
    """
    r = _get_redis()
    if r:
        try:
            r.ping()
            return {"ok": True, "mode": "redis", "redis": True}
        except Exception as e:
            return {"ok": True, "mode": "memory", "redis": False, "note": str(e)}
    return {"ok": True, "mode": "memory", "redis": False}