import argparse
from pathlib import Path
import pandas as pd

"""Consolidação dos indicadores BSC: ICPP, IPP e IAP.

Entradas (geradas pelas etapas anteriores do pipeline):
  - data/processed/consolidado_projetos.csv     (extracao.py)
  - data/processed/indicador_bsc_mensal.csv     (bsc_previsto.py)
  - data/processed/indicador_bsc_realizado.csv  (bsc_realizado.py)

Saídas (data/processed):
  - indicador_icpp.csv               ICPP por projeto e mês
  - indicador_atividades_mensal.csv  atividades previstas x realizadas por projeto e mês
  - indicador_ipp.csv                IPP por mês (visão do portfólio)
  - indicador_iap.csv                IAP por setor e mês

Regras de negócio (ajustáveis nas constantes abaixo):
  1. Atividade prevista no mês m: atividade cujo TÉRMINO cai no mês m e já venceu
     em relação à data de referência do projeto.
  2. Atividade realizada: atividade prevista com percentual de conclusão = 100%.
  3. Data de referência: informada em --data-referencia ou, se omitida, inferida de cada
     projeto como a data mais avançada em que há evidência de execução (último término
     de atividade concluída ou último início de atividade em andamento).
     Meses posteriores à data de referência não são avaliados (ainda não venceram).
  4. IAP considera apenas setores internos: ficam de fora "Cliente", atividades sem
     recurso e a linha-resumo do projeto ("Projeto Macro").
"""

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

DEFAULT_INPUT_CSV = PROCESSED_DIR / "consolidado_projetos.csv"
DEFAULT_PREVISTO_CSV = PROCESSED_DIR / "indicador_bsc_mensal.csv"
DEFAULT_REALIZADO_CSV = PROCESSED_DIR / "indicador_bsc_realizado.csv"

RESUMO_PROJETO = "macro"
SETORES_EXCLUIDOS = ("cliente", "desconhecido", "sem recurso", RESUMO_PROJETO)
CONCLUIDA = 100.0

def normalize_numeric(series):
    series = series.astype(str).str.replace(r"[^0-9,\.\-]", "", regex=True)
    series = series.str.replace(",", ".", regex=False)
    return pd.to_numeric(series, errors="coerce")

def load_activities(csv_path):
    """Lê o consolidado e devolve as atividades dos projetos (sem a linha-resumo)."""
    df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype=str).dropna(how="all")
    df["Projeto"] = df["Projeto"].astype(str).str.strip()
    df["Recursos"] = df["Recursos"].fillna("Sem recurso").astype(str).str.strip()
    df["Inicio"] = pd.to_datetime(df["Inicio"], errors="coerce")
    df["Termino"] = pd.to_datetime(df["Termino"], errors="coerce")
    df["Percentual"] = normalize_numeric(df["Percentual completo"]).clip(0, 100).fillna(0)

    resumo = df["Recursos"].str.contains(RESUMO_PROJETO, case=False, na=False)
    df = df.loc[~resumo & df["Inicio"].notna() & df["Termino"].notna()].copy()
    df["Mes"] = df["Termino"].dt.strftime("%Y-%m")
    return df.reset_index(drop=True)

def infer_reference_dates(activities, fixed_date=None):
    """Data de referência de cada projeto (Series indexada pelo nome do projeto)."""
    if fixed_date is not None:
        return pd.Series(pd.Timestamp(fixed_date), index=activities["Projeto"].unique())

    references = {}
    for project, group in activities.groupby("Projeto", sort=False):
        concluded_finish = group.loc[group["Percentual"] >= CONCLUIDA, "Termino"].max()
        running_start = group.loc[
            (group["Percentual"] > 0) & (group["Percentual"] < CONCLUIDA), "Inicio"
        ].max()
        candidates = [d for d in (concluded_finish, running_start) if pd.notna(d)]
        # Projeto sem nenhuma execução: nada venceu ainda.
        references[project] = max(candidates) if candidates else group["Inicio"].min() - pd.Timedelta(days=1)
    return pd.Series(references)

