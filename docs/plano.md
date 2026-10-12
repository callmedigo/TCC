# PLANO DE AÇÃO - BSC (Indicador de Avanço)

## Objetivo Geral
Comparar o desempenho esperado (previsto) com o desempenho realizado de atividades de projetos usando BSC (Balanced Scorecard), ponderando pelo peso (duração) das tarefas.

---

## FASE 1: DADOS PREVISTOS ✅ (CONCLUÍDO)

### 1.1 - Entrada: Cronograma em Excel (MS Planner/Project)
- **Status**: ✅ Implementado em `BSC/bsc_previsto.py`
- **Arquivo de entrada**: `Outputs/consolidado_projetos.csv`
- **Formato esperado**:
  - Colunas: `Projeto`, `Inicio`, `Termino`, `Duracao (dias)`, `Duracao Baseline (dias)`
  - Gera percentuais por mês para cada projeto

### 1.2 - Processamento: Calcular % Previsto por Mês
- **Status**: ✅ Implementado em `BSC/bsc_previsto.py` → `build_monthly_plan()`
- **Lógica**:
  1. Carrega o Excel com header=8
  2. Converte datas para datetime
  3. Remove marcos (duração = 0) e atividades macro com filhos
  4. Valida: Start ≤ End, ambas não-nulas
  5. Calcula SpanDays = (End - Start) + 1
  6. **Distribui a duração entre meses**: Para cada tarefa que cruza múltiplos meses, pondera a duração pela sobreposição de dias
  7. Calcula percentual: (peso_mês / peso_total) × 100

### 1.3 - Saída: CSV com % Previsto
- **Status**: ✅ Implementado
- **Arquivo gerado**: `Outputs/indicador_bsc_mensal.csv`
- **Estrutura**:
  ```
  Month, MonthlyPercent, CumulativePercent
  2024-01, 15, 15
  2024-02, 20, 35
  2024-03, 25, 60
  ...
  ```
- **Validação**: Total soma 100%

### 1.4 - Comando para Executar
```powershell
python .\BSC\bsc_previsto.py calculate --input "Inputs\Template V2.xlsx" --output-csv "Outputs\indicador_bsc_mensal.csv"
```

---

## FASE 2: DADOS REAIS (EM DESENVOLVIMENTO)

### 2.1 - Entrada: Dados Realizados em Excel
- **Status**: ⏳ A FAZER
- **Fonte**: Excel com % realizada de cada atividade
- **Questões a responder**:
  - [ ] Qual é o arquivo Excel com dados reais?
  - [ ] Qual coluna contém a % realizada de cada atividade?
  - [ ] Como os IDs/nomes das atividades estão identificados? (devem bater com o cronograma)
  - [ ] As atividades estão na mesma estrutura do cronograma?
  - [ ] Existe data de atualização dos dados reais?

### 2.2 - Processamento: Extrair % Realizada
- **Status**: ⏳ A FAZER
- **Arquivo a criar**: `BSC/bsc_realizado.py` (ou integrar ao `BSC/bsc_previsto.py`)
- **Lógica**:
  1. Carregar Excel com dados reais
  2. Extrair identificador da atividade (ID, nome, etc.)
  3. Extrair % realizada de cada atividade
  4. Validar formato (deve estar entre 0-100%)
  5. Fazer merge com o CSV de baseline para trazer durações e datas

### 2.3 - Agregação por Mês
- **Status**: ⏳ A FAZER
- **Lógica**:
  1. Para cada atividade com % realizada, multiplicar pela duração (peso)
  2. Distribuir esse valor entre os meses que a atividade se estende (mesma lógica de ponderação do previsto)
  3. Agregar: (% realizada × peso × dias_sobreposição) / dias_atividade
  4. Somar por mês
  5. Calcular % realizado por mês = (peso_realizado_mês / peso_total) × 100

### 2.4 - Saída: CSV com % Realizado
- **Status**: ⏳ A FAZER
- **Arquivo a gerar**: `Outputs/indicador_bsc_realizado.csv`
- **Estrutura** (compatível com previsto):
  ```
  Month, MonthlyPercent, CumulativePercent
  2024-01, 12, 12
  2024-02, 18, 30
  2024-03, 27, 57
  ...
  ```

---

## FASE 3: COMPARAÇÃO E RELATÓRIO

### 3.1 - Consolidação de Dados
- **Status**: ⏳ A FAZER
- **Arquivo a criar**: `BSC/bsc_consolidado.py`
- **Lógica**:
  1. Carregar `indicador_bsc_mensal.csv` (previsto)
  2. Carregar `indicador_bsc_realizado.csv` (realizado)
  3. Fazer join por mês
  4. Calcular variações:
     - Diferença absoluta: Realizado - Previsto
     - Diferença percentual: ((Realizado - Previsto) / Previsto) × 100
     - Status: ✅ (no prazo), ⚠️ (atrasado), 📈 (adiantado)

