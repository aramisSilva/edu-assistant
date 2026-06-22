from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.infra import repo


TIMEZONE = ZoneInfo("America/Fortaleza")
ALLOWED_DURATIONS = (30, 60, 90)


class AgendaError(ValueError):
    pass


def local_today() -> date:
    return datetime.now(TIMEZONE).date()


def _minutes(value: str) -> int:
    try:
        hour, minute = (int(part) for part in value.split(":", 1))
    except Exception as exc:
        raise AgendaError("Horário inválido. Use HH:MM.") from exc
    if hour not in range(24) or minute not in range(60):
        raise AgendaError("Horário inválido. Use HH:MM.")
    return hour * 60 + minute


def _time_string(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def validate_availability(slots: list[dict]):
    by_day: dict[int, list[tuple[int, int]]] = {}
    for slot in slots:
        weekday = slot["weekday"]
        if weekday not in range(7):
            raise AgendaError("Dia da semana inválido.")
        start = _minutes(slot["start_time"])
        end = _minutes(slot["end_time"])
        if end <= start:
            raise AgendaError("O horário final deve ser posterior ao inicial.")
        by_day.setdefault(weekday, []).append((start, end))
    for intervals in by_day.values():
        intervals.sort()
        for previous, current in zip(intervals, intervals[1:]):
            if current[0] < previous[1]:
                raise AgendaError("Os horários de disponibilidade não podem se sobrepor.")


def _task_priority(task: tuple, today: date):
    due = datetime.strptime(task[3][:10], "%Y-%m-%d").date()
    days = (due - today).days
    if days < 0:
        category = 0
    elif days <= 1:
        category = 1
    elif days <= 3:
        category = 2
    else:
        category = 3
    moodle_tiebreaker = 0 if task[6] == "moodle" else 1
    return category, due, moodle_tiebreaker, task[0]


def _suggested_duration(days_left: int) -> int:
    if days_left <= 1:
        return 90
    if days_left <= 3:
        return 60
    return 30


def _priority_reason(days_left: int, source: str) -> str:
    if days_left < 0:
        reason = "Atividade atrasada"
    elif days_left == 0:
        reason = "Prazo hoje"
    elif days_left == 1:
        reason = "Prazo em 24 horas"
    elif days_left <= 3:
        reason = f"Prazo em {days_left} dias"
    else:
        reason = f"Prazo em {days_left} dias"
    return f"{reason}; origem {source.capitalize()}."


def _occupied_intervals(student_id: int, start: date, end: date):
    occupied: dict[str, list[tuple[int, int]]] = {}
    for row in repo.list_study_blocks(student_id, start.isoformat(), end.isoformat()):
        if row[8] != "planned":
            continue
        begin = _minutes(row[5])
        occupied.setdefault(row[4], []).append((begin, begin + row[6]))
    return occupied


def _fits(intervals: list[tuple[int, int]], start: int, end: int) -> bool:
    return all(end <= existing_start or start >= existing_end for existing_start, existing_end in intervals)


def generate_suggestions(student_id: int, start_date: date | None = None, days: int = 7) -> list[dict]:
    start_date = start_date or local_today()
    end_date = start_date + timedelta(days=days - 1)
    availability_rows = repo.list_availability(student_id)
    if not availability_rows:
        raise AgendaError("Configure sua disponibilidade semanal antes de gerar sugestões.")

    availability: dict[int, list[tuple[int, int]]] = {}
    for _, weekday, start_time, end_time in availability_rows:
        availability.setdefault(weekday, []).append((_minutes(start_time), _minutes(end_time)))
    for intervals in availability.values():
        intervals.sort()

    planned_task_ids = {
        task_id for _, task_id, _, _, _ in repo.list_all_planned_study_blocks(student_id)
        if task_id is not None
    }
    tasks = [
        task for task in repo.list_tasks_detailed(student_id, "PENDING")
        if task[0] not in planned_task_ids
    ]
    tasks.sort(key=lambda task: _task_priority(task, start_date))

    occupied = _occupied_intervals(student_id, start_date, end_date)
    suggestions = []
    for task in tasks:
        due = datetime.strptime(task[3][:10], "%Y-%m-%d").date()
        days_left = (due - start_date).days
        desired_duration = _suggested_duration(days_left)
        latest_date = end_date if due < start_date else min(end_date, due)
        scheduled = None

        current = start_date
        while current <= latest_date and scheduled is None:
            date_key = current.isoformat()
            for window_start, window_end in availability.get(current.weekday(), []):
                for duration in (value for value in ALLOWED_DURATIONS[::-1] if value <= desired_duration):
                    slot_start = window_start
                    while slot_start + duration <= window_end:
                        slot_end = slot_start + duration
                        if _fits(occupied.get(date_key, []), slot_start, slot_end):
                            scheduled = (date_key, slot_start, duration)
                            break
                        slot_start += 30
                    if scheduled:
                        break
                if scheduled:
                    break
            current += timedelta(days=1)

        if not scheduled:
            continue
        study_date, start_minutes, duration = scheduled
        occupied.setdefault(study_date, []).append((start_minutes, start_minutes + duration))
        suggestions.append({
            "task_id": task[0],
            "title": task[1],
            "discipline": task[2],
            "study_date": study_date,
            "start_time": _time_string(start_minutes),
            "duration_minutes": duration,
            "origin": "suggested",
            "reason": _priority_reason(days_left, task[6]),
            "task_due_date": task[3],
            "task_source": task[6],
        })
    return suggestions


def validate_blocks(student_id: int, blocks: list[dict], ignore_block_id: int | None = None):
    availability_rows = repo.list_availability(student_id)
    availability: dict[int, list[tuple[int, int]]] = {}
    for _, weekday, start_time, end_time in availability_rows:
        availability.setdefault(weekday, []).append((_minutes(start_time), _minutes(end_time)))

    existing = repo.list_all_planned_study_blocks(student_id)
    pending_task_ids = {row[0] for row in repo.list_tasks_detailed(student_id, "PENDING")}
    occupied: dict[str, list[tuple[int, int]]] = {}
    for block_id, _, study_date, start_time, duration in existing:
        if block_id == ignore_block_id:
            continue
        start = _minutes(start_time)
        occupied.setdefault(study_date, []).append((start, start + duration))

    seen_task_ids = {
        task_id for block_id, task_id, _, _, _ in existing
        if task_id is not None and block_id != ignore_block_id
    }
    for block in blocks:
        duration = block["duration_minutes"]
        if duration not in ALLOWED_DURATIONS:
            raise AgendaError("A duração deve ser 30, 60 ou 90 minutos.")
        task_id = block.get("task_id")
        if task_id is not None and task_id not in pending_task_ids:
            raise AgendaError("A tarefa relacionada não está pendente.")
        if task_id is not None and task_id in seen_task_ids:
            raise AgendaError("Esta tarefa já possui um bloco planejado.")
        study_date = datetime.strptime(block["study_date"], "%Y-%m-%d").date()
        start = _minutes(block["start_time"])
        end = start + duration
        if not any(start >= window_start and end <= window_end for window_start, window_end in availability.get(study_date.weekday(), [])):
            raise AgendaError("O bloco deve estar dentro da disponibilidade configurada.")
        if not _fits(occupied.get(block["study_date"], []), start, end):
            raise AgendaError("O bloco se sobrepõe a outro horário planejado.")
        occupied.setdefault(block["study_date"], []).append((start, end))
        if task_id is not None:
            seen_task_ids.add(task_id)
