import streamlit as st
from datetime import date
from src.core.config import DISCIPLINES
from src.infra import repo
from src.core.dates import format_date_br

def render_tasks(student_id: int):
    st.subheader("Prazos e atividades")
    st.caption("Cadastre suas atividades e acompanhe o que está próximo de vencer.")

    with st.form("task_form"):
        title = st.text_input("Título da atividade", placeholder="Ex.: Lista 2 de SQL")
        discipline_label = st.selectbox("Disciplina (opcional)", ["—"] + list(DISCIPLINES.keys()))
        due = st.date_input("Data de vencimento", value=date.today(), format="DD/MM/YYYY")
        notes = st.text_area("Observações (opcional)", placeholder="Ex.: revisar JOIN e GROUP BY antes")

        submitted = st.form_submit_button("Adicionar atividade")

    if submitted:
        if not title.strip():
            st.error("Informe um título para a atividade.")
        else:
            discipline_key = None if discipline_label == "—" else DISCIPLINES[discipline_label]
            repo.create_task(
                student_id=student_id,
                title=title.strip(),
                discipline=discipline_key,
                due_date=due.isoformat(),
                notes=notes.strip() or None,
            )
            st.success("Atividade adicionada.")
            st.rerun()

    st.divider()
    st.subheader("Pendentes")
    pending = repo.list_tasks(student_id, status="PENDING")
    if not pending:
        st.info("Nenhuma atividade pendente.")
    else:
        for task_id, title, discipline, due_date, status, notes in pending:
            cols = st.columns([5, 2, 2])
            with cols[0]:
                st.write(f"**{title}**")
                if discipline:
                    st.caption(f"Disciplina: {discipline} | Vence em: {format_date_br(due_date)}")
                else:
                    st.caption(f"Vence em: {format_date_br(due_date)}")
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

    st.divider()
    st.subheader("Concluídas (últimas)")
    done = repo.list_tasks(student_id, status="DONE")
    if not done:
        st.info("Nenhuma atividade concluída ainda.")
    else:
        for task_id, title, discipline, due_date, status, notes in done[:10]:
            st.write(f"- {title} (vencimento {format_date_br(due_date)})")
