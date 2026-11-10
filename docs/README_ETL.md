# ETL de cronogramas MSPDI

O ETL lê cronogramas do ProjectLibre/Microsoft Project sem modificar os arquivos de entrada, consolida atividades em CSV e alimenta os cálculos BSC.

## Preparar o ambiente

Execute na raiz do repositório, em um terminal PowerShell. A configuração do ambiente virtual é necessária apenas uma vez:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se a ativação do ambiente for bloqueada, substitua `python` por `.\.venv\Scripts\python.exe` nos exemplos.

## Pastas

- `data/raw/`: cronogramas originais `.xml` e `.pod`.
- `data/synthetic/`: cronogramas sintéticos `.xml` (e `.pod`, se houver).
- `data/processed/`: relatórios da extração e resultados do BSC.
- `logs/`: log de execução da extração.

## Gerar cronogramas sintéticos

Na raiz do repositório:

```powershell
python .\src\generator\synthetic_generator.py
```

Por padrão, o gerador cria cinco cronogramas com base em `data/raw/Cronograma Completo XML.xml`, grava os XMLs em `data/synthetic` e acrescenta o código, o nome e a data de abertura de cada projeto a `data/processed/lista_mestre_projetos.csv`.

Para configurar a geração:

```powershell
python .\src\generator\synthetic_generator.py --count 5 --seed 123
python .\src\generator\synthetic_generator.py --help
```

O argumento `--seed` torna os resultados repetíveis. Também é possível informar um modelo XML, uma pasta de saída e outro caminho para a lista mestre com `source_xml`, `--output-dir` e `--master-list`. Use `--no-noise` para desativar os atrasos aleatórios.

## Executar extração

Na raiz do repositório:

```powershell
python .\src\main.py
```

O processo percorre recursivamente `data/raw/` e `data/synthetic/` e gera:

- `data/processed/arquivos_xml.csv`: status de leitura de cada cronograma.
- `data/processed/consolidado_projetos.csv`: atividades, datas, duração, progresso e origem de cada arquivo.

O arquivo `data/processed/lista_mestre_projetos.csv` é mantido pelo gerador e não é sobrescrito pela extração.

O módulo também pode ser executado diretamente:

```powershell
python .\src\extraction\extracao.py
```

## Executar o fluxo completo

Gere cronogramas sintéticos (opcional), atualize a extração e recalcule os dois indicadores, nesta ordem:

```powershell
python .\src\generator\synthetic_generator.py --count 5 --seed 123
python .\src\main.py
python .\src\bsc\bsc_previsto.py calculate
python .\src\bsc\bsc_realizado.py calculate
```

Os resultados são gravados em `data/processed/indicador_bsc_mensal.csv` e `data/processed/indicador_bsc_realizado.csv`. O cálculo realizado usa os percentuais dos cronogramas extraídos; uma planilha opcional pode ser fornecida com `--input-excel`.

Para abrir o dashboard depois de atualizar os CSVs:

```powershell
python -m streamlit run .\src\dashboard\app.py
```

Consulte [README_BSC.md](./README_BSC.md) para os comandos individuais e opções dos cálculos BSC.

Os caminhos padrão dos scripts Python são resolvidos a partir da raiz do repositório. Execute os exemplos a partir dessa raiz; o dashboard também deve ser iniciado nela. Os scripts de geração, BSC e extração aceitam caminhos alternativos nos argumentos de linha de comando.
