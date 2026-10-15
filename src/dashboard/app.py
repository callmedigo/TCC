import streamlit as st

st.set_page_config(
    page_title="Dashboard de Projetos",
    page_icon="📊",
    layout="wide",
)

st.sidebar.title("Portfólio de projetos")
st.sidebar.caption("Acompanhamento de cronogramas e indicadores BSC")

navigation = st.navigation(
    [
        st.Page(
            "pages/visao_geral.py",
            title="Visão geral",
            icon="📋",
            url_path="visao-geral",
            default=True,
        ),
        st.Page("pages/cronograma.py", title="Cronograma", icon="🗓️", url_path="cronograma"),
        st.Page(
            "pages/proximas_atividades.py",
            title="Próximas atividades",
            icon="⏳",
            url_path="proximas-atividades",
        ),
        st.Page("pages/bsc.py", title="Indicadores BSC", icon="📈", url_path="indicadores-bsc"),
    ]
)
navigation.run()