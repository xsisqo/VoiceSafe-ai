# file: AI/worker.py
import json
import os
import time
import shutil
import tempfile
import math
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
import librosa

from queue import (
    dequeue_block,
    get_audio,
    del_audio,
    get_job,
    set_job,
)
from db import db_init, insert_analysis


APP_NAME = "voicesafe-ai-worker"
VERSION = os.environ.get("APP_VERSION", "4.0.0-async")

TARGET_SR = int(os.environ.get("TARGET_SR", "16000"))
MAX_DURATION_S = float(os.environ.get("MAX_DURATION_S", "120"))
MIN_DURATION_S = float(os.environ.get("MIN_DURATION_S", "0.6"))

POLL_TIMEOUT_S = int(os.environ.get("WORKER_BLPOP_TIMEOUT_S", "30"))


def _clamp(x, a=0.0, b=100.0) -> float:
    try:
        x = float(x)
    except Exception:
        x = 0.0
    return max(a, min(b, x))


def _finite(x: Any) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64)
    return arr[np.isfinite(arr)]


def _safe_mean(x: Any) -> float:
    x = _finite(x)
    return float(np.mean(x)) if x.size else 0.0


def _safe_std(x: Any) -> float:
    x = _finite(x)
    return float(np.std(x)) if x.size else 0.0


def _sigmoid01(x: float) -> float:
    x = float(x)
    if x >= 35:
        return 1.0
    if x <= -35:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _ffmpeg_to_wav(src_path: str, dst_path: str) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg_not_installed")

    cmd = [
        ffmpeg, "-nostdin", "-y",
        "-i", src_path,
        "-ac", "1",
        "-ar", str(TARGET_SR),
        "-vn",
        dst_path,
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        err = (p.stderr or "").strip()
        if len(err) > 1400:
            err = err[-1400:]
        raise RuntimeError(f"ffmpeg_convert_failed: {err}")


@dataclass
class LoadInfo:
    sr: int
    duration_s: float
    loader: str


def _load_audio_any(path: str) -> Tuple[np.ndarray, LoadInfo]:
    try:
        y, sr = librosa.load(path, sr=TARGET_SR, mono=True)
        dur = float(librosa.get_duration(y=y, sr=sr))
        if not np.isfinite(dur) or dur <= 0 or y.size == 0:
            raise RuntimeError("invalid_audio")
        return y, LoadInfo(int(sr), dur, "librosa")
    except Exception:
        pass

    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "converted.wav")
        _ffmpeg_to_wav(path, wav_path)
        y, sr = librosa.load(wav_path, sr=TARGET_SR, mono=True)
        dur = float(librosa.get_duration(y=y, sr=sr))
        if not np.isfinite(dur) or dur <= 0 or y.size == 0:
            raise RuntimeError("invalid_audio_after_ffmpeg")
        return y, LoadInfo(int(sr), dur, "ffmpeg->librosa")


def _normalize_and_trim(y: np.ndarray, sr: int) -> np.ndarray:
    y = y.astype(np.float32, copy=False)
    max_n = int(MAX_DURATION_S * sr)
    if max_n > 0 and y.size > max_n:
        y = y[:max_n]
    y = y - float(np.mean(y))
    peak = float(np.max(np.abs(y)) + 1e-9)
    return y / peak


