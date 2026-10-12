import os
import random
import argparse
import re
import string
import xml.etree.ElementTree as ET

NAMESPACE = 'http://schemas.microsoft.com/project'
NS = {'p': NAMESPACE}
ET.register_namespace('', NAMESPACE)

DURATION_PATTERN = re.compile(
    r'^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$'
)
PROGRESS_STAGE_RANGES = {
    'early': (0.15, 0.30),
    'middle': (0.40, 0.65),
    'late': (0.75, 0.95),
}

def duration_to_seconds(value, uid):
    match = DURATION_PATTERN.fullmatch(value or '')
    if match is None:
        raise ValueError(f'Duração inválida na atividade UID {uid}: {value!r}')
    days, hours, minutes, seconds = match.groups()
    return round(
        int(days or 0) * 86400
        + int(hours or 0) * 3600
        + int(minutes or 0) * 60
        + float(seconds or 0)
    )

def format_duration(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'PT{hours}H{minutes}M{seconds}S'

def set_remaining_duration(task, percentage, uid):
    duration_tag = task.find('p:Duration', NS)
    if duration_tag is None:
        raise ValueError(f'A atividade UID {uid} não possui Duration.')

    duration_seconds = duration_to_seconds(duration_tag.text, uid)
    actual_seconds = round(duration_seconds * percentage / 100)
    remaining_seconds = duration_seconds - actual_seconds

    # 1. Ajustar RemainingDuration
    remaining_tag = task.find('p:RemainingDuration', NS)
    if remaining_seconds == 0: # Se for 100%
        if remaining_tag is not None:
            task.remove(remaining_tag)
    else:
        if remaining_tag is None:
            remaining_tag = ET.Element(f'{{{NAMESPACE}}}RemainingDuration')
            task.append(remaining_tag)
        remaining_tag.text = format_duration(remaining_seconds)
        
    # 2. Ajustar ActualDuration (Garante que o ProjectLibre valide o percentual)
    actual_tag = task.find('p:ActualDuration', NS)
    if actual_seconds == 0: # Se for 0%
        if actual_tag is not None:
            task.remove(actual_tag)
    else:
        if actual_tag is None:
            actual_tag = ET.Element(f'{{{NAMESPACE}}}ActualDuration')
            task.append(actual_tag)
        actual_tag.text = format_duration(actual_seconds)

    # 3. FAXINA CRÍTICA: Remover Término Real se não estiver 100% concluído
    if percentage < 100:
        actual_finish = task.find('p:ActualFinish', NS)
        if actual_finish is not None:
            task.remove(actual_finish)
        
        # ProjectLibre também usa a tag Resume para cálculos de interrupção
        resume_tag = task.find('p:Resume', NS)
        if resume_tag is not None:
            task.remove(resume_tag)

    # 4. FAXINA CRÍTICA: Remover Início Real se estiver 0% (nem começou)
    if percentage == 0:
        actual_start = task.find('p:ActualStart', NS)
        if actual_start is not None:
            task.remove(actual_start)


def assign_completion_percentages(root, progress_stage):
    tasks = root.findall('.//p:Task', NS)
    tasks_by_uid = {}
    task_order = []
    summary_by_uid = {}
    outline_levels = {}
    summary_descendants = {}

    for task in tasks:
        uid_tag = task.find('p:UID', NS)
        if uid_tag is None or not uid_tag.text:
            raise ValueError('Todas as atividades precisam ter um UID.')
        uid = uid_tag.text
        if uid in tasks_by_uid:
            raise ValueError(f'UID duplicado: {uid}')

        level_tag = task.find('p:OutlineLevel', NS)
        if level_tag is None or not level_tag.text:
            raise ValueError(f'Atividade UID {uid} sem OutlineLevel.')

        tasks_by_uid[uid] = task
        task_order.append(uid)
        summary_by_uid[uid] = task.findtext('p:Summary', default='0', namespaces=NS) == '1'
        outline_levels[uid] = int(level_tag.text)
        if summary_by_uid[uid]:
            summary_descendants[uid] = []

    summary_stack = []
    for uid in task_order:
        level = outline_levels[uid]
        while summary_stack and summary_stack[-1][0] >= level:
            summary_stack.pop()
        if not summary_by_uid[uid]:
            for _, summary_uid in summary_stack:
                summary_descendants[summary_uid].append(uid)
        else:
            summary_stack.append((level, uid))

    topological_order = [uid for uid in task_order if not summary_by_uid[uid]]
    
    active_tasks = [
        uid for uid in topological_order
        if tasks_by_uid[uid].findtext('p:Milestone', default='0', namespaces=NS) != '1'
        and duration_to_seconds(tasks_by_uid[uid].findtext('p:Duration', namespaces=NS), uid) > 0
    ]

    project_is_complete = progress_stage == 'complete'
    active_uid = None
    partial_percentage = 0

    if active_tasks and not project_is_complete:
        lower_fraction, upper_fraction = PROGRESS_STAGE_RANGES[progress_stage]
        first_index = min(int(len(active_tasks) * lower_fraction), len(active_tasks) - 1)
        last_index = min(max(first_index, int(len(active_tasks) * upper_fraction)), len(active_tasks) - 1)
        
        progress_cut_index = random.randint(first_index, last_index)
        active_uid = active_tasks[progress_cut_index]
        partial_percentage = random.randint(1, 99)
    
    active_index = topological_order.index(active_uid) if active_uid is not None else None
    completion_by_uid = {}

    for index, uid in enumerate(topological_order):
        task = tasks_by_uid[uid]
        
        if project_is_complete or active_uid is None:
            percentage = 100
        elif index < active_index:
            percentage = 100
        elif uid == active_uid:
            percentage = partial_percentage
        else:
            percentage = 0

        percent_tag = task.find('p:PercentComplete', NS)
        work_percent_tag = task.find('p:PercentWorkComplete', NS)
        
        if percent_tag is None or work_percent_tag is None:
            raise ValueError(f'Atividade UID {uid} sem tag de percentual no modelo.')
            
        percent_tag.text = str(percentage)
        is_milestone = task.findtext('p:Milestone', default='0', namespaces=NS) == '1'
        work_percent_tag.text = '0' if is_milestone else str(percentage)
        
        set_remaining_duration(task, percentage, uid)
        completion_by_uid[uid] = percentage

    # Calcula e ajusta as tarefas resumos (pacotes de trabalho)
    for uid, descendants in summary_descendants.items():
        percent_tag = tasks_by_uid[uid].find('p:PercentComplete', NS)
        work_percent_tag = tasks_by_uid[uid].find('p:PercentWorkComplete', NS)
        
        if descendants:
            weighted_completion = 0
            total_duration = 0
            for descendant_uid in descendants:
                duration_tag = tasks_by_uid[descendant_uid].find('p:Duration', NS)
                duration_seconds = duration_to_seconds(duration_tag.text, descendant_uid)
                weighted_completion += (completion_by_uid.get(descendant_uid, 0) * duration_seconds)
                total_duration += duration_seconds
                
            percentage = round(weighted_completion / total_duration) if total_duration else 0
        else:
            percentage = 0
            
        percent_tag.text = str(percentage)
        work_percent_tag.text = str(percentage)
        set_remaining_duration(tasks_by_uid[uid], percentage, uid)


def generate_synthetic_xml(source_path, output_path, project_name, progress_stage):
    tree = ET.parse(source_path)
    root = tree.getroot()

    assign_completion_percentages(root, progress_stage)

    title_tag = root.find('p:Title', NS)
    if title_tag is not None:
        title_tag.text = project_name
        
    root_name_tag = root.find('p:Name', NS)
    if root_name_tag is not None:
        root_name_tag.text = project_name

    for task in root.findall('.//p:Task', NS):
        uid_tag = task.find('p:UID', NS)
        if uid_tag is not None and uid_tag.text == '0':
            name_tag = task.find('p:Name', NS)
            if name_tag is not None:
                name_tag.text = project_name

    tree.write(output_path, encoding='utf-8', xml_declaration=True)


def get_max_sequence(output_dir):
    """Lê a pasta de saída e descobre qual foi o último número gerado."""
    max_seq = 0
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            match = re.search(r'-(\d{3})-26\.xml$', filename)
            if match:
                max_seq = max(max_seq, int(match.group(1)))
    return max_seq


def create_synthetic_dataset(source_xml, output_dir, count, seed=None):
    if count < 1:
        raise ValueError('A quantidade de cronogramas deve ser maior que zero.')
    if seed is not None:
        random.seed(seed)

    os.makedirs(output_dir, exist_ok=True)
    
    try:
        ET.parse(source_xml)
    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo modelo não encontrado: {source_xml}")

    progress_stages = ['early', 'middle', 'late'] if count >= 3 else []
    while len(progress_stages) < count:
        stage_options = ('early', 'middle', 'late', 'complete')
        if 'complete' in progress_stages:
            stage_options = ('early', 'middle', 'late')
        progress_stages.append(random.choices(stage_options, weights=(3, 3, 3, 1)[:len(stage_options)], k=1)[0])
        
    progress_stages = progress_stages[:count]
    random.shuffle(progress_stages)

    # -------------------------------------------------------------
    # GERAÇÃO DE NÚMEROS ÚNICOS COM BASE NO HISTÓRICO DA PASTA
    # -------------------------------------------------------------
    start_seq = get_max_sequence(output_dir)

    for i in range(1, count + 1):
        current_seq = start_seq + i
        prefix = "".join(random.choices(string.ascii_uppercase, k=2))
        
        project_code = f"{prefix}-{current_seq:03d}-26"
        output_filename = os.path.join(output_dir, f'{project_code}.xml')
        progress_stage = progress_stages[i - 1]

        generate_synthetic_xml(source_xml, output_filename, project_code, progress_stage)
        
        print(f'Gerado: {output_filename} | Estágio: {progress_stage} | Código interno: {project_code}')

if __name__ == '__main__':
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    default_source = os.path.join(project_root, 'data', 'raw', 'Cronograma Completo XML.xml')
    default_output = os.path.join(project_root, 'data', 'synthetic')

    parser = argparse.ArgumentParser(description='Gerar arquivos XML sintéticos a partir de um modelo Project XML.')
    parser.add_argument('source_xml', nargs='?', default=default_source, help='Arquivo XML de entrada')
    parser.add_argument('--count', type=int, default=5, help='Número de arquivos sintéticos a gerar')
    parser.add_argument('--output-dir', default=default_output, help='Pasta de saída onde os arquivos .xml serão criados')
    parser.add_argument('--seed', type=int, default=None, help='Semente')
    args = parser.parse_args()

    create_synthetic_dataset(args.source_xml, args.output_dir, args.count, args.seed)
