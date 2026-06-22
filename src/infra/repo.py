from datetime import date, datetime, timedelta
from urllib.parse import quote
from src.infra.db import db_conn


def _today() -> date:
    return date.today()


def _days_left(due_date: str) -> int | None:
    try:
        return (datetime.strptime(due_date[:10], "%Y-%m-%d").date() - _today()).days
    except Exception:
        return None


def _insert_notification(
    cur,
    student_id: int,
    type_: str,
    severity: str,
    title: str,
    message: str,
    dedupe_key: str,
    related_kind: str | None = None,
    related_id: str | None = None,
    action_url: str | None = None,
    expires_at: str | None = None,
) -> int:
    cur.execute("""
        INSERT OR IGNORE INTO notifications(
            student_id, type, severity, title, message, read, dedupe_key,
            related_kind, related_id, action_url, expires_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
    """, (
        student_id, type_, severity, title, message, dedupe_key,
        related_kind, related_id, action_url, expires_at, datetime.utcnow().isoformat(),
    ))
    return cur.rowcount


def _insert_deadline_notifications(cur, student_id: int) -> int:
    cur.execute("""
        SELECT id, title, discipline, due_date, source
        FROM tasks
        WHERE student_id=? AND status='PENDING'
    """, (student_id,))
    created = 0
    for task_id, title, discipline, due_date, source in cur.fetchall():
        days = _days_left(due_date)
        if days not in (1, 3):
            continue
        label = "24h" if days == 1 else "3d"
        severity = "urgent" if days == 1 else "warning"
        when = "amanhã" if days == 1 else "em 3 dias"
        course = f" em {discipline}" if discipline else ""
        prompt = quote(f"Me ajude a estudar para a atividade '{title}'{course}, que vence em {due_date}.")
        created += _insert_notification(
            cur,
            student_id,
            "deadline",
            severity,
            f"Prazo vence {when}",
            f"A atividade '{title}'{course} vence {when}.",
            f"deadline:{label}:{student_id}:{task_id}",
            "task",
            str(task_id),
            f"/chat?prompt={prompt}",
            due_date,
        )
    return created

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

def get_profile(student_id: int):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT student_id, course_name, semester, pole_name, weekly_hours, focus, study_disciplines
        FROM student_profile
        WHERE student_id=?
        LIMIT 1
    """, (student_id,))
    row = cur.fetchone()
    con.close()

    if not row:
        return None
    study_disciplines = row[6] or ""
    keys = [k.strip() for k in study_disciplines.split(",") if k.strip()]
    return {
        "student_id": row[0],
        "course_name": row[1],
        "semester": row[2],
        "pole_name": row[3],
        "weekly_hours": row[4],
        "focus": row[5],
        "study_disciplines": keys,
    }

def upsert_profile(
    student_id: int,
    course_name: str,
    semester: int,
    pole_name: str,
    weekly_hours: int | None,
    focus: str | None,
    study_disciplines: list[str] | None = None,
):
    now = datetime.utcnow().isoformat()
    disciplines_csv = ",".join(study_disciplines or [])

    con = db_conn()
    cur = con.cursor()

    cur.execute("SELECT student_id FROM student_profile WHERE student_id=?", (student_id,))
    exists = cur.fetchone()

    if exists:
        cur.execute("""
            UPDATE student_profile
            SET course_name=?, semester=?, pole_name=?, weekly_hours=?, focus=?, study_disciplines=?, updated_at=?
            WHERE student_id=?
        """, (course_name, semester, pole_name, weekly_hours, focus, disciplines_csv, now, student_id))
    else:
        cur.execute("""
            INSERT INTO student_profile(
                student_id, course_name, semester, pole_name, weekly_hours, focus, study_disciplines, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (student_id, course_name, semester, pole_name, weekly_hours, focus, disciplines_csv, now, now))

    con.commit()
    con.close()


