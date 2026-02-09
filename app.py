import streamlit as st

from src.infra.db import init_db
from src.infra.repo import get_or_create_default_student
from src.infra import repo

from src.ui.welcome import render_welcome
from src.ui.onboarding import render_onboarding
from src.ui.profile_editor import render_profile_editor

from src.ui.sidebar import render_sidebar
from src.ui.dashboard_page import render_dashboard
from src.ui.chat_view import render_chat
from src.ui.pages import render_progress, render_recommendations
from src.ui.tasks_page import render_tasks


def main():
    st.set_page_config(page_title="Assistente Acadêmico", layout="centered")
    st.title("Chatbot Inteligente - Edu Assistant")

    init_db()
    student_id = get_or_create_default_student()

    if "app_step" not in st.session_state:
        st.session_state.app_step = "welcome"

    if "edit_profile" not in st.session_state:
        st.session_state.edit_profile = False

    profile = repo.get_profile(student_id)

    if st.session_state.app_step == "welcome":
        render_welcome()
        return

    if not profile or st.session_state.app_step == "onboarding":
        render_onboarding(student_id)

        if repo.get_profile(student_id):
            st.session_state.app_step = "app"
            st.rerun()
        return

    if st.session_state.edit_profile:
        saved = render_profile_editor(student_id)
        if saved:
            st.session_state.edit_profile = False
            st.rerun()
        return

    discipline_label, discipline_key, conversation_id = render_sidebar(student_id)

    tabs = st.tabs(["Dashboard", "Chat", "Meu Progresso", "Recomendações", "Prazos"])

    with tabs[0]:
        render_dashboard(student_id, discipline_key)

    with tabs[1]:
        render_chat(student_id, discipline_label, discipline_key, conversation_id)

    with tabs[2]:
        render_progress(student_id, discipline_key)

    with tabs[3]:
        render_recommendations(student_id, discipline_key)

    with tabs[4]:
        render_tasks(student_id)


if __name__ == "__main__":
    main()
