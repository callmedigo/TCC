# TCC
ETL para Gestão de Projetos com automação e integração entre diversas ferramentas (ProjectLibre, PowerBI, gerenciamento de pastas) 

# Cronograma e Mapeamento de atividades 

Previsão:
| Etapa   | Data  |
|---------|:-----:|
| Etapa 1 | 12/04 |
| Etapa 2 | 19/04 |
| Etapa 3 | 26/04 |
| Etapa 4 | 03/05 |
| Etapa 5 | 10/05 |

### Etapa 1 - Definições

1. **Mapeamento dos dados atualmente**

**Lista Mestre**
| Colunas         | Descrição                         |
|-----------------|:---------------------------------:|
| Mercado         | Nome extraido do titulo do arquivo|
| Código          | Nome da tarefa no cronograma      |
| Data Abertura   | Lista de setores atribuídos       |
| Data Conclusão  | Progresso atual da tarefa         |
| Projeto         | Data formatas                     |
| Marca           | Nome extraido do titulo do arquivo|
| Responsavel     | Nome da tarefa no cronograma      |
| Tipo do Projeto | Lista de setores atribuídos       |
| Cronograma      | Progresso atual da tarefa         |
| Status          | Data formatas                     |
| Prazo           | Data formatas                     |
| Atividades      | Nome extraido do titulo do arquivo|
| Anotações       | Nome da tarefa no cronograma      |
| Ano             | Lista de setores atribuídos       |
| Atrasado        | Progresso atual da tarefa         |
| Motivo Atraso   | Data formatas                     |
| Lançamento      | Nome da tarefa no cronograma      |
| Duração Prevista| Lista de setores atribuídos       |
| Cron. Conclusão | Progresso atual da tarefa         |
| Duração Real    | Data formatas                     |

**• Organização das pastas  
• Cronogramas .xml**  
• *Excel de controle do BSC de atividades do P&D (Futuro)*  
• *Excel de notas do BSC de Marketing (Futuro)*

2. **Definição dos Requisitos Funcionais**  
• Ser capaz de percorrer as diversas pastas que separam os projetos.  
• Identificar quais tiveram modificações desde a ultima vez que rodou.  
• Extrair o conteudo de dentro dos .xml's.  
• Comparar com a ultima versão para analisar o que teve de alteração.  
• Gerar um arquivo com essas alterações tratadas. (CSV/JSON)  
• Armazenar em um Banco de dados.  
• Exibir as informações do Banco em um PowerBI dinamico.

3. **Configuração do ambiente**  
• Python  
• Pandas  
• Json  
• Postgree  
• os  
• xml.etree.ElementTree  

### Etapa 2 - Códigos e Documentação
1. **Script de Extração**  
• **[Código]** Desenvolver a função que monitora a pasta de arquivos de projeto.  
• **[Código]** Desenvolver geração de dados sinteticos para testes  
• **[Código]** Criar um módulo de validação (Script que verifica se algum dado de projeto ficou de fora da automação).  
• **[Código]** Criar um módulo de excessões de erros.  
• **[Código]** Criar o Módulo de extração dos dados.  

2. **Script de Transformação**  
• **[Código]** Limpar dados e padronizar.  
• **[Código]** Criar o Módulo de compilação dos dados.  
• **[Documentação]** Escrita da Introdução e Justificativa (por que automatizar o PMO?).  
• **[Documentação]** Levantamento do Referencial Teórico (Agile, Governança de Dados, Python no BI).  
• **[Documentação]**  Descrição da Metodologia e arquitetura do sistema (Diagrama de Fluxo de Dados).  

### Etapa 3 - Desenvolvimento do Front-end
1. **Mockup básico do Dashboard**  
• **[Código]** Pull de informações do Banco de dados.  
• **[Código]** Implementação dos filtros dinâmicos (por projeto, por status, por data).  
• **[Código]** Integração dos gráficos (Plotly ou Altair) com o motor Python.  
• **[Documentação]** Capturas de tela e descrição das funcionalidades da interface.  

### Etapa 4 - Testes e Validação de Resultados  
• **[Documentação]** Explicar como foi desenvolver os dados sinteticos e como eles se encaixam na realidade.  
• **[Documentação]** Testes de estresse (carregar +30 arquivos).  
• **[Documentação]** Comparativo de Tempo: quanto tempo levava o processo manual vs. o automatizado?  
• **[Documentação]** Elaboração de um quadro comparativo: "Esforço Humano Mensal (Manual) vs. Esforço de Manutenção (Automatizado)".  
• **[Análise]** Coleta de feedbacks (pode ser uma simulação de "validação com stakeholders").  
• **[Documentação]** Escrita do capítulo de "Resultados e Discussão".  

### Etapa 5 - Finalização e Revisão
• **[Documentação]** Escrita da Conclusão (limitações do projeto e melhorias futuras como por exemplo a escalabilidade e integração com ferramentas como  o TOTVS Fluig).  
• **[Documentação]** Formatação ABNT (referências, sumário, figuras).  
• **[Documentação]** Revisão ortográfica e lógica do texto.  
• **[Documentação]** Preparação dos slides para a banca.  