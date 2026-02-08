import streamlit as st
from src.core.poles import POLES
from src.core.curriculum import get_disciplines_for_semester, flatten_disciplines
from src.infra import repo

DEFAULT_COURSE_NAME = "Bacharelado Interdisciplinar em Ciência e Tecnologia (BICT) – UFMT"


def render_profile_editor(student_id: int) -> bool:
    profile = repo.get_profile(student_id)

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
    st.caption("Atualize seu período, dedicação semanal e disciplinas, sem perder chats e prazos.")

    # session_state defaults para evitar “piscadas”
    if "edit_course_name" not in st.session_state:
        st.session_state.edit_course_name = profile.get("course_name") or DEFAULT_COURSE_NAME
    if "edit_semester" not in st.session_state:
        st.session_state.edit_semester = int(profile.get("semester") or 1)
    if "edit_weekly_hours" not in st.session_state:
        st.session_state.edit_weekly_hours = int(profile.get("weekly_hours") or 5)
    if "edit_focus" not in st.session_state:
        st.session_state.edit_focus = profile.get("focus") or ""
    if "edit_pole_name" not in st.session_state:
        st.session_state.edit_pole_name = profile.get("pole_name") or ("Cuiabá" if "Cuiabá" in POLES else list(POLES.keys())[0])

    # As disciplinas salvas são keys. Vamos mapear para nomes do semestre selecionado.
    all_disc = flatten_disciplines()
    saved_keys = set(profile.get("study_disciplines") or [])

    # Form
    with st.form("edit_profile_form"):
        course_name = st.text_input("Curso", value=st.session_state.edit_course_name)
        semester = st.selectbox("Período/Semestre atual", [1, 2, 3, 4, 5, 6], index=st.session_state.edit_semester - 1)
        weekly_hours = st.number_input("Dedicação semanal do aluno (horas por semana)", min_value=0, max_value=60, value=st.session_state.edit_weekly_hours)
        focus = st.text_input("Foco de aprendizado do aluno (disciplinas/temas)", value=st.session_state.edit_focus)

        # Disciplinas do semestre escolhido
        semester_disc = get_disciplines_for_semester(int(semester))
        disc_options = [v["name"] for v in semester_disc.values()]
        name_to_key = {v["name"]: k for k, v in semester_disc.items()}
        key_to_name = {k: v["name"] for k, v in semester_disc.items()}

        # default: as que estavam salvas e ainda pertencem ao semestre
        default_names = [key_to_name[k] for k in saved_keys if k in key_to_name]

        study_names = st.multiselect(
            "Disciplinas que você está estudando (do seu semestre)",
            options=disc_options,
            default=default_names if default_names else disc_options,  # se vazio, assume todas do semestre
        )

        pole_name = st.selectbox("Polo", list(POLES.keys()), index=list(POLES.keys()).index(st.session_state.edit_pole_name) if st.session_state.edit_pole_name in POLES else 0)

        submitted = st.form_submit_button("Salvar alterações")

    if submitted:
        study_keys = [name_to_key[n] for n in study_names if n in name_to_key]

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

    # Preview do polo selecionado
    st.divider()
    st.subheader("Dados do polo selecionado")
    p = POLES[st.session_state.edit_pole_name] if st.session_state.edit_pole_name in POLES else POLES[list(POLES.keys())[0]]
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
