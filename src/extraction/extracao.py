import os
import csv
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import logging
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
CAMINHOS_ENTRADA = (
    REPO_ROOT / "data" / "raw",
    REPO_ROOT / "data" / "synthetic",
)
PASTA_SAIDA = REPO_ROOT / "data" / "processed"
LOG_DIR = REPO_ROOT / "logs"

os.makedirs(PASTA_SAIDA, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

log_file = LOG_DIR / "extracao_pastas.log"
logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filemode='a'
)

logger = logging.getLogger(__name__)

def sanitizar_texto(texto):
    if not texto or not isinstance(texto, str):
        return None
    texto_limpo = ' '.join(texto.strip().split())
    texto_limpo = ''.join(char for char in texto_limpo if ord(char) >= 32)
    return texto_limpo if texto_limpo else None

def validar_caminho_arquivo(caminho):
    caminho_normalizado = os.path.normpath(caminho)
    if '..' in caminho_normalizado:
        logger.warning(f"Tentativa de path traversal detectada: {caminho}")
        return False
    return True

def validar_data(data_obj):
    return isinstance(data_obj, datetime) and data_obj.year > 1900 and data_obj.year < 2100

def parse_data_iso(data_str):
    if not data_str:
        return None
    try:
        data_limpa = data_str.replace('Z', '').split('T')[0]
        return datetime.fromisoformat(data_limpa)
    except (ValueError, AttributeError):
        return None

