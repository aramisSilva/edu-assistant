from src.services.llm import chat_completion
from src.core.dates import format_date_br

def generate_daily_suggestion(profile: dict, top_topics: list[tuple[str, int]], upcoming_tasks: list[tuple]) -> str:
    """
    profile: dict do get_profile
    top_topics: [(topic, count), ...]
    upcoming_tasks: [(id, title, discipline, due_date, notes), ...]
    """
    topics_text = "\n".join([f"- {t} ({c})" for t, c in top_topics[:5]]) or "- (ainda sem dados)"
    tasks_text = "\n".join(
        [f"- {title} (vence em {format_date_br(due_date)})" for _, title, _, due_date, _ in upcoming_tasks]
    ) or "- (nenhum prazo cadastrado)"

    wh = profile.get("weekly_hours")
    wh_txt = f"{wh} horas/semana" if wh is not None else "—"

    focus = profile.get("focus") or "—"

    prompt = f"""
Contexto do aluno:
- Curso: {profile.get('course_name')}
- Semestre do aluno: {profile.get('semester')}/6
- Polo: {profile.get('pole_name')}
- Dedicação semanal do aluno (não é carga horária do curso): {wh_txt}
- Foco de aprendizado do aluno (disciplinas/temas): {focus}

Tópicos mais pesquisados (na disciplina selecionada):
{topics_text}

Prazos próximos (pendentes):
{tasks_text}

Tarefa:
Crie uma sugestão do dia curta e prática (máximo 6 linhas), em português do Brasil, combinando:
- 1 prioridade (o que fazer hoje),
- 1 microplano (15–30 min),
- 1 recomendação de estudo ligada ao foco do aluno.
Não invente dados. Não diga que o curso tem foco em disciplinas. Não chame dedicação semanal de "carga horária do curso".
"""

    messages = [
        {"role": "system", "content": "Você é um assistente acadêmico objetivo, em português do Brasil."},
        {"role": "user", "content": prompt.strip()},
    ]

    return chat_completion(messages, temperature=0.4).strip()
