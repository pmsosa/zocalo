"""SQLite storage. One file in the data folder; WAL mode so the job runner and the web server can share it."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Iterator

from .config import DATA_DIR

DB_PATH = DATA_DIR / "zocalo.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL,
  is_admin INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS invites (code TEXT PRIMARY KEY, created_by INTEGER, used_by INTEGER, created_at REAL NOT NULL);

CREATE TABLE IF NOT EXISTS providers (
  id INTEGER PRIMARY KEY, kind TEXT NOT NULL, label TEXT NOT NULL, base_url TEXT,
  key_enc TEXT, key_hint TEXT, status TEXT NOT NULL DEFAULT 'unknown', status_msg TEXT,
  checked_at REAL, models_json TEXT NOT NULL DEFAULT '[]', created_at REAL NOT NULL);
-- models chosen for use; prices are per million tokens and editable
CREATE TABLE IF NOT EXISTS models (
  id INTEGER PRIMARY KEY, provider_id INTEGER NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
  model_id TEXT NOT NULL, label TEXT NOT NULL, price_in REAL, price_out REAL,
  enabled INTEGER NOT NULL DEFAULT 1, UNIQUE(provider_id, model_id));

CREATE TABLE IF NOT EXISTS populations (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, country TEXT NOT NULL, source TEXT NOT NULL,
  size INTEGER NOT NULL, seed INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'ready',
  meta_json TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL);
-- a person's base record never changes after it is written
CREATE TABLE IF NOT EXISTS people (
  id INTEGER PRIMARY KEY, population_id INTEGER NOT NULL REFERENCES populations(id) ON DELETE CASCADE,
  name TEXT NOT NULL, base_json TEXT NOT NULL, weight REAL NOT NULL DEFAULT 1, source_ref TEXT);
CREATE INDEX IF NOT EXISTS people_pop ON people(population_id);
-- branches layer changes on top of a base record (trait tweaks, "saw the news", an interview)
CREATE TABLE IF NOT EXISTS branches (
  id INTEGER PRIMARY KEY, person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  parent_id INTEGER, name TEXT NOT NULL, overlay_json TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL);

CREATE TABLE IF NOT EXISTS panels (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, population_id INTEGER NOT NULL REFERENCES populations(id) ON DELETE CASCADE,
  filter_json TEXT NOT NULL DEFAULT '{}', person_ids_json TEXT NOT NULL, created_at REAL NOT NULL);

CREATE TABLE IF NOT EXISTS studies (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, population_id INTEGER NOT NULL,
  panel_id INTEGER, filter_json TEXT NOT NULL DEFAULT '{}', config_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'draft', progress REAL NOT NULL DEFAULT 0, status_msg TEXT,
  cost_estimate REAL, cost_actual REAL NOT NULL DEFAULT 0, created_at REAL NOT NULL, finished_at REAL);
CREATE TABLE IF NOT EXISTS questions (
  id INTEGER PRIMARY KEY, study_id INTEGER NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
  idx INTEGER NOT NULL, text TEXT NOT NULL, options_json TEXT NOT NULL, qtype TEXT NOT NULL DEFAULT 'opinion',
  topical INTEGER NOT NULL DEFAULT 0, meta_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS answers (
  id INTEGER PRIMARY KEY, study_id INTEGER NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
  question_id INTEGER NOT NULL, person_id INTEGER NOT NULL, branch_id INTEGER, arm TEXT NOT NULL DEFAULT 'main',
  model_ref TEXT NOT NULL, spread_json TEXT, answer_idx INTEGER, reason TEXT, prompt_hash TEXT,
  option_order_json TEXT, seed INTEGER, tokens_in INTEGER, tokens_out INTEGER, cost REAL, ok INTEGER NOT NULL DEFAULT 1,
  error TEXT, created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS answers_study ON answers(study_id, question_id);

CREATE TABLE IF NOT EXISTS usage (
  id INTEGER PRIMARY KEY, ts REAL NOT NULL, study_id INTEGER, purpose TEXT NOT NULL, provider_id INTEGER,
  model_ref TEXT, tokens_in INTEGER NOT NULL DEFAULT 0, tokens_out INTEGER NOT NULL DEFAULT 0, cost REAL NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS usage_ts ON usage(ts);

CREATE TABLE IF NOT EXISTS chats (
  id INTEGER PRIMARY KEY, kind TEXT NOT NULL, title TEXT, study_id INTEGER, model_ref TEXT,
  config_json TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS chat_members (
  chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE, person_id INTEGER NOT NULL,
  branch_id INTEGER NOT NULL, stance TEXT, PRIMARY KEY (chat_id, person_id));
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
  role TEXT NOT NULL, person_id INTEGER, content TEXT NOT NULL, meta_json TEXT NOT NULL DEFAULT '{}', ts REAL NOT NULL);

CREATE TABLE IF NOT EXISTS harness_runs (
  id INTEGER PRIMARY KEY, testset TEXT NOT NULL, model_ref TEXT NOT NULL, method TEXT NOT NULL,
  config_json TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'queued', progress REAL NOT NULL DEFAULT 0,
  status_msg TEXT, metrics_json TEXT, created_at REAL NOT NULL, finished_at REAL);
CREATE TABLE IF NOT EXISTS harness_items (
  id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES harness_runs(id) ON DELETE CASCADE,
  item_ref TEXT NOT NULL, qtype TEXT, subgroup TEXT, real_json TEXT NOT NULL, sim_json TEXT NOT NULL,
  abs_error REAL, meta_json TEXT NOT NULL DEFAULT '{}');

CREATE TABLE IF NOT EXISTS human_samples (
  id INTEGER PRIMARY KEY, study_id INTEGER NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
  question_id INTEGER NOT NULL, rows_json TEXT NOT NULL, created_at REAL NOT NULL);

CREATE TABLE IF NOT EXISTS anchors (
  id INTEGER PRIMARY KEY, source TEXT NOT NULL, ref TEXT NOT NULL, country TEXT, year INTEGER,
  text TEXT NOT NULL, options_json TEXT NOT NULL, dist_json TEXT NOT NULL, UNIQUE(source, ref, country));

CREATE TABLE IF NOT EXISTS downloads (
  source_id TEXT PRIMARY KEY, status TEXT NOT NULL, progress REAL NOT NULL DEFAULT 0, message TEXT, updated_at REAL NOT NULL);
"""


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    con = connect()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init() -> None:
    with tx() as con:
        con.executescript(SCHEMA)


def q(sql: str, *args: Any) -> list[dict]:
    con = connect()
    try:
        return [dict(r) for r in con.execute(sql, args).fetchall()]
    finally:
        con.close()


def q1(sql: str, *args: Any) -> dict | None:
    rows = q(sql, *args)
    return rows[0] if rows else None


def ex(sql: str, *args: Any) -> int:
    with tx() as con:
        cur = con.execute(sql, args)
        return cur.lastrowid


def get_setting(key: str, default: Any = None) -> Any:
    row = q1("SELECT value FROM settings WHERE key=?", key)
    return json.loads(row["value"]) if row else default


def set_setting(key: str, value: Any) -> None:
    ex("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
       key, json.dumps(value))


def now() -> float:
    return time.time()


def loads(s: str | None, default: Any = None) -> Any:
    if s is None:
        return default
    try:
        return json.loads(s)
    except (TypeError, ValueError):
        return default
