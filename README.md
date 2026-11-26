# TCC
Sistema de ETL para Gestão de Projetos com automação e integração entre diversas ferramentas (ProjectLibre, Streamlit, gerenciamento de pastas) 
### Definições

1. **Mapeamento dos dados atualmente**

**• Organização das pastas  
• Cronogramas .xml**  
• *Excel de controle do BSC de atividades do P&D (Futuro)*  
• *Excel de notas do BSC de Marketing (Futuro)*

2. **Definição dos Requisitos Funcionais**  
• Ser capaz de percorrer as diversas pastas que separam os projetos.  
• Identificar quais tiveram modificações desde a ultima vez que rodou. *(futuro)*  
• Identificar automaticamente status do projeto de acordo com qual pasta ele se encontra. *(futuro)*  
• Extrair o conteudo de dentro dos .xml's/.pod's.  
• Comparar com a ultima versão para analisar o que teve de alteração. *(futuro)*  
• Gerar um arquivo com essas alterações tratadas. (CSV)  
• Exibir as informações do Banco em um BI dinamico.

3. **Configuração do ambiente**  
• Python  
• Pandas  
• CSV
• os  
• xml.etree.ElementTree  

### Códigos e Documentação
1. **Script de Extração**  
• **[Código]** Desenvolver a função que monitora a pasta de arquivos de projeto. *(varredura recursiva implementada; monitoramento contínuo é futuro)*  
• **[Código]** Desenvolver geração de dados sinteticos para testes  
• **[Código]** Criar um módulo de validação (Script que verifica se algum dado de projeto ficou de fora da automação). *(futuro)*  
• **[Código]** Criar um módulo de excessões de erros. *(parcial: registro em log e tratamento por arquivo)*  
• **[Código]** Criar o Módulo de extração dos dados.  

2. **Script de Transformação**  
• **[Código]** Limpar dados e padronizar.  
• **[Código]** Criar o Módulo de compilação dos dados.  
• **[Documentação]** Escrita da Introdução e Justificativa (por que automatizar o PMO?).  
• **[Documentação]** Levantamento do Referencial Teórico (Agile, Governança de Dados, Python no BI).  
• **[Documentação]**  Descrição da Metodologia e arquitetura do sistema (Diagrama de Fluxo de Dados).  

### Desenvolvimento da ferramenta de Business Intelligence
1. **Mockup básico do Dashboard**  
• **[Código]** Pull de informações do Banco de dados.  
• **[Código]** Implementação dos filtros dinâmicos (por projeto, por status, por data).  
• **[Código]** Integração dos gráficos (Plotly ou Altair) com o motor Python.  
• **[Documentação]** Capturas de tela e descrição das funcionalidades da interface.  

### Testes e Validação de Resultados  
• **[Documentação]** Explicar como foi desenvolver os dados sinteticos e como eles se encaixam na realidade.  
• **[Documentação]** Testes de estresse (carregar +30 arquivos).  
• **[Documentação]** Comparativo de Tempo: quanto tempo levava o processo manual vs. o automatizado?  
• **[Documentação]** Elaboração de um quadro comparativo: "Esforço Humano Mensal (Manual) vs. Esforço de Manutenção (Automatizado)".  
• **[Análise]** Coleta de feedbacks (pode ser uma simulação de "validação com stakeholders").  
• **[Documentação]** Escrita do capítulo de "Resultados e Discussão".  

### Finalização e Revisão
• **[Documentação]** Escrita da Conclusão (limitações do projeto e melhorias futuras como por exemplo a escalabilidade e integração com ferramentas como  o TOTVS Fluig).  
• **[Documentação]** Formatação ABNT (referências, sumário, figuras).  
• **[Documentação]** Revisão ortográfica e lógica do texto.  
• **[Documentação]** Preparação dos slides para a banca.

## Como preparar e executar

Execute os comandos abaixo no PowerShell, a partir da raiz do repositório.

### Preparar o ambiente (uma vez)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se o PowerShell bloquear a ativação do ambiente, use diretamente `.\.venv\Scripts\python.exe` no lugar de `python` nos comandos a seguir.

### Gerar cronogramas sintéticos

```powershell
python .\src\generator\synthetic_generator.py
```

Por padrão, gera cinco XMLs usando `data/raw/Cronograma Completo XML.xml`, grava-os em `data/synthetic` e acrescenta código, nome e data de abertura a `data/processed/lista_mestre_projetos.csv`. Para definir a quantidade e obter resultados repetíveis:

```powershell
python .\src\generator\synthetic_generator.py --count 5 --seed 123
```

Para usar outro modelo, pasta de saída ou arquivo da lista mestre:

```powershell
python .\src\generator\synthetic_generator.py "data\raw\Cronograma Modelo XML.xml" --count 5 --output-dir "data\synthetic" --master-list "data\processed\lista_mestre_projetos.csv" --seed 123
```

Use `--no-noise` para gerar o progresso sem atrasos aleatórios. Consulte todas as opções com:

