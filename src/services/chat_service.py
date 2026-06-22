from src.core.dates import format_date_br
import unicodedata

from src.core.topics import TOPICS, TOPIC_ALIASES
from src.core.poles import POLES
from src.core.curriculum import flatten_disciplines
from src.services.llm import generate_pedagogical_answer, generate_short_title, generate_topic_label
from src.infra import repo


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _clean_generated_topic(topic: str) -> str:
    topic = " ".join((topic or "").strip().strip("\"'`.,:;!?").split())
    if not topic:
        return "Dúvidas gerais"
    if len(topic) > 60 or len(topic.split()) > 5 or "\n" in topic:
        return "Dúvidas gerais"
    return topic[0].upper() + topic[1:]


def _classify_topic_by_alias(discipline_key: str, text: str) -> str | None:
    topics = TOPICS.get(discipline_key) or TOPICS.get("general") or []
    text_l = _normalize_text(text)

    for topic in topics:
        aliases = [topic, *TOPIC_ALIASES.get(topic, [])]
        if any(_normalize_text(alias) in text_l for alias in aliases):
            return topic

    return None


def classify_topic(discipline_key: str, text: str) -> str:
    known_topic = _classify_topic_by_alias(discipline_key, text)
    if known_topic:
        return known_topic

    try:
        generated_topic = generate_topic_label(text)
    except Exception:
        generated_topic = ""

    return _clean_generated_topic(generated_topic)


def _build_extra_context(student_id: int) -> str | None:
    profile = repo.get_profile(student_id)
    if not profile:
        return None
    pole_name = profile.get("pole_name") or "Cuiabá"
    pole = POLES.get(pole_name)
    ...
    pole_lines = []
    pole_lines.append(f"- Polo: {pole_name}")

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

    upcoming = repo.upcoming_tasks(student_id, limit=5)
    tasks_lines = ["Prazos próximos (pendentes):"]
    if upcoming:
        for t_title, t_disc, t_due in upcoming:
            tasks_lines.append(f"- {t_title} (disciplina: {t_disc or '—'}; vence em {format_date_br(t_due)})")
    else:
        tasks_lines.append("- Nenhum prazo cadastrado.")
    moodle_courses = repo.list_moodle_courses(student_id)
    moodle_lines = ["Cursos importados do Moodle:"]
    if moodle_courses:
        moodle_lines.extend(
            f"- {fullname} ({shortname or external_id})"
            for external_id, shortname, fullname in moodle_courses
        )
    else:
        moodle_lines.append("- Nenhum curso sincronizado.")
    all_disc = flatten_disciplines()
    disc_keys = profile.get("study_disciplines") or []
    disc_labels = [all_disc[k]["name"] for k in disc_keys if k in all_disc]
    disciplines_text = ", ".join(disc_labels) if disc_labels else "—"

    triage_lines = [
        "Contexto do aluno (triagem):",
        f"- Curso: {profile.get('course_name')}",
        f"- Semestre atual do aluno: {profile.get('semester')}/6",
        f"- Disciplinas do semestre selecionadas pelo aluno: {disciplines_text}",
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
    triage_lines.extend(moodle_lines)
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
    topic = classify_topic(discipline_key, user_text)

    repo.save_message(student_id, discipline_key, conversation_id, "user", user_text, topic=topic)

    msgs = repo.load_messages(conversation_id, limit=80)
    user_msgs_count = sum(1 for r, _, _ in msgs if r == "user")
    if user_msgs_count == 1:
        title = generate_short_title(user_text)
        repo.rename_conversation(conversation_id, title)

    context = [(r, c) for r, c, _ in msgs][-12:]

    extra_context = _build_extra_context(student_id)

    answer = generate_pedagogical_answer(
        discipline_label=discipline_label,
        user_text=user_text,
        recent_msgs=context,
        extra_context=extra_context,
    )

    repo.save_message(student_id, discipline_key, conversation_id, "assistant", answer, topic=topic)

    return topic, answer
