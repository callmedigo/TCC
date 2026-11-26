import argparse
import math
import re
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_CSV = REPO_ROOT / "data" / "processed" / "consolidado_projetos.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "indicador_bsc_realizado.csv"

def normalize_numeric(series):
    series = series.astype(str).str.replace(r"[^0-9,\.\-]", "", regex=True)
    series = series.str.replace(",", ".", regex=False)
    return pd.to_numeric(series, errors="coerce")

def load_excel_actual(excel_path, header_row=8):
    """
    Carrega o Excel com % realizado.
    Espera encontrar: Nome (col ~3), % concluída (col ~6)
    """
    df = pd.read_excel(excel_path, header=header_row, engine="openpyxl")
    df = df.dropna(how="all").reset_index(drop=True)
    return df

def find_column_flex(df, candidates):
    """Localiza coluna de forma flexível, retornando None se não encontrar."""
    
    def tokens(s):
        return re.findall(r"\w+", s.lower()) if isinstance(s, str) else []
    
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
    return None

def load_and_clean_csv(csv_path):
    """Carrega o consolidado_projetos.csv como base de duração e datas."""
    df = pd.read_csv(csv_path, encoding="utf-8", dtype=str)
    df = df.dropna(how="all").reset_index(drop=True)
    return df


def build_monthly_actual(excel_df=None, csv_df=None):
    """
    Calcula o percentual realizado por mês, usando:
    - CSV processado: duração, datas, projeto, atividade e percentual concluído;
    - Excel opcional: substitui percentuais quando é fornecido.
    """
    if csv_df is None:
        csv_df, excel_df = excel_df, None
    if csv_df is None:
        raise ValueError("O CSV consolidado processado é obrigatório.")

    name_lookup = {}
    wbs_lookup = {}
    if excel_df is not None:
        name_col_excel = find_column_flex(excel_df, ["nome", "name", "título", "titulo", "atividade", "task"])
        pct_col_excel = find_column_flex(excel_df, ["% concluída", "% completo", "percentual completo", "percent complete"])

        if name_col_excel is None or pct_col_excel is None:
            raise ValueError(
                f"Não encontrei colunas necessárias no Excel. "
                f"Nome: {name_col_excel}, %: {pct_col_excel}"
            )

        excel_df_clean = excel_df[[name_col_excel, pct_col_excel]].copy()
        excel_df_clean["Name"] = excel_df_clean[name_col_excel].astype(str).str.strip()
        excel_df_clean["PercentComplete"] = normalize_numeric(excel_df_clean[pct_col_excel])
        excel_df_clean = excel_df_clean[excel_df_clean["PercentComplete"].notna()].copy()
        excel_df_clean = excel_df_clean[excel_df_clean["PercentComplete"].between(0, 100)].copy()

        wbs_col_excel = find_column_flex(
            excel_df,
            ["número do nível hierárquico", "numero do nivel hierarquico", "outline", "wbs", "número de tarefa", "numero de tarefa"],
        )
        if wbs_col_excel is not None:
            excel_df_clean["WBS"] = excel_df[wbs_col_excel].astype(str).str.strip()

        name_lookup = dict(zip(excel_df_clean["Name"], excel_df_clean["PercentComplete"]))
        if "WBS" in excel_df_clean.columns:
            wbs_lookup = dict(zip(excel_df_clean["WBS"], excel_df_clean["PercentComplete"]))
    
    # Prepara CSV
    csv_df_clean = csv_df.copy()
    csv_df_clean["Project"] = csv_df_clean["Projeto"].astype(str).str.strip()
    csv_df_clean["Activity"] = csv_df_clean["Atividade"].astype(str).str.strip()
    csv_df_clean["Start"] = pd.to_datetime(csv_df_clean["Inicio"], errors="coerce", dayfirst=False)
    csv_df_clean["End"] = pd.to_datetime(csv_df_clean["Termino"], errors="coerce", dayfirst=False)
    if "Recursos" in csv_df_clean.columns:
        is_project_summary = csv_df_clean["Recursos"].astype(str).str.contains(
            "macro", case=False, na=False
        )
        csv_df_clean = csv_df_clean[~is_project_summary].copy()
    
    # Normaliza duração
    csv_df_clean["Duration"] = normalize_numeric(csv_df_clean["Duracao (dias)"])
    baseline_col = "Duracao Baseline (dias)" if "Duracao Baseline (dias)" in csv_df_clean.columns else None
    if baseline_col:
        csv_df_clean["BaselineDuration"] = normalize_numeric(csv_df_clean[baseline_col])
        csv_df_clean["Duration"] = csv_df_clean["Duration"].fillna(csv_df_clean["BaselineDuration"])
    
    csv_df_clean = csv_df_clean[csv_df_clean["Duration"].notna()].copy()
    csv_df_clean = csv_df_clean[csv_df_clean["Duration"] != 0].copy()
    csv_df_clean = csv_df_clean[csv_df_clean["Start"].notna() & csv_df_clean["End"].notna()].copy()
    csv_df_clean = csv_df_clean[csv_df_clean["End"] >= csv_df_clean["Start"]].copy()
    
    if csv_df_clean.empty:
        raise ValueError("Nenhuma atividade válida encontrada no CSV consolidado.")
    
    csv_df_clean["SpanDays"] = (csv_df_clean["End"] - csv_df_clean["Start"]).dt.days + 1
    csv_df_clean["SpanDays"] = csv_df_clean["SpanDays"].clip(lower=1)
    csv_df_clean["Duration"] = csv_df_clean["Duration"].clip(lower=1)
    
    # Normalize potential UID/OutlineNumber columns to strings for matching
    if "UID" in csv_df_clean.columns:
        csv_df_clean["UID"] = csv_df_clean["UID"].astype(str).str.strip()
    if "OutlineNumber" in csv_df_clean.columns:
        csv_df_clean["OutlineNumber"] = csv_df_clean["OutlineNumber"].astype(str).str.strip()

    csv_percent_col = "Percentual completo"
    if csv_percent_col in csv_df_clean.columns:
        csv_df_clean["PercentComplete"] = normalize_numeric(csv_df_clean[csv_percent_col])
        csv_df_clean["PercentComplete"] = csv_df_clean["PercentComplete"].clip(0, 100).fillna(0)
    else:
        csv_df_clean["PercentComplete"] = 0

    # Percentuais da planilha opcional têm precedência; sem correspondência usa o XML extraído.
    def lookup_pct(row):
        if "OutlineNumber" in row and pd.notna(row.get("OutlineNumber")):
            key = str(row.get("OutlineNumber")).strip()
            if key in wbs_lookup:
                return wbs_lookup[key]
        name_key = str(row.get("Activity", "")).strip()
        if name_key in name_lookup:
            return name_lookup[name_key]
        return row["PercentComplete"]

    if excel_df is not None:
        csv_df_clean["PercentComplete"] = csv_df_clean.apply(lookup_pct, axis=1)
    
    records = []
    
    for project, group in csv_df_clean.groupby("Project", sort=False):
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
            pct_complete = float(row["PercentComplete"]) / 100.0  # Converte para decimal
            
            # Distribui a duração ponderada pelo % realizado
            weighted_duration = task_duration * pct_complete
            
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
                        month_weights[label] += weighted_duration * overlap_days / task_span_days
                
                task_month = next_month
        
        total_pct = 0
        for label in month_labels:
            month_value = month_weights[label]
            month_pct_raw = month_value / total_weight * 100
            month_pct = int(math.floor(month_pct_raw + 0.5))
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
    return summary_df, csv_df_clean

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
    csv_path = resolve_input_path(args.input_csv)
    excel_df = (
        load_excel_actual(resolve_input_path(args.input_excel), header_row=8)
        if args.input_excel
        else None
    )
    csv_df = load_and_clean_csv(csv_path)
    summary_df, clean_data = build_monthly_actual(excel_df, csv_df)
    output_path = save_outputs(summary_df, args.output_csv)
    
    print(f"Resumo mensal realizado salvo em: {output_path}")
    print(f"Projetos processados: {clean_data['Project'].nunique()}")
    print(f"Atividades vinculadas: {len(clean_data)}")

