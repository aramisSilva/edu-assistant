import time
import streamlit as st


def render_welcome() -> None:
    st.markdown("""
    <style>
    @keyframes float {
      0% { transform: translateY(0px); opacity: .85; }
      50% { transform: translateY(-10px); opacity: 1; }
      100% { transform: translateY(0px); opacity: .85; }
    }

    @keyframes shimmer {
      0% { background-position: -200% 0; }
      100% { background-position: 200% 0; }
    }

    .welcome-box {
      border-radius: 16px;
      padding: 26px;
      border: 1px solid rgba(0,0,0,0.10);
      background: linear-gradient(135deg, #f7f9fc, #eef2f7);
      position: relative;
      overflow: hidden;
    }

    .welcome-box::before{
      content:"";
      position:absolute;
      top:0; left:0; right:0; bottom:0;
      background: linear-gradient(
        90deg,
        rgba(255,255,255,0.0),
        rgba(255,255,255,0.35),
        rgba(255,255,255,0.0)
      );
      background-size: 200% 100%;
      animation: shimmer 3.2s ease-in-out infinite;
      pointer-events:none;
      opacity: .7;
    }

    .icon {
      font-size: 56px;
      animation: float 2.6s ease-in-out infinite;
      line-height: 1;
    }

    .subtitle {
      margin: 6px 0 0 0;
      opacity: .85;
    }

    .pill {
      display:inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(13, 110, 253, 0.10);
      border: 1px solid rgba(13, 110, 253, 0.18);
      font-size: 12px;
      margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2], vertical_alignment="center")

    with col1:
        st.markdown("""
        <div class="welcome-box">
          <div style="display:flex; gap:16px; align-items:center;">
            <div class="icon">🎓</div>
            <div>
              <div style="font-weight:700; font-size:18px;">Assistente Acadêmico</div>
              <div class="subtitle">BICT – UFMT</div>
              <div class="pill">IA + Organização + Prazos</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("## Bem-vindo ao Assistente Acadêmico do BICT – UFMT")
        st.caption("Chatbot Inteligente Educacional: apoio ao aprendizado e organização acadêmica.")

        st.write(
            "Aqui você poderá organizar prazos, gerar um plano de estudo para hoje e tirar dúvidas "
            "com base no seu perfil acadêmico."
        )

    st.divider()

    st.markdown("### O que você pode fazer aqui")
    st.markdown("- ✅ Realizar a **triagem** para personalizar o assistente")
    st.markdown("- ✅ Acompanhar **prazos inteligentes** (atrasada, vence hoje, urgente, etc.)")
    st.markdown("- ✅ Gerar um **Plano de hoje** com base no tempo disponível")
    st.markdown("- ✅ Fazer perguntas no **chat** usando seu contexto")

    st.info("Clique em **Iniciar** para realizar a triagem e personalizar o sistema para você.")

    c1, c2, c3 = st.columns([1.2, 1.2, 6])

    with c1:
        if st.button("Iniciar", type="primary", use_container_width=True):
            with st.spinner("Iniciando..."):
                time.sleep(0.4)
            st.session_state.app_step = "onboarding"
            st.rerun()

    with c2:
        if st.button("Ver demo", use_container_width=True):
            st.session_state.app_step = "app"
            st.rerun()

    with c3:
        st.caption("Dica: após a triagem, você poderá editar seu perfil a qualquer momento pela barra lateral.")