def analyze_audio(path: str) -> Dict[str, Any]:
    y, info = _load_audio_any(path)
    if info.duration_s < MIN_DURATION_S:
        raise RuntimeError("too_short_audio")

    y = _normalize_and_trim(y, info.sr)

    rms = _safe_mean(librosa.feature.rms(y=y))
    zcr = _safe_mean(librosa.feature.zero_crossing_rate(y))
    centroid = _safe_mean(librosa.feature.spectral_centroid(y=y, sr=info.sr))
    flatness = _safe_mean(librosa.feature.spectral_flatness(y=y))
    rolloff = _safe_mean(librosa.feature.spectral_rolloff(y=y, sr=info.sr, roll_percent=0.85))

    mfcc = librosa.feature.mfcc(y=y, sr=info.sr, n_mfcc=13)
    mfcc_std = _safe_mean(np.std(mfcc, axis=1))

    f0 = librosa.yin(y, fmin=70, fmax=400, sr=info.sr)
    f0 = _finite(f0)
    f0 = f0[(f0 > 50) & (f0 < 500)]
    f0_mean = _safe_mean(f0)
    f0_std = _safe_std(f0)

    if f0.size >= 4 and f0_mean > 1e-6:
        jitter = float(np.median(np.abs(np.diff(f0))) / f0_mean)
    else:
        jitter = 0.0

    rms_frames = librosa.feature.rms(y=y).flatten()
    rms_var = _safe_std(rms_frames)

    s_smooth = 1.0 - _clamp(jitter * 220.0, 0, 100) / 100.0
    s_mfcc = 1.0 - _clamp(mfcc_std * 18.0, 0, 100) / 100.0
    s_f0std = 1.0 - _clamp(f0_std * 0.45, 0, 100) / 100.0
    s_flat = _clamp(flatness * 140.0, 0, 100) / 100.0

    s_zcr = _clamp(zcr * 1300.0, 0, 100) / 100.0
    s_rmsvar = _clamp(rms_var * 85.0, 0, 100) / 100.0
    s_cent = _clamp((centroid / 5000.0) * 100.0, 0, 100) / 100.0

    compression_hint = _clamp(((rolloff / 8000.0) - (centroid / 5000.0)) * 140.0 + 50.0, 0, 100) / 100.0

    ai_raw = (0.36 * s_smooth) + (0.26 * s_mfcc) + (0.22 * s_f0std) + (0.16 * s_flat)
    ai_prob = 100.0 * _sigmoid01((ai_raw - 0.52) * 6.0)

    stress_raw = (0.48 * s_zcr) + (0.32 * s_rmsvar) + (0.20 * s_cent)
    stress_level = 100.0 * _sigmoid01((stress_raw - 0.40) * 6.0)

    scam_raw = (0.62 * (ai_prob / 100.0)) + (0.28 * (stress_level / 100.0)) + (0.10 * compression_hint)
    scam_score = 100.0 * _sigmoid01((scam_raw - 0.48) * 7.0)

    flags: List[str] = []
    if ai_prob >= 75:
        flags.append("Synthetic voice characteristics (prototype)")
    if stress_level >= 70:
        flags.append("High vocal stress detected (prototype)")
    if compression_hint >= 0.72:
        flags.append("High compression / telephony-like signal (prototype)")
    if info.duration_s < 2.0:
        flags.append("Very short sample (lower confidence)")

    if scam_score >= 75:
        summary = "High-risk pattern detected (prototype). Verify identity via official channels."
    elif scam_score >= 45:
        summary = "Moderate risk indicators detected (prototype). Stay cautious and verify the caller."
    else:
        summary = "Low risk indicators in this sample (prototype), but remain cautious."

    return {
        "summary": summary,
        "scam_score": round(_clamp(scam_score), 1),
        "ai_voice_prob": round(_clamp(ai_prob), 1),
        "stress_level": round(_clamp(stress_level), 1),
        "flags": flags,
        "voice_match": "Unknown",
        "meta": {
            "version": VERSION,
            "duration_s": round(float(info.duration_s), 3),
            "sr": int(info.sr),
            "loader": info.loader,
        },
    }


def _job_update(job_id: str, patch: Dict[str, Any]) -> None:
    raw = get_job(job_id)
    if raw:
        try:
            obj = json.loads(raw.decode("utf-8"))
        except Exception:
            obj = {"id": job_id}
    else:
        obj = {"id": job_id}

    obj.update(patch)
    set_job(job_id, json.dumps(obj).encode("utf-8"))


def main():
    # init DB if present
    try:
        db_init()
    except Exception:
        pass

    print(f"[worker] started {APP_NAME} version={VERSION}")

    while True:
        job_id = dequeue_block(timeout_s=POLL_TIMEOUT_S)
        if not job_id:
            continue

        t0 = time.time()
        _job_update(job_id, {"status": "processing", "started_at": int(time.time())})

        audio = get_audio(job_id)
        if not audio:
            _job_update(job_id, {"status": "failed", "error": "audio_missing_or_expired"})
            continue

        tmp_dir = tempfile.mkdtemp(prefix="voicesafe_worker_")
        file_path = os.path.join(tmp_dir, "input.bin")

        try:
            with open(file_path, "wb") as f:
                f.write(audio)

            result = analyze_audio(file_path)

            # Persist to DB (optional)
            try:
                insert_analysis({
                    "id": job_id,
                    "ip": (get_job(job_id) and json.loads(get_job(job_id).decode("utf-8")).get("ip")) or None,
                    "filename": (get_job(job_id) and json.loads(get_job(job_id).decode("utf-8")).get("filename")) or None,
                    "bytes": len(audio),
                    "scam_score": float(result.get("scam_score", 0.0)),
                    "ai_voice_prob": float(result.get("ai_voice_prob", 0.0)),
                    "stress_level": float(result.get("stress_level", 0.0)),
                    "summary": str(result.get("summary", ""))[:2000],
                    "flags": json.dumps(result.get("flags", [])),
                    "meta": json.dumps(result.get("meta", {})),
                })
            except Exception:
                pass

            _job_update(job_id, {
                "status": "done",
                "finished_at": int(time.time()),
                "result": result,
                "ms": round((time.time() - t0) * 1000.0, 2),
            })

        except Exception as e:
            _job_update(job_id, {"status": "failed", "error": str(e)[:200]})
        finally:
            # cleanup
            del_audio(job_id) # free Redis memory
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()