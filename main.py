import os
import csv
import xml.etree.ElementTree as ET
from datetime import datetime
import logging

# Criar pasta de logs se não existir (ANTES de configurar logging)
os.makedirs("logs", exist_ok=True)

# Configurar logging silencioso
log_file = "logs/extracao_pastas.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filemode='a'
)

logger = logging.getLogger(__name__)

def sanitizar_texto(texto):
    """
    Sanitiza texto removendo espaçamento excessivo e caracteres inválidos.
    Retorna None se o texto for vazio após sanitização.
    """
    if not texto or not isinstance(texto, str):
        return None
    
    # Remove espaços em branco das extremidades e reduz espaços múltiplos
    texto_limpo = ' '.join(texto.strip().split())
    
    # Remove caracteres de controle
    texto_limpo = ''.join(char for char in texto_limpo if ord(char) >= 32)
    
    return texto_limpo if texto_limpo else None

def validar_caminho_arquivo(caminho):
    """
    Valida se o caminho é seguro e não contém tentativas de path traversal.
    """
    # Normaliza o caminho
    caminho_normalizado = os.path.normpath(caminho)
    
    # Verifica se tenta sair do diretório de projeto
    if '..' in caminho_normalizado:
        logger.warning(f"Tentativa de path traversal detectada: {caminho}")
        return False
    
    return True

def validar_data(data_obj):
    """
    Valida se a data é um objeto datetime válido.
    """
    return isinstance(data_obj, datetime) and data_obj.year > 1900 and data_obj.year < 2100

def parse_data_iso(data_str):
    """Converte data ISO para objeto datetime"""
    if not data_str:
        return None
    try:
        # Remove 'T' e 'Z' para compatibilidade com fromisoformat
        data_limpa = data_str.replace('Z', '').split('T')[0]
        return datetime.fromisoformat(data_limpa)
    except (ValueError, AttributeError):
        return None

def get_xml_tag_text(element, tag, ns):
    node = element.find(f'p:{tag}', ns)
    return node.text if node is not None else None

def parse_mspdi_to_list(file_path):
    # Valida caminho do arquivo
    if not validar_caminho_arquivo(file_path):
        raise ValueError(f"Caminho de arquivo inválido: {file_path}")
    
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'p': 'http://schemas.microsoft.com/project'}
    
    # Define o nome do projeto (título ou nome do arquivo)
    title_node = root.find('.//p:Title', ns)
    project_name = title_node.text if title_node is not None else os.path.basename(file_path)
    project_name = sanitizar_texto(project_name) or os.path.basename(file_path)
    
    # Carrega recursos em um dicionário {UID: Name}
    recursos = {}
    for resource in root.findall('.//p:Resource', ns):
        uid = get_xml_tag_text(resource, 'UID', ns)
        name = get_xml_tag_text(resource, 'Name', ns)
        if uid:
            # Sanitiza o nome do recurso
            name_sanitizado = sanitizar_texto(name) if name else None
            recursos[uid] = name_sanitizado or 'Sem nome'
    
    # Carrega assignments em um dicionário {TaskUID: [ResourceUIDs]}
    assignments = {}
    for assignment in root.findall('.//p:Assignment', ns):
        task_uid = get_xml_tag_text(assignment, 'TaskUID', ns)
        resource_uid = get_xml_tag_text(assignment, 'ResourceUID', ns)
        if task_uid and resource_uid:
            if task_uid not in assignments:
                assignments[task_uid] = []
            assignments[task_uid].append(resource_uid)
    
    tasks = []
    for task in root.findall('.//p:Task', ns):
        is_summary = get_xml_tag_text(task, 'Summary', ns)
        name = get_xml_tag_text(task, 'Name', ns)
        start = get_xml_tag_text(task, 'Start', ns)
        finish = get_xml_tag_text(task, 'Finish', ns)
        percentual = get_xml_tag_text(task, 'PercentComplete', ns)
        task_uid = get_xml_tag_text(task, 'UID', ns)
        
        # Sanitiza e valida dados
        name_sanitizado = sanitizar_texto(name)
        
        if is_summary == '0' and name_sanitizado and start:
            # Valida e converte datas
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
            
            # Valida e sanitiza percentual
            percentual_limpo = percentual
            if percentual:
                try:
                    float(percentual)  # Valida se é número
                except (ValueError, TypeError):
                    logger.warning(f"Percentual inválido em tarefa '{name_sanitizado}': {percentual}")
                    percentual_limpo = None
            
            tasks.append({
                'Projeto': project_name,
                'Atividade': name_sanitizado,
                'Recursos': ', '.join(recursos_da_tarefa) if recursos_da_tarefa else 'Sem recurso',
                'Percentual completo': percentual_limpo,
                'Inicio': data_inicio,
                'Termino': data_termino
            })
    
    return tasks

