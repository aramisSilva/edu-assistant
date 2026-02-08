import streamlit as st
from src.core.dates import format_date_br
from src.core.curriculum import flatten_disciplines
from src.infra import repo


def render_sidebar(student_id: int):
    """
    Sidebar com:
    - Perfil do aluno (com botão Editar)
    - Chats salvos
    Retorna: (discipline_label, discipline_key, conversation_id)

    OBS: Para não quebrar o chat atual, mantemos uma disciplina/categoria fixa.
    """
    st.sidebar.header("Configurações")

    profile = repo.get_profile(student_id)

    with st.sidebar.expander("Perfil do aluno", expanded=True):
        if profile:
            st.write(f"**Curso:** {profile.get('course_name')}")
            st.write(f"**Período:** {profile.get('semester')}/6")
            st.write(f"**Polo:** {profile.get('pole_name')}")

            wh = profile.get("weekly_hours")
            st.write(f"**Dedicação:** {wh if wh is not None else '—'} h/semana")

            keys = profile.get("study_disciplines") or []
            all_disc = flatten_disciplines()
            labels = [all_disc[k]["name"] for k in keys if k in all_disc]

            if labels:
                st.write(f"**Disciplinas:** {', '.join(labels)}")
            else:
                st.write("**Disciplinas:** —")
        else:
            st.info("Triagem ainda não cadastrada.")

        if st.button("Editar perfil", key="btn_edit_profile"):
            st.session_state.edit_profile = True
            st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("Chats")

    # Mantém chats em uma categoria fixa para não mexer no seu chat agora
    discipline_label = "Chat geral"
    discipline_key = "general"

    convs = repo.list_conversations(student_id, discipline_key, limit=50)

    if st.sidebar.button("Novo chat", key="btn_new_chat"):
        new_id = repo.create_conversation(student_id, discipline_key, title="Novo chat")
        st.session_state.selected_conversation_id = new_id
        st.rerun()

    if not convs:
        cid = repo.create_conversation(student_id, discipline_key, title="Novo chat")
        st.session_state.selected_conversation_id = cid
        st.rerun()

    conv_map = {
        f"{title}  ({format_date_br(updated_at)})": cid
        for cid, title, updated_at in convs
    }

    if "selected_conversation_id" not in st.session_state:
        st.session_state.selected_conversation_id = convs[0][0]

    current_id = st.session_state.selected_conversation_id
    valid_ids = [cid for cid, _, _ in convs]
    if current_id not in valid_ids:
        st.session_state.selected_conversation_id = convs[0][0]
        current_id = st.session_state.selected_conversation_id

    labels = list(conv_map.keys())
    ids = list(conv_map.values())
    current_index = ids.index(current_id) if current_id in ids else 0

    selected_label = st.sidebar.selectbox(
        "Conversas",
        options=labels,
        index=current_index,
        key="selected_conversation_label",
    )
    conversation_id = conv_map[selected_label]

    if st.sidebar.button("Excluir conversa", key="btn_delete_chat"):
        repo.delete_conversation(conversation_id)
        convs2 = repo.list_conversations(student_id, discipline_key, limit=50)
        if convs2:
            st.session_state.selected_conversation_id = convs2[0][0]
        else:
            cid = repo.create_conversation(student_id, discipline_key, title="Novo chat")
            st.session_state.selected_conversation_id = cid
        st.rerun()

    st.session_state.selected_conversation_id = conversation_id

    return discipline_label, discipline_key, conversation_id
