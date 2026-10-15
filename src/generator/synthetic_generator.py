import os
import random
import argparse
import re
import string
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

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

FF, FS, SF, SS = 0, 1, 2, 3

# Probabilidades do "ruído" (atrasos realistas). Use --no-noise para desligar.
PROB_SLIP_FINISH = 0.25   # tarefa que terminou HÁ POUCO (veja FRONTIER_DAYS) ainda está em 80-99%
PROB_SLIP_START = 0.10    # tarefa que deveria estar em andamento ainda não começou
FRONTIER_DAYS = 14        # só tarefas que terminaram nos últimos N dias podem "escorregar"

TASK_TAG_ORDER = [
    'UID', 'ID', 'Name', 'Type', 'IsNull', 'CreateDate', 'WBS', 'OutlineNumber',
    'OutlineLevel', 'Priority', 'Start', 'Finish', 'Duration', 'DurationFormat',
    'Stop', 'Resume', 'ResumeValid', 'EffortDriven', 'Recurring', 'OverAllocated',
    'Estimated', 'Milestone', 'Summary', 'Critical', 'IsSubproject',
    'IsSubprojectReadOnly', 'ExternalTask', 'FixedCostAccrual', 'PercentComplete',
    'PercentWorkComplete', 'RemainingDuration', 'ConstraintType', 'CalendarUID',
    'ConstraintDate', 'LevelAssignments', 'LevelingCanSplit', 'LevelingDelay',
    'LevelingDelayFormat', 'IgnoreResourceCalendar', 'HideBar', 'Rollup',
    'EarnedValueMethod', 'PredecessorLink', 'ExtendedAttribute', 'Active', 'Manual',
]

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

def set_child(task, tag, text):
    element = task.find(f'p:{tag}', NS)
    if element is None:
        element = ET.Element(f'{{{NAMESPACE}}}{tag}')
        my_pos = TASK_TAG_ORDER.index(tag)
        insert_at = len(task)
        for idx, child in enumerate(task):
            name = child.tag.split('}')[-1]
            if name in TASK_TAG_ORDER and TASK_TAG_ORDER.index(name) > my_pos:
                insert_at = idx
                break
        task.insert(insert_at, element)
    element.text = text

def remove_child(task, tag):
    element = task.find(f'p:{tag}', NS)
    if element is not None:
        task.remove(element)

def parse_dt(text, uid, tag):
    if not text:
        raise ValueError(f'Atividade UID {uid} sem {tag}.')
    return datetime.fromisoformat(text)

def back_to_weekday(moment):
    while moment.weekday() >= 5:
        moment -= timedelta(days=1)
    return moment

def load_schedule(root):
    """Lê tarefas, hierarquia (resumo/folha) e dependências."""
    tasks = root.findall('.//p:Task', NS)
    info, order = {}, []
    for task in tasks:
        uid = task.findtext('p:UID', namespaces=NS)
        if not uid:
            raise ValueError('Todas as atividades precisam ter um UID.')
        if uid in info:
            raise ValueError(f'UID duplicado: {uid}')
        level_text = task.findtext('p:OutlineLevel', namespaces=NS)
        if not level_text:
            raise ValueError(f'Atividade UID {uid} sem OutlineLevel.')
        if task.find('p:PercentComplete', NS) is None or task.find('p:PercentWorkComplete', NS) is None:
            raise ValueError(f'Atividade UID {uid} sem tag de percentual no modelo.')

        links = []
        for link in task.findall('p:PredecessorLink', NS):
            links.append((
                link.findtext('p:PredecessorUID', namespaces=NS),
                int(link.findtext('p:Type', default=str(FS), namespaces=NS)),
            ))

        info[uid] = {
            'task': task,
            'level': int(level_text),
            'summary': task.findtext('p:Summary', default='0', namespaces=NS) == '1',
            'milestone': task.findtext('p:Milestone', default='0', namespaces=NS) == '1',
            'start': parse_dt(task.findtext('p:Start', namespaces=NS), uid, 'Start'),
            'finish': parse_dt(task.findtext('p:Finish', namespaces=NS), uid, 'Finish'),
            'duration': duration_to_seconds(task.findtext('p:Duration', namespaces=NS), uid),
            'links': links,
            'leaves': [],
            'ancestors': [],
        }
        order.append(uid)

    stack = []
    for uid in order:
        level = info[uid]['level']
        while stack and info[stack[-1]]['level'] >= level:
            stack.pop()
        if info[uid]['summary']:
            stack.append(uid)
        else:
            info[uid]['ancestors'] = list(stack)
            for summary_uid in stack:
                info[summary_uid]['leaves'].append(uid)

    for uid in order:
        for pred_uid, _ in info[uid]['links']:
            if pred_uid not in info:
                raise ValueError(f'Atividade UID {uid} aponta para predecessora inexistente {pred_uid}.')

    return info, order

