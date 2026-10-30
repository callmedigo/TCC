import streamlit as st
import pandas as pd
from src.dashboard.data import build_timeline, load_dashboard_data

st.set_page_config(layout="wide")

def show() -> None:
    try:
        projects, _, _ = load_dashboard_data()
    except (FileNotFoundError, ValueError) as error:
        st.error(f"Não foi possível carregar os CSVs do dashboard: {error}")
        st.stop()

    project_names = sorted(projects["Projeto"].dropna().unique().tolist())
    if not project_names:
        st.info("Nenhum projeto foi encontrado em consolidado_projetos.csv.")
        return

    col_filtro = st.columns([2, 1])
    with col_filtro:
        selected_project = st.selectbox("Nome do Projeto", project_names, label_visibility="visible")

    projeto_info = projects[projects["Projeto"] == selected_project].iloc[0] if not projects[projects["Projeto"] == selected_project].empty else None

    def get_info(coluna, df_row, default="N/D"):
        if df_row is None or coluna not in df_row or pd.isna(df_row[coluna]):
            return default
        value = df_row[coluna]
        if coluna == "Abertura Briefing":
            return pd.to_datetime(value).strftime("%d/%m/%Y")
        return str(value)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Código", get_info("Código", projeto_info))
    c2.metric("Mercado", get_info("Mercado", projeto_info))
    c3.metric("Marca", get_info("Marca", projeto_info))
    c4.metric("Responsável", get_info("Responsável", projeto_info))
    c5.metric("Status", get_info("Situação", projeto_info))
    c6.metric("Categoria de Projeto", get_info("Categoria", projeto_info))

    st.write("")
    c7, c8, c9, c10, c11, c12 = st.columns(6)
    c7.metric("Abertura Briefing", get_info("Abertura Briefing", projeto_info))
    c8.metric("Conclusão Briefing", get_info("Conclusão Briefing", projeto_info))
    c9.metric("Prazo Original", get_info("Prazo Original", projeto_info))
    c10.metric("Desvio em dias", get_info("Desvio", projeto_info, "0"))
    c11.metric("Conclusão Prevista", get_info("Termino", projeto_info))
    c12.metric("% Progresso", f"{get_info('Progresso (%)', projeto_info, '0')}%")

    st.divider()

    timeline = build_timeline(projects, selected_project)
    if timeline.empty:
        st.info("Não há atividades com datas válidas para este projeto.")
        return

    display_columns = [
        "Atividade",
        "Recursos",
        "Progresso (%)",
        "Duração",
        "Inicio",
        "Termino",
        "Situação"
    ]
    
    if "Duração" not in timeline.columns:
        timeline["Duração"] = (pd.to_datetime(timeline["Termino"]) - pd.to_datetime(timeline["Inicio"])).dt.days

    display = timeline[[col for col in display_columns if col in timeline.columns]].rename(
        columns={
            "Recursos": "Responsável",
            "Progresso (%)": "% Completo",
            "Inicio": "Inicio",
            "Termino": "Fim",
            "Situação": "Status Atividade"
        }
    ).copy()
    
    if "Inicio" in display.columns:
        display["Inicio"] = pd.to_datetime(display["Inicio"]).dt.strftime("%d/%m/%y")
    if "Fim" in display.columns:
        display["Fim"] = pd.to_datetime(display["Fim"]).dt.strftime("%d/%m/%y")
    
    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        column_config={
            "% Completo": st.column_config.ProgressColumn(
                "% Completo", 
                min_value=0, 
                max_value=100, 
                format="%.0f%%"
            )
        }
    )

if __name__ == "__main__":
    show()