import streamlit as st
from src.core.config import DISCIPLINES
from src.core.poles import POLES
from src.infra import repo

DEFAULT_COURSE_NAME = "Bacharelado Interdisciplinar em Ciência e Tecnologia (BICT) – UFMT"


def render_profile_editor(student_id: int):
    """
    Renderiza um formulário de edição do perfil (triagem) pré-preenchido.
    Retorna True quando salvar.
    """
    profile = repo.get_profile(student_id)

    # fallback (caso extremo)
    if not profile:
        profile = {
            "course_name": DEFAULT_COURSE_NAME,
            "semester": 1,
            "pole_name": "Cuiabá" if "Cuiabá" in POLES else list(POLES.keys())[0],
            "weekly_hours": 5,
            "focus": "",
            "study_disciplines": [],
        }

    st.header("Editar perfil do aluno")
    st.caption("Atualize seu período, dedicação semanal e disciplinas estudadas, sem perder histórico de chats e prazos.")

    discipline_labels = list(DISCIPLINES.keys())
    # converte keys salvas -> labels
    saved_keys = set(profile.get("study_disciplines") or [])
    default_selected_labels = [lbl for lbl in discipline_labels if DISCIPLINES[lbl] in saved_keys]

    with st.form("edit_profile_form"):
        course_name = st.text_input("Curso", value=profile.get("course_name") or DEFAULT_COURSE_NAME)
        semester = st.selectbox("Período/Semestre atual", [1, 2, 3, 4, 5, 6], index=(profile.get("semester", 1) - 1))
        weekly_hours = st.number_input(
            "Dedicação semanal do aluno (horas por semana)",
            min_value=0,
            max_value=60,
            value=int(profile.get("weekly_hours") or 5),
        )

        focus = st.text_input(
            "Foco de aprendizado do aluno (disciplinas/temas)",
            value=profile.get("focus") or "",
        )

        study_labels = st.multiselect(
            "Disciplinas que você está estudando agora",
            options=discipline_labels,
            default=default_selected_labels,
        )

        pole_name = st.selectbox(
            "Polo",
            list(POLES.keys()),
            index=list(POLES.keys()).index(profile.get("pole_name")) if profile.get("pole_name") in POLES else 0,
        )

        submitted = st.form_submit_button("Salvar alterações")

    if submitted:
        # labels -> keys
        study_keys = [DISCIPLINES[lbl] for lbl in study_labels]

        repo.upsert_profile(
            student_id=student_id,
            course_name=(course_name.strip() or DEFAULT_COURSE_NAME),
            semester=int(semester),
            pole_name=pole_name,
            weekly_hours=int(weekly_hours) if weekly_hours else None,
            focus=(focus.strip() or None),
            study_disciplines=study_keys,
        )

        st.success("Perfil atualizado com sucesso.")
        return True

    # preview do polo (opcional)
    st.divider()
    st.subheader("Dados do polo selecionado")
    p = POLES[pole_name]
    st.write(f"**Endereço:** {p['address']}")
    if p.get("cep"):
        st.write(f"**CEP:** {p['cep']}")
    if p.get("gps"):
        st.write(f"**Coordenadas (GPS):** {p['gps']}")
    if p.get("email"):
        st.write(f"**E-mail:** {p['email']}")
    if p.get("phone"):
        st.write(f"**Telefone:** {p['phone']}")
    if p.get("extra"):
        st.write(f"**Complemento:** {p['extra']}")

    return False