def due_activities(activities, references):
    """Atividades previstas até a data de referência do respectivo projeto."""
    activities = activities.copy()
    activities["DataReferencia"] = activities["Projeto"].map(references)
    due = activities.loc[activities["Termino"] <= activities["DataReferencia"]].copy()
    due["Realizada"] = due["Percentual"] >= CONCLUIDA
    return due

def build_monthly_activities(due):
    """Atividades previstas x realizadas por projeto e mês (base do IPP)."""
    columns = ["Projeto", "Month", "DataReferencia", "AtividadesPlanejadas", "AtividadesRealizadas", "Conforme"]
    if due.empty:
        return pd.DataFrame(columns=columns)
    grouped = (
        due.groupby(["Projeto", "Mes"], sort=True)
        .agg(
            DataReferencia=("DataReferencia", "first"),
            AtividadesPlanejadas=("Realizada", "size"),
            AtividadesRealizadas=("Realizada", "sum"),
        )
        .reset_index()
        .rename(columns={"Mes": "Month"})
    )
    grouped["AtividadesRealizadas"] = grouped["AtividadesRealizadas"].astype(int)
    grouped["Conforme"] = grouped["AtividadesPlanejadas"] == grouped["AtividadesRealizadas"]
    grouped["DataReferencia"] = grouped["DataReferencia"].dt.strftime("%Y-%m-%d")
    return grouped[columns]

def build_ipp(monthly_activities):
    """IPP(m) = projetos que concluíram tudo o que era previsto no mês / projetos ativos no mês x 100."""
    columns = ["Month", "ProjetosAtivos", "ProjetosConformes", "IPP"]
    if monthly_activities.empty:
        return pd.DataFrame(columns=columns)
    ipp = (
        monthly_activities.groupby("Month", sort=True)
        .agg(ProjetosAtivos=("Projeto", "nunique"), ProjetosConformes=("Conforme", "sum"))
        .reset_index()
    )
    ipp["ProjetosConformes"] = ipp["ProjetosConformes"].astype(int)
    ipp["IPP"] = (ipp["ProjetosConformes"] / ipp["ProjetosAtivos"] * 100).round(1)
    return ipp[columns]

def split_sectors(resources):
    sectors = []
    for name in str(resources).split(","):
        name = name.strip()
        if not name or any(token in name.lower() for token in SETORES_EXCLUIDOS):
            continue
        if name not in sectors:
            sectors.append(name)
    return sectors

def build_iap(due):
    """IAP(S, m) = atividades do setor S concluídas no mês / atividades do setor previstas no mês x 100."""
    columns = ["Setor", "Month", "AtividadesPlanejadas", "AtividadesRealizadas", "IAP"]
    if due.empty:
        return pd.DataFrame(columns=columns)
    exploded = due.assign(Setor=due["Recursos"].map(split_sectors)).explode("Setor")
    exploded = exploded.loc[exploded["Setor"].notna()]
    if exploded.empty:
        return pd.DataFrame(columns=columns)
    iap = (
        exploded.groupby(["Setor", "Mes"], sort=True)
        .agg(AtividadesPlanejadas=("Realizada", "size"), AtividadesRealizadas=("Realizada", "sum"))
        .reset_index()
        .rename(columns={"Mes": "Month"})
    )
    iap["AtividadesRealizadas"] = iap["AtividadesRealizadas"].astype(int)
    iap["IAP"] = (iap["AtividadesRealizadas"] / iap["AtividadesPlanejadas"] * 100).round(1)
    return iap[columns]