def leaves_of(info, uid):
    """Se for resumo, devolve as folhas dentro dele; senão, a própria tarefa."""
    return info[uid]['leaves'] if info[uid]['summary'] else [uid]

def effective_links(info, uid):
    """Links da própria folha + links herdados dos resumos ancestrais (como o MS Project faz)."""
    links = list(info[uid]['links'])
    for summary_uid in info[uid]['ancestors']:
        links.extend(info[summary_uid]['links'])
    return [(p, t) for p, t in dict.fromkeys(links)]

def dependency_order(info, order):
    """Ordem topológica REAL das folhas (predecessoras sempre antes das sucessoras)."""
    leaves = [uid for uid in order if not info[uid]['summary']]
    deps = {}
    for uid in leaves:
        wanted = set()
        for pred_uid, _ in effective_links(info, uid):
            wanted.update(leaves_of(info, pred_uid))
        wanted.discard(uid)
        deps[uid] = wanted

    result, state = [], {}

    def visit(uid):
        if state.get(uid) == 'done':
            return
        if state.get(uid) == 'visiting':
            raise ValueError(f'Ciclo de dependências envolvendo a atividade UID {uid}.')
        state[uid] = 'visiting'
        for dep in sorted(deps[uid], key=order.index):
            visit(dep)
        state[uid] = 'done'
        result.append(uid)

    for uid in leaves:
        visit(uid)
    return result

def planned_percentage(item, status_date):
    """% que a tarefa teria na data de status SE tudo ocorresse conforme o planejado."""
    start, finish = item['start'], item['finish']
    if finish <= status_date:
        return 100
    if start >= status_date:
        return 0
    elapsed = (status_date - start) / (finish - start)
    return max(1, min(99, round(elapsed * 100)))

def apply_noise(item, planned, status_date, rng):
    """Introduz atrasos na FRONTEIRA do trabalho (o que acabou de terminar ou está em andamento).

    Atrasos em tarefas concluídas há muito tempo travariam toda a cascata e
    deixariam todos os cronogramas "presos" no começo, qualquer que fosse o estágio.
    """
    if item['milestone'] or item['duration'] == 0 or planned == 0:
        return planned
    if planned == 100:
        recently_finished = status_date - item['finish'] <= timedelta(days=FRONTIER_DAYS)
        if recently_finished and rng.random() < PROB_SLIP_FINISH:
            return rng.randint(80, 99)
        return 100
    if rng.random() < PROB_SLIP_START:
        return 0
    return max(1, round(planned * rng.uniform(0.5, 1.0)))

def enforce_dependencies(item, percentage, links, info, final):
    """Aplica a regra de cascata: uma tarefa só avança se as predecessoras permitirem."""
    for pred_uid, link_type in links:
        pred_leaves = [u for u in leaves_of(info, pred_uid) if u != item['uid']]
        if not pred_leaves:
            continue
        done = all(final[u] == 100 for u in pred_leaves)
        started = any(final[u] > 0 for u in pred_leaves)

        if link_type == FS and not done:
            percentage = 0
        elif link_type == SS and not started:
            percentage = 0
        elif link_type == FF and not done:
            percentage = min(percentage, 99)
        elif link_type == SF and not started:
            percentage = min(percentage, 99)

    if (item['milestone'] or item['duration'] == 0) and percentage < 100:
        percentage = 0                          # marcos são binários
    return percentage

def compute_leaf_percentages(info, order, progress_stage, rng, noise):
    leaves = [uid for uid in order if not info[uid]['summary']]
    if progress_stage == 'complete':
        return {uid: 100 for uid in leaves}, None

    project_start = min(info[u]['start'] for u in leaves)
    project_finish = max(info[u]['finish'] for u in leaves)
    lower, upper = PROGRESS_STAGE_RANGES[progress_stage]
    status_date = project_start + (project_finish - project_start) * rng.uniform(lower, upper)

    final = {}
    for uid in dependency_order(info, order):
        item = info[uid]
        item['uid'] = uid
        percentage = planned_percentage(item, status_date)
        if noise:
            percentage = apply_noise(item, percentage, status_date, rng)
        final[uid] = enforce_dependencies(item, percentage, effective_links(info, uid), info, final)
    return final, status_date

def write_progress(item, percentage, is_summary):
    task = item['task']
    duration = item['duration']
    actual = round(duration * percentage / 100)
    remaining = duration - actual

    task.find('p:PercentComplete', NS).text = str(percentage)
    work = task.find('p:PercentWorkComplete', NS)
    work.text = '0' if item['milestone'] else str(percentage)

    if remaining > 0:
        set_child(task, 'RemainingDuration', format_duration(remaining))
    else:
        remove_child(task, 'RemainingDuration')

    # O ProjectLibre não exporta estes campos; o % é derivado de PercentComplete/Stop.
    for tag in ('ActualDuration', 'ActualStart', 'ActualFinish'):
        remove_child(task, tag)

    start, finish = item['start'], item['finish']
    if is_summary:
        if percentage == 100:
            set_child(task, 'Stop', finish.isoformat(timespec='seconds'))
        else:
            remove_child(task, 'Stop')
        return
    # Stop = até onde o trabalho avançou | Resume = de onde ele continua
    if percentage == 100:
        stop = finish
    elif percentage == 0:
        stop = None
    else:
        stop = back_to_weekday(start + timedelta(days=round((finish - start).days * percentage / 100)))
        stop = min(max(stop, start), finish)

    if stop is None:
        remove_child(task, 'Stop')
        set_child(task, 'Resume', start.isoformat(timespec='seconds'))
    else:
        set_child(task, 'Stop', stop.isoformat(timespec='seconds'))
        set_child(task, 'Resume', stop.isoformat(timespec='seconds'))

