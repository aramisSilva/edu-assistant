from datetime import datetime
from src.infra.db import db_conn

# -------- Students --------
def get_or_create_default_student(name: str = "Aluno") -> int:
    con = db_conn()
    cur = con.cursor()
    cur.execute("SELECT id FROM students LIMIT 1")
    row = cur.fetchone()

    if row:
        con.close()
        return row[0]

    cur.execute(
        "INSERT INTO students(name, created_at) VALUES (?, ?)",
        (name, datetime.utcnow().isoformat()),
    )
    con.commit()
    sid = cur.lastrowid
    con.close()
    return sid

# -------- Conversations --------
def create_conversation(student_id: int, discipline: str, title: str = "Novo chat") -> int:
    con = db_conn()
    cur = con.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO conversations(student_id, discipline, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (student_id, discipline, title, now, now),
    )
    con.commit()
    cid = cur.lastrowid
    con.close()
    return cid

def list_conversations(student_id: int, discipline: str, limit: int = 50):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT id, title, updated_at
        FROM conversations
        WHERE student_id=? AND discipline=?
        ORDER BY updated_at DESC
        LIMIT ?
    """, (student_id, discipline, limit))
    rows = cur.fetchall()
    con.close()
    return rows

def rename_conversation(conversation_id: int, new_title: str):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        UPDATE conversations
        SET title=?, updated_at=?
        WHERE id=?
    """, (new_title, datetime.utcnow().isoformat(), conversation_id))
    con.commit()
    con.close()

def delete_conversation(conversation_id: int):
    con = db_conn()
    cur = con.cursor()
    cur.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
    cur.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
    con.commit()
    con.close()

def touch_conversation(conversation_id: int):
    con = db_conn()
    cur = con.cursor()
    cur.execute(
        "UPDATE conversations SET updated_at=? WHERE id=?",
        (datetime.utcnow().isoformat(), conversation_id),
    )
    con.commit()
    con.close()

# -------- Messages --------
def save_message(student_id: int, discipline: str, conversation_id: int, role: str, content: str, topic: str = None):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO messages(conversation_id, student_id, discipline, role, content, topic, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (conversation_id, student_id, discipline, role, content, topic, datetime.utcnow().isoformat()))
    con.commit()
    con.close()
    touch_conversation(conversation_id)

def load_messages(conversation_id: int, limit: int = 300):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT role, content, topic
        FROM messages
        WHERE conversation_id=?
        ORDER BY id ASC
        LIMIT ?
    """, (conversation_id, limit))
    rows = cur.fetchall()
    con.close()
    return rows

def topic_ranking(student_id: int, discipline: str, limit: int = 10):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT COALESCE(topic, 'Sem tópico') as topic, COUNT(*) as c
        FROM messages
        WHERE student_id=? AND discipline=? AND role='user'
        GROUP BY topic
        ORDER BY c DESC
        LIMIT ?
    """, (student_id, discipline, limit))
    rows = cur.fetchall()
    con.close()
    return rows

# -------- Profile --------
def get_profile(student_id: int):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT student_id, course_name, semester, pole_name, weekly_hours, focus
        FROM student_profile
        WHERE student_id=?
        LIMIT 1
    """, (student_id,))
    row = cur.fetchone()
    con.close()

    if not row:
        return None

    return {
        "student_id": row[0],
        "course_name": row[1],
        "semester": row[2],
        "pole_name": row[3],
        "weekly_hours": row[4],
        "focus": row[5],
    }

def upsert_profile(
    student_id: int,
    course_name: str,
    semester: int,
    pole_name: str,
    weekly_hours: int | None,
    focus: str | None
):
    now = datetime.utcnow().isoformat()
    con = db_conn()
    cur = con.cursor()

    cur.execute("SELECT student_id FROM student_profile WHERE student_id=?", (student_id,))
    exists = cur.fetchone()

    if exists:
        cur.execute("""
            UPDATE student_profile
            SET course_name=?, semester=?, pole_name=?, weekly_hours=?, focus=?, updated_at=?
            WHERE student_id=?
        """, (course_name, semester, pole_name, weekly_hours, focus, now, student_id))
    else:
        cur.execute("""
            INSERT INTO student_profile(student_id, course_name, semester, pole_name, weekly_hours, focus, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (student_id, course_name, semester, pole_name, weekly_hours, focus, now, now))

    con.commit()
    con.close()

# -------- Tasks --------
def create_task(student_id: int, title: str, discipline: str | None, due_date: str, notes: str | None = None):
    now = datetime.utcnow().isoformat()
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO tasks(student_id, title, discipline, due_date, status, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?)
    """, (student_id, title, discipline, due_date, notes, now, now))
    con.commit()
    con.close()

def list_tasks(student_id: int, status: str | None = None):
    con = db_conn()
    cur = con.cursor()
    if status:
        cur.execute("""
            SELECT id, title, discipline, due_date, status, notes
            FROM tasks
            WHERE student_id=? AND status=?
            ORDER BY due_date ASC
        """, (student_id, status))
    else:
        cur.execute("""
            SELECT id, title, discipline, due_date, status, notes
            FROM tasks
            WHERE student_id=?
            ORDER BY due_date ASC
        """, (student_id,))
    rows = cur.fetchall()
    con.close()
    return rows

def set_task_status(task_id: int, status: str):
    now = datetime.utcnow().isoformat()
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        UPDATE tasks
        SET status=?, updated_at=?
        WHERE id=?
    """, (status, now, task_id))
    con.commit()
    con.close()

def upcoming_tasks(student_id: int, discipline: str | None = None, limit: int = 5):
    con = db_conn()
    cur = con.cursor()
    if discipline:
        cur.execute("""
            SELECT title, discipline, due_date
            FROM tasks
            WHERE student_id=? AND status='PENDING' AND discipline=?
            ORDER BY due_date ASC
            LIMIT ?
        """, (student_id, discipline, limit))
    else:
        cur.execute("""
            SELECT title, discipline, due_date
            FROM tasks
            WHERE student_id=? AND status='PENDING'
            ORDER BY due_date ASC
            LIMIT ?
        """, (student_id, limit))
    rows = cur.fetchall()
    con.close()
    return rows
