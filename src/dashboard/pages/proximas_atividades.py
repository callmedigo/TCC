import streamlit as st
from src.dashboard.data import build_upcoming_activities, load_dashboard_data

def show() -> None:
    st.title("Próximas atividades")
    st.caption(
        "Atividades em aberto agrupadas pelo mês de início; atividades vencidas "
        "são identificadas como atrasadas."
    )

    try:
        projects, _, _ = load_dashboard_data()
    except (FileNotFoundError, ValueError) as error:
        st.error(f"Não foi possível carregar os CSVs do dashboard: {error}")
        st.stop()

    activities = build_upcoming_activities(projects)
    if activities.empty:
        st.info(
            "Não há atividades em aberto nos cronogramas carregados."
        )
        return

    months = sorted(activities["Inicio"].dt.strftime("%Y-%m").dropna().unique().tolist())
    selected_month = st.selectbox("Filtrar mês de início", ["Todos os meses", *months])
    if selected_month != "Todos os meses":
        activities = activities.loc[
            activities["Inicio"].dt.strftime("%Y-%m") == selected_month
        ]

    st.metric("Atividades em aberto", len(activities))
    display_columns = [
        "Projeto",
        "Atividade",
        "Recursos",
        "Inicio",
        "Termino",
        "Situação",
        "Progresso (%)",
    ]
    display = activities[display_columns].rename(
        columns={"Inicio": "Início", "Termino": "Término"}
    ).copy()
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

show()