from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).with_name("lab.db")

SCHEMA_SQL = """
DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0)
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    score REAL NOT NULL CHECK (score >= 0 AND score <= 100),
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'dropped')),
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id)
);
"""

SEED_SQL = """
INSERT INTO students (name, cohort, email) VALUES
    ('An Nguyen', 'A1', 'an.nguyen@example.edu'),
    ('Binh Tran', 'A1', 'binh.tran@example.edu'),
    ('Chi Pham', 'B2', 'chi.pham@example.edu'),
    ('Dung Le', 'B2', 'dung.le@example.edu'),
    ('Mai Vo', 'C3', 'mai.vo@example.edu');

INSERT INTO courses (code, title, credits) VALUES
    ('MCP101', 'Model Context Protocol Foundations', 3),
    ('SQL201', 'Safe SQL for Applications', 4),
    ('AI301', 'Applied AI Tooling', 3);

INSERT INTO enrollments (student_id, course_id, score, status) VALUES
    (1, 1, 92.5, 'completed'),
    (1, 2, 88.0, 'active'),
    (2, 1, 79.5, 'completed'),
    (2, 3, 84.0, 'active'),
    (3, 2, 91.0, 'completed'),
    (4, 3, 66.0, 'dropped'),
    (5, 1, 73.5, 'active');
"""


def create_database(db_path: str | Path = DB_PATH) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("-journal", "-wal", "-shm"):
        candidate = Path(f"{path}{suffix}")
        if candidate.exists():
            candidate.unlink()
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = OFF")
        connection.executescript(SCHEMA_SQL)
        connection.executescript(SEED_SQL)
        connection.commit()
    return path


if __name__ == "__main__":
    created_path = create_database()
    print(f"Initialized SQLite database at {created_path}")
