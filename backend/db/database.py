import sqlite3
import os
from contextlib import contextmanager
from backend.config import DB_PATH


def init_db():
    """Create the database file and required tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS screenings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL,               -- 'recruiter' or 'student'
                job_description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screening_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                resume_text TEXT NOT NULL,         -- full text retained (per project decision)
                skills_score REAL,
                experience_score REAL,
                similarity_score REAL,
                evidence_score REAL,
                final_score REAL,
                fit_label TEXT,                    -- Strong Fit / Partial Fit / No Fit
                priority_label TEXT,                -- High / Medium / Low
                judge_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (screening_id) REFERENCES screenings (id)
            )
        """)

        conn.commit()


@contextmanager
def get_connection():
    """Provides a SQLite connection as a context manager."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()