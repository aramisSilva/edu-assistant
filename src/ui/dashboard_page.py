import streamlit as st

from src.infra import repo
from src.core.dates import format_date_br
from src.core.deadlines import get_deadline_status
from src.services.dashboard_service import generate_daily_suggestion
from src.services.plan_service import build_today_plan_text
from src.services.moodle_client import MoodleClientError
from src.services.moodle_sync import sync_moodle


def render_dashboard(student_id: int, discipline_key: str):
    profile = repo.get_profile(student_id)
    if not profile:
        st.info("Triagem não encontrada.")
        return

    sync_state = repo.get_moodle_sync_state(student_id)
    moodle_courses = repo.list_moodle_courses(student_id)
    if st.button("Sincronizar Moodle", key="btn_sync_moodle"):
        try:
            with st.spinner("Sincronizando cursos e prazos do Moodle..."):
                result = sync_moodle(student_id)
            st.success(f"Moodle sincronizado: {result['courses']} curso(s) e {result['tasks']} prazo(s).")
            st.rerun()
        except MoodleClientError as exc:
            st.error(str(exc))

    if sync_state:
        st.caption(f"Ultima sincronizacao Moodle: {sync_state['last_synced_at']}")
    if moodle_courses:
        st.caption("Cursos Moodle: " + ", ".join(course[2] for course in moodle_courses))

    pendentes = repo.count_tasks(student_id, status="PENDING")
    vencem_7d = repo.count_tasks_due_within_days(student_id, days=7)
    proximas = repo.list_upcoming_tasks(student_id, limit=10)
    ranking = repo.topic_ranking(student_id, discipline_key, limit=10)

    st.subheader("Visão geral")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Semestre", f"{profile.get('semester')}/6")
        st.caption(profile.get("course_name"))

    with c2:
        st.metric("Polo", profile.get("pole_name"))
        st.caption("Informações do polo cadastradas na triagem")

    with c3:
        wh = profile.get("weekly_hours")
        st.metric("Dedicação semanal", f"{wh if wh is not None else '—'} h")
        st.caption("Tempo que você pretende estudar por semana (não é carga horária do curso)")

    with c4:
        st.metric("Atividades pendentes", str(pendentes))
        st.caption(f"Vencem em até 7 dias: {vencem_7d}")

    st.divider()


    st.subheader("Plano de hoje")

    if "today_plan_text" not in st.session_state:
        st.session_state.today_plan_text = None

    btn_cols = st.columns([2, 2, 6])
    with btn_cols[0]:
        if st.button("Gerar plano", key="btn_today_plan"):
            with st.spinner("Gerando plano de hoje..."):
                st.session_state.today_plan_text = build_today_plan_text(profile, proximas, max_tasks=3)
            st.rerun()

    with btn_cols[1]:
        if st.button("Limpar plano", key="btn_clear_today_plan"):
            st.session_state.today_plan_text = None
            st.rerun()

    if st.session_state.today_plan_text:
        st.write(st.session_state.today_plan_text)
    else:
        st.caption("Clique em “Gerar plano” para receber um microplano baseado nos seus prazos e foco.")

    st.divider()

    st.subheader("Prazos próximos (pendentes)")
    if not proximas:
        st.info("Nenhuma atividade pendente cadastrada.")
    else:
        for task_id, title, discipline, due_date, notes in proximas[:5]:
            ds = get_deadline_status(due_date)
            badge = f"[{ds.label}]"

            st.write(f"**{badge} {title}**")
            st.caption(f"Data: {format_date_br(due_date)} • Disciplina: {discipline or '—'}")
            if notes:
                st.caption(notes)
            st.markdown("---")

    st.divider()

    st.subheader("Tópicos mais pesquisados (na disciplina selecionada)")
    if not ranking:
        st.info("Sem dados ainda. Faça algumas perguntas no chat para gerar histórico.")
    else:
        for t, c in ranking[:8]:
            st.write(f"- **{t}** — {c} pergunta(s)")

    st.divider()

    st.subheader("Sugestão do dia")
    with st.spinner("Gerando sugestão..."):
        suggestion = generate_daily_suggestion(profile, ranking, proximas[:5])
    st.write(suggestion)
