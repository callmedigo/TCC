import streamlit as st
import altair as alt
from src.dashboard.data import build_project_overview, load_dashboard_data

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

    for col in ["Mercado", "Marca", "Categoria", "Ano", "Status"]:
        if col not in overview.columns:
            overview[col] = "N/D"

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

    df_filtrado["Condição_Prazo"] = df_filtrado["Status"].apply(
        lambda x: "Atrasado" if "atrasado" in str(x).lower() else "No Prazo"
    )

    total_projetos = len(df_filtrado)
    
    condicao_ativos = df_filtrado["Status"].str.contains("estudo|execução|andamento", case=False, na=False)
    projetos_ativos = len(df_filtrado[condicao_ativos])
    
    atrasados = len(df_filtrado[(condicao_ativos) & (df_filtrado["Condição_Prazo"] == "Atrasado")])
    no_prazo = projetos_ativos - atrasados
    
    stand_by_susp = len(df_filtrado[df_filtrado["Status"].str.contains("stand|susp", case=False, na=False)])
    
    perc_em_dia = int((no_prazo / projetos_ativos) * 100) if projetos_ativos > 0 else 0

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total de Projetos", total_projetos)
    m2.metric("Projetos Ativos", projetos_ativos)
    m3.metric("No Prazo", no_prazo)
    m4.metric("Atrasados", atrasados)
    m5.metric("Stand-by / Suspensos", stand_by_susp)
    m6.metric("Percentual Projetos em Dia", f"{perc_em_dia}%")

    st.write("")

    st.subheader("Status dos Projetos")
    df_status = df_filtrado["Status"].value_counts().reset_index()
    df_status.columns = ["Status", "Quantidade"]
    
    chart_status = alt.Chart(df_status).mark_bar().encode(
        x=alt.X("Status:N", title="", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Quantidade:Q", title=""),
        color=alt.Color("Status:N", legend=None), # Cores automáticas variadas
        tooltip=["Status", "Quantidade"]
    ).properties(height=250)
    
    text_status = chart_status.mark_text(align='center', baseline='bottom', dy=-5, size=16).encode(text='Quantidade:Q')
    st.altair_chart(chart_status + text_status, use_container_width=True)

    col_esq, col_dir = st.columns([1, 2])

    with col_esq:
        st.subheader("Projetos no Prazo / Atrasado")
        df_ativos = df_filtrado[condicao_ativos].copy()
        
        if not df_ativos.empty:
            df_prazo = df_ativos.groupby(["Status", "Condição_Prazo"]).size().reset_index(name="Quantidade")
            
            domain = ["No Prazo", "Atrasado"]
            range_ = ["#27ae60", "#e74c3c"]
            
            chart_prazo = alt.Chart(df_prazo).mark_bar().encode(
                x=alt.X("Status:N", title="", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Quantidade:Q", title=""),
                color=alt.Color("Condição_Prazo:N", scale=alt.Scale(domain=domain, range=range_), legend=None),
                tooltip=["Status", "Condição_Prazo", "Quantidade"]
            ).properties(height=300)
            
            text_prazo = alt.Chart(df_prazo).mark_text(dx=0, dy=10, color='white', size=14).encode(
                x=alt.X('Status:N'),
                y=alt.Y('Quantidade:Q', stack='zero'),
                text=alt.Text('Quantidade:Q')
            )
            
            st.altair_chart(chart_prazo + text_prazo, use_container_width=True)
        else:
            st.info("Não há projetos ativos para exibir neste gráfico.")

    with col_dir:
        st.subheader("Categoria dos Projetos")
        df_cat = df_filtrado["Categoria"].value_counts().reset_index()
        df_cat.columns = ["Categoria", "Quantidade"]
        
        chart_cat = alt.Chart(df_cat).mark_bar().encode(
            x=alt.X("Categoria:N", title="", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Quantidade:Q", title=""),
            color=alt.Color("Categoria:N", legend=None),
            tooltip=["Categoria", "Quantidade"]
        ).properties(height=300)
        
        text_cat = chart_cat.mark_text(align='center', baseline='bottom', dy=-5, size=16).encode(text='Quantidade:Q')
        st.altair_chart(chart_cat + text_cat, use_container_width=True)

if __name__ == "__main__":
    show()