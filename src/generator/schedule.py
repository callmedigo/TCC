from .constants import FS, NS
from .xml_utils import duration_to_seconds, parse_dt


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
    """Links da própria folha + links herdados dos resumos ancestrais."""
    links = list(info[uid]['links'])
    for summary_uid in info[uid]['ancestors']:
        links.extend(info[summary_uid]['links'])
    return [(predecessor, link_type) for predecessor, link_type in dict.fromkeys(links)]


def dependency_order(info, order):
    """Ordem topológica REAL das folhas (predecessoras sempre antes das sucessoras)."""
    leaves = [uid for uid in order if not info[uid]['summary']]
    order_index = {uid: index for index, uid in enumerate(order)}
    dependencies = {}
    for uid in leaves:
        wanted = set()
        for pred_uid, _ in effective_links(info, uid):
            wanted.update(leaves_of(info, pred_uid))
        wanted.discard(uid)
        dependencies[uid] = wanted

    result, state = [], {}

    def visit(uid):
        if state.get(uid) == 'done':
            return
        if state.get(uid) == 'visiting':
            raise ValueError(f'Ciclo de dependências envolvendo a atividade UID {uid}.')
        state[uid] = 'visiting'
        for dependency in sorted(dependencies[uid], key=order_index.__getitem__):
            visit(dependency)
        state[uid] = 'done'
        result.append(uid)

    for uid in leaves:
        visit(uid)
    return result