def create_task(student_id: int, title: str, discipline: str | None, due_date: str, notes: str | None = None):
    now = datetime.utcnow().isoformat()
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO tasks(student_id, title, discipline, due_date, status, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?)
    """, (student_id, title, discipline, due_date, notes, now, now))
    task_id = cur.lastrowid
    course = f" em {discipline}" if discipline else ""
    created = _insert_notification(
        cur,
        student_id,
        "task",
        "info",
        "Nova tarefa manual",
        f"A tarefa '{title}'{course} foi criada no Edu Assistant.",
        f"task:new:{student_id}:manual:{task_id}",
        "task",
        str(task_id),
        "/tasks",
        due_date,
    )
    created += _insert_deadline_notifications(cur, student_id)
    con.commit()
    con.close()
    return task_id, created

def sync_moodle_snapshot(student_id: int, moodle_user: dict, courses: list[dict], tasks: list[dict]):
    now = datetime.utcnow().isoformat()
    con = db_conn()
    cur = con.cursor()
    notifications_created = 0
    try:
        cur.execute("BEGIN")
        cur.execute("SELECT external_id FROM moodle_courses WHERE student_id=?", (student_id,))
        existing_courses = {row[0] for row in cur.fetchall()}
        cur.execute("""
            SELECT id, external_id, title, discipline
            FROM tasks
            WHERE student_id=? AND source='moodle'
        """, (student_id,))
        existing_tasks = {str(external_id): (task_id, title, discipline) for task_id, external_id, title, discipline in cur.fetchall()}

        cur.execute("DELETE FROM moodle_courses WHERE student_id=?", (student_id,))
        cur.executemany("""
            INSERT INTO moodle_courses(student_id, external_id, shortname, fullname)
            VALUES (?, ?, ?, ?)
        """, [
            (student_id, str(course["id"]), course.get("shortname"), course["fullname"])
            for course in courses
        ])
        for course in courses:
            course_id = str(course["id"])
            if course_id not in existing_courses:
                notifications_created += _insert_notification(
                    cur,
                    student_id,
                    "course",
                    "info",
                    "Novo curso Moodle",
                    f"Você foi matriculado em '{course['fullname']}'.",
                    f"course:new:{student_id}:{course_id}",
                    "course",
                    course_id,
                    "/moodle",
                )

        active_ids = []
        for task in tasks:
            external_id = str(task["external_id"])
            active_ids.append(external_id)
            if external_id not in existing_tasks:
                course = f" em {task.get('discipline')}" if task.get("discipline") else ""
                notifications_created += _insert_notification(
                    cur,
                    student_id,
                    "task",
                    "info",
                    "Nova atividade Moodle",
                    f"A atividade '{task['title']}'{course} foi importada do Moodle.",
                    f"task:new:{student_id}:moodle:{external_id}",
                    "task",
                    external_id,
                    "/tasks",
                    task["due_date"],
                )
            cur.execute("""
                INSERT INTO tasks(
                    student_id, title, discipline, due_date, status, notes,
                    source, external_id, external_course_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, 'PENDING', ?, 'moodle', ?, ?, ?, ?)
                ON CONFLICT(student_id, source, external_id) DO UPDATE SET
                    title=excluded.title,
                    discipline=excluded.discipline,
                    due_date=excluded.due_date,
                    status='PENDING',
                    notes=excluded.notes,
                    external_course_id=excluded.external_course_id,
                    updated_at=excluded.updated_at
            """, (
                student_id, task["title"], task.get("discipline"), task["due_date"],
                task.get("notes"), external_id, str(task.get("course_id") or ""), now, now,
            ))

        if active_ids:
            placeholders = ",".join("?" for _ in active_ids)
            cur.execute(f"""
                SELECT id, external_id, title, discipline
                FROM tasks
                WHERE student_id=? AND source='moodle' AND status='PENDING'
                  AND external_id NOT IN ({placeholders})
            """, (student_id, *active_ids))
            for task_id, external_id, title, discipline in cur.fetchall():
                course = f" em {discipline}" if discipline else ""
                notifications_created += _insert_notification(
                    cur,
                    student_id,
                    "sync",
                    "info",
                    "Atividade Moodle concluída",
                    f"A atividade '{title}'{course} deixou de aparecer no Moodle e foi marcada como concluída.",
                    f"task:removed:{student_id}:moodle:{external_id}",
                    "task",
                    str(task_id),
                    "/tasks",
                )
            cur.execute(f"""
                UPDATE tasks SET status='DONE', updated_at=?
                WHERE student_id=? AND source='moodle'
                  AND external_id NOT IN ({placeholders})
            """, (now, student_id, *active_ids))
        else:
            cur.execute("""
                SELECT id, external_id, title, discipline
                FROM tasks
                WHERE student_id=? AND source='moodle' AND status='PENDING'
            """, (student_id,))
            for task_id, external_id, title, discipline in cur.fetchall():
                course = f" em {discipline}" if discipline else ""
                notifications_created += _insert_notification(
                    cur,
                    student_id,
                    "sync",
                    "info",
                    "Atividade Moodle concluída",
                    f"A atividade '{title}'{course} deixou de aparecer no Moodle e foi marcada como concluída.",
                    f"task:removed:{student_id}:moodle:{external_id}",
                    "task",
                    str(task_id),
                    "/tasks",
                )
            cur.execute("""
                UPDATE tasks SET status='DONE', updated_at=?
                WHERE student_id=? AND source='moodle'
            """, (now, student_id))

        cur.execute("""
            INSERT INTO moodle_sync_state(student_id, moodle_user_id, moodle_username, last_synced_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET
                moodle_user_id=excluded.moodle_user_id,
                moodle_username=excluded.moodle_username,
                last_synced_at=excluded.last_synced_at
        """, (student_id, moodle_user["id"], moodle_user.get("username"), now))
        notifications_created += _insert_deadline_notifications(cur, student_id)
        con.commit()
        return notifications_created
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def list_moodle_courses(student_id: int):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT external_id, shortname, fullname
        FROM moodle_courses WHERE student_id=? ORDER BY fullname
    """, (student_id,))
    rows = cur.fetchall()
    con.close()
    return rows

