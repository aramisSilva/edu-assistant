import os
import sqlite3
from src.core.config import DB_PATH

def db_conn():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

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

    con.commit()
    con.close()
