from datetime import date

import streamlit as st

from src.dashboard.data import build_project_overview, load_dashboard_data


def show() -> None:
    st.title("Visão geral dos projetos")
    st.caption("Resumo do portfólio calculado a partir das atividades consolidadas.")

    try:
        projects, _, _ = load_dashboard_data()
    except (FileNotFoundError, ValueError) as error:
        st.error(f"Não foi possível carregar os CSVs do dashboard: {error}")
        st.stop()

    overview = build_project_overview(projects)
    total_projects = len(overview)
    completed = int(overview["Status"].eq("Concluído").sum()) if total_projects else 0
    late = int(overview["Status"].eq("Atrasado").sum()) if total_projects else 0
    average_progress = overview["Progresso (%)"].mean() if total_projects else 0.0

    metric_columns = st.columns(4)
    metric_columns[0].metric("Projetos", total_projects)
    metric_columns[1].metric("Concluídos", completed)
    metric_columns[2].metric("Atrasados", late)
    metric_columns[3].metric("Progresso médio", f"{average_progress:.1f}%")

    if overview.empty:
        st.info("Nenhum projeto foi encontrado em consolidado_projetos.csv.")
        return

    today = date.today()
    display = overview.copy()
    display["Início"] = display["Início"].dt.strftime("%d/%m/%Y")
    display["Término"] = display["Término"].dt.strftime("%d/%m/%Y")
    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        column_config={
            "Progresso (%)": st.column_config.ProgressColumn(
                "Progresso (%)", min_value=0, max_value=100, format="%.1f%%"
            )
        },
    )
    st.caption(f"Situação calculada considerando a data de hoje: {today:%d/%m/%Y}.")


show()
