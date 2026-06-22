import os
import tempfile
import unittest
from datetime import timedelta

from src.infra import db, repo
from src.services.agenda_service import generate_suggestions, local_today, validate_blocks


class AgendaServiceTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        db.DB_PATH = os.path.join(self.tempdir.name, "agenda.db")
        db.init_db()
        self.student_id = repo.get_or_create_default_student()
        repo.replace_availability(self.student_id, [
            {"weekday": weekday, "start_time": "18:00", "end_time": "21:00"}
            for weekday in range(7)
        ])

    def test_prioritizes_tasks_and_avoids_overlap(self):
        today = local_today()
        repo.create_task(self.student_id, "Prazo distante", "Física", (today + timedelta(days=6)).isoformat())
        repo.create_task(self.student_id, "Atrasada", "Cálculo", (today - timedelta(days=1)).isoformat())
        repo.create_task(self.student_id, "Prazo amanhã", "Álgebra", (today + timedelta(days=1)).isoformat())

        suggestions = generate_suggestions(self.student_id, today)

        self.assertEqual([item["title"] for item in suggestions[:3]], ["Atrasada", "Prazo amanhã", "Prazo distante"])
        self.assertEqual(suggestions[0]["duration_minutes"], 90)
        intervals = [
            (
                item["study_date"],
                item["start_time"],
                item["duration_minutes"],
            )
            for item in suggestions
        ]
        self.assertEqual(len(intervals), len(set(intervals)))

    def test_completed_tasks_are_ignored(self):
        task_id, _ = repo.create_task(
            self.student_id, "Concluída", None, (local_today() + timedelta(days=2)).isoformat(),
        )
        repo.set_task_status(task_id, "DONE")
        self.assertEqual(generate_suggestions(self.student_id), [])

    def test_confirmed_task_is_not_suggested_again(self):
        task_id, _ = repo.create_task(
            self.student_id, "Lista", "Cálculo", (local_today() + timedelta(days=2)).isoformat(),
        )
        suggestion = generate_suggestions(self.student_id)[0]
        validate_blocks(self.student_id, [suggestion])
        repo.create_study_blocks(self.student_id, [suggestion])

        self.assertEqual(generate_suggestions(self.student_id), [])
        self.assertEqual(repo.list_all_planned_study_blocks(self.student_id)[0][1], task_id)


if __name__ == "__main__":
    unittest.main()
