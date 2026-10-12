from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

PROJECT_COLUMNS = (
    "Projeto",
    "Atividade",
    "Recursos",
    "Percentual completo",
    "Inicio",
    "Termino",
    "Duracao (dias)",
)
BSC_COLUMNS = ("Projeto", "Month", "MonthlyPercent", "CumulativePercent")


def _read_csv(filename: str, required_columns: tuple[str, ...]) -> pd.DataFrame:
    path = PROCESSED_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"CSV não encontrado: {path}")

    dataframe = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    missing_columns = [column for column in required_columns if column not in dataframe.columns]
    if missing_columns:
        raise ValueError(
            f"O arquivo {path} não contém as colunas obrigatórias: "
            f"{', '.join(missing_columns)}."
        )
    return dataframe.dropna(how="all").reset_index(drop=True)


def _normalize_numeric(series: pd.Series) -> pd.Series:
    normalized = (
        series.astype("string")
        .str.replace(r"[^0-9,.\-]", "", regex=True)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(normalized, errors="coerce")


def _prepare_projects(projects: pd.DataFrame) -> pd.DataFrame:
    prepared = projects.copy()
    prepared["Projeto"] = prepared["Projeto"].astype("string").str.strip()
    prepared["Atividade"] = prepared["Atividade"].astype("string").str.strip()
    prepared["Recursos"] = prepared["Recursos"].astype("string").fillna("Sem recurso")
    prepared["Inicio"] = pd.to_datetime(prepared["Inicio"], errors="coerce")
    prepared["Termino"] = pd.to_datetime(prepared["Termino"], errors="coerce")
    prepared["_percentual"] = _normalize_numeric(prepared["Percentual completo"]).clip(0, 100).fillna(0)
    prepared["_duracao"] = _normalize_numeric(prepared["Duracao (dias)"])
    return prepared


def _prepare_bsc(dataframe: pd.DataFrame) -> pd.DataFrame:
    prepared = dataframe.copy()
    prepared["Projeto"] = prepared["Projeto"].astype("string").str.strip()
    prepared["Month"] = pd.to_datetime(prepared["Month"], errors="coerce").dt.strftime("%Y-%m")
    prepared["MonthlyPercent"] = _normalize_numeric(prepared["MonthlyPercent"])
    prepared["CumulativePercent"] = _normalize_numeric(prepared["CumulativePercent"])
    return prepared.dropna(subset=["Projeto", "Month"]).reset_index(drop=True)


def load_dashboard_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    projects = _prepare_projects(_read_csv("consolidado_projetos.csv", PROJECT_COLUMNS))
    planned = _prepare_bsc(_read_csv("indicador_bsc_mensal.csv", BSC_COLUMNS))
    actual = _prepare_bsc(_read_csv("indicador_bsc_realizado.csv", BSC_COLUMNS))
    return projects, planned, actual


def _is_project_summary(projects: pd.DataFrame) -> pd.Series:
    return projects["Recursos"].astype("string").str.contains("macro", case=False, na=False)


def build_project_overview(projects: pd.DataFrame, today: date | None = None) -> pd.DataFrame:
    reference_date = today or date.today()
    activities = projects.loc[~_is_project_summary(projects)].copy()
    if activities.empty:
        activities = projects.copy()

    records: list[dict[str, object]] = []
    for project_name, group in activities.groupby("Projeto", sort=True, dropna=True):
        durations = group["_duracao"].clip(lower=0)
        if durations.notna().any() and durations.fillna(0).sum() > 0:
            progress = float(
                (group["_percentual"].fillna(0) * durations.fillna(0)).sum()
                / durations.fillna(0).sum()
            )
        else:
            progress = float(group["_percentual"].mean())

        start = group["Inicio"].min()
        end = group["Termino"].max()
        if progress >= 100:
            status = "Concluído"
        elif pd.notna(end) and end.date() < reference_date:
            status = "Atrasado"
        elif pd.notna(start) and start.date() > reference_date:
            status = "Não iniciado"
        else:
            status = "Em andamento"

        records.append(
            {
                "Projeto": project_name,
                "Início": start,
                "Término": end,
                "Atividades": len(group),
                "Progresso (%)": round(progress, 1),
                "Status": status,
            }
        )

    return pd.DataFrame(
        records,
        columns=["Projeto", "Início", "Término", "Atividades", "Progresso (%)", "Status"],
    )


def build_timeline(projects: pd.DataFrame, project_name: str) -> pd.DataFrame:
    activities = projects.loc[
        (projects["Projeto"] == project_name)
        & ~_is_project_summary(projects)
        & projects["Inicio"].notna()
        & projects["Termino"].notna()
        & (projects["Termino"] >= projects["Inicio"])
    ].copy()
    activities["Progresso (%)"] = activities["_percentual"]
    activities["Termino visual"] = activities["Termino"] + pd.to_timedelta(
        activities["Termino"].eq(activities["Inicio"]).astype(int), unit="D"
    )
    activities["Atividade exibida"] = activities["Atividade"]
    if "OutlineNumber" in activities.columns:
        outline = activities["OutlineNumber"].astype("string").str.strip()
        has_outline = outline.notna() & outline.ne("")
        activities.loc[has_outline, "Atividade exibida"] = (
            outline[has_outline] + " · " + activities.loc[has_outline, "Atividade"]
        )
    return activities.sort_values(["Inicio", "Termino", "Atividade"], kind="stable")


def build_upcoming_activities(projects: pd.DataFrame, today: date | None = None) -> pd.DataFrame:
    reference_date = pd.Timestamp(today or date.today())
    activities = projects.loc[
        ~_is_project_summary(projects)
        & projects["Inicio"].notna()
        & projects["Termino"].notna()
        & (projects["Termino"] >= projects["Inicio"])
        & (projects["_percentual"] < 100)
    ].copy()
    activities["Situação"] = activities["Inicio"].apply(
        lambda start: "Em andamento" if start.date() <= reference_date.date() else "Próxima"
    )
    overdue = activities["Termino"].dt.date < reference_date.date()
    activities.loc[overdue, "Situação"] = "Atrasada"
    activities["Progresso (%)"] = activities["_percentual"]
    return activities.sort_values(["Inicio", "Projeto", "Atividade"], kind="stable")


def build_bsc_comparison(planned: pd.DataFrame, actual: pd.DataFrame) -> pd.DataFrame:
    planned_values = planned[
        ["Projeto", "Month", "MonthlyPercent", "CumulativePercent"]
    ].rename(
        columns={
            "MonthlyPercent": "Planejado mensal (%)",
            "CumulativePercent": "Planejado acumulado (%)",
        }
    )
    actual_values = actual[
        ["Projeto", "Month", "MonthlyPercent", "CumulativePercent"]
    ].rename(
        columns={
            "MonthlyPercent": "Realizado mensal (%)",
            "CumulativePercent": "Realizado acumulado (%)",
        }
    )
    comparison = planned_values.merge(
        actual_values,
        on=["Projeto", "Month"],
        how="outer",
        validate="one_to_one",
    )
    comparison["Desvio mensal (p.p.)"] = (
        comparison["Realizado mensal (%)"] - comparison["Planejado mensal (%)"]
    )
    comparison["Desvio acumulado (p.p.)"] = (
        comparison["Realizado acumulado (%)"] - comparison["Planejado acumulado (%)"]
    )
    return comparison.sort_values(["Projeto", "Month"], kind="stable").reset_index(drop=True)
