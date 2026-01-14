import streamlit as st

from src.infra.db import init_db
from src.infra.repo import get_or_create_default_student
from src.infra import repo

from src.ui.onboarding import render_onboarding
from src.ui.sidebar import render_sidebar
from src.ui.chat_view import render_chat
from src.ui.pages import render_progress, render_recommendations
from src.ui.tasks_page import render_tasks


def main():
    st.set_page_config(page_title="Chatbot Educacional", layout="centered")
    st.title("Chatbot Inteligente Educacional")

    # 1) Banco e aluno default
    init_db()
    student_id = get_or_create_default_student()

    # 2) Triagem obrigatória (perfil do aluno)
    profile = repo.get_profile(student_id)
    if not profile:
        # Se não existe perfil, mostra onboarding e encerra a execução do fluxo principal
        render_onboarding(student_id)
        return

    # 3) Sidebar com disciplina + conversas (estilo ChatGPT)
    discipline_label, discipline_key, conversation_id = render_sidebar(student_id)

    # 4) Conteúdo principal
    tabs = st.tabs(["Chat", "Meu Progresso", "Recomendações", "Prazos"])

    with tabs[0]:
        render_chat(student_id, discipline_label, discipline_key, conversation_id)

    with tabs[1]:
        render_progress(student_id, discipline_key)

    with tabs[2]:
        render_recommendations(student_id, discipline_key)

    with tabs[3]:
        render_tasks(student_id)


if __name__ == "__main__":
    main()