def processar_xmls_recursivos(diretorio_raiz):
    """
    Processa todos os XMLs recursivamente a partir de um diretório raiz.
    Retorna um DataFrame com informações de cada arquivo e suas leituras.
    """
    arquivo_infos = []
    tarefas_consolidadas = []
    
    # Percorre recursivamente todos os diretórios
    for root, dirs, files in os.walk(diretorio_raiz):
        # Calcula o nome da pasta relativa (ex: "Em Estudo", "Em Execução", "teste")
        pasta_relativa = os.path.relpath(root, diretorio_raiz)
        if pasta_relativa == ".":
            pasta_relativa = "Root"
        
        # Processa cada arquivo XML encontrado
        for arquivo in files:
            if arquivo.endswith('.xml'):
                caminho_completo = os.path.join(root, arquivo)
                status_leitura = "Não lido"
                
                try:
                    # Tenta ler o arquivo XML
                    tarefas = parse_mspdi_to_list(caminho_completo)
                    status_leitura = "Lido com sucesso"
                    logger.info(f"XML lido com sucesso: {arquivo} - {len(tarefas)} tarefas extraídas")
                    
                    # Adiciona as tarefas ao consolidado
                    for tarefa in tarefas:
                        tarefa['Pasta'] = pasta_relativa if pasta_relativa != "Root" else "teste"
                        tarefa['Arquivo'] = arquivo
                        tarefas_consolidadas.append(tarefa)
                
                except ET.ParseError as e:
                    status_leitura = f"Erro de XML: {str(e)[:50]}"
                    logger.warning(f"Erro de parsing XML em '{arquivo}': {str(e)[:100]}")
                except Exception as e:
                    status_leitura = f"Erro: {str(e)[:50]}"
                    logger.error(f"Erro ao processar '{arquivo}': {str(e)[:100]}")
                
                # Registra informações do arquivo
                arquivo_infos.append({
                    'Nome do Arquivo': arquivo,
                    'Pasta': pasta_relativa if pasta_relativa != "Root" else "teste",
                    'Status de Leitura': status_leitura,
                    'Caminho Completo': caminho_completo
                })
    
    return arquivo_infos, tarefas_consolidadas

def gerar_relatorios(diretorio_raiz="./teste"):
    """
    Gera dois CSVs:
    1. arquivos_xml.csv - informações de cada arquivo XML
    2. consolidado_projetos.csv - tarefas consolidadas de todos os XMLs
    """
    
    logger.info(f"Iniciando processamento recursivo de XML em: {diretorio_raiz}")
    
    if not os.path.exists(diretorio_raiz):
        logger.error(f"Pasta '{diretorio_raiz}' não encontrada.")
        print(f"A pasta '{diretorio_raiz}' não foi encontrada.")
        return
    
    print(f"Iniciando processamento recursivo de XML em: {diretorio_raiz}")
    
    # Processa todos os XMLs recursivamente
    arquivo_infos, tarefas_consolidadas = processar_xmls_recursivos(diretorio_raiz)
    
    # Gera CSV com detalhes de cada arquivo
    if arquivo_infos:
        try:
            with open("arquivos_xml.csv", 'w', encoding='utf-8-sig', newline='') as f:
                escritor = csv.DictWriter(f, fieldnames=['Nome do Arquivo', 'Pasta', 'Status de Leitura', 'Caminho Completo'])
                escritor.writeheader()
                escritor.writerows(arquivo_infos)
            
            logger.info(f"CSV de detalhes gerado: arquivos_xml.csv ({len(arquivo_infos)} arquivos)")
            print(f"\n✓ CSV de detalhes gerado: arquivos_xml.csv ({len(arquivo_infos)} arquivos)")
            for info in arquivo_infos:
                print(f"  {info['Nome do Arquivo']} - {info['Status de Leitura']}")
        except Exception as e:
            logger.error(f"Erro ao gerar 'arquivos_xml.csv': {str(e)}")
            print(f"Erro ao gerar CSV de detalhes: {str(e)}")
    else:
        logger.warning("Nenhum arquivo XML encontrado no diretório.")
        print("\nNenhum arquivo XML encontrado!")
    
    # Gera CSV com tarefas consolidadas
    if tarefas_consolidadas:
        fieldnames = ['Projeto', 'Atividade', 'Recursos', 'Percentual completo', 'Inicio', 'Termino', 'Pasta', 'Arquivo']
        
        try:
            with open("consolidado_projetos.csv", 'w', encoding='utf-8-sig', newline='') as f:
                escritor = csv.DictWriter(f, fieldnames=fieldnames)
                escritor.writeheader()
                
                for tarefa in tarefas_consolidadas:
                    # Formata as datas para string ISO
                    tarefa_fmt = tarefa.copy()
                    if isinstance(tarefa_fmt['Inicio'], datetime):
                        tarefa_fmt['Inicio'] = tarefa_fmt['Inicio'].strftime('%Y-%m-%d')
                    if isinstance(tarefa_fmt['Termino'], datetime):
                        tarefa_fmt['Termino'] = tarefa_fmt['Termino'].strftime('%Y-%m-%d')
                    
                    escritor.writerow(tarefa_fmt)
            
            logger.info(f"CSV consolidado gerado: consolidado_projetos.csv ({len(tarefas_consolidadas)} tarefas)")
            print(f"\n✓ CSV consolidado gerado: consolidado_projetos.csv ({len(tarefas_consolidadas)} tarefas)")
            print(f"Colunas: {fieldnames}")
        except Exception as e:
            logger.error(f"Erro ao gerar 'consolidado_projetos.csv': {str(e)}")
            print(f"Erro ao gerar CSV consolidado: {str(e)}")
    else:
        logger.warning("Nenhuma tarefa foi extraída dos XMLs.")
        print("\nNenhuma tarefa foi extraída dos XMLs.")

# Executa o processamento
if __name__ == "__main__":
    try:
        logger.info("=" * 60)
        logger.info("Iniciando execução do script de extração de XML")
        gerar_relatorios("./teste")
        logger.info("Execução concluída com sucesso")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Erro geral durante execução: {str(e)}", exc_info=True)
        print(f"Erro durante execução: {str(e)}")
        exit(1)