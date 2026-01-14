import streamlit as st
from src.infra import repo
from src.services.coaching import build_daily_plan

def render_progress(student_id: int, discipline_key: str):
    st.subheader("Meu Progresso")
    st.caption("Tópicos mais pesquisados (baseado nas suas perguntas).")

    ranking = repo.topic_ranking(student_id, discipline_key)
    if not ranking:
        st.info("Sem dados ainda. Faça algumas perguntas no chat.")
        return

    for t, c in ranking:
        st.write(f"- **{t}** — {c} perguntas")

def render_recommendations(student_id: int, discipline_key: str):
    st.subheader("Recomendações")
    ranking = repo.topic_ranking(student_id, discipline_key)

    st.markdown(build_daily_plan(ranking))

    st.divider()
    st.subheader("Sugestões rápidas")
    if ranking:
        top_topic = ranking[0][0]
        st.write(f"• Continue praticando: **{top_topic}**")
        st.write("• Peça: “Crie 3 exercícios graduais sobre X com gabarito”")
        st.write("• Peça: “Faça um quiz de 5 perguntas sobre X”")
    else:
        st.write("• Comece fazendo 3 perguntas sobre o conteúdo da disciplina.")
