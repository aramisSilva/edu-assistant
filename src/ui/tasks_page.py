import streamlit as st
from datetime import date

from src.core.dates import format_date_br
from src.core.deadlines import get_deadline_status
from src.core.curriculum import get_disciplines_for_semester, flatten_disciplines
from src.infra import repo


def render_tasks(student_id: int):
    st.subheader("Prazos e atividades")
    st.caption("Cadastre suas atividades e acompanhe o que está próximo de vencer.")

    profile = repo.get_profile(student_id)
    semester = int(profile.get("semester") or 1) if profile else 1

    semester_disc = get_disciplines_for_semester(semester)
    disc_options = ["—"] + [v["name"] for v in semester_disc.values()]
    name_to_key = {v["name"]: k for k, v in semester_disc.items()}

    with st.form("task_form"):
        title = st.text_input("Título da atividade", placeholder="Ex.: Lista 2 de Cálculo I")
        discipline_name = st.selectbox("Disciplina (opcional)", options=disc_options)
        due = st.date_input("Data de vencimento", value=date.today(), format="DD/MM/YYYY")
        notes = st.text_area("Observações (opcional)", placeholder="Ex.: revisar derivadas e resolver exercícios 1–5")

        submitted = st.form_submit_button("Adicionar atividade")

    if submitted:
        if not title.strip():
            st.error("Informe um título para a atividade.")
        else:
            discipline_key = None if discipline_name == "—" else name_to_key.get(discipline_name)
            repo.create_task(
                student_id=student_id,
                title=title.strip(),
                discipline=discipline_key,        # salva key real
                due_date=due.isoformat(),
                notes=notes.strip() or None,
            )
            st.success("Atividade adicionada.")
            st.rerun()

    st.divider()

    all_disc = flatten_disciplines()

    st.subheader("Pendentes")
    pending = repo.list_tasks(student_id, status="PENDING")
    if not pending:
        st.info("Nenhuma atividade pendente.")
    else:
        for task_id, title, discipline, due_date, status, notes in pending:
            ds = get_deadline_status(due_date)
            badge = f"[{ds.label}]"

            discipline_label = all_disc.get(discipline, {}).get("name") if discipline else "—"

            cols = st.columns([6, 2, 2])
            with cols[0]:
                st.write(f"**{badge} {title}**")
                st.caption(f"Data: {format_date_br(due_date)} • Disciplina: {discipline_label}")
                if notes:
                    st.caption(notes)

            with cols[1]:
                if st.button("Concluir", key=f"done_{task_id}"):
                    repo.set_task_status(task_id, "DONE")
                    st.rerun()

            with cols[2]:
                if st.button("Reabrir", key=f"reopen_{task_id}"):
                    repo.set_task_status(task_id, "PENDING")
                    st.rerun()

            st.markdown("---")

    st.subheader("Concluídas (últimas)")
    done = repo.list_tasks(student_id, status="DONE")
    if not done:
        st.info("Nenhuma atividade concluída ainda.")
    else:
        for task_id, title, discipline, due_date, status, notes in done[:10]:
            discipline_label = all_disc.get(discipline, {}).get("name") if discipline else "—"
            st.write(f"- {title} (vencimento {format_date_br(due_date)} • {discipline_label})")
