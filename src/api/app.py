from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.core.curriculum import CURRICULUM
from src.core.deadlines import get_deadline_status
from src.core.poles import POLES
from src.infra import repo
from src.infra.db import init_db
from src.services.chat_service import handle_user_message
from src.services.agenda_service import AgendaError, generate_suggestions, local_today, validate_availability, validate_blocks
from src.services.coaching import build_daily_plan
from src.services.dashboard_service import generate_daily_suggestion
from src.services.moodle_client import MoodleClientError
from src.services.moodle_diagnostics import diagnose_moodle
from src.services.moodle_sync import sync_moodle
from src.services.plan_service import build_today_plan_text


GENERAL_DISCIPLINE = "general"
GENERAL_LABEL = "Chat geral"


class ProfileInput(BaseModel):
    course_name: str = Field(min_length=1)
    semester: int = Field(ge=1, le=6)
    pole_name: str
    weekly_hours: int | None = Field(default=None, ge=0, le=60)
    focus: str | None = None
    study_disciplines: list[str] = Field(default_factory=list)


class TaskInput(BaseModel):
    title: str = Field(min_length=1)
    discipline: str | None = None
    due_date: str
    notes: str | None = None


class TaskStatusInput(BaseModel):
    status: Literal["PENDING", "DONE"]


class ConversationInput(BaseModel):
    title: str = "Novo chat"


class MessageInput(BaseModel):
    content: str = Field(min_length=1)


class ProfileResponse(BaseModel):
    profile: ProfileInput | None


class DeadlineOutput(BaseModel):
    code: str
    label: str
    days_left: int
    severity: int


class TaskOutput(BaseModel):
    id: int
    title: str
    discipline: str | None
    due_date: str
    status: Literal["PENDING", "DONE"]
    notes: str | None
    source: Literal["manual", "moodle"]
    external_id: str | None
    external_course_id: str | None
    deadline: DeadlineOutput


class CourseOutput(BaseModel):
    external_id: str
    shortname: str | None
    fullname: str


class TopicOutput(BaseModel):
    topic: str
    count: int


class TopicInsightOutput(TopicOutput):
    percent: int


class SyncStateOutput(BaseModel):
    moodle_user_id: int
    moodle_username: str | None
    last_synced_at: str


class BootstrapResponse(ProfileResponse):
    poles: dict[str, Any]
    curriculum: dict[Any, Any]
    has_profile: bool


class DashboardResponse(ProfileResponse):
    metrics: dict[str, int]
    courses: list[CourseOutput]
    sync_state: SyncStateOutput | None
    upcoming_tasks: list[TaskOutput]
    topics: list[TopicOutput]
    today_blocks: list["StudyBlockOutput"]
    planned_minutes_today: int


class TasksResponse(BaseModel):
    tasks: list[TaskOutput]


class ConversationOutput(BaseModel):
    id: int
    title: str
    updated_at: str


class ConversationsResponse(BaseModel):
    conversations: list[ConversationOutput]


class CreateConversationResponse(ConversationsResponse):
    id: int


class MessagesResponse(BaseModel):
    messages: list[dict[str, str | None]]


class SendMessageResponse(BaseModel):
    topic: str
    answer: str


class TextResponse(BaseModel):
    text: str


class MoodleSyncResponse(BaseModel):
    courses: int
    tasks: int
    notifications_created: int = 0


class NotificationOutput(BaseModel):
    id: int
    type: Literal["course", "task", "deadline", "sync"]
    severity: Literal["info", "warning", "urgent"]
    title: str
    message: str
    read: bool
    created_at: str
    related_kind: str | None
    related_id: str | None
    action_url: str | None


class NotificationsResponse(BaseModel):
    notifications: list[NotificationOutput]


class NotificationsSummaryResponse(NotificationsResponse):
    unread_count: int


class NotificationMutationResponse(BaseModel):
    unread_count: int
    changed: int = 0


class MoodleDiagnosticUser(BaseModel):
    id: int
    username: str | None
    fullname: str | None = None


class MoodleDiagnosticCheck(BaseModel):
    label: str
    status: Literal["ok", "warning", "error"]
    detail: str


class MoodleDiagnosticsResponse(BaseModel):
    status: Literal["ok", "warning", "error"]
    base_url: str
    token_configured: bool
    moodle_available: bool
    user: MoodleDiagnosticUser | None
    courses_count: int
    last_sync: SyncStateOutput | None
    message: str
    checks: list[MoodleDiagnosticCheck]