def get_moodle_sync_state(student_id: int):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT moodle_user_id, moodle_username, last_synced_at
        FROM moodle_sync_state WHERE student_id=?
    """, (student_id,))
    row = cur.fetchone()
    con.close()
    if not row:
        return None
    return {"moodle_user_id": row[0], "moodle_username": row[1], "last_synced_at": row[2]}


def list_notifications(student_id: int, read: bool | None = None, limit: int = 50):
    con = db_conn()
    cur = con.cursor()
    sql = """
        SELECT id, type, severity, title, message, read, created_at,
               related_kind, related_id, action_url
        FROM notifications
        WHERE student_id=?
    """
    params = [student_id]
    if read is not None:
        sql += " AND read=?"
        params.append(1 if read else 0)
    sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
    params.append(limit)
    cur.execute(sql, params)
    rows = cur.fetchall()
    con.close()
    return rows


def count_unread_notifications(student_id: int) -> int:
    con = db_conn()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM notifications WHERE student_id=? AND read=0", (student_id,))
    count = cur.fetchone()[0]
    con.close()
    return count


def mark_notification_read(student_id: int, notification_id: int):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        UPDATE notifications
        SET read=1
        WHERE student_id=? AND id=?
    """, (student_id, notification_id))
    con.commit()
    con.close()


def mark_all_notifications_read(student_id: int) -> int:
    con = db_conn()
    cur = con.cursor()
    cur.execute("UPDATE notifications SET read=1 WHERE student_id=? AND read=0", (student_id,))
    changed = cur.rowcount
    con.commit()
    con.close()
    return changed


def delete_read_notifications(student_id: int) -> int:
    con = db_conn()
    cur = con.cursor()
    cur.execute("DELETE FROM notifications WHERE student_id=? AND read=1", (student_id,))
    deleted = cur.rowcount
    con.commit()
    con.close()
    return deleted

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

def count_tasks(student_id: int, status: str | None = None) -> int:
    con = db_conn()
    cur = con.cursor()
    if status:
        cur.execute("SELECT COUNT(*) FROM tasks WHERE student_id=? AND status=?", (student_id, status))
    else:
        cur.execute("SELECT COUNT(*) FROM tasks WHERE student_id=?", (student_id,))
    n = cur.fetchone()[0]
    con.close()
    return n

def count_tasks_due_within_days(student_id: int, days: int = 7) -> int:

    today = datetime.utcnow().date()
    cutoff = today + timedelta(days=days)
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM tasks
        WHERE student_id=? AND status='PENDING' AND due_date <= ?
    """, (student_id, cutoff.isoformat()))
    n = cur.fetchone()[0]
    con.close()
    return n

def list_upcoming_tasks(student_id: int, limit: int = 5):

    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT id, title, discipline, due_date, notes
        FROM tasks
        WHERE student_id=? AND status='PENDING'
        ORDER BY due_date ASC
        LIMIT ?
    """, (student_id, limit))
    rows = cur.fetchall()
    con.close()
    return rows

