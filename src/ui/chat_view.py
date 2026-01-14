import streamlit as st
from src.infra import repo
from src.services.chat_service import handle_user_message

def render_chat(student_id: int, discipline_label: str, discipline_key: str, conversation_id: int):
    st.subheader("Chat")

    msgs = repo.load_messages(conversation_id, limit=300)

    for role, content, _topic in msgs:
        with st.chat_message(role):
            st.markdown(content)

    user_input = st.chat_input("Digite sua dúvida…")

    if user_input:
        _topic, answer = handle_user_message(
            student_id=student_id,
            discipline_label=discipline_label,
            discipline_key=discipline_key,
            conversation_id=conversation_id,
            user_text=user_input,
        )
        st.rerun()

