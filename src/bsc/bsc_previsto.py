import argparse
import math
import re
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "data" / "processed" / "consolidado_projetos.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "indicador_bsc_mensal.csv"

def find_column(df, candidates, default_letter):
    def tokens(s):
        return re.findall(r"\w+", s.lower()) if isinstance(s, str) else []

    default_index = ord(default_letter.upper()) - ord("A")
    for col in df.columns:
        col_tokens = tokens(col)
        if not col_tokens:
            continue
        for candidate in candidates:
            cand_tokens = tokens(candidate)
            if not cand_tokens:
                continue
            for i in range(len(col_tokens) - len(cand_tokens) + 1):
                if col_tokens[i:i + len(cand_tokens)] == cand_tokens:
                    return col
    if 0 <= default_index < len(df.columns):
        return df.columns[default_index]
    raise ValueError(f"Coluna para {default_letter} não encontrada")

def find_optional_column(df, candidates, default_letter):
    try:
        return find_column(df, candidates, default_letter)
    except ValueError:
        return None

def load_and_clean(path):
    df = pd.read_csv(path, encoding="utf-8", dtype=str)
    df = df.dropna(how="all").reset_index(drop=True)
    return df

def normalize_numeric(series):
    series = series.astype(str).str.replace(r"[^0-9,\.\-]", "", regex=True)
    series = series.str.replace(",", ".", regex=False)
    return pd.to_numeric(series, errors="coerce")

def build_monthly_plan(df):
    project_col = find_column(df, ["projeto", "project", "project name", "nome do projeto"], "A")
    start_col = find_column(df, ["início", "inicio", "start", "data de inicio", "data inicio"], "E")
    end_col = find_column(df, ["término", "termino", "end", "data de fim", "data fim"], "F")
    baseline_col = find_optional_column(df, ["duração baseline", "duracao baseline", "baseline", "duracao baseline (dias)"], "H")
    duration_col = find_column(df, ["duração (dias)", "duracao (dias)", "duracao dias", "duracao", "duration", "dias"], "G")
    resource_col = find_optional_column(df, ["recursos", "resource", "recurso"], "C")

    df2 = df.copy()
    df2["Project"] = df2[project_col].astype(str).str.strip()
    df2["Start"] = pd.to_datetime(df2[start_col], errors="coerce", dayfirst=False)
    df2["End"] = pd.to_datetime(df2[end_col], errors="coerce", dayfirst=False)

    df2["BaselineDuration"] = normalize_numeric(df2[baseline_col]) if baseline_col is not None else pd.NA
    df2["Duration"] = normalize_numeric(df2[duration_col])
    df2["Duration"] = df2["Duration"].fillna(df2["BaselineDuration"])

    df2 = df2[df2["Duration"].notna()].copy()
    df2 = df2[df2["Duration"] != 0].copy()

    if resource_col is not None:
        resources = df2[resource_col].astype(str).str.lower().fillna("")
        df2 = df2[~resources.str.contains(r"macro", regex=True)].copy()

    df2 = df2[df2["Start"].notna() & df2["End"].notna()].copy()
    df2 = df2[df2["End"] >= df2["Start"]].copy()
    if df2.empty:
        raise ValueError("Nenhuma atividade válida encontrada após a limpeza.")

    df2["SpanDays"] = (df2["End"] - df2["Start"]).dt.days + 1
    df2["SpanDays"] = df2["SpanDays"].clip(lower=1)
    df2["Duration"] = df2["Duration"].clip(lower=1)

    records = []
    for project, group in df2.groupby("Project", sort=False):
        total_weight = group["Duration"].sum()
        if total_weight <= 0:
            continue

        start_month = group["Start"].min().replace(day=1)
        end_month = group["End"].max().replace(day=1)

        month_labels = []
        current_month = start_month
        while current_month <= end_month:
            month_labels.append(current_month.strftime("%Y-%m"))
            year = current_month.year + (current_month.month // 12)
            month = current_month.month % 12 + 1
            current_month = current_month.replace(year=year, month=month, day=1)

        month_weights = {label: 0.0 for label in month_labels}

        for _, row in group.iterrows():
            task_start = row["Start"]
            task_end = row["End"]
            task_duration = float(row["Duration"])
            task_span_days = float(row["SpanDays"])

            task_month = task_start.replace(day=1)
            while task_month <= task_end:
                next_month_year = task_month.year + (task_month.month // 12)
                next_month_month = task_month.month % 12 + 1
                next_month = task_month.replace(year=next_month_year, month=next_month_month, day=1)
                month_end_date = next_month - pd.Timedelta(days=1)

                overlap_start = max(task_start, task_month)
                overlap_end = min(task_end, month_end_date)
                overlap_days = max((overlap_end - overlap_start).days + 1, 0)
                if overlap_days > 0:
                    label = task_month.strftime("%Y-%m")
                    if label in month_weights:
                        month_weights[label] += task_duration * overlap_days / task_span_days

                task_month = next_month

        total_pct = 0
        for idx, label in enumerate(month_labels):
            month_value = month_weights[label]
            month_pct_raw = month_value / total_weight * 100
            month_pct = int(math.floor(month_pct_raw + 0.5))
            if idx == len(month_labels) - 1:
                month_pct = max(0, 100 - total_pct)
            total_pct += month_pct
            records.append(
                {
                    "Projeto": project,
                    "Month": label,
                    "MonthlyPercent": month_pct,
                    "CumulativePercent": total_pct,
                }
            )

    summary_df = pd.DataFrame(records)
    return summary_df, df2

def save_outputs(summary_df, output_csv):
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(output_path, index=False, encoding="utf-8")
    return output_path

def resolve_input_path(raw_input):
    input_path = Path(raw_input)
    if not input_path.is_absolute():
        input_path = REPO_ROOT / input_path
    if not input_path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")
    return input_path

def cmd_calculate(args):
    input_path = resolve_input_path(args.input)
    raw_df = load_and_clean(input_path)
    summary_df, cleaned_df = build_monthly_plan(raw_df)
    output_path = save_outputs(summary_df, args.output_csv)

    print(f"Resumo mensal previsto salvo em: {output_path}")
    print(f"Projetos processados: {cleaned_df['Project'].nunique()}")
    print(f"Atividades válidas: {len(cleaned_df)}")

def cmd_debug(args):
    input_path = resolve_input_path(args.input)
    df = load_and_clean(input_path)
    print(f"Arquivo carregado com {len(df)} linhas")
    print("Colunas do arquivo:")
    for i, c in enumerate(df.columns):
        print(f"  {i}: {repr(c)}")

    try:
        summary_df, cleaned_df = build_monthly_plan(df)
        print("\nResumo calculado (primeiras linhas):")
        print(summary_df.head(20).to_string(index=False))
    except Exception as e:
        print(f"Erro durante build_monthly_plan: {e}")

def main():
    parser = argparse.ArgumentParser(description="Ferramentas BSC: cálculo mensal previsto a partir de consolidado_projetos.csv.")
    sub = parser.add_subparsers(dest="cmd")

    p_calc = sub.add_parser("calculate", help="Gerar resumo mensal previsto por projeto")
    p_calc.add_argument("--input", default=str(DEFAULT_INPUT))
    p_calc.add_argument("--output-csv", default=str(DEFAULT_OUTPUT))
    p_calc.set_defaults(func=cmd_calculate)

    p_debug = sub.add_parser("debug", help="Executar impressões de debug e validações")
    p_debug.add_argument("--input", default=str(DEFAULT_INPUT))
    p_debug.set_defaults(func=cmd_debug)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)

if __name__ == "__main__":
    main()