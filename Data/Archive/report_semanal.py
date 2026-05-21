import csv
import logging
from pathlib import Path
import os
from datetime import datetime, timedelta

REPO_ROOT = Path(__file__).resolve().parent.parent
PASTA_SAIDA = REPO_ROOT / "relatorios"
LOG_DIR = REPO_ROOT / "logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_file = LOG_DIR / "report_semanal.log"
logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filemode='a'
)

logger = logging.getLogger(__name__)
logger.info("=" * 60)
logger.info("Iniciando execucao do script de relatorio semanal")

def sanitizar_texto(texto):
    if not texto or not isinstance(texto, str):
        return None
    
    texto_limpo = ' '.join(texto.strip().split())
    texto_limpo = ''.join(char for char in texto_limpo if ord(char) >= 32)
    return texto_limpo if texto_limpo else None

def validar_data(data_obj):
    return isinstance(data_obj, datetime) and data_obj.year > 1900 and data_obj.year < 2100

def parse_data(data_str):
    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d']:
        try:
            return datetime.strptime(data_str.strip(), fmt)
        except ValueError:
            continue
    return None

def formatar_data_br(data_obj):
    """Formata data para formato brasileiro DD/MM/YYYY"""
    if data_obj:
        return data_obj.strftime('%d/%m/%Y')
    return ""

dados = []
headers = []
caminho_consolidado = os.path.join(PASTA_SAIDA, "consolidado_projetos.csv")

try:
    with open(caminho_consolidado, 'r', encoding='utf-8') as f:
        leitor = csv.reader(f)
        headers = next(leitor)
        for linha in leitor:
            dados.append(linha)
    logger.info(f"Arquivo 'consolidado_projetos.csv' lido com sucesso. {len(dados)} linhas carregadas.")
except FileNotFoundError:
    logger.error(f"Arquivo 'consolidado_projetos.csv' não encontrado em {caminho_consolidado}.")
    print(f"Erro: Arquivo 'consolidado_projetos.csv' não encontrado em {caminho_consolidado}.")
    exit(1)
except Exception as e:
    logger.error(f"Erro ao ler 'consolidado_projetos.csv': {str(e)}")
    print(f"Erro ao ler arquivo: {str(e)}")
    exit(1)

try:
    idx_inicio = headers.index('Inicio')
    idx_termino = headers.index('Termino')
    logger.info(f"Colunas identificadas: 'Inicio' (indice {idx_inicio}), 'Termino' (índice {idx_termino})")
except ValueError as e:
    logger.error(f"Colunas 'Inicio' ou 'Termino' não encontradas no CSV. Erro: {str(e)}")
    print("Erro: Arquivo CSV deve conter colunas 'Inicio' e 'Termino'.")
    exit(1)
except Exception as e:
    logger.error(f"Erro ao encontrar colunas: {str(e)}")
    print(f"Erro: {str(e)}")
    exit(1)

hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
fim_esta_semana = hoje + timedelta(days=7)

logger.debug(f"Filtro de datas: {hoje.strftime('%Y-%m-%d')} a {fim_esta_semana.strftime('%Y-%m-%d')}")

atividades_semana = []
for linha in dados:
    data_inicio = parse_data(linha[idx_inicio])
    data_termino = parse_data(linha[idx_termino])
    
    if data_inicio and data_termino:
        if not validar_data(data_inicio) or not validar_data(data_termino):
            logger.warning(f"Datas inválidas detectadas na linha: {linha[0]}")
            continue
        
        if (data_inicio <= fim_esta_semana) and (data_termino >= hoje):
            atividades_semana.append(linha)

dados_formatados = []
headers_formatados = headers.copy()

for linha in atividades_semana:
    linha_fmt = []
    data_inicio = parse_data(linha[idx_inicio])
    data_termino = parse_data(linha[idx_termino])

    for idx, valor in enumerate(linha):
        if idx == idx_inicio:
            linha_fmt.append(formatar_data_br(data_inicio))
        elif idx == idx_termino:
            linha_fmt.append(formatar_data_br(data_termino))
        else:
            valor_sanitizado = sanitizar_texto(str(valor)) if valor else ''
            linha_fmt.append(valor_sanitizado)
    dados_formatados.append(linha_fmt)

caminho_relatorio = os.path.join(PASTA_SAIDA, "Relatorio_Semanal_Projetos.csv")
try:
    with open(caminho_relatorio, 'w', encoding='utf-8-sig', newline='') as f:
        escritor = csv.writer(f, delimiter=';')
        escritor.writerow(headers_formatados)
        escritor.writerows(dados_formatados)
    
    logger.info(f"Relatorio salvo com sucesso: {caminho_relatorio} ({len(dados_formatados)} tarefas)")
    print(f"✓ Relatório gerado: {caminho_relatorio} ({len(dados_formatados)} tarefas)")
except Exception as e:
    logger.error(f"Erro ao salvar relatorio CSV: {str(e)}")
    print(f"Erro ao salvar relatório: {str(e)}")
    exit(1)

#os.startfile(caminho_relatorio)
logger.info("Execucao concluida com sucesso")
logger.info("=" * 60)