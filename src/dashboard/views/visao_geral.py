import streamlit as st
import pandas as pd
from datetime import date
from src.dashboard.data import build_project_overview, load_dashboard_data
st.set_page_config(layout="wide")

def show() -> None:
    try:
        projects, _, _ = load_dashboard_data()
    except (FileNotFoundError, ValueError) as error:
        st.error(f"Não foi possível carregar os CSVs do dashboard: {error}")
        st.stop()

    overview = build_project_overview(projects)
    if overview.empty:
        st.info("Nenhum projeto foi encontrado em consolidado_projetos.csv.")
        return

    for col in ["Mercado", "Marca", "Categoria", "Ano", "Desvio"]:
        if col not in overview.columns:
            overview[col] = "N/D"
    if "Código" not in overview.columns:
        overview["Código"] = "-"
    if "Abertura Briefing" in overview.columns:
        overview["Abertura Briefing"] = (
            pd.to_datetime(overview["Abertura Briefing"], errors="coerce")
            .dt.strftime("%d/%m/%Y")
            .fillna("N/D")
        )

    f1, f2, f3, f4, f5, f6, f7 = st.columns(7)
    
    with f1:
        projetos_lista = ["Todos"] + sorted(overview["Projeto"].dropna().unique().tolist())
        sel_projeto = st.selectbox("Nome Projeto", projetos_lista)
    with f2:
        mercado_lista = ["Todos"] + sorted(overview["Mercado"].astype(str).dropna().unique().tolist())
        sel_mercado = st.selectbox("Mercado", mercado_lista)
    with f3:
        marca_lista = ["Todos"] + sorted(overview["Marca"].astype(str).dropna().unique().tolist())
        sel_marca = st.selectbox("Marca", marca_lista)
    with f4:
        # Se 'Responsável' não existir na overview, tenta usar o que tiver ou cria N/D
        if "Responsável" not in overview.columns:
            overview["Responsável"] = "N/D"
        resp_lista = ["Todos"] + sorted(overview["Responsável"].astype(str).dropna().unique().tolist())
        sel_resp = st.selectbox("Responsável", resp_lista)
    with f5:
        cat_lista = ["Todos"] + sorted(overview["Categoria"].astype(str).dropna().unique().tolist())
        sel_cat = st.selectbox("Categoria", cat_lista)
    with f6:
        status_lista = ["Todos"] + sorted(overview["Status"].astype(str).dropna().unique().tolist())
        sel_status = st.selectbox("Status", status_lista)
    with f7:
        ano_lista = ["Todos"] + sorted(overview["Ano"].astype(str).dropna().unique().tolist())
        sel_ano = st.selectbox("Ano", ano_lista)

    df_filtrado = overview.copy()
    if sel_projeto != "Todos": df_filtrado = df_filtrado[df_filtrado["Projeto"] == sel_projeto]
    if sel_mercado != "Todos": df_filtrado = df_filtrado[df_filtrado["Mercado"] == sel_mercado]
    if sel_marca != "Todos": df_filtrado = df_filtrado[df_filtrado["Marca"] == sel_marca]
    if sel_resp != "Todos": df_filtrado = df_filtrado[df_filtrado["Responsável"] == sel_resp]
    if sel_cat != "Todos": df_filtrado = df_filtrado[df_filtrado["Categoria"] == sel_cat]
    if sel_status != "Todos": df_filtrado = df_filtrado[df_filtrado["Status"] == sel_status]
    if sel_ano != "Todos": df_filtrado = df_filtrado[df_filtrado["Ano"] == sel_ano]

    qtd_em_estudo = len(df_filtrado[df_filtrado["Status"].str.contains("estudo", case=False, na=False)])
    qtd_em_execucao = len(df_filtrado[df_filtrado["Status"].str.contains("execução|andamento|atrasado", case=False, na=False)])
    qtd_atrasados = len(df_filtrado[df_filtrado["Status"].str.contains("atrasado", case=False, na=False)])
    qtd_no_prazo = qtd_em_execucao - qtd_atrasados
    
    desvios = pd.to_numeric(df_filtrado["Desvio"], errors='coerce').dropna()
    media_desvio = int(desvios.mean()) if not desvios.empty else 0
    
    ano_atual = str(date.today().year)
    qtd_lancados_ano = len(df_filtrado[(df_filtrado["Status"].str.contains("concluído|lançado", case=False, na=False)) & (df_filtrado["Ano"] == ano_atual)])

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Em Estudo", qtd_em_estudo)
    m2.metric("Em Execução", qtd_em_execucao)
    m3.metric("No Prazo", qtd_no_prazo)
    m4.metric("Atrasados", qtd_atrasados)
    m5.metric("Média Desvio (Dias)", media_desvio)
    m6.metric(f"Projetos Lançados em {ano_atual}", qtd_lancados_ano)

    st.divider()
    df_filtrado["Atraso_Icone"] = df_filtrado["Status"].apply(lambda x: "🔴" if "atrasado" in str(x).lower() else "🟢")
    
    if "Término" in df_filtrado.columns:
        df_filtrado["Término"] = df_filtrado["Término"].dt.strftime("%d/%m/%y")

    display_columns = {
        "Código": "Código",
        "Mercado": "Mercado",
        "Projeto": "Nome do Projeto",
        "Abertura Briefing": "Abertura Briefing",
        "Marca": "Marca",
        "Responsável": "Responsável",
        "Categoria": "Categoria",
        "Status": "Status",
        "Progresso (%)": "Progresso",
        "Atraso_Icone": "Atraso",
        "Término": "Conclusão",
        "Ano": "Ano"
    }

    cols_to_keep = [col for col in display_columns.keys() if col in df_filtrado.columns]
    display = df_filtrado[cols_to_keep].rename(columns=display_columns).copy()

    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        column_config={
            "Progresso": st.column_config.ProgressColumn(
                "Progresso", min_value=0, max_value=100, format="%.0f%%"
            ),
            "Atraso": st.column_config.TextColumn(
                "Atraso"
            )
        },
    )

if __name__ == "__main__":
    show()