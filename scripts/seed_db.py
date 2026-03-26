#!/usr/bin/env python3
"""
scripts/seed_db.py — Initialize and optionally seed the database.

Usage:
    python scripts/seed_db.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import log
from utils.database import init_db

def main():
    log.info("Initializing database...")
    init_db()
    log.info("Database ready.")

if __name__ == "__main__":
    main()
