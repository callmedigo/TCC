import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.dashboard.data import build_upcoming_activities, load_dashboard_data
st.set_page_config(layout="wide")

def colorir_datas(coluna):
    cores = []
    hoje = pd.to_datetime(datetime.today().date())
    
    for val in coluna:
        try:
            data_fim = pd.to_datetime(val, format="%d/%m/%Y")
            dias_diferenca = (data_fim - hoje).days
            
            if dias_diferenca < 0:
                cores.append('color: #ff4b4b')
            elif 0 <= dias_diferenca <= 7:
                cores.append('color: #faca2b')
            elif dias_diferenca > 30:
                cores.append('color: #808080')
            else:
                cores.append('')
        except:
            cores.append('') 
    return cores

def show() -> None:
    st.title("Atividades Mensais")

    try:
        projects, _, _ = load_dashboard_data()
    except (FileNotFoundError, ValueError) as error:
        st.error(f"Não foi possível carregar os CSVs do dashboard: {error}")
        st.stop()

    activities = build_upcoming_activities(projects)
    if activities.empty:
        st.info("Não há atividades em aberto nos cronogramas carregados.")
        return

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        projetos_lista = ["Todos"] + sorted(activities["Projeto"].dropna().unique().tolist())
        selected_projeto = st.selectbox("Nome Projeto", projetos_lista)
    with f_col2:
        recursos_lista = ["Todos"] + sorted(activities["Recursos"].dropna().unique().tolist())
        selected_recurso = st.selectbox("Setor Responsável", recursos_lista)
    with f_col3:
        months = sorted(activities["Inicio"].dt.strftime("%Y-%m").dropna().unique().tolist())
        selected_month = st.selectbox("Prazo (Mês de Início)", ["Todos", *months])
    with f_col4:
        selected_marca = st.selectbox("Marca", ["Todos"])

    df_filtrado = activities.copy()
    if selected_projeto != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Projeto"] == selected_projeto]
    if selected_recurso != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Recursos"] == selected_recurso]
    if selected_month != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Inicio"].dt.strftime("%Y-%m") == selected_month]

    hoje = pd.to_datetime(datetime.today())
    total_atividades = len(df_filtrado)
    atividades_atrasadas = len(df_filtrado[df_filtrado["Termino"] < hoje]) 
    atividades_urgentes = len(df_filtrado[(df_filtrado["Termino"] >= hoje) & (df_filtrado["Termino"] <= hoje + timedelta(days=7))])
    atividades_proximas = len(df_filtrado[(df_filtrado["Termino"] >= hoje) & (df_filtrado["Termino"] <= hoje + timedelta(days=30))])

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Total de Atividades", total_atividades)
    m_col2.metric("Atividades Atrasadas", atividades_atrasadas)
    m_col3.metric("Atividades Urgentes (7 Dias)", atividades_urgentes)
    m_col4.metric("Atividades Próximas (30 Dias)", atividades_proximas)

    st.divider()

    display_columns = [
        "Projeto",
        "Atividade",
        "Recursos",
        "Progresso (%)",
        "Termino",
        "Situação"
    ]
    
    display = df_filtrado[display_columns].rename(
        columns={
            "Projeto": "Nome do Projeto",
            "Recursos": "Responsável",
            "Progresso (%)": "% Completo",
            "Termino": "Fim previsto",
            "Situação": "Status Atividade"
        }
    ).copy()
    
    display["Fim previsto"] = display["Fim previsto"].dt.strftime("%d/%m/%Y")
    df_estilizado = display.style.apply(colorir_datas, subset=['Fim previsto'])
    
    st.dataframe(
        df_estilizado,
        hide_index=True,
        width="stretch",
        column_config={
            "% Completo": st.column_config.ProgressColumn(
                "% Completo", 
                min_value=0, 
                max_value=100, 
                format="%.0f%%"
            ),
            "Fim previsto": st.column_config.TextColumn("Fim previsto")
        },
    )

if __name__ == "__main__":
    show()