# ETL .xml
## MSPDI Project Aggregator & Reporter
Este projeto automatiza a extração de dados de múltiplos cronogramas do Microsoft Project (formato .xml/MSPDI), consolidando-os em uma base de dados unificada e gerando relatórios semanais formatados em CSV.

### Princípio de Segurança: Least Privilege
Este projeto segue rigorosamente o princípio de **Least Privilege (Menor Privilégio)**:

- **Não modifica** arquivos XML originais (apenas leitura)
- **Não deleta** nenhum arquivo
- **Não requer** privilégios administrativos
- **Não acessa** dados do sistema operacional
- Cria apenas arquivos **em diretórios locais do projeto**
- **Sem dependências externas** - usa apenas bibliotecas padrão do Python

#### Permissões Necessárias
O projeto requer apenas:
- **Leitura**: Pasta `./teste/` com arquivos `.xml` (como no exemplo ou com o diretorio de onde fica os projetos)
- **Escrita**: Pasta `./relatorios/` para gerar CSVs e pasta `./logs/` para auditoria
- **Nenhum acesso a**: Sistema de arquivos global, registro do Windows, dados de usuário
### Data Sanitization (Limpeza de Dados)
Este projeto implementa validação e sanitização rigorosa de todos os dados de entrada:

#### Validações Implementadas
- **Sanitização de Texto**: Remove espaçamento excessivo, caracteres de controle e espaços inconsistentes
- **Validação de Datas**: Verifica se datas estão em formato válido (ano entre 1900-2100)
- **Validação de Caminho (Path Traversal)**: Bloqueia tentativas de acesso fora do diretório do projeto
- **Validação de Percentuais**: Verifica se são valores numéricos válidos
- **Validação de Recursos**: Substitui valores nulos por padrões seguros
- **Detecção de Erros**: Registra e ignora dados inválidos com logs detalhados

#### Exemplo de Sanitização
```
Entrada inválida: "   Tarefa com   espaços   múltiplos   "
Saída sanitizada:  "Tarefa com espaços múltiplos"

Entrada inválida: "2030-15-45" (data impossível)
Saída: Ignorada e registrada em log
```

Todos os dados inválidos são **registrados em `logs/`** sem interromper a execução.
### Funcionalidades
**Parsing de MSPDI**: Extração profunda de arquivos XML, incluindo mapeamento de Recursos e Atribuições (Assignments).  

**Consolidação Automática**: Une diversos arquivos de projeto em um único arquivo `consolidado_projetos.csv` na pasta `./relatorios/`.

**Relatório Semanal**: Filtra atividades que estão em execução ou iniciam nos próximos 7 dias, gerando `Relatorio_Semanal_Projetos.csv` na pasta `./relatorios/` (compatível com Excel).

**Logging Automático**: Registra todas as operações em `./logs/` para auditoria de TI sem interferir na execução.

### Estrutura de Arquivos
**extracao_pastas.py**: Responsável por ler a pasta `./teste`, processar os XMLs de forma recursiva e gerar na pasta `./relatorios/`:
- `consolidado_projetos.csv` - Base consolidada com todas as tarefas
- `arquivos_xml.csv` - Relatório de status de leitura de cada arquivo XML

**report_semanal.py**: Lê a base `consolidado_projetos.csv` da pasta `./relatorios/` e gera o relatório semanal `Relatorio_Semanal_Projetos.csv` na mesma pasta.

