import os
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone

from src.infra import db, repo
from src.services.moodle_sync import sync_moodle


class FakeMoodleClient:
    def __init__(self, events):
        self.events = events

    def get_site_info(self):
        return {"userid": 7, "username": "edu.student"}

    def get_user_courses(self, user_id):
        return [{"id": 10, "shortname": "EDU-TEST", "fullname": "Curso de Teste"}]

    def get_action_events(self):
        return self.events


class MoodleSyncTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        db.DB_PATH = os.path.join(self.tempdir.name, "app.db")
        db.init_db()
        self.student_id = repo.get_or_create_default_student()
        repo.create_task(self.student_id, "Manual", None, "2030-01-01")

    def ts_for_days(self, days: int) -> int:
        target = date.today() + timedelta(days=days)
        return int(datetime(target.year, target.month, target.day, 12, tzinfo=timezone.utc).timestamp())

    def test_sync_is_idempotent_and_preserves_manual_task(self):
        events = [{"id": 20, "name": "Lista", "timesort": 1893456000, "course": {"id": 10}}]
        sync_moodle(self.student_id, FakeMoodleClient(events))
        sync_moodle(self.student_id, FakeMoodleClient(events))

        tasks = repo.list_tasks(self.student_id)
        self.assertEqual(len(tasks), 2)
        self.assertEqual({task[1] for task in tasks}, {"Manual", "Lista"})
        self.assertEqual(repo.list_moodle_courses(self.student_id)[0][2], "Curso de Teste")

        notifications = repo.list_notifications(self.student_id)
        titles = [row[3] for row in notifications]
        self.assertEqual(titles.count("Novo curso Moodle"), 1)
        self.assertEqual(titles.count("Nova atividade Moodle"), 1)

    def test_missing_moodle_event_is_marked_done(self):
        events = [{"id": 20, "name": "Lista", "timesort": 1893456000, "course": {"id": 10}}]
        sync_moodle(self.student_id, FakeMoodleClient(events))
        sync_moodle(self.student_id, FakeMoodleClient([]))

        pending = repo.list_tasks(self.student_id, status="PENDING")
        done = repo.list_tasks(self.student_id, status="DONE")
        self.assertEqual([task[1] for task in pending], ["Manual"])
        self.assertEqual([task[1] for task in done], ["Lista"])
        self.assertIn("Atividade Moodle concluída", [row[3] for row in repo.list_notifications(self.student_id)])

    def test_existing_moodle_event_is_updated(self):
        first = [{"id": 20, "name": "Lista", "timesort": 1893456000, "course": {"id": 10}}]
        second = [{"id": 20, "name": "Lista revisada", "timesort": 1893542400, "course": {"id": 10}}]
        sync_moodle(self.student_id, FakeMoodleClient(first))
        sync_moodle(self.student_id, FakeMoodleClient(second))

        imported = [task for task in repo.list_tasks(self.student_id) if task[1] != "Manual"]
        self.assertEqual(len(imported), 1)
        self.assertEqual(imported[0][1], "Lista revisada")
        self.assertEqual(imported[0][3], "2030-01-02")

    def test_deadline_notifications_are_created_once_for_three_days_and_24h(self):
        events = [
            {"id": 20, "name": "Lista 3 dias", "timesort": self.ts_for_days(3), "course": {"id": 10}},
            {"id": 21, "name": "Lista 24h", "timesort": self.ts_for_days(1), "course": {"id": 10}},
        ]
        first = sync_moodle(self.student_id, FakeMoodleClient(events))
        second = sync_moodle(self.student_id, FakeMoodleClient(events))

        titles = [row[3] for row in repo.list_notifications(self.student_id)]
        self.assertIn("Prazo vence em 3 dias", titles)
        self.assertIn("Prazo vence amanhã", titles)
        self.assertEqual(titles.count("Prazo vence em 3 dias"), 1)
        self.assertEqual(titles.count("Prazo vence amanhã"), 1)
        self.assertGreaterEqual(first["notifications_created"], 4)
        self.assertEqual(second["notifications_created"], 0)


if __name__ == "__main__":
    unittest.main()
