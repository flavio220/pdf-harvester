"""
Couche base de données — SQLite via sqlite3 standard.
Sur Render : monter un Persistent Disk sur /var/data et pointer DATABASE_PATH=/var/data/app.db
"""
import sqlite3
import os
from flask import g, current_app

DATABASE_PATH = os.environ.get('DATABASE_PATH', 'instance/app.db')


def get_db():
    if 'db' not in g:
        os.makedirs(os.path.dirname(DATABASE_PATH) or '.', exist_ok=True)
        g.db = sqlite3.connect(DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")   # meilleure concurrence
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Crée les tables si elles n'existent pas encore."""
    os.makedirs(os.path.dirname(DATABASE_PATH) or '.', exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            email         TEXT NOT NULL UNIQUE,
            name          TEXT NOT NULL,
            bio           TEXT DEFAULT '',
            avatar_color  TEXT DEFAULT '#4fffb0',
            password_hash TEXT NOT NULL,
            plan          TEXT DEFAULT 'free',
            downloads_used  INTEGER DEFAULT 0,
            bonus_downloads INTEGER DEFAULT 0,
            ref_code      TEXT UNIQUE,
            referred_by   TEXT,
            referrals_count INTEGER DEFAULT 0,
            created_at    TEXT NOT NULL,
            email_verified INTEGER DEFAULT 0,
            is_admin       INTEGER DEFAULT 0,
            is_banned      INTEGER DEFAULT 0,
            FOREIGN KEY (referred_by) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()


def teardown_appcontext(app):
    app.teardown_appcontext(close_db)