**relatorios/**: Diretório criado automaticamente para armazenar todos os arquivos CSV gerados.

**logs/**: Diretório criado automaticamente para armazenar histórico de execuções (auditoria para TI).

### Pré-requisitos
Este projeto **não requer instalação de dependências externas**. Utiliza apenas bibliotecas padrão do Python (versão 3.6+):
- `csv` - processamento de arquivos CSV
- `xml.etree.ElementTree` - parsing de XML
- `datetime` - manipulação de datas
- `logging` - registro de operações
- `os` - operações do sistema de arquivos

### Como Usar

1. **Preparação**
O script `extracao_pastas.py` permite alternar entre o processamento local (testes) e o processamento em rede (produção). No cabeçalho do arquivo, escolha a variável **CAMINHO_ENTRADA** adequada:

- Modo Local (Teste): Utilize o caminho apontando para a pasta \teste. Certifique-se de que os arquivos .xml exportados do MS Project estejam dentro desta pasta.

- Modo Rede (Produção): Utilize o caminho da unidade N:\ para ler diretamente o diretório oficial de projetos.

```
# Exemplo de alternância no código
7 #CAMINHO_ENTRADA = r"N:\...\Gestão de Projetos de Produto" # Produção
8 CAMINHO_ENTRADA = r"C:\...\ETLxml\teste" # Teste local
```
2. **Extração e Consolidação**
Execute o primeiro script individualmente para processar os arquivos:
```
python extracao_pastas.py
```
**Outputs gerados na pasta `./relatorios/`:**
- `consolidado_projetos.csv` - Base consolidada com todas as tarefas
- `arquivos_xml.csv` - Relatório de status de leitura de cada arquivo XML
- `logs/extracao_pastas.log` - Log detalhado da execução

3. **Geração do Relatório Executivo**
Execute o segundo script para gerar o relatório semanal:
```
python report_semanal.py
```
**Output gerado na pasta `./relatorios/`:**
- `Relatorio_Semanal_Projetos.csv` - Tarefas da semana em formato CSV (compatível com Excel - delimitado por `;` e encoding UTF-8 BOM)
- `logs/report_semanal.log` - Log detalhado da execução

4. **Extração simplificada**
Ao executar através do `main.py`, o sistema processa ambos os scripts de forma integrada e gera a totalidade dos relatórios.

```
=== INICIANDO FLUXO DE TRABALHO ===

---> Executando: extracao_pastas.py
Iniciando processamento recursivo de XML em: C:\...\ETLxml\teste

✓ CSV de detalhes gerado: C:\...\ETLxml\relatorios\arquivos_xml.csv (5 arquivos)
  Teste3.xml - Lido com sucesso
  Teste5.xml - Lido com sucesso
  Teste1.xml - Lido com sucesso
  Teste6.xml - Lido com sucesso
  Teste4.xml - Lido com sucesso

✓ CSV consolidado gerado: C:\...\ETLxml\relatorios\consolidado_projetos.csv (403 tarefas)
Colunas: ['Projeto', ..., 'Arquivo']
V Sucesso: extracao_pastas.py

---> Executando: report_semanal.py
✓ Relatório gerado: C:\...\ETLxml\relatorios\Relatorio_Semanal_Projetos.csv (17 tarefas)
V Sucesso: report_semanal.py

=== PROCESSAMENTO FINALIZADO ===
```

### Monitoramento e Auditoria
Todos os eventos são registrados automaticamente em arquivos de log (sem interferência visual):
```bash
# Consultar logs de extração
tail -f logs/extracao_pastas.log

# Consultar logs de relatório
tail -f logs/report_semanal.log

# Filtrar apenas erros
cat logs/extracao_pastas.log | grep ERROR

# Filtrar dados inválidos/ignorados
cat logs/extracao_pastas.log | grep WARNING
```

### Resumo de Segurança
Este projeto implementa as três práticas essenciais de segurança em processamento de dados:

| Aspecto | Implementação | Detalhes |
|---------|:------------:|----------|
| **Least Privilege** | Read-Only + Local Output | Sem privilégios de sistema, apenas dados locais nas pastas `./relatorios/` e `./logs/` |
| **Data Sanitization** | Validação Rigorosa | Remove caracteres inválidos, valida datas, bloqueia path traversal |
| **Auditing/Logging** | Silent Logging | Todos os eventos registrados em `logs/` para análise de TI |

### Detalhes Técnicos
**Lógica de Extração**: O extrator utiliza o namespace oficial do Microsoft Project (http://schemas.microsoft.com/project) para localizar:

* **Resources**: Mapeia os nomes de quem executa as tarefas.
* **Assignments**: Faz o "PROCV" interno no XML para ligar cada tarefa ao seu respectivo recurso.
* **Tasks**: Filtra apenas tarefas operacionais (Summary == 0), ignorando as linhas de resumo/fases para evitar duplicidade de prazos.

**Compatibilidade com Excel**: Os arquivos CSV são gerados com:
* **Encoding UTF-8 BOM** (`utf-8-sig`) - Reconhecido automaticamente pelo Excel
* **Delimitador ponto-e-vírgula** (`;`) - Padrão brasileiro/português no Excel
* **Formatação de datas** - DD/MM/YYYY para melhor visualização


### Colunas Geradas no Relatorio_Semanal_Projetos.csv
| Colunas   | Descrição                         |
|-----------|:---------------------------------:|
| Projeto   | Nome extraido do titulo do arquivo|
| Atividade | Nome da tarefa no cronograma      |
| Recursos  | Lista de setores atribuídos       |
| Percentual| Progresso atual da tarefa         |
| Inicio/Fim| Data formatas                     |
| Pasta     | Qual pasta o projeto faz parte    |
| Arquivo   | Nome do arquivo                   |