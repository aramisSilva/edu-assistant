from __future__ import annotations

from datetime import datetime, timezone

from src.core.config import MOODLE_BASE_URL, MOODLE_TOKEN
from src.infra import repo
from src.services.moodle_client import MoodleClient


def _to_date(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()


def sync_moodle(student_id: int, client: MoodleClient | None = None) -> dict:
    owns_client = client is None
    client = client or MoodleClient(MOODLE_BASE_URL, MOODLE_TOKEN)
    try:
        user = client.get_site_info()
        courses = client.get_user_courses(user["userid"])
        course_names = {str(course["id"]): course["fullname"] for course in courses}
        events = client.get_action_events()
        tasks = []
        for event in events:
            course_id = str(event.get("course", {}).get("id") or event.get("courseid") or "")
            due_at = event.get("timesort") or event.get("timestart")
            if not due_at:
                continue
            tasks.append({
                "external_id": event["id"],
                "title": event["name"],
                "discipline": course_names.get(course_id),
                "due_date": _to_date(int(due_at)),
                "notes": event.get("url"),
                "course_id": course_id,
            })
        notifications_created = repo.sync_moodle_snapshot(
            student_id,
            {"id": user["userid"], "username": user.get("username")},
            courses,
            tasks,
        )
        return {"courses": len(courses), "tasks": len(tasks), "notifications_created": notifications_created}
    finally:
        if owns_client:
            client.close()
