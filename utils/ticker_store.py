"""
utils/ticker_store.py — Persistent ticker watchlist storage using SQLite.
"""

import json
import sqlite3
import os
from typing import List

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alphasignal.db")

DEFAULT_TICKERS = ["AAPL", "NVDA", "TSLA", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN", "META"]


def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_ticker_table():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker     TEXT NOT NULL UNIQUE,
                added_at   TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        if count == 0:
            for t in DEFAULT_TICKERS:
                try:
                    conn.execute("INSERT INTO watchlist (ticker) VALUES (?)", (t,))
                except Exception:
                    pass
            conn.commit()


def get_watchlist() -> List[str]:
    init_ticker_table()
    with _conn() as conn:
        rows = conn.execute("SELECT ticker FROM watchlist ORDER BY added_at ASC").fetchall()
    return [r["ticker"] for r in rows]


def add_ticker(ticker: str) -> bool:
    init_ticker_table()
    try:
        with _conn() as conn:
            conn.execute("INSERT INTO watchlist (ticker) VALUES (?)", (ticker.upper().strip(),))
            conn.commit()
        return True
    except Exception:
        return False


def remove_ticker(ticker: str) -> bool:
    init_ticker_table()
    with _conn() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper().strip(),))
        conn.commit()
    return True


def ticker_exists(ticker: str) -> bool:
    init_ticker_table()
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM watchlist WHERE ticker = ?", (ticker.upper().strip(),)
        ).fetchone()
    return row is not None
