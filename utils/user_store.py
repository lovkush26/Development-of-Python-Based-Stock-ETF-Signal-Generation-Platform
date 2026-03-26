"""
utils/user_store.py — Persistent user and alert history storage using SQLite.

Users and alert history are saved to the database and survive restarts.
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alphasignal.db")


def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_user_tables():
    """Create alert_users and alert_history tables if they don't exist."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                phone       TEXT,
                email       TEXT,
                channels    TEXT DEFAULT 'sms',
                min_confidence REAL DEFAULT 0.65,
                tickers     TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name   TEXT,
                ticker      TEXT,
                signal      TEXT,
                confidence  REAL,
                price       REAL,
                channel     TEXT,
                message     TEXT,
                sent_at     TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


def get_all_users() -> List[dict]:
    """Return all registered alert users."""
    init_user_tables()
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM alert_users ORDER BY created_at DESC").fetchall()
    users = []
    for r in rows:
        users.append({
            "id":             r["id"],
            "name":           r["name"],
            "phone":          r["phone"] or "",
            "email":          r["email"] or "",
            "channels":       json.loads(r["channels"]) if r["channels"] else [],
            "min_confidence": r["min_confidence"],
            "tickers":        json.loads(r["tickers"]) if r["tickers"] else None,
            "created_at":     r["created_at"],
        })
    return users


def add_user(
    name: str,
    phone: str = None,
    email: str = None,
    channels: list = None,
    min_confidence: float = 0.65,
    tickers: list = None,
) -> bool:
    """Add a new user. Returns True on success, False if name already exists."""
    init_user_tables()
    try:
        with _conn() as conn:
            conn.execute("""
                INSERT INTO alert_users (name, phone, email, channels, min_confidence, tickers)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                phone or None,
                email or None,
                json.dumps(channels or ["sms"]),
                min_confidence,
                json.dumps(tickers) if tickers else None,
            ))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def delete_user(user_id: int) -> bool:
    """Delete a user by ID."""
    init_user_tables()
    with _conn() as conn:
        conn.execute("DELETE FROM alert_users WHERE id = ?", (user_id,))
        conn.commit()
    return True


def log_alert(
    user_name: str,
    ticker: str,
    signal: str,
    confidence: float,
    price: float,
    channel: str,
    message: str,
):
    """Save an alert delivery record to history."""
    init_user_tables()
    with _conn() as conn:
        conn.execute("""
            INSERT INTO alert_history (user_name, ticker, signal, confidence, price, channel, message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_name, ticker, signal, confidence, price, channel, message))
        conn.commit()


def get_alert_history(user_name: str = None, limit: int = 50) -> List[dict]:
    """Return alert history, optionally filtered by user."""
    init_user_tables()
    with _conn() as conn:
        if user_name:
            rows = conn.execute("""
                SELECT * FROM alert_history
                WHERE user_name = ?
                ORDER BY sent_at DESC LIMIT ?
            """, (user_name, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM alert_history
                ORDER BY sent_at DESC LIMIT ?
            """, (limit,)).fetchall()
    return [dict(r) for r in rows]