def list_tasks_detailed(student_id: int, status: str | None = None):
    con = db_conn()
    cur = con.cursor()
    sql = """
        SELECT id, title, discipline, due_date, status, notes, source, external_id, external_course_id
        FROM tasks
        WHERE student_id=?
    """
    params = [student_id]
    if status:
        sql += " AND status=?"
        params.append(status)
    sql += " ORDER BY due_date ASC"
    cur.execute(sql, params)
    rows = cur.fetchall()
    con.close()
    return rows


def replace_availability(student_id: int, slots: list[dict]):
    con = db_conn()
    cur = con.cursor()
    try:
        cur.execute("BEGIN")
        cur.execute("DELETE FROM student_availability WHERE student_id=?", (student_id,))
        cur.executemany("""
            INSERT INTO student_availability(student_id, weekday, start_time, end_time)
            VALUES (?, ?, ?, ?)
        """, [
            (student_id, slot["weekday"], slot["start_time"], slot["end_time"])
            for slot in slots
        ])
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def list_availability(student_id: int):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT id, weekday, start_time, end_time
        FROM student_availability
        WHERE student_id=?
        ORDER BY weekday, start_time
    """, (student_id,))
    rows = cur.fetchall()
    con.close()
    return rows


def list_study_blocks(student_id: int, date_from: str, date_to: str):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT sb.id, sb.task_id, sb.title, sb.discipline, sb.study_date,
               sb.start_time, sb.duration_minutes, sb.origin, sb.status,
               t.due_date, t.source
        FROM study_blocks sb
        LEFT JOIN tasks t ON t.id=sb.task_id
        WHERE sb.student_id=? AND sb.study_date BETWEEN ? AND ?
        ORDER BY sb.study_date, sb.start_time
    """, (student_id, date_from, date_to))
    rows = cur.fetchall()
    con.close()
    return rows


def get_study_block(student_id: int, block_id: int):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT sb.id, sb.task_id, sb.title, sb.discipline, sb.study_date,
               sb.start_time, sb.duration_minutes, sb.origin, sb.status,
               t.due_date, t.source
        FROM study_blocks sb
        LEFT JOIN tasks t ON t.id=sb.task_id
        WHERE sb.student_id=? AND sb.id=?
    """, (student_id, block_id))
    row = cur.fetchone()
    con.close()
    return row


def list_all_planned_study_blocks(student_id: int):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        SELECT id, task_id, study_date, start_time, duration_minutes
        FROM study_blocks
        WHERE student_id=? AND status='planned'
        ORDER BY study_date, start_time
    """, (student_id,))
    rows = cur.fetchall()
    con.close()
    return rows


def create_study_blocks(student_id: int, blocks: list[dict]):
    now = datetime.utcnow().isoformat()
    con = db_conn()
    cur = con.cursor()
    created_ids = []
    try:
        cur.execute("BEGIN")
        for block in blocks:
            cur.execute("""
                INSERT INTO study_blocks(
                    student_id, task_id, title, discipline, study_date,
                    start_time, duration_minutes, origin, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'planned', ?, ?)
            """, (
                student_id, block.get("task_id"), block["title"], block.get("discipline"),
                block["study_date"], block["start_time"], block["duration_minutes"],
                block.get("origin", "suggested"), now, now,
            ))
            created_ids.append(cur.lastrowid)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return created_ids


def complete_study_block(student_id: int, block_id: int):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        UPDATE study_blocks
        SET status='completed', updated_at=?
        WHERE id=? AND student_id=?
    """, (datetime.utcnow().isoformat(), block_id, student_id))
    changed = cur.rowcount
    con.commit()
    con.close()
    return changed


def reschedule_study_block(
    student_id: int,
    block_id: int,
    study_date: str,
    start_time: str,
    duration_minutes: int,
):
    con = db_conn()
    cur = con.cursor()
    cur.execute("""
        UPDATE study_blocks
        SET study_date=?, start_time=?, duration_minutes=?, status='planned', updated_at=?
        WHERE id=? AND student_id=?
    """, (
        study_date, start_time, duration_minutes, datetime.utcnow().isoformat(),
        block_id, student_id,
    ))
    changed = cur.rowcount
    con.commit()
    con.close()
    return changed

