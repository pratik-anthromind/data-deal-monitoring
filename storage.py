"""SQLite storage for signal dedup and history tracking."""

import csv
import json
import sqlite3
from pathlib import Path

import config


def _get_conn() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            title TEXT,
            text TEXT,
            author TEXT,
            extra_json TEXT,
            category TEXT,
            pain_intensity INTEGER DEFAULT 0,
            urgency INTEGER DEFAULT 0,
            commercial_context INTEGER DEFAULT 0,
            decision_maker INTEGER DEFAULT 0,
            anthromind_fit INTEGER DEFAULT 0,
            total_score INTEGER DEFAULT 0,
            haiku_reasoning TEXT,
            notified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS seen_urls (
            url TEXT PRIMARY KEY,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def is_seen(url: str) -> bool:
    """Check if a URL has already been processed."""
    conn = _get_conn()
    row = conn.execute("SELECT 1 FROM seen_urls WHERE url = ?", (url,)).fetchone()
    conn.close()
    return row is not None


def mark_seen(url: str):
    """Mark a URL as processed."""
    conn = _get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO seen_urls (url) VALUES (?)", (url,)
    )
    conn.commit()
    conn.close()


def save_signal(signal: dict, scores: dict):
    """Save a scored signal to the database."""
    conn = _get_conn()
    extra = {k: v for k, v in signal.items()
             if k not in ("source", "url", "title", "text", "author")}
    conn.execute(
        """INSERT OR IGNORE INTO signals
           (source, url, title, text, author, extra_json,
            category, pain_intensity, urgency, commercial_context,
            decision_maker, anthromind_fit, total_score, haiku_reasoning)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            signal.get("source", ""),
            signal.get("url", ""),
            signal.get("title", ""),
            signal.get("text", ""),
            signal.get("author", ""),
            json.dumps(extra),
            scores.get("category", ""),
            scores.get("pain_intensity", 0),
            scores.get("urgency", 0),
            scores.get("commercial_context", 0),
            scores.get("decision_maker", 0),
            scores.get("anthromind_fit", 0),
            scores.get("total_score", 0),
            scores.get("reasoning", ""),
        ),
    )
    conn.commit()
    conn.close()


def mark_notified(url: str):
    """Mark a signal as having triggered a Slack notification."""
    conn = _get_conn()
    conn.execute("UPDATE signals SET notified = 1 WHERE url = ?", (url,))
    conn.commit()
    conn.close()


def is_in_outreach_log(author: str) -> bool:
    """Check if an author has already been contacted via auto-bdr."""
    log_path = Path(config.AUTO_BDR_OUTREACH_LOG)
    if not log_path.exists():
        return False
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Check if the Reddit/GitHub username appears anywhere in the row
                for val in row.values():
                    if val and author.lower() in val.lower():
                        return True
    except Exception:
        pass
    return False