def assign_completion_percentages(root, progress_stage, rng, noise=True):
    info, order = load_schedule(root)
    leaf_pct, status_date = compute_leaf_percentages(info, order, progress_stage, rng, noise)

    for uid, percentage in leaf_pct.items():
        info[uid]['uid'] = uid
        write_progress(info[uid], percentage, is_summary=False)

    # Resumos: média ponderada pela duração. Só chega a 100 se TODAS as filhas forem 100.
    for uid in order:
        item = info[uid]
        if not item['summary']:
            continue
        children = item['leaves']
        total = sum(info[c]['duration'] for c in children)
        if children and all(leaf_pct[c] == 100 for c in children):
            percentage = 100
        elif total:
            weighted = sum(leaf_pct[c] * info[c]['duration'] for c in children)
            percentage = min(99, int(weighted / total))
            if percentage == 0 and any(leaf_pct[c] > 0 for c in children):
                percentage = 1
        else:
            percentage = 0
        write_progress(item, percentage, is_summary=True)

    return status_date

def validate_cascade(root):
    """Retorna lista de violações da regra de cascata no XML gerado."""
    info, _ = load_schedule(root)
    pct = {u: int(i['task'].findtext('p:PercentComplete', namespaces=NS)) for u, i in info.items()}
    errors = []
    for uid, item in info.items():
        if item['summary']:
            continue
        for pred_uid, link_type in effective_links(info, uid):
            preds = [u for u in leaves_of(info, pred_uid) if u != uid]
            if not preds:
                continue
            done = all(pct[u] == 100 for u in preds)
            started = any(pct[u] > 0 for u in preds)
            if link_type == FS and pct[uid] > 0 and not done:
                errors.append(f'UID {uid} ({pct[uid]}%) iniciou antes de 100% de {pred_uid} (FS)')
            if link_type == SS and pct[uid] > 0 and not started:
                errors.append(f'UID {uid} ({pct[uid]}%) iniciou antes de {pred_uid} iniciar (SS)')
            if link_type == FF and pct[uid] == 100 and not done:
                errors.append(f'UID {uid} terminou antes de {pred_uid} (FF)')
    return errors

def generate_synthetic_xml(source_path, output_path, project_name, progress_stage, rng, noise=True):
    tree = ET.parse(source_path)
    root = tree.getroot()

    assign_completion_percentages(root, progress_stage, rng, noise)

    errors = validate_cascade(root)
    if errors:
        raise RuntimeError(f'Cronograma {project_name} viola a cascata:\n' + '\n'.join(errors))

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

def create_synthetic_dataset(source_xml, output_dir, count, seed=None, noise=True):
    if count < 1:
        raise ValueError('A quantidade de cronogramas deve ser maior que zero.')
    rng = random.Random(seed)

    os.makedirs(output_dir, exist_ok=True)

    try:
        ET.parse(source_xml)
    except FileNotFoundError:
        raise FileNotFoundError(f'Arquivo modelo não encontrado: {source_xml}')

    progress_stages = ['early', 'middle', 'late'] if count >= 3 else []
    while len(progress_stages) < count:
        stage_options = ('early', 'middle', 'late', 'complete')
        if 'complete' in progress_stages:
            stage_options = ('early', 'middle', 'late')
        progress_stages.append(
            rng.choices(stage_options, weights=(3, 3, 3, 1)[:len(stage_options)], k=1)[0]
        )

    progress_stages = progress_stages[:count]
    rng.shuffle(progress_stages)

    start_seq = get_max_sequence(output_dir)

    for i in range(1, count + 1):
        current_seq = start_seq + i
        prefix = ''.join(rng.choices(string.ascii_uppercase, k=2))

        project_code = f'{prefix}-{current_seq:03d}-26'
        output_filename = os.path.join(output_dir, f'{project_code}.xml')
        progress_stage = progress_stages[i - 1]

        generate_synthetic_xml(source_xml, output_filename, project_code, progress_stage, rng, noise)

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
    parser.add_argument('--no-noise', action='store_true', help='Desliga os atrasos aleatórios (segue o plano à risca)')
    args = parser.parse_args()

    create_synthetic_dataset(args.source_xml, args.output_dir, args.count, args.seed, noise=not args.no_noise)