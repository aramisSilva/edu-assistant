import streamlit as st
from src.core.poles import POLES
from src.core.curriculum import get_disciplines_for_semester
from src.infra import repo

DEFAULT_COURSE_NAME = "Bacharelado Interdisciplinar em Ciência e Tecnologia (BICT) – UFMT"


def render_onboarding(student_id: int):
    st.header("Triagem do aluno")
    st.caption("Preencha para personalizar o assistente (curso, semestre, disciplinas, polo, foco e prazos).")

    if "onboarding_course_name" not in st.session_state:
        st.session_state.onboarding_course_name = DEFAULT_COURSE_NAME
    if "onboarding_semester" not in st.session_state:
        st.session_state.onboarding_semester = 1
    if "onboarding_weekly_hours" not in st.session_state:
        st.session_state.onboarding_weekly_hours = 5
    if "onboarding_focus" not in st.session_state:
        st.session_state.onboarding_focus = ""
    if "onboarding_pole_name" not in st.session_state:
        st.session_state.onboarding_pole_name = "Cuiabá" if "Cuiabá" in POLES else list(POLES.keys())[0]

    st.text_input(
        "Curso",
        key="onboarding_course_name",
        help="Curso principal do aluno (não confundir com disciplinas).",
    )

    st.selectbox(
        "Período/Semestre atual",
        [1, 2, 3, 4, 5, 6],
        key="onboarding_semester",
    )

    st.number_input(
        "Dedicação semanal do aluno (horas por semana)",
        min_value=0,
        max_value=60,
        key="onboarding_weekly_hours",
    )

    st.text_input(
        "Foco de aprendizado do aluno (disciplinas/temas)",
        key="onboarding_focus",
        placeholder="Ex.: melhorar em cálculo e revisar programação",
    )

    semester = int(st.session_state.onboarding_semester)
    semester_disc = get_disciplines_for_semester(semester)

    disc_options = [v["name"] for v in semester_disc.values()]
    name_to_key = {v["name"]: k for k, v in semester_disc.items()}

    st.multiselect(
        "Disciplinas que você está estudando agora (do seu semestre)",
        options=disc_options,
        key="onboarding_study_disciplines",
        default=disc_options,
        help="Você pode ajustar depois em 'Editar perfil'.",
    )

    st.markdown("### Polo (selecione por último)")
    st.selectbox(
        "Qual polo você está matriculado?",
        list(POLES.keys()),
        key="onboarding_pole_name",
    )

    pole_name = st.session_state.onboarding_pole_name

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

    st.divider()

    if st.button("Salvar triagem"):
        course_name = (st.session_state.onboarding_course_name or "").strip() or DEFAULT_COURSE_NAME
        semester = int(st.session_state.onboarding_semester)
        weekly_hours = st.session_state.onboarding_weekly_hours
        focus = (st.session_state.onboarding_focus or "").strip() or None

        selected_names = st.session_state.get("onboarding_study_disciplines", []) or []
        study_keys = [name_to_key[n] for n in selected_names if n in name_to_key]

        repo.upsert_profile(
            student_id=student_id,
            course_name=course_name,
            semester=semester,
            pole_name=pole_name,
            weekly_hours=int(weekly_hours) if weekly_hours else None,
            focus=focus,
            study_disciplines=study_keys,
        )

        st.success("Triagem salva. Você já pode usar o assistente.")
        st.rerun()
