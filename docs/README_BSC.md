# BSC: Cálculo Mensal a partir do Consolidado de Projetos

Este documento descreve o propósito, funcionamento e uso da ferramenta `BSC/bsc_previsto.py`.

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

Gerar resumo mensal previsto por projeto:

```powershell
python .\src\bsc\bsc_previsto.py calculate
```

Se quiser passar input e output explicitamente:

```powershell
python .\src\bsc\bsc_previsto.py calculate --input data\processed\consolidado_projetos.csv --output-csv data\processed\indicador_bsc_mensal.csv
```

Executar modo debug:

```powershell
python .\src\bsc\bsc_previsto.py debug --input data\processed\consolidado_projetos.csv
```

Calcular o realizado a partir dos percentuais dos cronogramas:

```powershell
python .\src\bsc\bsc_realizado.py calculate
```

Os caminhos padrão são absolutos e baseados na raiz do repositório, portanto os comandos também funcionam quando executados de outra pasta.

Observações
- O script usa o projeto como agrupador e gera percentuais mensais por projeto.
- O cálculo utiliza `Duracao (dias)` ou `Duracao Baseline (dias)` quando disponível.
- Atividades com duração zero e atividades macro (`Recursos` contendo `macro`) são descartadas.
- Os percentuais por mês são arredondados e ajustados para que cada projeto some 100%.
