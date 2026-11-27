import altair as alt
import streamlit as st
from src.dashboard.data import build_bsc_comparison, load_dashboard_data, load_indicator_data
from src.dashboard.views import indicadores

MONTHLY_FIELDS = ["Planejado mensal (%)", "Realizado mensal (%)"]
CUMULATIVE_FIELDS = ["Planejado acumulado (%)", "Realizado acumulado (%)"]
SERIES_DOMAIN = [
    "Planejado mensal (%)",
    "Realizado mensal (%)",
    "Planejado acumulado (%)",
    "Realizado acumulado (%)",
]
SERIES_COLORS = ["#2563eb", "#10b981", "#f59e0b", "#ef4444"]

def _build_project_chart(comparison):
    months = sorted(comparison["Month"].dropna().unique().tolist())
    color = alt.Color(
        "Serie:N",
        title="Indicador",
        scale=alt.Scale(domain=SERIES_DOMAIN, range=SERIES_COLORS),
    )
    x = alt.X("Month:N", title="Mês", sort=months, axis=alt.Axis(labelAngle=-45))
    y = alt.Y(
        "Percentual:Q",
        title="Percentual",
        scale=alt.Scale(domain=[0, 100]),
        axis=alt.Axis(format=".0f"),
    )
    tooltip = [
        alt.Tooltip("Month:N", title="Mês"),
        alt.Tooltip("Serie:N", title="Indicador"),
        alt.Tooltip("Percentual:Q", title="Percentual", format=".1f"),
    ]

    monthly_bars = (
        alt.Chart(comparison)
        .transform_fold(MONTHLY_FIELDS, as_=["Serie", "Percentual"])
        .mark_bar(opacity=0.8)
        .encode(
            x=x,
            xOffset=alt.XOffset("Serie:N"),
            y=y,
            color=color,
            tooltip=tooltip,
        )
    )
    cumulative_lines = (
        alt.Chart(comparison)
        .transform_fold(CUMULATIVE_FIELDS, as_=["Serie", "Percentual"])
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=x,
            y=y,
            color=color,
            detail="Serie:N",
            tooltip=tooltip,
        )
    )
    return (monthly_bars + cumulative_lines).properties(
        height=400,
        title="Percentual mensal (colunas) e acumulado (linhas)",
    )

def _previsto_realizado() -> None:
    st.subheader("Previsto × realizado por projeto")
    st.caption(
        "Base do ICPP: colunas comparam o percentual mensal planejado e realizado; "
        "linhas mostram os percentuais acumulados."
    )

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
    project_options = ["Todos os projetos", *project_names]
    selected_project = st.selectbox(
        "Projeto",
        project_options,
        index=1 if project_names else 0,
    )

    if selected_project != "Todos os projetos":
        comparison = comparison.loc[comparison["Projeto"] == selected_project]
    if comparison.empty:
        st.info("Não há indicadores BSC para o filtro selecionado.")
        return

    projects_to_show = (
        project_names if selected_project == "Todos os projetos" else [selected_project]
    )
    for project_name in projects_to_show:
        project_comparison = comparison.loc[comparison["Projeto"] == project_name]
        if project_comparison.empty:
            continue
        st.subheader(project_name)
        st.altair_chart(
            _build_project_chart(project_comparison),
            width="stretch",
        )

def show() -> None:
    st.title("BSC: ICPP, IPP e IAP")
    try:
        icpp, ipp, iap = load_indicator_data()
    except (FileNotFoundError, ValueError) as error:
        st.error(
            f"Não foi possível carregar os indicadores: {error}. "
            "Execute `python src/main.py --completo` para gerá-los."
        )
        st.stop()

    tab_icpp, tab_ipp, tab_iap = st.tabs(["ICPP por projeto", "IPP do portfólio", "IAP por setor"])
    with tab_icpp:
        if icpp.empty:
            st.info("Sem dados de ICPP.")
        else:
            indicadores.icpp_tab(icpp)
        st.divider()
        _previsto_realizado()
    with tab_ipp:
        if ipp.empty:
            st.info("Sem dados de IPP.")
        else:
            indicadores.ipp_tab(ipp)
    with tab_iap:
        if iap.empty:
            st.info("Sem dados de IAP.")
        else:
            indicadores.iap_tab(iap)

if __name__ == "__main__":
    show()