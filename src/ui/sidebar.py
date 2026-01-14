import streamlit as st
from src.core.config import DISCIPLINES
from src.infra import repo
from src.core.dates import format_date_br

def render_sidebar(student_id: int):
    st.sidebar.header("Configuração")

    discipline_label = st.sidebar.selectbox("Disciplina", list(DISCIPLINES.keys()))
    discipline_key = DISCIPLINES[discipline_label]

    st.sidebar.divider()
    st.sidebar.header("Conversas")

    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None

    if st.sidebar.button("➕ Novo chat"):
        cid = repo.create_conversation(student_id, discipline_key, title="Novo chat")
        st.session_state.conversation_id = cid
        st.rerun()

    convs = repo.list_conversations(student_id, discipline_key)

    # garante ao menos 1 conversa
    if not convs and st.session_state.conversation_id is None:
        st.session_state.conversation_id = repo.create_conversation(student_id, discipline_key, title="Novo chat")
        st.rerun()

    if convs:
        conv_map = {f"{title}  ({format_date_br(updated_at)})": cid for cid, title, updated_at in convs}

        # se a conversa atual não pertence à disciplina, ajusta para a mais recente
        valid_ids = [cid for cid, _, _ in convs]
        if st.session_state.conversation_id not in valid_ids:
            st.session_state.conversation_id = valid_ids[0]

        # encontra índice do radio atual
        labels = list(conv_map.keys())
        current_id = st.session_state.conversation_id
        current_label = next((lbl for lbl, cid in conv_map.items() if cid == current_id), labels[0])
        current_index = labels.index(current_label)

        selected_label = st.sidebar.radio("Meus chats", options=labels, index=current_index)
        st.session_state.conversation_id = conv_map[selected_label]

        st.sidebar.divider()
        st.sidebar.subheader("Gerenciar chat")

        # Renomear (pega apenas a parte antes do "(YYYY-MM-DD)")
        base_title = selected_label.split("  (")[0]
        new_title = st.sidebar.text_input("Título", value=base_title)

        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Salvar", key="save_title"):
                t = (new_title.strip() or "Sem título")
                repo.rename_conversation(st.session_state.conversation_id, t)
                st.rerun()

        with col2:
            if st.button("Excluir", key="delete_chat"):
                repo.delete_conversation(st.session_state.conversation_id)
                st.session_state.conversation_id = None
                st.rerun()

    return discipline_label, discipline_key, st.session_state.conversation_id
