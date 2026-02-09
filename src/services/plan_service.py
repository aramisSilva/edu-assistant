from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from src.core.dates import format_date_br
from src.core.deadlines import get_deadline_status
from src.services.llm import chat_completion


@dataclass(frozen=True)
class PlanTask:
    title: str
    discipline: str | None
    due_date_iso: str
    status_label: str
    severity: int


def _sort_key_for_task(due_date_iso: str) -> tuple[int, int]:
    """
    Ordena por criticidade (severity desc) e depois por dias restantes (menor primeiro).
    severity: 5 (crítico) -> 1 (leve)
    """
    ds = get_deadline_status(due_date_iso)
    days_left = ds.days_left if ds.days_left is not None else 9999
    return (-ds.severity, days_left)


def build_today_plan_text(profile: dict, tasks_rows: list[tuple], max_tasks: int = 3) -> str:
    """
    tasks_rows: [(id, title, discipline, due_date, notes), ...] (pendentes, já ordenadas por due_date no repo)
    """
    weekly_hours = profile.get("weekly_hours")
    focus = profile.get("focus") or "—"

    sorted_rows = sorted(tasks_rows, key=lambda r: _sort_key_for_task(r[3]))

    selected = []
    for _, title, discipline, due_date, _ in sorted_rows[:10]:
        ds = get_deadline_status(due_date)
        selected.append(
            PlanTask(
                title=title,
                discipline=discipline,
                due_date_iso=due_date,
                status_label=ds.label,
                severity=ds.severity,
            )
        )
        if len(selected) >= max_tasks:
            break

    tasks_text_lines = []
    if selected:
        for t in selected:
            tasks_text_lines.append(
                f"- [{t.status_label}] {t.title} (disciplina: {t.discipline or '—'}; vence em {format_date_br(t.due_date_iso)})"
            )
    else:
        tasks_text_lines.append("- Nenhuma atividade pendente cadastrada.")

    wh_txt = f"{weekly_hours} h/semana" if weekly_hours is not None else "—"

    prompt = f"""
Contexto do aluno (não inventar dados):
- Curso: {profile.get('course_name')}
- Semestre do aluno: {profile.get('semester')}/6
- Polo: {profile.get('pole_name')}
- Dedicação semanal do aluno (não é carga horária do curso): {wh_txt}
- Foco de aprendizado do aluno (disciplinas/temas): {focus}

Atividades pendentes priorizadas (usar como base):
{chr(10).join(tasks_text_lines)}

Tarefa:
Gere um "Plano de hoje" em português do Brasil, com no máximo 10 linhas, objetivo e acionável.
Regras:
- Priorize as atividades mais críticas (Atrasada/Vence hoje/Vence amanhã/Urgente).
- Se não houver atividades, proponha um plano baseado no foco do aluno.
- Não diga que o curso tem foco em disciplinas.
- Não chame dedicação semanal de "carga horária do curso".
- Inclua: (1) Prioridade do dia, (2) Microplano 30–60 min (passos), (3) Uma recomendação de estudo ligada ao foco.
"""

    messages = [
        {"role": "system", "content": "Você é um assistente acadêmico objetivo, em português do Brasil."},
        {"role": "user", "content": prompt.strip()},
    ]

    return chat_completion(messages, temperature=0.35).strip()
