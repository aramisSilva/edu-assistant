import os
import tempfile
import unittest
from datetime import timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.infra import db
from src.infra import repo
from src.services.moodle_client import MoodleClientError
from src.services.agenda_service import local_today


class FakeDiagnosticClient:
    def __init__(self, *_args, **_kwargs):
        self.closed = False

    def get_site_info(self):
        return {"userid": 7, "username": "edu.student", "fullname": "Edu Student"}

    def get_user_courses(self, user_id):
        return [{"id": 10, "shortname": "C4", "fullname": "Cálculo IV"}]

    def close(self):
        self.closed = True


class EmptyCoursesDiagnosticClient(FakeDiagnosticClient):
    def get_user_courses(self, user_id):
        return []


class FailingDiagnosticClient(FakeDiagnosticClient):
    def get_site_info(self):
        raise MoodleClientError("Moodle recusou a sincronizacao: Invalid token")


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        db.DB_PATH = os.path.join(self.tempdir.name, "api.db")
        from src.api.app import create_app
        self.client = TestClient(create_app())

    def profile(self):
        return {
            "course_name": "BICT", "semester": 1, "pole_name": "Cuiabá",
            "weekly_hours": 5, "focus": "Cálculo", "study_disciplines": [],
        }

    def test_profile_and_dashboard(self):
        self.assertFalse(self.client.get("/api/bootstrap").json()["has_profile"])
        self.assertEqual(self.client.put("/api/profile", json=self.profile()).status_code, 200)
        dashboard = self.client.get("/api/dashboard").json()
        self.assertEqual(dashboard["profile"]["course_name"], "BICT")

    def test_task_lifecycle(self):
        self.client.put("/api/profile", json=self.profile())
        created = self.client.post("/api/tasks", json={"title": "Lista", "due_date": "2030-01-01"}).json()
        task = created["tasks"][0]
        self.assertEqual(task["source"], "manual")
        summary = self.client.get("/api/notifications/summary").json()
        self.assertEqual(summary["unread_count"], 1)
        self.assertEqual(summary["notifications"][0]["title"], "Nova tarefa manual")
        updated = self.client.patch(f"/api/tasks/{task['id']}/status", json={"status": "DONE"}).json()
        self.assertEqual(updated["tasks"][0]["status"], "DONE")

    def test_notification_lifecycle(self):
        self.client.post("/api/tasks", json={"title": "Lista", "due_date": "2030-01-01"})
        listed = self.client.get("/api/notifications").json()
        notification_id = listed["notifications"][0]["id"]
        self.assertFalse(listed["notifications"][0]["read"])

        marked = self.client.patch(f"/api/notifications/{notification_id}/read").json()
        self.assertEqual(marked["unread_count"], 0)

        self.client.post("/api/tasks", json={"title": "Outra", "due_date": "2030-01-02"})
        all_read = self.client.post("/api/notifications/read-all").json()
        self.assertEqual(all_read["unread_count"], 0)

        deleted = self.client.delete("/api/notifications/read").json()
        self.assertGreaterEqual(deleted["changed"], 2)
        self.assertEqual(self.client.get("/api/notifications").json()["notifications"], [])

    def test_agenda_lifecycle(self):
        availability = [
            {"weekday": weekday, "start_time": "18:00", "end_time": "21:00"}
            for weekday in range(7)
        ]
        saved = self.client.put("/api/agenda/availability", json=availability)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(len(saved.json()["availability"]), 7)

        due_date = (local_today() + timedelta(days=2)).isoformat()
        self.client.post("/api/tasks", json={"title": "Lista de cálculo", "discipline": "Cálculo", "due_date": due_date})
        suggested = self.client.post("/api/agenda/suggestions", json={})
        self.assertEqual(suggested.status_code, 200)
        suggestion = suggested.json()["suggestions"][0]
        suggestion["duration_minutes"] = 30

        confirmed = self.client.post("/api/agenda/blocks", json={"blocks": [suggestion]})
        self.assertEqual(confirmed.status_code, 201)
        block = confirmed.json()["blocks"][0]
        self.assertEqual(block["status"], "planned")
        self.assertEqual(block["duration_minutes"], 30)

        completed = self.client.patch(f"/api/agenda/blocks/{block['id']}/complete")
        self.assertEqual(completed.json()["blocks"][0]["status"], "completed")

        tomorrow = (local_today() + timedelta(days=1)).isoformat()
        rescheduled = self.client.patch(
            f"/api/agenda/blocks/{block['id']}/reschedule",
            json={"study_date": tomorrow, "start_time": "19:00", "duration_minutes": 60},
        )
        updated = rescheduled.json()["blocks"][0]
        self.assertEqual(updated["status"], "planned")
        self.assertEqual(updated["study_date"], tomorrow)
        self.assertEqual(updated["start_time"], "19:00")

    def test_conversation_lifecycle(self):
        created = self.client.post("/api/conversations", json={}).json()
        self.assertEqual(len(created["conversations"]), 1)
        deleted = self.client.delete(f"/api/conversations/{created['id']}").json()
        self.assertEqual(deleted["conversations"], [])

    def test_chat_message(self):
        created = self.client.post("/api/conversations", json={}).json()
        with patch("src.api.app.handle_user_message", return_value=("Chat geral", "Resposta simulada")):
            response = self.client.post(
                f"/api/conversations/{created['id']}/messages",
                json={"content": "Como organizo meus estudos?"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "Resposta simulada")

    def test_chat_context_exposes_profile_courses_tasks_and_topics(self):
        self.client.put("/api/profile", json=self.profile())
        student_id = repo.get_or_create_default_student()
        conversation_id = repo.create_conversation(student_id, "general")
        repo.save_message(student_id, "general", conversation_id, "user", "Explique derivadas", "Derivadas")
        repo.create_task(student_id, "Tarefa manual", "Cálculo", "2030-01-01")
        repo.sync_moodle_snapshot(
            student_id,
            {"id": 7, "username": "edu.student"},
            [{"id": 10, "shortname": "CALC4", "fullname": "Cálculo IV"}],
            [{"external_id": "event-1", "title": "Lista Moodle", "discipline": "Cálculo IV", "due_date": "2030-01-02", "course_id": 10}],
        )

        response = self.client.get("/api/chat/context")
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["profile"]["course_name"], "BICT")
        self.assertEqual(data["courses"][0]["fullname"], "Cálculo IV")
        self.assertEqual(data["upcoming_tasks"][0]["title"], "Tarefa manual")
        self.assertEqual(data["topics"][0]["topic"], "Derivadas")
        self.assertEqual(data["sync_state"]["moodle_username"], "edu.student")

    def test_moodle_error_is_reported(self):
        with patch("src.api.app.sync_moodle", side_effect=MoodleClientError("Moodle indisponivel")):
            response = self.client.post("/api/moodle/sync")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "Moodle indisponivel")

    def test_moodle_diagnostics_reports_missing_token(self):
        with patch("src.services.moodle_diagnostics.config.MOODLE_TOKEN", ""):
            response = self.client.get("/api/moodle/diagnostics")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "error")
        self.assertFalse(data["token_configured"])
        self.assertNotIn("wstoken", response.text)

    def test_moodle_diagnostics_success_does_not_expose_token(self):
        with patch("src.services.moodle_diagnostics.config.MOODLE_TOKEN", "secret-token"), \
             patch("src.services.moodle_diagnostics.MoodleClient", FakeDiagnosticClient):
            response = self.client.get("/api/moodle/diagnostics")
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["moodle_available"])
        self.assertEqual(data["user"]["username"], "edu.student")
        self.assertEqual(data["courses_count"], 1)
        self.assertNotIn("secret-token", response.text)

    def test_moodle_diagnostics_warns_when_user_has_no_courses(self):
        with patch("src.services.moodle_diagnostics.config.MOODLE_TOKEN", "secret-token"), \
             patch("src.services.moodle_diagnostics.MoodleClient", EmptyCoursesDiagnosticClient):
            response = self.client.get("/api/moodle/diagnostics")
        data = response.json()
        self.assertEqual(data["status"], "warning")
        self.assertEqual(data["courses_count"], 0)
        self.assertIn("matriculado", data["message"])

    def test_moodle_diagnostics_reports_moodle_error(self):
        with patch("src.services.moodle_diagnostics.config.MOODLE_TOKEN", "secret-token"), \
             patch("src.services.moodle_diagnostics.MoodleClient", FailingDiagnosticClient):
            response = self.client.get("/api/moodle/diagnostics")
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertFalse(data["moodle_available"])
        self.assertIn("Invalid token", data["message"])

    def test_insights_include_progress_and_recommendations(self):
        student_id = repo.get_or_create_default_student()
        conversation_id = repo.create_conversation(student_id, "general")
        repo.save_message(student_id, "general", conversation_id, "user", "Explique limites", "Limites")
        repo.save_message(student_id, "general", conversation_id, "user", "Mais um exemplo", "Limites")
        repo.create_task(student_id, "Lista urgente", "Cálculo", "2030-01-01")

        response = self.client.get("/api/insights")
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["progress"]["total_questions"], 2)
        self.assertEqual(data["topics"][0]["topic"], "Limites")
        self.assertEqual(data["topics"][0]["percent"], 100)
        self.assertTrue(data["recommendations"])


if __name__ == "__main__":
    unittest.main()
