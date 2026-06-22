import os
import sqlite3
from src.core.config import DB_PATH

def db_conn():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def _add_column_if_missing(cur, table: str, column: str, definition: str):
    cur.execute(f"PRAGMA table_info({table})")
    if column not in {row[1] for row in cur.fetchall()}:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def init_db():
    con = db_conn()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            discipline TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            discipline TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            topic TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS student_profile (
            student_id INTEGER PRIMARY KEY,
            semester INTEGER NOT NULL,
            course_name TEXT NOT NULL,
            pole_name TEXT NOT NULL,
            weekly_hours INTEGER,
            focus TEXT,
            study_disciplines TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            discipline TEXT,
            due_date TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    _add_column_if_missing(cur, "tasks", "source", "TEXT NOT NULL DEFAULT 'manual'")
    _add_column_if_missing(cur, "tasks", "external_id", "TEXT")
    _add_column_if_missing(cur, "tasks", "external_course_id", "TEXT")

    cur.execute("DROP INDEX IF EXISTS idx_tasks_external")
    cur.execute("""
        CREATE UNIQUE INDEX idx_tasks_external
        ON tasks(student_id, source, external_id)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS moodle_courses (
            student_id INTEGER NOT NULL,
            external_id TEXT NOT NULL,
            shortname TEXT,
            fullname TEXT NOT NULL,
            PRIMARY KEY(student_id, external_id),
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS moodle_sync_state (
            student_id INTEGER PRIMARY KEY,
            moodle_user_id INTEGER NOT NULL,
            moodle_username TEXT,
            last_synced_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            read INTEGER NOT NULL DEFAULT 0,
            dedupe_key TEXT NOT NULL,
            related_kind TEXT,
            related_id TEXT,
            action_url TEXT,
            expires_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_notifications_dedupe
        ON notifications(student_id, dedupe_key)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_notifications_student_read
        ON notifications(student_id, read, created_at)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS student_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            weekday INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_availability_unique
        ON student_availability(student_id, weekday, start_time, end_time)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS study_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            task_id INTEGER,
            title TEXT NOT NULL,
            discipline TEXT,
            study_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            origin TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(task_id) REFERENCES tasks(id)
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_study_blocks_student_date
        ON study_blocks(student_id, study_date, start_time)
    """)

    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_study_blocks_slot
        ON study_blocks(student_id, study_date, start_time)
    """)

    con.commit()
    con.close()
