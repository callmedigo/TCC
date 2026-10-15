import altair as alt
import streamlit as st
from src.dashboard.data import build_timeline, load_dashboard_data

def show() -> None:
    st.title("Cronograma dos projetos")
    st.caption("Visualização das atividades, períodos e percentuais concluídos.")

    try:
        projects, _, _ = load_dashboard_data()
    except (FileNotFoundError, ValueError) as error:
        st.error(f"Não foi possível carregar os CSVs do dashboard: {error}")
        st.stop()

    project_names = sorted(projects["Projeto"].dropna().unique().tolist())
    if not project_names:
        st.info("Nenhum projeto foi encontrado em consolidado_projetos.csv.")
        return

    selected_project = st.selectbox("Filtrar por projeto", project_names)
    timeline = build_timeline(projects, selected_project)
    if timeline.empty:
        st.info("Não há atividades com datas válidas para este projeto.")
        return

    chart = (
        alt.Chart(timeline)
        .mark_bar()
        .encode(
            x=alt.X("Inicio:T", title="Início"),
            x2=alt.X2("Termino visual:T"),
            y=alt.Y("Atividade exibida:N", sort="-x", title=None),
            color=alt.Color(
                "Progresso (%):Q",
                scale=alt.Scale(domain=[0, 100], scheme="viridis"),
                title="Concluído (%)",
            ),
            tooltip=[
                alt.Tooltip("Atividade:N", title="Atividade"),
                alt.Tooltip("Recursos:N", title="Recursos"),
                alt.Tooltip("Inicio:T", title="Início", format="%d/%m/%Y"),
                alt.Tooltip("Termino:T", title="Término", format="%d/%m/%Y"),
                alt.Tooltip("Progresso (%):Q", title="Concluído", format=".1f"),
            ],
        )
        .properties(height=max(280, min(28 * len(timeline), 900)))
        .interactive()
    )
    st.altair_chart(chart, width="stretch")
    st.caption(f"{len(timeline)} atividades exibidas para **{selected_project}**.")

show()