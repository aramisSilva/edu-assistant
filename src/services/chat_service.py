from src.core.dates import format_date_br
from src.core.topics import TOPICS
from src.core.poles import POLES

from src.services.llm import chat_completion, generate_pedagogical_answer, generate_short_title
from src.infra import repo


def classify_topic(discipline_key: str, user_text: str) -> str:
    lowered = user_text.lower()
    for t in TOPICS[discipline_key]:
        if t.lower() in lowered:
            return t

    topics_list = ", ".join(TOPICS[discipline_key])
    msgs = [
        {
            "role": "system",
            "content": (
                f"Classifique a pergunta em exatamente 1 tópico desta lista: {topics_list}. "
                "Responda só com o nome do tópico."
            ),
        },
        {"role": "user", "content": user_text},
    ]
    topic = chat_completion(msgs, temperature=0.0).strip()
    return topic if topic in TOPICS[discipline_key] else "Sem tópico"


def _build_extra_context(student_id: int) -> str | None:
    profile = repo.get_profile(student_id)
    if not profile:
        return None

    # Etapa 5 (como solicitado): forçar polo "Cuiabá" no contexto
    forced_pole_name = "Cuiabá"
    pole = POLES.get(forced_pole_name)

    # Polo (endereço/contatos)
    pole_lines = []
    pole_lines.append(f"- Polo: {forced_pole_name}")
    if pole:
        if pole.get("address"):
            pole_lines.append(f"- Endereço do polo: {pole['address']}")
        if pole.get("cep"):
            pole_lines.append(f"- CEP: {pole['cep']}")
        if pole.get("gps"):
            pole_lines.append(f"- Coordenadas (GPS): {pole['gps']}")
        if pole.get("email"):
            pole_lines.append(f"- E-mail do polo: {pole['email']}")
        if pole.get("phone"):
            pole_lines.append(f"- Telefone do polo: {pole['phone']}")
        if pole.get("extra"):
            pole_lines.append(f"- Observação: {pole['extra']}")
    else:
        pole_lines.append("- (Dados do polo não encontrados no catálogo.)")

    # Próximas tarefas
    upcoming = repo.upcoming_tasks(student_id, limit=5)
    tasks_lines = ["Prazos próximos (pendentes):"]
    if upcoming:
        for t_title, t_disc, t_due in upcoming:
            tasks_lines.append(f"- {t_title} (disciplina: {t_disc or '—'}; vence em {format_date_br(t_due)})")
    else:
        tasks_lines.append("- Nenhum prazo cadastrado.")

    # Triagem + curso
    triage_lines = [
        "Contexto do aluno (triagem):",
        f"- Curso: {profile.get('course_name')}",
        f"- Semestre atual do aluno: {profile.get('semester')}/6",
        f"- Dedicação semanal do aluno (não é carga horária do curso): {profile.get('weekly_hours')} horas/semana",
        f"- Foco atual do aluno (não é foco do curso): {profile.get('focus')}",
        "",
        "Restrições de interpretação:",
        "- Python/SQL/Estruturas de Dados são disciplinas/temas da grade, não 'foco do curso'.",
        "- As horas/semana informadas representam a dedicação do aluno, não a carga horária do curso.",
        "",
        "Ao descrever o perfil, use frases como:",
        "- 'Você está focado em aprender X, Y, Z.'",
        "- 'Você pretende estudar aproximadamente N horas por semana.'",
        "",
    ]

    triage_lines.extend(pole_lines)
    triage_lines.append("")
    triage_lines.extend(tasks_lines)
    triage_lines.append("")
    triage_lines.append(
        "Use esse contexto quando o aluno perguntar sobre curso, semestre, polo/endereço/contatos, prazos, organização e recomendações. "
        "Não invente informações fora deste contexto."
    )
    triage_lines.append("Se o usuário pedir 'me fale sobre meu perfil', descreva o aluno. Não descreva o curso como tendo foco ou carga horária semanal.")


    return "\n".join(triage_lines)


def handle_user_message(
    student_id: int,
    discipline_label: str,
    discipline_key: str,
    conversation_id: int,
    user_text: str
):
    # 1) Topic
    topic = classify_topic(discipline_key, user_text)

    # 2) Save user message
    repo.save_message(student_id, discipline_key, conversation_id, "user", user_text, topic=topic)

    # 3) Auto-title on first user message
    msgs = repo.load_messages(conversation_id, limit=80)
    user_msgs_count = sum(1 for r, _, _ in msgs if r == "user")
    if user_msgs_count == 1:
        title = generate_short_title(user_text)
        repo.rename_conversation(conversation_id, title)

    # 4) Context (last 12 messages)
    context = [(r, c) for r, c, _ in msgs][-12:]

    # 5) Extra context (triagem + curso + polo fixo Cuiabá + prazos)
    extra_context = _build_extra_context(student_id)

    # 6) Answer
    answer = generate_pedagogical_answer(
        discipline_label=discipline_label,
        user_text=user_text,
        recent_msgs=context,
        extra_context=extra_context,
    )

    # 7) Save assistant
    repo.save_message(student_id, discipline_key, conversation_id, "assistant", answer, topic=topic)

    return topic, answer
