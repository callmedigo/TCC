import altair as alt
import pandas as pd
import streamlit as st
from src.dashboard.data import load_indicator_data


def _situacao(valor) -> str:
    if pd.isna(valor):
        return "Sem dado"
    return "Em dia" if valor >= 1 else "Atrasado"


def _icpp_tab(icpp: pd.DataFrame) -> None:
    st.caption(
        "ICPP = realizado acumulado / previsto acumulado. Valores a partir de 1,0 indicam projeto em dia "
        "ou adiantado; abaixo de 1,0, atraso físico. O último mês de cada projeto é parcial quando a "
        "data de referência não é o fim do mês."
    )
    projects = sorted(icpp["Projeto"].dropna().unique().tolist())
    # Situação atual: último mês completo; só usa o mês parcial se o projeto ainda não tiver nenhum completo.
    ordered = icpp.sort_values(["Projeto", "Month"])
    complete = ordered.loc[~ordered["MesParcial"]].groupby("Projeto").tail(1)
    only_partial = ordered.loc[~ordered["Projeto"].isin(complete["Projeto"])].groupby("Projeto").tail(1)
    latest = pd.concat([complete, only_partial], ignore_index=True)
    latest = latest.assign(Situação=latest["ICPP"].map(_situacao))
    st.dataframe(
        latest[["Projeto", "Month", "DataReferencia", "PrevistoAcumulado", "RealizadoAcumulado", "ICPP", "Situação", "MesParcial"]]
        .rename(columns={"Month": "Mês", "DataReferencia": "Data de referência", "MesParcial": "Mês parcial"})
        .sort_values("ICPP"),
        hide_index=True,
        use_container_width=True,
    )

    selected = st.multiselect("Projetos no gráfico", projects, default=projects[:3])
    if not selected:
        st.info("Selecione ao menos um projeto para ver a evolução do ICPP.")
        return
    data = icpp.loc[icpp["Projeto"].isin(selected)]
    months = sorted(data["Month"].unique().tolist())
    line = (
        alt.Chart(data)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("Month:N", title="Mês", sort=months, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("ICPP:Q", title="ICPP", scale=alt.Scale(domain=[0, 1.2])),
            color=alt.Color("Projeto:N", title="Projeto"),
            tooltip=["Projeto", "Month", "PrevistoAcumulado", "RealizadoAcumulado", "ICPP"],
        )
    )
    target = alt.Chart(pd.DataFrame({"y": [1.0]})).mark_rule(strokeDash=[6, 4], color="#ef4444").encode(y="y:Q")
    st.altair_chart((line + target).properties(height=380), width="stretch")


def _ipp_tab(ipp: pd.DataFrame) -> None:
    st.caption(
        "IPP = projetos que concluíram todas as atividades previstas no mês / projetos ativos no mês x 100. "
        "Um projeto fica fora do grupo conforme se uma única atividade vencida estiver incompleta."
    )
    months = sorted(ipp["Month"].unique().tolist())
    chart = (
        alt.Chart(ipp)
        .mark_bar(color="#2563eb")
        .encode(
            x=alt.X("Month:N", title="Mês", sort=months, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("IPP:Q", title="IPP (%)", scale=alt.Scale(domain=[0, 100])),
            tooltip=["Month", "ProjetosAtivos", "ProjetosConformes", "IPP"],
        )
        .properties(height=360)
    )
    st.altair_chart(chart, width="stretch")
    st.dataframe(
        ipp.rename(columns={"Month": "Mês", "ProjetosAtivos": "Projetos ativos", "ProjetosConformes": "Projetos conformes"}),
        hide_index=True,
        use_container_width=True,
    )


def _iap_tab(iap: pd.DataFrame) -> None:
    st.caption(
        "IAP = atividades do setor concluídas no mês / atividades do setor previstas no mês x 100. "
        "Consideram-se apenas setores internos (sem Cliente e sem atividades sem recurso)."
    )
    months = sorted(iap["Month"].unique().tolist())
    sectors = sorted(iap["Setor"].unique().tolist())
    heat = (
        alt.Chart(iap)
        .mark_rect()
        .encode(
            x=alt.X("Month:N", title="Mês", sort=months, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("Setor:N", title="Setor", sort=sectors),
            color=alt.Color("IAP:Q", title="IAP (%)", scale=alt.Scale(domain=[0, 100], scheme="redyellowgreen")),
            tooltip=["Setor", "Month", "AtividadesPlanejadas", "AtividadesRealizadas", "IAP"],
        )
        .properties(height=max(120, 48 * len(sectors)))
    )
    st.altair_chart(heat, width="stretch")
    summary = (
        iap.groupby("Setor", as_index=False)[["AtividadesPlanejadas", "AtividadesRealizadas"]].sum()
        .assign(IAP=lambda d: (d["AtividadesRealizadas"] / d["AtividadesPlanejadas"] * 100).round(1))
        .sort_values("IAP")
    )
    st.dataframe(summary, hide_index=True, use_container_width=True)


def show() -> None:
    st.title("Indicadores: ICPP, IPP e IAP")
    try:
        icpp, ipp, iap = load_indicator_data()
    except (FileNotFoundError, ValueError) as error:
        st.error(
            f"Não foi possível carregar os indicadores: {error}. "
            "Execute `python src/main.py --completo` para gerá-los."
        )
        st.stop()

    tab_icpp, tab_ipp, tab_iap = st.tabs(["ICPP por projeto", "IPP do portfólio", "IAP por setor"])
    for tab, dados, desenhar, nome in (
        (tab_icpp, icpp, _icpp_tab, "ICPP"),
        (tab_ipp, ipp, _ipp_tab, "IPP"),
        (tab_iap, iap, _iap_tab, "IAP"),
    ):
        with tab:
            if dados.empty:
                st.info(f"Sem dados de {nome}.")
            else:
                desenhar(dados)


if __name__ == "__main__":
    show()
