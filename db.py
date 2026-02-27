# file: AI/db.py
import os
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

engine = None
if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
    )


DDL = """
CREATE TABLE IF NOT EXISTS analyses (
  id TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ip TEXT,
  filename TEXT,
  bytes BIGINT,
  scam_score REAL,
  ai_voice_prob REAL,
  stress_level REAL,
  summary TEXT,
  flags JSONB,
  meta JSONB
);
"""


def db_init() -> None:
    if not engine:
        return
    with engine.begin() as conn:
        conn.execute(text(DDL))


def insert_analysis(row: Dict[str, Any]) -> None:
    if not engine:
        return
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO analyses
                (id, ip, filename, bytes, scam_score, ai_voice_prob, stress_level, summary, flags, meta)
                VALUES
                (:id, :ip, :filename, :bytes, :scam_score, :ai_voice_prob, :stress_level, :summary, :flags::jsonb, :meta::jsonb)
            """),
            row,
        )


def list_cases(limit: int = 50) -> List[Dict[str, Any]]:
    if not engine:
        return []
    limit = max(1, min(int(limit), 200))
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, created_at, ip, filename, bytes, scam_score, ai_voice_prob, stress_level, summary, flags, meta
                FROM analyses
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"limit": limit},
        ).mappings().all()
        return [dict(r) for r in rows]