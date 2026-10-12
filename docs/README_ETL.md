# ETL de cronogramas MSPDI

O ETL lê cronogramas do ProjectLibre/Microsoft Project sem modificar os arquivos de entrada, consolida atividades em CSV e alimenta os cálculos BSC.

## Pastas

- `data/raw/`: cronogramas originais `.xml` e `.pod`.
- `data/synthetic/`: cronogramas sintéticos `.xml` (e `.pod`, se houver).
- `data/processed/`: relatórios da extração e resultados do BSC.
- `logs/`: log de execução da extração.

## Executar extração

Na raiz do repositório:

```powershell
python .\src\main.py
```

O processo percorre recursivamente `data/raw/` e `data/synthetic/` e gera:

- `data/processed/arquivos_xml.csv`: status de leitura de cada cronograma.
- `data/processed/consolidado_projetos.csv`: atividades, datas, duração, progresso e origem de cada arquivo.

O módulo também pode ser executado diretamente:

```powershell
python .\src\extraction\extracao.py
```

## Calcular indicadores BSC

Depois da extração, gere os indicadores usando o consolidado:

```powershell
python .\src\bsc\bsc_previsto.py calculate
python .\src\bsc\bsc_realizado.py calculate
```

Os resultados são gravados em `data/processed/indicador_bsc_mensal.csv` e `data/processed/indicador_bsc_realizado.csv`. O cálculo realizado usa os percentuais dos cronogramas extraídos; uma planilha opcional pode ser fornecida com `--input-excel`.

Os caminhos padrão são relativos à raiz do repositório, então os comandos funcionam mesmo quando executados de outra pasta. Todos os scripts aceitam caminhos alternativos nos argumentos de linha de comando.
