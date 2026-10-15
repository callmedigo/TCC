import streamlit as st
from src.dashboard.data import build_bsc_comparison, load_dashboard_data

def show() -> None:
    st.title("Indicadores BSC")
    st.caption("Comparação dos percentuais mensais e acumulados planejados e realizados.")

    try:
        projects, planned, actual = load_dashboard_data()
    except (FileNotFoundError, ValueError) as error:
        st.error(f"Não foi possível carregar os CSVs do dashboard: {error}")
        st.stop()

    comparison = build_bsc_comparison(planned, actual)
    if comparison.empty:
        st.info("Não há dados mensais de BSC nos CSVs processados.")
        return

    consolidated_projects = set(projects["Projeto"].dropna().unique())
    bsc_projects = set(comparison["Projeto"].dropna().unique())
    projects_without_bsc = sorted(consolidated_projects - bsc_projects)
    if projects_without_bsc:
        st.warning(
            f"Não há indicadores BSC mensais para {len(projects_without_bsc)} "
            f"projeto(s) do consolidado: {', '.join(projects_without_bsc)}."
        )

    project_names = sorted(comparison["Projeto"].dropna().unique().tolist())
    selected_project = st.selectbox("Filtrar por projeto", ["Todos os projetos", *project_names])
    if selected_project != "Todos os projetos":
        comparison = comparison.loc[comparison["Projeto"] == selected_project]

    if comparison.empty:
        st.info("Não há indicadores BSC para o filtro selecionado.")
        return

    st.dataframe(
        comparison,
        hide_index=True,
        width="stretch",
        column_config={
            "Month": st.column_config.TextColumn("Mês"),
            "Planejado mensal (%)": st.column_config.NumberColumn(
                "Planejado mensal", format="%.1f%%"
            ),
            "Realizado mensal (%)": st.column_config.NumberColumn(
                "Realizado mensal", format="%.1f%%"
            ),
            "Desvio mensal (p.p.)": st.column_config.NumberColumn(
                "Desvio mensal (p.p.)", format="%+.1f"
            ),
            "Planejado acumulado (%)": st.column_config.NumberColumn(
                "Planejado acumulado", format="%.1f%%"
            ),
            "Realizado acumulado (%)": st.column_config.NumberColumn(
                "Realizado acumulado", format="%.1f%%"
            ),
            "Desvio acumulado (p.p.)": st.column_config.NumberColumn(
                "Desvio acumulado (p.p.)", format="%+.1f"
            ),
        },
    )
    st.caption("O desvio é calculado como realizado menos planejado, em pontos percentuais.")

show()