### 3.2 - Saída: CSV de Comparação
- **Status**: ⏳ A FAZER
- **Arquivo a gerar**: `Outputs/indicador_bsc_consolidado.csv`
- **Estrutura**:
  ```
  Month, Previsto%, Realizado%, Diferença%, Status
  2024-01, 15, 12, -3, ⚠️
  2024-02, 20, 18, -2, ⚠️
  2024-03, 25, 27, +2, 📈
  ...
  ```

### 3.3 - Relatório Executivo (Opcional)
- **Status**: ⏳ A FAZER
- Gráfico de linhas: Previsto vs Realizado (cumulativo)
- Tabela de desvios por mês
- Análise de causa raiz (por projeto, se aplicável)

---

## ESTRUTURA DE DADOS - MAPEAMENTO

### CSV Baseline (previsto)
```
Month | MonthlyPercent | CumulativePercent
```
→ Gerado por `BSC/bsc_previsto.py` a partir do cronograma

### Excel com Dados Reais
```
[Identificador da Atividade] | [% Realizada] | [Data de Atualização?]
```
→ Precisa ser carregado e vinculado ao baseline

### CSV Final (consolidado)
```
Month | Previsto% | Realizado% | Diferença% | Diferença_Dias? | Status
```

---

## CHECKLIST DE IMPLEMENTAÇÃO

### FASE 1 - PREVISTO
- [x] Criar `BSC/bsc_previsto.py` com lógica de cálculo
- [x] Testar com arquivo de entrada
- [x] Validar saída CSV
- [x] Documentar em `README_BSC.md`

### FASE 2 - REALIZADO
- [ ] **Identificar arquivo Excel com dados reais**
- [ ] **Validar estrutura (colunas, nomes, IDs)**
- [ ] **Criar `BSC/bsc_realizado.py` com:**
  - [ ] Função para carregar dados reais
  - [ ] Função para vincular com baseline (merge por ID)
  - [ ] Função para distribuir % realizado por mês
  - [ ] Função para salvar CSV com resultado
- [ ] **Testar com dados reais**
- [ ] **Validar resultado**

### FASE 3 - CONSOLIDADO
- [ ] **Criar `BSC/bsc_consolidado.py` com:**
  - [ ] Função para carregar previsto e realizado
  - [ ] Função para calcular variações
  - [ ] Função para atribuir status (ok/atrasado/adiantado)
  - [ ] Função para salvar CSV consolidado
- [ ] **Testar merge e cálculos**
- [ ] **Gerar relatório visual (opcional)**

---

## PONTOS CRÍTICOS A NÃO ESQUECER

1. **Integridade de Pesos**: O peso (duração) de uma atividade deve ser IMUTÁVEL entre previsto e realizado
   - → Sempre vincular pelo ID único da atividade
   - → Usar duração do cronograma original

2. **Ponderação por Mês**: A mesma lógica de distribuição de duração deve ser aplicada em ambos (previsto e realizado)
   - → Reusa a lógica de sobreposição de dias

3. **Validação**:
   - Previsto% deve sempre somar 100% por projeto
   - Realizado% pode estar < 100% (atividades em progresso) ou > 100% (erros/divergências)

4. **Identificadores Únicos**:
   - Decidir qual será o ID único da atividade (nome, código, linha_excel, etc.)
   - Este ID deve estar em ambos os arquivos (cronograma e dados reais)

---

## NOTAS E DECISÕES PENDENTES

- [ ] Qual é o arquivo Excel com dados reais? Compartilhar localização.
- [ ] Como está estruturado? (Colunas, tipo de ID)
- [ ] Há múltiplos projetos ou apenas um?
- [ ] Os dados reais são atualizados diariamente, semanalmente, etc.?
- [ ] Gerar relatório visual (matplotlib/plotly)?

---

## PRÓXIMOS PASSOS

1. **Você responde**:
   - Localização do arquivo Excel com % realizada
   - Estrutura do arquivo (nomes de colunas, como as atividades são identificadas)

2. **Eu implemento**:
   - `BSC/bsc_realizado.py` para extrair e processar dados reais
   - `BSC/bsc_consolidado.py` para consolidar e comparar
   - Testes e validações

3. **Você valida**:
   - Resultado está correto?
   - Há ajustes necessários?

---

**Última atualização**: 2026-05-19