class InsightsResponse(BaseModel):
    progress: dict[str, int]
    topics: list[TopicInsightOutput]
    recommendations: list[dict[str, str]]
    recommendation: str


class ChatContextResponse(ProfileResponse):
    courses: list[CourseOutput]
    upcoming_tasks: list[TaskOutput]
    topics: list[TopicOutput]
    sync_state: SyncStateOutput | None


class AvailabilityInput(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: str
    end_time: str


class AvailabilityResponse(BaseModel):
    availability: list[AvailabilityInput]


class StudyBlockInput(BaseModel):
    task_id: int | None = None
    title: str = Field(min_length=1)
    discipline: str | None = None
    study_date: str
    start_time: str
    duration_minutes: Literal[30, 60, 90]
    origin: Literal["suggested", "manual"] = "suggested"


class StudyBlockOutput(StudyBlockInput):
    id: int
    status: Literal["planned", "completed"]
    task_due_date: str | None = None
    task_source: Literal["manual", "moodle"] | None = None


class StudyBlocksInput(BaseModel):
    blocks: list[StudyBlockInput] = Field(min_length=1)


class StudyBlocksResponse(BaseModel):
    blocks: list[StudyBlockOutput]


class AgendaSuggestionOutput(StudyBlockInput):
    reason: str
    task_due_date: str
    task_source: Literal["manual", "moodle"]


class AgendaSuggestionsInput(BaseModel):
    start_date: str | None = None


class AgendaSuggestionsResponse(BaseModel):
    suggestions: list[AgendaSuggestionOutput]


class RescheduleInput(BaseModel):
    study_date: str
    start_time: str
    duration_minutes: Literal[30, 60, 90]


def _student_id() -> int:
    return repo.get_or_create_default_student()


def _task(row) -> dict:
    status = get_deadline_status(row[3])
    return {
        "id": row[0], "title": row[1], "discipline": row[2], "due_date": row[3],
        "status": row[4], "notes": row[5], "source": row[6],
        "external_id": row[7], "external_course_id": row[8],
        "deadline": {"code": status.code, "label": status.label, "days_left": status.days_left, "severity": status.severity},
    }


def _courses(student_id: int) -> list[dict]:
    return [{"external_id": external_id, "shortname": shortname, "fullname": fullname}
            for external_id, shortname, fullname in repo.list_moodle_courses(student_id)]


def _notification(row) -> dict:
    return {
        "id": row[0],
        "type": row[1],
        "severity": row[2],
        "title": row[3],
        "message": row[4],
        "read": bool(row[5]),
        "created_at": row[6],
        "related_kind": row[7],
        "related_id": row[8],
        "action_url": row[9],
    }


def _study_block(row) -> dict:
    return {
        "id": row[0],
        "task_id": row[1],
        "title": row[2],
        "discipline": row[3],
        "study_date": row[4],
        "start_time": row[5],
        "duration_minutes": row[6],
        "origin": row[7],
        "status": row[8],
        "task_due_date": row[9],
        "task_source": row[10],
    }


def _topics(student_id: int) -> list[dict]:
    return [{"topic": topic, "count": count}
            for topic, count in repo.topic_ranking(student_id, GENERAL_DISCIPLINE, limit=10)]


def _conversations(student_id: int) -> list[dict]:
    return [{"id": cid, "title": title, "updated_at": updated_at}
            for cid, title, updated_at in repo.list_conversations(student_id, GENERAL_DISCIPLINE)]


def _build_insights(student_id: int) -> dict:
    raw_topics = repo.topic_ranking(student_id, GENERAL_DISCIPLINE, limit=10)
    total_questions = sum(count for _, count in raw_topics)
    topics = [
        {"topic": topic, "count": count, "percent": round((count / total_questions) * 100) if total_questions else 0}
        for topic, count in raw_topics
    ]
    pending_rows = repo.list_tasks_detailed(student_id, "PENDING")
    pending_tasks = [_task(row) for row in pending_rows]
    overdue = sum(1 for task in pending_tasks if task["deadline"]["code"] == "OVERDUE")
    due_soon = sum(1 for task in pending_tasks if task["deadline"]["severity"] >= 3)
    courses = _courses(student_id)
    completed = repo.count_tasks(student_id, "DONE")
    progress = {
        "total_questions": total_questions,
        "active_topics": len(raw_topics),
        "pending_tasks": len(pending_tasks),
        "completed_tasks": completed,
        "moodle_courses": len(courses),
        "due_soon": due_soon,
        "overdue": overdue,
    }

    recommendations: list[dict[str, str]] = []
    if overdue:
        recommendations.append({
            "title": "Regularize prazos atrasados",
            "priority": "Alta",
            "description": f"Você tem {overdue} atividade(s) atrasada(s). Comece pela menor entrega para reduzir risco acadêmico.",
        })
    elif due_soon:
        recommendations.append({
            "title": "Proteja os próximos prazos",
            "priority": "Alta",
            "description": f"{due_soon} prazo(s) exigem atenção nesta semana. Reserve um bloco curto hoje para avançar neles.",
        })
    if raw_topics:
        top_topic, top_count = raw_topics[0]
        if pending_tasks:
            next_task = pending_tasks[0]
            discipline_text = f" em {next_task['discipline']}" if next_task.get("discipline") else ""
            recommendations.append({
                "title": f"Conecte {top_topic} ao próximo prazo",
                "priority": "Alta" if next_task["deadline"]["severity"] >= 3 else "Média",
                "description": (
                    f"Você perguntou bastante sobre {top_topic} e tem '{next_task['title']}'{discipline_text}. "
                    "Use o chat para transformar essa entrega em um plano de estudo objetivo."
                ),
            })
        recommendations.append({
            "title": f"Reforce {top_topic}",
            "priority": "Média",
            "description": f"Esse foi seu tema mais perguntado ({top_count} pergunta(s)). Faça uma revisão ativa e resolva um exercício.",
        })
    else:
        recommendations.append({
            "title": "Use o chat para gerar histórico",
            "priority": "Média",
            "description": "Faça perguntas sobre suas disciplinas para o sistema identificar seus principais pontos de dúvida.",
        })
    if not courses:
        recommendations.append({
            "title": "Sincronize o Moodle",
            "priority": "Média",
            "description": "Nenhum curso Moodle foi importado. Matricule edu.student, sincronize e use os prazos no planejamento.",
        })
    if completed and len(pending_tasks) == 0:
        recommendations.append({
            "title": "Mantenha a rotina",
            "priority": "Baixa",
            "description": "Você está sem pendências abertas. Use o plano de hoje para consolidar o conteúdo mais perguntado.",
        })

    return {
        "progress": progress,
        "topics": topics,
        "recommendations": recommendations[:4],
        "recommendation": build_daily_plan(raw_topics),
    }


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="Edu Assistant API")
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/bootstrap", response_model=BootstrapResponse)
    def bootstrap():
        student_id = _student_id()
        profile = repo.get_profile(student_id)
        return {"profile": profile, "poles": POLES, "curriculum": CURRICULUM, "has_profile": profile is not None}

    @app.get("/api/profile", response_model=ProfileResponse)
    def get_profile():
        return {"profile": repo.get_profile(_student_id())}

    @app.put("/api/profile", response_model=ProfileResponse)
    def put_profile(body: ProfileInput):
        if body.pole_name not in POLES:
            raise HTTPException(422, "Polo desconhecido.")
        repo.upsert_profile(_student_id(), **body.model_dump())
        return {"profile": repo.get_profile(_student_id())}

    @app.get("/api/dashboard", response_model=DashboardResponse)
    def dashboard():
        student_id = _student_id()
        pending = repo.list_tasks_detailed(student_id, "PENDING")
        today = local_today().isoformat()
        today_blocks = [_study_block(row) for row in repo.list_study_blocks(student_id, today, today)]
        return {"profile": repo.get_profile(student_id),
                "metrics": {"pending_tasks": repo.count_tasks(student_id, "PENDING"), "due_within_7_days": repo.count_tasks_due_within_days(student_id, 7)},
                "courses": _courses(student_id), "sync_state": repo.get_moodle_sync_state(student_id),
                "upcoming_tasks": [_task(row) for row in pending[:10]], "topics": _topics(student_id),
                "today_blocks": today_blocks,
                "planned_minutes_today": sum(block["duration_minutes"] for block in today_blocks if block["status"] == "planned")}

    @app.post("/api/dashboard/today-plan", response_model=TextResponse)
    def today_plan():
        student_id = _student_id()
        profile = repo.get_profile(student_id)
        if not profile:
            raise HTTPException(422, "Preencha o perfil antes de gerar o plano.")
        return {"text": build_today_plan_text(profile, repo.list_upcoming_tasks(student_id, 10))}

    @app.post("/api/dashboard/suggestion", response_model=TextResponse)
    def suggestion():
        student_id = _student_id()
        profile = repo.get_profile(student_id)
        if not profile:
            raise HTTPException(422, "Preencha o perfil antes de gerar a sugestao.")
        return {"text": generate_daily_suggestion(profile, repo.topic_ranking(student_id, GENERAL_DISCIPLINE), repo.list_upcoming_tasks(student_id, 5))}

    @app.post("/api/moodle/sync", response_model=MoodleSyncResponse)
    def moodle_sync():
        try:
            return sync_moodle(_student_id())
        except MoodleClientError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.get("/api/moodle/diagnostics", response_model=MoodleDiagnosticsResponse)
    def moodle_diagnostics():
        return diagnose_moodle(_student_id())

    @app.get("/api/tasks", response_model=TasksResponse)
    def tasks(status: Literal["PENDING", "DONE"] | None = None):
        return {"tasks": [_task(row) for row in repo.list_tasks_detailed(_student_id(), status)]}

    @app.post("/api/tasks", status_code=201, response_model=TasksResponse)
    def create_task(body: TaskInput):
        repo.create_task(_student_id(), **body.model_dump())
        return {"tasks": [_task(row) for row in repo.list_tasks_detailed(_student_id())]}

    @app.patch("/api/tasks/{task_id}/status", response_model=TasksResponse)
    def update_task_status(task_id: int, body: TaskStatusInput):
        repo.set_task_status(task_id, body.status)
        return {"tasks": [_task(row) for row in repo.list_tasks_detailed(_student_id())]}

    @app.get("/api/agenda/availability", response_model=AvailabilityResponse)
    def agenda_availability():
        return {
            "availability": [
                {"weekday": weekday, "start_time": start_time, "end_time": end_time}
                for _, weekday, start_time, end_time in repo.list_availability(_student_id())
            ]
        }

    @app.put("/api/agenda/availability", response_model=AvailabilityResponse)
    def put_agenda_availability(body: list[AvailabilityInput]):
        slots = [slot.model_dump() for slot in body]
        try:
            validate_availability(slots)
        except AgendaError as exc:
            raise HTTPException(422, str(exc)) from exc
        repo.replace_availability(_student_id(), slots)
        return {"availability": slots}

    @app.get("/api/agenda", response_model=StudyBlocksResponse)
    def agenda(date_from: str | None = None, date_to: str | None = None):
        start = date_from or local_today().isoformat()
        end = date_to or (local_today() + timedelta(days=6)).isoformat()
        try:
            if date.fromisoformat(end) < date.fromisoformat(start):
                raise ValueError
        except ValueError as exc:
            raise HTTPException(422, "Intervalo de datas inválido.") from exc
        return {"blocks": [_study_block(row) for row in repo.list_study_blocks(_student_id(), start, end)]}

    @app.post("/api/agenda/suggestions", response_model=AgendaSuggestionsResponse)
    def agenda_suggestions(body: AgendaSuggestionsInput):
        try:
            start = date.fromisoformat(body.start_date) if body.start_date else local_today()
            suggestions = generate_suggestions(_student_id(), start)
        except (AgendaError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"suggestions": suggestions}

    @app.post("/api/agenda/blocks", status_code=201, response_model=StudyBlocksResponse)
    def create_agenda_blocks(body: StudyBlocksInput):
        student_id = _student_id()
        blocks = [block.model_dump() for block in body.blocks]
        try:
            validate_blocks(student_id, blocks)
            repo.create_study_blocks(student_id, blocks)
        except (AgendaError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        start = min(block["study_date"] for block in blocks)
        end = max(block["study_date"] for block in blocks)
        return {"blocks": [_study_block(row) for row in repo.list_study_blocks(student_id, start, end)]}

    @app.patch("/api/agenda/blocks/{block_id}/complete", response_model=StudyBlocksResponse)
    def complete_agenda_block(block_id: int):
        student_id = _student_id()
        block = repo.get_study_block(student_id, block_id)
        if not block:
            raise HTTPException(404, "Bloco de estudo não encontrado.")
        repo.complete_study_block(student_id, block_id)
        return {"blocks": [_study_block(repo.get_study_block(student_id, block_id))]}

    @app.patch("/api/agenda/blocks/{block_id}/reschedule", response_model=StudyBlocksResponse)
    def reschedule_agenda_block(block_id: int, body: RescheduleInput):
        student_id = _student_id()
        current = repo.get_study_block(student_id, block_id)
        if not current:
            raise HTTPException(404, "Bloco de estudo não encontrado.")
        block = {
            "task_id": current[1],
            "title": current[2],
            "discipline": current[3],
            "study_date": body.study_date,
            "start_time": body.start_time,
            "duration_minutes": body.duration_minutes,
            "origin": current[7],
        }
        try:
            validate_blocks(student_id, [block], ignore_block_id=block_id)
            repo.reschedule_study_block(
                student_id, block_id, body.study_date, body.start_time, body.duration_minutes,
            )
        except (AgendaError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"blocks": [_study_block(repo.get_study_block(student_id, block_id))]}

    @app.get("/api/notifications", response_model=NotificationsResponse)
    def notifications(status: Literal["all", "read", "unread"] = "all", limit: int = 50):
        read = None if status == "all" else status == "read"
        return {"notifications": [_notification(row) for row in repo.list_notifications(_student_id(), read, limit)]}

    @app.get("/api/notifications/summary", response_model=NotificationsSummaryResponse)
    def notifications_summary():
        student_id = _student_id()
        return {
            "unread_count": repo.count_unread_notifications(student_id),
            "notifications": [_notification(row) for row in repo.list_notifications(student_id, None, 5)],
        }

    @app.patch("/api/notifications/{notification_id}/read", response_model=NotificationMutationResponse)
    def mark_notification_read(notification_id: int):
        student_id = _student_id()
        repo.mark_notification_read(student_id, notification_id)
        return {"unread_count": repo.count_unread_notifications(student_id), "changed": 1}

    @app.post("/api/notifications/read-all", response_model=NotificationMutationResponse)
    def mark_all_notifications_read():
        student_id = _student_id()
        changed = repo.mark_all_notifications_read(student_id)
        return {"unread_count": repo.count_unread_notifications(student_id), "changed": changed}

    @app.delete("/api/notifications/read", response_model=NotificationMutationResponse)
    def delete_read_notifications():
        student_id = _student_id()
        deleted = repo.delete_read_notifications(student_id)
        return {"unread_count": repo.count_unread_notifications(student_id), "changed": deleted}

    @app.get("/api/conversations", response_model=ConversationsResponse)
    def conversations():
        return {"conversations": _conversations(_student_id())}

    @app.post("/api/conversations", status_code=201, response_model=CreateConversationResponse)
    def create_conversation(body: ConversationInput):
        cid = repo.create_conversation(_student_id(), GENERAL_DISCIPLINE, body.title)
        return {"id": cid, "conversations": _conversations(_student_id())}

    @app.delete("/api/conversations/{conversation_id}", response_model=ConversationsResponse)
    def delete_conversation(conversation_id: int):
        repo.delete_conversation(conversation_id)
        return {"conversations": _conversations(_student_id())}

    @app.get("/api/conversations/{conversation_id}/messages", response_model=MessagesResponse)
    def messages(conversation_id: int):
        return {"messages": [{"role": role, "content": content, "topic": topic}
                             for role, content, topic in repo.load_messages(conversation_id)]}

    @app.post("/api/conversations/{conversation_id}/messages", response_model=SendMessageResponse)
    def send_message(conversation_id: int, body: MessageInput):
        topic, answer = handle_user_message(_student_id(), GENERAL_LABEL, GENERAL_DISCIPLINE, conversation_id, body.content)
        return {"topic": topic, "answer": answer}

    @app.get("/api/chat/context", response_model=ChatContextResponse)
    def chat_context():
        student_id = _student_id()
        pending = repo.list_tasks_detailed(student_id, "PENDING")
        return {
            "profile": repo.get_profile(student_id),
            "courses": _courses(student_id),
            "upcoming_tasks": [_task(row) for row in pending[:5]],
            "topics": _topics(student_id),
            "sync_state": repo.get_moodle_sync_state(student_id),
        }

    @app.get("/api/insights", response_model=InsightsResponse)
    def insights():
        return _build_insights(_student_id())

    dev_frontend_url = os.getenv("EDU_ASSISTANT_FRONTEND_DEV_URL")
    if dev_frontend_url:
        @app.get("/{path:path}", include_in_schema=False)
        def spa_dev(path: str):
            target = f"{dev_frontend_url.rstrip('/')}/{path}" if path else dev_frontend_url
            return RedirectResponse(target)
        return app

    frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend.exists():
        app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            return FileResponse(frontend / "index.html")
    return app


app = create_app()
