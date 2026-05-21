# BSC: Cálculo Mensal Previsto a partir do Consolidado de Projetos

Este documento descreve o propósito, funcionamento e uso da ferramenta `BSC/bsc_previsto.py`.

Resumo
- Objetivo: calcular o percentual previsto por mês para cada projeto usando o arquivo consolidado de tarefas.
- Entrada esperada: `Outputs/consolidado_projetos.csv`, com colunas como `Projeto`, `Inicio`, `Termino`, `Duracao (dias)` e `Duracao Baseline (dias)`.
- Saída: `Outputs/indicador_bsc_mensal.csv`, com percentuais mensais por projeto.

Arquivos
- `BSC/bsc_previsto.py`: Script para calcular percentuais previstos por projeto a partir de `Outputs/consolidado_projetos.csv`.
- `BSC/bsc_realizado.py`: (planejado) script para extrair e calcular percentuais realizados a partir de dados reais.

Como funciona (visão rápida)
- `find_column`: identifica automaticamente colunas relevantes usando listas de candidatos em português e inglês.
- `load_and_clean`: lê o CSV de entrada e remove linhas vazias.
- `build_monthly_plan`: transforma datas, normaliza duração, remove atividades não relevantes e distribui a duração de cada tarefa entre os meses de execução.
- `save_outputs`: grava o CSV final em `Outputs/`.

Uso - exemplos

Gerar resumo mensal previsto por projeto:

```powershell
python .\BSC\bsc_previsto.py calculate
```

Se quiser passar input e output explicitamente:

```powershell
python .\BSC\bsc_previsto.py calculate --input Outputs\consolidado_projetos.csv --output-csv Outputs\indicador_bsc_mensal.csv
```

Executar modo debug:

```powershell
python .\BSC\bsc_previsto.py debug --input Outputs\consolidado_projetos.csv
```

Observações
- O script usa o projeto como agrupador e gera percentuais mensais por projeto.
- O cálculo utiliza `Duracao (dias)` ou `Duracao Baseline (dias)` quando disponível.
- Atividades com duração zero e atividades macro (`Recursos` contendo `macro`) são descartadas.
- Os percentuais por mês são arredondados e ajustados para que cada projeto some 100%.