```powershell
python .\src\generator\synthetic_generator.py --help
```

Cada lote com pelo menos três cronogramas inclui projetos no início, no meio e no fim do progresso. O corte é escolhido dentro de faixas diferentes para cada estágio, sem reutilizar uma atividade de corte no mesmo lote: início (15–30% das tarefas), meio (40–65%) e fim (75–95%). As tarefas antes do corte ficam em 100%, uma tarefa fica parcialmente concluída e todas as tarefas depois ficam em 0%; assim, projetos no início não recebem progresso artificial nas atividades finais. As atividades-resumo refletem o progresso ponderado das tarefas descendentes.

Cada XML sintético recebe um nome de projeto único e uma data de abertura aleatória, preservada em `data/processed/lista_mestre_projetos.csv` junto ao código do arquivo. O `StartDate` do projeto e as datas do cronograma são deslocados pelo mesmo número de semanas, mantendo a duração e os dias da semana do modelo. O dashboard associa o código e a abertura ao projeto pelo nome.

Os XMLs gerados mantêm os metadados essenciais do projeto e os campos das tarefas usados pela extração e pelo ProjectLibre. A hierarquia, dependências, calendários, recursos, linhas de base e percentuais são preservados; as datas `Start`/`Finish` mantêm os intervalos do modelo, deslocados junto à nova data de abertura. Dados redundantes de distribuição temporal dos recursos são omitidos, mas as alocações, unidades, trabalho e datas dos recursos permanecem. Os códigos gerados começam com duas letras aleatórias (por exemplo, `AB-001-26`).

### Extração e BSC

Depois de gerar (ou atualizar) os cronogramas, extraia os XMLs de `data/raw` e `data/synthetic`:

```powershell
python .\src\main.py
```

O comando atualiza `data/processed/arquivos_xml.csv` e `data/processed/consolidado_projetos.csv`. A lista mestre gerada junto aos cronogramas é um arquivo separado e não é sobrescrita pela extração.

Calcule os indicadores BSC previsto e realizado e consolide ICPP, IPP e IAP:

```powershell
python .\src\bsc\bsc_previsto.py calculate
python .\src\bsc\bsc_realizado.py calculate
python .\src\bsc\bsc_cons.py calculate
```

Para executar extração e as três etapas BSC de uma só vez:

```powershell
python .\src\main.py --completo
```

Os comandos usam `data/processed/consolidado_projetos.csv` como entrada e gravam os resultados em `data/processed`. O BSC realizado usa os percentuais extraídos dos cronogramas. Se quiser fornecer uma planilha com percentuais realizados, instale também `openpyxl` (`python -m pip install openpyxl`) e informe-a com `--input-excel \"caminho\\para\\arquivo.xlsx\"` (a planilha afeta apenas o BSC realizado; ICPP, IPP e IAP usam os percentuais do cronograma).

Por exemplo:

```powershell
python .\src\bsc\bsc_realizado.py calculate --input-excel \"caminho\\para\\arquivo.xlsx\"
```

#### Indicadores ICPP, IPP e IAP (`bsc_cons.py`)

| Arquivo gerado | Conteúdo |
|---|---|
| `indicador_icpp.csv` | ICPP por projeto e mês (realizado acumulado / previsto acumulado) e ∆AV |
| `indicador_atividades_mensal.csv` | Atividades previstas x realizadas por projeto e mês |
| `indicador_ipp.csv` | IPP por mês: projetos conformes / projetos ativos x 100 |
| `indicador_iap.csv` | IAP por setor e mês: atividades concluídas / previstas x 100 |

Regras adotadas (constantes no topo de `bsc_cons.py`):

1. Atividade prevista no mês *m*: o **término** cai em *m* e já venceu em relação à data de referência do projeto.
2. Atividade realizada: atividade prevista com 100% de conclusão (o cronograma é uma fotografia; não há data real de conclusão).
3. Data de referência: `--data-referencia AAAA-MM-DD` (comum a todos) ou, se omitida, inferida por projeto (último término concluído ou último início em andamento). Meses posteriores não são avaliados. O mês da data de referência é marcado como parcial (`MesParcial`) no ICPP, e o dashboard usa o último mês completo como situação atual.
4. IAP considera setores internos; ficam de fora "Cliente", atividades sem recurso e a linha-resumo do projeto. Uma atividade com mais de um setor conta para cada um.

Para executar os testes das regras: `python -m unittest discover -s tests -v`.

### Dashboard Streamlit

Com os CSVs atualizados, inicie o dashboard a partir da raiz do repositório:

```powershell
python -m streamlit run .\src\dashboard\app.py
```

O menu lateral contém telas para a lista mestre/visão geral, gráficos, cronogramas, atividades mensais, comparação BSC e indicadores (ICPP, IPP e IAP). Para atualizar os dados exibidos após uma nova geração, execute `python .\src\main.py --completo` antes de reiniciar ou atualizar o dashboard.