def parse_duration_to_days(duration_str):
    if not duration_str or not isinstance(duration_str, str):
        return None
    match = re.match(r'PT(\d+)H(\d+)M(\d+)S', duration_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        total_hours = hours + minutes / 60 + seconds / 3600
        days = total_hours / 8
        return round(days, 2)
    match_d = re.match(r'P(\d+)DT(\d+)H(\d+)M(\d+)S', duration_str)
    if match_d:
        days = int(match_d.group(1))
        hours = int(match_d.group(2))
        minutes = int(match_d.group(3))
        seconds = int(match_d.group(4))
        total_hours = days * 24 + hours + minutes / 60 + seconds / 3600
        days_total = total_hours / 8
        return round(days_total, 2)
    return None

def get_xml_tag_text(element, tag, ns):
    node = element.find(f'p:{tag}', ns)
    return node.text if node is not None else None

def parse_mspdi_to_list(file_path):
    if not validar_caminho_arquivo(file_path):
        raise ValueError(f"Caminho de arquivo inválido: {file_path}")
    
    tree = ET.parse(file_path)
    root = tree.getroot()
    return _parse_mspdi_root(root, os.path.basename(file_path))

def _parse_mspdi_root(root, project_label):
    ns = {'p': 'http://schemas.microsoft.com/project'}

    title_node = root.find('.//p:Title', ns)
    project_name = title_node.text if title_node is not None else project_label
    project_name = sanitizar_texto(project_name) or project_label

    recursos = {}
    for resource in root.findall('.//p:Resource', ns):
        uid = get_xml_tag_text(resource, 'UID', ns)
        name = get_xml_tag_text(resource, 'Name', ns)
        if uid:
            name_sanitizado = sanitizar_texto(name) if name else None
            recursos[uid] = name_sanitizado or 'Sem nome'

    assignments = {}
    for assignment in root.findall('.//p:Assignment', ns):
        task_uid = get_xml_tag_text(assignment, 'TaskUID', ns)
        resource_uid = get_xml_tag_text(assignment, 'ResourceUID', ns)
        if task_uid and resource_uid:
            if task_uid not in assignments:
                assignments[task_uid] = []
            assignments[task_uid].append(resource_uid)

    tasks = []

    summary_task = root.find('.//p:Task', ns)
    if summary_task:
        name = get_xml_tag_text(summary_task, 'Name', ns)
        start = get_xml_tag_text(summary_task, 'Start', ns)
        finish = get_xml_tag_text(summary_task, 'Finish', ns)
        percentual = get_xml_tag_text(summary_task, 'PercentComplete', ns)
        duracao = get_xml_tag_text(summary_task, 'Duration', ns)

        baseline_element = summary_task.find('p:Baseline', ns)
        uid = get_xml_tag_text(summary_task, 'UID', ns)
        outline = get_xml_tag_text(summary_task, 'OutlineNumber', ns)
        baseline_duracao = None
        if baseline_element is not None:
            baseline_duracao = get_xml_tag_text(baseline_element, 'Duration', ns)

        duracao_dias = parse_duration_to_days(duracao)
        baseline_duracao_dias = parse_duration_to_days(baseline_duracao)
        name_sanitizado = sanitizar_texto(name)

        if name_sanitizado and start:
            data_inicio = parse_data_iso(start)
            data_termino = parse_data_iso(finish) if finish else None

            if validar_data(data_inicio):
                recursos_da_tarefa = []
                percentual_limpo = percentual
                if percentual:
                    try:
                        float(percentual)
                    except (ValueError, TypeError):
                        percentual_limpo = None

                tasks.append({
                    'Projeto': project_name,
                    'Atividade': name_sanitizado,
                    'Recursos': 'Projeto Macro',
                    'Percentual completo': percentual_limpo,
                    'Inicio': data_inicio,
                    'Termino': data_termino,
                    'Duracao (dias)': duracao_dias,
                    'UID': uid,
                    'OutlineNumber': outline,
                    'Duracao Baseline (dias)': baseline_duracao_dias
                })

    all_tasks = root.findall('.//p:Task', ns)
    for task in all_tasks[1:]:
        is_summary = get_xml_tag_text(task, 'Summary', ns)
        name = get_xml_tag_text(task, 'Name', ns)
        start = get_xml_tag_text(task, 'Start', ns)
        finish = get_xml_tag_text(task, 'Finish', ns)
        percentual = get_xml_tag_text(task, 'PercentComplete', ns)
        task_uid = get_xml_tag_text(task, 'UID', ns)
        duracao = get_xml_tag_text(task, 'Duration', ns)
        outline_number = get_xml_tag_text(task, 'OutlineNumber', ns)
        baseline_element = task.find('p:Baseline', ns)
        baseline_duracao = None
        if baseline_element is not None:
            baseline_duracao = get_xml_tag_text(baseline_element, 'Duration', ns)

        duracao_dias = parse_duration_to_days(duracao)
        baseline_duracao_dias = parse_duration_to_days(baseline_duracao)

        name_sanitizado = sanitizar_texto(name)

        if is_summary == '0' and name_sanitizado and start:
            data_inicio = parse_data_iso(start)
            data_termino = parse_data_iso(finish) if finish else None

            if not validar_data(data_inicio):
                logger.warning(f"Data de início inválida em tarefa '{name_sanitizado}': {start}")
                continue

            if data_termino and not validar_data(data_termino):
                logger.warning(f"Data de término inválida em tarefa '{name_sanitizado}': {finish}")
                data_termino = None

            recursos_da_tarefa = []
            if task_uid in assignments:
                recursos_da_tarefa = [recursos.get(uid, f'Desconhecido ({uid})') for uid in assignments[task_uid]]

            percentual_limpo = percentual
            if percentual:
                try:
                    float(percentual)
                except (ValueError, TypeError):
                    logger.warning(f"Percentual inválido em tarefa '{name_sanitizado}': {percentual}")
                    percentual_limpo = None

            tasks.append({
                'Projeto': project_name,
                'Atividade': name_sanitizado,
                'Recursos': ', '.join(recursos_da_tarefa) if recursos_da_tarefa else 'Sem recurso',
                'Percentual completo': percentual_limpo,
                'Inicio': data_inicio,
                'Termino': data_termino,
                'Duracao (dias)': duracao_dias,
                'Duracao Baseline (dias)': baseline_duracao_dias,
                'UID': task_uid,
                'OutlineNumber': outline_number
            })
    return tasks

def extract_xml_from_pod(pod_path):
    """Extrai o bloco de texto XML dentro de um arquivo .pod.
    Procura pela tag <Project xmlns="http://schemas.microsoft.com/project">
    e remove tudo que vem antes dela, tratando corretamente o encoding UTF-8."""
    if not validar_caminho_arquivo(pod_path):
        raise ValueError(f"Caminho de arquivo inválido: {pod_path}")

    with open(pod_path, 'rb') as f:
        raw = f.read()

    marker = b'<Project xmlns="http://schemas.microsoft.com/project">'
    pos = raw.find(marker)
    
    if pos >= 0:
        xml_bytes = raw[pos:]
        xml_text = xml_bytes.decode('utf-8', errors='replace')
        logger.info(f"Tag Project encontrada em posição {pos} (Tratado em UTF-8)")
        return xml_text
    else:
        pos = raw.find(b'<Project')
        if pos >= 0:
            logger.warning(f"Tag Project com xmlns diferente encontrada em posição {pos}")
            xml_bytes = raw[pos:]
            xml_text = xml_bytes.decode('utf-8', errors='replace')
            return xml_text
        
        raise ValueError('Arquivo .pod não contém a tag <Project esperada.')

def parse_mspdi_from_pod(pod_path):
    """Extrai XML de .pod e retorna lista de tarefas como parse_mspdi_to_list."""
    xml_text = extract_xml_from_pod(pod_path)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        # tenta localizar primeiro '<' e parsear novamente
        pos = xml_text.find('<')
        if pos > 0:
            xml_text = xml_text[pos:]
            root = ET.fromstring(xml_text)
        else:
            raise
    return _parse_mspdi_root(root, os.path.basename(pod_path))

def processar_xmls_recursivos(diretorio_raiz):
    arquivo_infos = []
    tarefas_consolidadas = []
    nome_origem = Path(diretorio_raiz).name
    
    for root, dirs, files in os.walk(diretorio_raiz):
        pasta_relativa = os.path.relpath(root, diretorio_raiz)
        if pasta_relativa == ".":
            pasta_relativa = nome_origem
        else:
            pasta_relativa = os.path.join(nome_origem, pasta_relativa)
        
        for arquivo in files:
            if Path(arquivo).suffix.lower() in {'.xml', '.pod'}:
                caminho_completo = os.path.join(root, arquivo)
                status_leitura = "Não lido"

                try:
                    if Path(arquivo).suffix.lower() == '.xml':
                        tarefas = parse_mspdi_to_list(caminho_completo)
                    else:
                        tarefas = parse_mspdi_from_pod(caminho_completo)

                    status_leitura = "Lido com sucesso"
                    logger.info(f"Arquivo lido com sucesso: {arquivo} - {len(tarefas)} tarefas extraídas")

                    for tarefa in tarefas:
                        tarefa['Pasta'] = pasta_relativa if pasta_relativa != "Root" else "teste"
                        tarefa['Arquivo'] = arquivo
                        tarefas_consolidadas.append(tarefa)

                except ET.ParseError as e:
                    status_leitura = f"Erro de XML: {str(e)[:50]}"
                    logger.warning(f"Erro de parsing em '{arquivo}': {str(e)[:100]}")
                except Exception as e:
                    status_leitura = f"Erro: {str(e)[:50]}"
                    logger.error(f"Erro ao processar '{arquivo}': {str(e)[:100]}")

                arquivo_infos.append({
                    'Nome do Arquivo': arquivo,
                    'Pasta': pasta_relativa if pasta_relativa != "Root" else "teste",
                    'Status de Leitura': status_leitura,
                    'Caminho Completo': caminho_relativo(caminho_completo)
                })
    
    return arquivo_infos, tarefas_consolidadas

def caminho_relativo(caminho):
    """Grava caminhos relativos à raiz do repositório, sem expor diretórios pessoais."""
    try:
        return str(Path(caminho).resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return Path(caminho).name

def desambiguar_nomes_de_projeto(tarefas):
    """Diferencia projetos de arquivos distintos que compartilham o mesmo nome.

    Os indicadores BSC agrupam as atividades pelo nome do projeto; sem esta etapa,
    cronogramas diferentes com o mesmo título seriam somados como se fossem um só.
    """
    arquivos_por_projeto = {}
    for tarefa in tarefas:
        arquivos_por_projeto.setdefault(tarefa['Projeto'], set()).add(tarefa['Arquivo'])

    repetidos = {nome for nome, arquivos in arquivos_por_projeto.items() if len(arquivos) > 1}
    for tarefa in tarefas:
        if tarefa['Projeto'] in repetidos:
            tarefa['Projeto'] = f"{tarefa['Projeto']} [{Path(tarefa['Arquivo']).stem}]"
    return tarefas

def gerar_relatorios(diretorios_raiz=CAMINHOS_ENTRADA, diretorio_saida=PASTA_SAIDA):
    if isinstance(diretorios_raiz, (str, os.PathLike)):
        diretorios_raiz = (Path(diretorios_raiz),)
    else:
        diretorios_raiz = tuple(Path(path) for path in diretorios_raiz)

    for diretorio_raiz in diretorios_raiz:
        if not diretorio_raiz.is_dir():
            raise FileNotFoundError(f"Pasta de entrada não encontrada: {diretorio_raiz}")

    diretorio_saida = Path(diretorio_saida)
    diretorio_saida.mkdir(parents=True, exist_ok=True)
    logger.info(f"Iniciando processamento de arquivos em: {diretorios_raiz}")
    print(f"Iniciando processamento de arquivos em: {diretorios_raiz}")

    arquivo_infos = []
    tarefas_consolidadas = []
    for diretorio_raiz in diretorios_raiz:
        arquivos_origem, tarefas_origem = processar_xmls_recursivos(diretorio_raiz)
        arquivo_infos.extend(arquivos_origem)
        tarefas_consolidadas.extend(tarefas_origem)
    desambiguar_nomes_de_projeto(tarefas_consolidadas)
    if arquivo_infos:
        try:
            caminho_arquivo_detalhes = diretorio_saida / "arquivos_xml.csv"
            with open(caminho_arquivo_detalhes, 'w', encoding='utf-8-sig', newline='') as f:
                escritor = csv.DictWriter(f, fieldnames=['Nome do Arquivo', 'Pasta', 'Status de Leitura', 'Caminho Completo'])
                escritor.writeheader()
                escritor.writerows(arquivo_infos)
            
            logger.info(f"CSV de detalhes gerado: {caminho_arquivo_detalhes} ({len(arquivo_infos)} arquivos)")
            print(f"\nCSV de detalhes gerado: {caminho_arquivo_detalhes} ({len(arquivo_infos)} arquivos)")
            for info in arquivo_infos:
                print(f"  {info['Nome do Arquivo']} - {info['Status de Leitura']}")
        except Exception as e:
            logger.error(f"Erro ao gerar 'arquivos_xml.csv': {str(e)}")
            print(f"Erro ao gerar CSV de detalhes: {str(e)}")
    else:
        logger.warning("Nenhum arquivo XML encontrado no diretório.")
        print("\nNenhum arquivo XML encontrado!")
    
    if tarefas_consolidadas:
        fieldnames = ['Projeto', 'Atividade', 'Recursos', 'Percentual completo', 'Inicio', 'Termino', 'Duracao (dias)', 'Duracao Baseline (dias)', 'UID', 'OutlineNumber', 'Pasta', 'Arquivo']    
        try:
            caminho_consolidado = diretorio_saida / "consolidado_projetos.csv"
            with open(caminho_consolidado, 'w', encoding='utf-8-sig', newline='') as f:
                escritor = csv.DictWriter(f, fieldnames=fieldnames)
                escritor.writeheader()
                
                for tarefa in tarefas_consolidadas:
                    tarefa_fmt = tarefa.copy()
                    if isinstance(tarefa_fmt['Inicio'], datetime):
                        tarefa_fmt['Inicio'] = tarefa_fmt['Inicio'].strftime('%Y-%m-%d')
                    if isinstance(tarefa_fmt['Termino'], datetime):
                        tarefa_fmt['Termino'] = tarefa_fmt['Termino'].strftime('%Y-%m-%d')
                    escritor.writerow(tarefa_fmt)
            
            logger.info(f"CSV consolidado gerado: {caminho_consolidado} ({len(tarefas_consolidadas)} tarefas)")
            print(f"\nCSV consolidado gerado: {caminho_consolidado} ({len(tarefas_consolidadas)} tarefas)")
            print(f"Colunas: {fieldnames}")
        except Exception as e:
            logger.error(f"Erro ao gerar 'consolidado_projetos.csv': {str(e)}")
            print(f"Erro ao gerar CSV consolidado: {str(e)}")
    else:
        logger.warning("Nenhuma tarefa foi extraida dos XMLs.")
        print("\nNenhuma tarefa foi extraida dos XMLs.")

if __name__ == "__main__":
    try:
        logger.info("=" * 60)
        logger.info("Iniciando execucao do script de extração de XML")
        gerar_relatorios(CAMINHOS_ENTRADA, PASTA_SAIDA)
        logger.info("Execucao concluida com sucesso")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Erro geral durante execucao: {str(e)}", exc_info=True)
        print(f"Erro durante execucao: {str(e)}")
        exit(1)