def cmd_debug(args):
    csv_path = resolve_input_path(args.input_csv)
    excel_df = (
        load_excel_actual(resolve_input_path(args.input_excel), header_row=8)
        if args.input_excel
        else None
    )
    if excel_df is not None:
        print("=== EXCEL ===")
        print(f"Arquivo carregado com {len(excel_df)} linhas")
        print("Colunas:")
        for i, c in enumerate(excel_df.columns):
            print(f"  {i}: {repr(c)}")

    print("\n=== CSV PROCESSADO ===")
    csv_df = load_and_clean_csv(csv_path)
    print(f"Arquivo carregado com {len(csv_df)} linhas")
    print("Colunas:")
    for i, c in enumerate(csv_df.columns):
        print(f"  {i}: {repr(c)}")
    
    print("\n=== PROCESSAMENTO ===")
    try:
        summary_df, clean_data = build_monthly_actual(excel_df, csv_df)
        print("\nResumo calculado (primeiras linhas):")
        print(summary_df.head(20).to_string(index=False))
    except Exception as e:
        print(f"Erro: {e}")

def main():
    parser = argparse.ArgumentParser(description="Ferramentas BSC: cálculo mensal realizado a partir do CSV consolidado; Excel opcional.")
    sub = parser.add_subparsers(dest="cmd")
    
    p_calc = sub.add_parser("calculate", help="Gerar resumo mensal realizado por projeto")
    p_calc.add_argument("--input-excel", default=None, help="Planilha opcional para substituir os percentuais extraídos do XML.")
    p_calc.add_argument("--input-csv", default=str(DEFAULT_INPUT_CSV))
    p_calc.add_argument("--output-csv", default=str(DEFAULT_OUTPUT))
    p_calc.set_defaults(func=cmd_calculate)
    
    p_debug = sub.add_parser("debug", help="Executar impressões de debug e validações")
    p_debug.add_argument("--input-excel", default=None)
    p_debug.add_argument("--input-csv", default=str(DEFAULT_INPUT_CSV))
    p_debug.set_defaults(func=cmd_debug)
    
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)

if __name__ == "__main__":
    main()