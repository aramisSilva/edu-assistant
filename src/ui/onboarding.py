import streamlit as st
from src.core.poles import POLES
from src.infra import repo

DEFAULT_COURSE_NAME = "Bacharelado Interdisciplinar em Ciência e Tecnologia (BICT) – UFMT"


def render_onboarding(student_id: int):
    st.header("Triagem do aluno")
    st.caption("Preencha para personalizar o assistente (curso, semestre, polo, foco e prazos).")

    # Defaults em session_state
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

    # 1) Campos do perfil (podem ficar em um bloco/“form visual”, mas fora de st.form)
    st.text_input(
        "Curso",
        key="onboarding_course_name",
        help="Este é o curso principal do aluno (não confundir com disciplinas como Python).",
    )
    st.selectbox(
        "Em qual semestre você está?",
        [1, 2, 3, 4, 5, 6],
        key="onboarding_semester",
    )
    st.number_input(
        "Horas disponíveis por semana (opcional)",
        min_value=0,
        max_value=60,
        key="onboarding_weekly_hours",
    )
    st.text_input(
        "Seu foco agora (opcional)",
        key="onboarding_focus",
        placeholder="Ex.: melhorar em SQL e organizar prazos",
    )

    # 2) Polo por ÚLTIMO, fora do form => atualiza em tempo real
    st.markdown("### Polo (selecione por último)")
    st.selectbox(
        "Qual polo você está matriculado?",
        list(POLES.keys()),
        key="onboarding_pole_name",
    )

    pole_name = st.session_state.onboarding_pole_name

    # Dados do polo mudam instantaneamente
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

    # 3) Botão de salvar (fora do form)
    if st.button("Salvar triagem"):
        course_name = (st.session_state.onboarding_course_name or "").strip() or DEFAULT_COURSE_NAME
        semester = int(st.session_state.onboarding_semester)
        weekly_hours = st.session_state.onboarding_weekly_hours
        focus = (st.session_state.onboarding_focus or "").strip() or None

        repo.upsert_profile(
            student_id=student_id,
            course_name=course_name,
            semester=semester,
            pole_name=pole_name,
            weekly_hours=int(weekly_hours) if weekly_hours else None,
            focus=focus,
        )
        st.success("Triagem salva. Você já pode usar o assistente.")
        st.rerun()
