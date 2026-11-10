# BSC: Cálculo Mensal a partir do Consolidado de Projetos

Este documento descreve o propósito, funcionamento e uso de `src/bsc/bsc_previsto.py` e `src/bsc/bsc_realizado.py`.

## Preparar e executar

Execute os comandos na raiz do repositório. Para preparar o ambiente uma vez:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Antes do cálculo, gere ou atualize o CSV consolidado executando:

```powershell
python .\src\main.py
```

Se também precisar criar cronogramas de teste, gere-os antes da extração:

```powershell
python .\src\generator\synthetic_generator.py --count 5 --seed 123
python .\src\main.py
```

O gerador mantém a lista mestre separada em `data/processed/lista_mestre_projetos.csv`; a extração não sobrescreve esse arquivo.

Resumo
- Objetivo: calcular o percentual previsto por mês para cada projeto usando o arquivo consolidado de tarefas.
- Entrada esperada: `data/processed/consolidado_projetos.csv`, gerado pela extração dos arquivos em `data/raw/` e `data/synthetic/`.
- Saídas: `data/processed/indicador_bsc_mensal.csv` e `data/processed/indicador_bsc_realizado.csv`.

Arquivos
- `src/bsc/bsc_previsto.py`: calcula percentuais previstos por projeto a partir do consolidado processado.
- `src/bsc/bsc_realizado.py`: calcula percentuais realizados usando os percentuais extraídos dos XMLs; pode receber uma planilha opcional para substituir esses percentuais.

Como funciona (visão rápida)
- `find_column`: identifica automaticamente colunas relevantes usando listas de candidatos em português e inglês.
- `load_and_clean`: lê o CSV de entrada e remove linhas vazias.
- `build_monthly_plan`: transforma datas, normaliza duração, remove atividades não relevantes e distribui a duração de cada tarefa entre os meses de execução.
- `save_outputs`: grava o CSV final em `data/processed/`.

Uso - exemplos

Gerar o resumo mensal previsto e, em seguida, o realizado:

```powershell
python .\src\bsc\bsc_previsto.py calculate
python .\src\bsc\bsc_realizado.py calculate
```

Se quiser passar input e output explicitamente:

```powershell
python .\src\bsc\bsc_previsto.py calculate --input data\processed\consolidado_projetos.csv --output-csv data\processed\indicador_bsc_mensal.csv
```

Executar modo debug:

```powershell
python .\src\bsc\bsc_previsto.py debug --input data\processed\consolidado_projetos.csv
```

Para usar uma planilha com percentuais realizados em vez dos percentuais extraídos dos XMLs, instale `openpyxl` e informe o arquivo:

```powershell
python -m pip install openpyxl
python .\src\bsc\bsc_realizado.py calculate --input-excel "caminho\para\arquivo.xlsx"
```

Após gerar os CSVs de extração e BSC, execute o dashboard:

```powershell
python -m streamlit run .\src\dashboard\app.py
```

Os caminhos padrão dos cálculos BSC são baseados na raiz do repositório. Para consultar as opções disponíveis:

```powershell
python .\src\bsc\bsc_previsto.py --help
python .\src\bsc\bsc_realizado.py --help
```

Observações
- O script usa o projeto como agrupador e gera percentuais mensais por projeto.
- O cálculo utiliza `Duracao (dias)` ou `Duracao Baseline (dias)` quando disponível.
- Atividades com duração zero e atividades macro (`Recursos` contendo `macro`) são descartadas.
- Os percentuais por mês são arredondados e ajustados para que cada projeto some 100%.
