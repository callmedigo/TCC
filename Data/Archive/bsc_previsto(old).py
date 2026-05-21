import argparse
from datetime import datetime
import math
import re
from pathlib import Path
import pandas as pd


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
            # look for candidate token sequence inside column tokens
            for i in range(len(col_tokens) - len(cand_tokens) + 1):
                if col_tokens[i:i+len(cand_tokens)] == cand_tokens:
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
    df = pd.read_excel(path, header=8, engine="openpyxl")
    df = df.dropna(how="all").reset_index(drop=True)
    return df


def build_monthly_plan(df):
    start_col = find_column(df, ["início", "inicio", "start", "data de inicio", "data inicio"], "G")
    end_col = find_column(df, ["fim", "concluir", "data de fim", "data fim", "end"], "H")
    duration_col = find_column(df, ["duração", "duracao", "dias", "duration"], "I")
    hierarchy_col = find_optional_column(df, ["número do nível hierárquico", "numero do nivel hierarquico", "número da tarefa", "numero da tarefa", "outline", "hierarquia"], "B")

    df2 = df.copy()
    df2["Start"] = pd.to_datetime(df2[start_col], errors="coerce", dayfirst=True)
    df2["End"] = pd.to_datetime(df2[end_col], errors="coerce", dayfirst=True)

    # Converter duração: remover " dias" se existir, depois converter para número
    if df2[duration_col].dtype == 'object':
        df2["Duration"] = df2[duration_col].str.replace(r'\s*dias\s*', '', case=False, regex=True)
        df2["Duration"] = pd.to_numeric(df2["Duration"], errors="coerce")
    else:
        df2["Duration"] = pd.to_numeric(df2[duration_col], errors="coerce")

    # Excluir marcos (duração igual a zero)
    df2 = df2[df2["Duration"].fillna(-1) != 0].copy()

    # Excluir atividades macro que têm filhos na hierarquia
    if hierarchy_col is not None:
        hierarchy = df2[hierarchy_col].astype(str).str.strip()
        parent_keys = set()
        for value in hierarchy.dropna().unique():
            if '.' in value:
                parts = value.split('.')
                for i in range(1, len(parts)):
                    parent_keys.add('.'.join(parts[:i]))
        df2["IsMacro"] = hierarchy.isin(parent_keys)
        df2 = df2[~df2["IsMacro"]].copy()
        df2 = df2.drop(columns=["IsMacro"])

    df2 = df2[df2["Start"].notna() & df2["End"].notna()].copy()
    df2 = df2[df2["End"] >= df2["Start"]].copy()
    if df2.empty:
        raise ValueError("Nenhuma atividade válida encontrada após a limpeza.")

    df2["SpanDays"] = (df2["End"] - df2["Start"]).dt.days + 1
    df2["SpanDays"] = df2["SpanDays"].clip(lower=1)
    df2["Duration"] = df2["Duration"].fillna(df2["SpanDays"]).clip(lower=1)

    total_weight = df2["Duration"].sum()
    if total_weight <= 0:
        raise ValueError("A soma das durações é zero ou negativa.")

    start_month = df2["Start"].min().replace(day=1)
    end_date = df2["End"].max()
    end_month = end_date.replace(day=1)

    month_labels = []
    current_month = start_month
    while current_month <= end_month:
        month_labels.append(current_month.strftime("%Y-%m"))
        year = current_month.year + (current_month.month // 12)
        month = current_month.month % 12 + 1
        current_month = current_month.replace(year=year, month=month, day=1)

    month_weights = {label: 0.0 for label in month_labels}

    for _, row in df2.iterrows():
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

    records = []
    total = 0
    for idx, label in enumerate(month_labels):
        month_value = month_weights[label]
        month_pct_raw = month_value / total_weight * 100
        month_pct = int(math.floor(month_pct_raw + 0.5))
        if idx == len(month_labels) - 1:
            month_pct = max(0, 100 - total)
        total += month_pct
        records.append(
            {
                "Month": label,
                "MonthlyPercent": month_pct,
                "CumulativePercent": total,
            }
        )

    return pd.DataFrame(records), df2


def save_outputs(clean_df, summary_df, input_path, output_csv, output_excel=None):
    if output_excel is None:
        output_excel = Path(input_path).with_name(f"cleaned_{Path(input_path).stem}.xlsx")
    clean_df.to_excel(output_excel, index=False)
    summary_df.to_csv(output_csv, index=False)
    return output_excel


def cmd_calculate(args):
    input_path = Path(args.input)
    if not input_path.exists() and not input_path.is_absolute():
        candidate = Path(__file__).resolve().parent / args.input
        if candidate.exists():
            input_path = candidate
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    raw_df = load_and_clean(input_path)
    summary_df, cleaned_df = build_monthly_plan(raw_df)
    output_excel = save_outputs(cleaned_df, summary_df, input_path, args.output_csv, args.output_excel)

    print(f"Resumo mensal salvo em: {args.output_csv}")
    print(f"Planilha limpa salva em: {output_excel}")


def cmd_debug(args):
    input_path = Path(args.input)
    df = load_and_clean(input_path)
    print(f"Arquivo carregado com {len(df)} linhas")
    print("Colunas do arquivo:")
    for i, c in enumerate(df.columns):
        print(f"  {i}: {repr(c)}")

    try:
        summary_df, cleaned_df = build_monthly_plan(df)
        print("\nResumo calculado (primeiras linhas):")
        print(summary_df.head(10))
    except Exception as e:
        print(f"Erro durante build_monthly_plan: {e}")


def main():
    parser = argparse.ArgumentParser(description="Ferramentas BSC: cálculo mensal a partir de cronogramas do MS Project (exportados para Excel).")
    sub = parser.add_subparsers(dest="cmd")

    p_calc = sub.add_parser("calculate", help="Gerar resumo mensal e planilha limpa")
    p_calc.add_argument("--input", default="Template V2.xlsx")
    p_calc.add_argument("--output-csv", default="monthly_summary.csv")
    p_calc.add_argument("--output-excel", default=None)
    p_calc.set_defaults(func=cmd_calculate)

    p_debug = sub.add_parser("debug", help="Executar impressões de debug e validações")
    p_debug.add_argument("--input", default="Template.xlsx")
    p_debug.set_defaults(func=cmd_debug)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
