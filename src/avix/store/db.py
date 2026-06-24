import sqlite3
from pathlib import Path
from .. import config

DB_PATH = config.ROOT / "data" / "avix.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS businesses (
  id INTEGER PRIMARY KEY, name TEXT, category TEXT, area TEXT,
  UNIQUE(name, category, area));
CREATE TABLE IF NOT EXISTS mentions (
  id INTEGER PRIMARY KEY, date TEXT, area TEXT, category TEXT, engine TEXT,
  archetype TEXT, business TEXT, rank INTEGER, accuracy TEXT, sentiment TEXT,
  source TEXT, prompt_text TEXT);
CREATE TABLE IF NOT EXISTS raw_responses (
  id INTEGER PRIMARY KEY, ts TEXT, category TEXT, area TEXT, engine TEXT,
  archetype TEXT, prompt_text TEXT, raw TEXT, reviewed INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY, ts TEXT, business TEXT, email TEXT, category TEXT,
  area TEXT, verdict TEXT);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY, ts TEXT, event TEXT, ref TEXT);
"""

def connect(path: Path | None = None) -> sqlite3.Connection:
    p = Path(path) if path else DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