def build_icpp(previsto, realizado, references):
    """ICPP(m) = Preal(m) / Pprev(m), avaliado apenas até o mês da data de referência."""
    columns = ["Projeto", "Month", "DataReferencia", "PrevistoAcumulado", "RealizadoAcumulado", "DeltaAV", "ICPP", "MesParcial"]
    previsto = previsto[["Projeto", "Month", "CumulativePercent"]].rename(
        columns={"CumulativePercent": "PrevistoAcumulado"}
    )
    realizado = realizado[["Projeto", "Month", "CumulativePercent"]].rename(
        columns={"CumulativePercent": "RealizadoAcumulado"}
    )
    merged = previsto.merge(realizado, on=["Projeto", "Month"], how="inner")
    merged["DataReferencia"] = merged["Projeto"].map(references)
    merged = merged.loc[merged["DataReferencia"].notna()].copy()
    merged = merged.loc[merged["Month"] <= merged["DataReferencia"].dt.strftime("%Y-%m")].copy()
    if merged.empty:
        return pd.DataFrame(columns=columns)

    merged["DeltaAV"] = merged["RealizadoAcumulado"] - merged["PrevistoAcumulado"]
    previsto_valido = merged["PrevistoAcumulado"].where(merged["PrevistoAcumulado"] > 0)
    merged["ICPP"] = (merged["RealizadoAcumulado"] / previsto_valido).round(3)
    # O mês da data de referência é parcial quando a data não é o último dia do mês.
    reference_month = merged["DataReferencia"].dt.strftime("%Y-%m")
    month_end = merged["DataReferencia"] + pd.offsets.MonthEnd(0)
    merged["MesParcial"] = (merged["Month"] == reference_month) & (merged["DataReferencia"] < month_end)
    merged["DataReferencia"] = merged["DataReferencia"].dt.strftime("%Y-%m-%d")
    return merged.sort_values(["Projeto", "Month"])[columns].reset_index(drop=True)

def save(dataframe, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False, encoding="utf-8")
    return path

def resolve_path(raw_path):
    path = Path(raw_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    return path

def consolidate(activities, previsto, realizado, fixed_date=None):
    references = infer_reference_dates(activities, fixed_date)
    due = due_activities(activities, references)
    monthly = build_monthly_activities(due)
    return {
        "icpp": build_icpp(previsto, realizado, references),
        "atividades": monthly,
        "ipp": build_ipp(monthly),
        "iap": build_iap(due),
    }

def cmd_calculate(args):
    activities = load_activities(resolve_path(args.input_csv))
    previsto = pd.read_csv(resolve_path(args.previsto_csv), encoding="utf-8-sig")
    realizado = pd.read_csv(resolve_path(args.realizado_csv), encoding="utf-8-sig")
    fixed_date = pd.Timestamp(args.data_referencia) if args.data_referencia else None

    results = consolidate(activities, previsto, realizado, fixed_date)
    output_dir = Path(args.output_dir)
    names = {
        "icpp": "indicador_icpp.csv",
        "atividades": "indicador_atividades_mensal.csv",
        "ipp": "indicador_ipp.csv",
        "iap": "indicador_iap.csv",
    }
    for key, filename in names.items():
        path = save(results[key], output_dir / filename)
        print(f"{filename}: {len(results[key])} linhas -> {path}")
    print(f"Projetos avaliados: {activities['Projeto'].nunique()}")

def main():
    parser = argparse.ArgumentParser(description="Consolida os indicadores BSC (ICPP, IPP e IAP).")
    sub = parser.add_subparsers(dest="cmd")
    calc = sub.add_parser("calculate", help="Gerar indicadores ICPP, IPP e IAP")
    calc.add_argument("--input-csv", default=str(DEFAULT_INPUT_CSV))
    calc.add_argument("--previsto-csv", default=str(DEFAULT_PREVISTO_CSV))
    calc.add_argument("--realizado-csv", default=str(DEFAULT_REALIZADO_CSV))
    calc.add_argument("--output-dir", default=str(PROCESSED_DIR))
    calc.add_argument(
        "--data-referencia",
        default=None,
        help="Data de corte (AAAA-MM-DD) comum a todos os projetos. Se omitida, é inferida de cada projeto.",
    )
    calc.set_defaults(func=cmd_calculate)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)

if __name__ == "__main__":
    main()