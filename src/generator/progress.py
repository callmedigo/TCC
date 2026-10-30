from datetime import timedelta

from .constants import (
    FF,
    FRONTIER_DAYS,
    FS,
    NS,
    PROB_SLIP_FINISH,
    PROB_SLIP_START,
    PROGRESS_STAGE_RANGES,
    SF,
    SS,
)
from .schedule import (
    dependency_order,
    effective_links,
    leaves_of,
    load_schedule,
)
from .xml_utils import back_to_weekday, format_duration, remove_child, set_child


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
    """Introduz atrasos na fronteira do trabalho, em tarefas recém-finalizadas ou em andamento.

    Atrasos antigos travariam a cascata no início, independentemente do estágio.
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
        pred_leaves = [uid for uid in leaves_of(info, pred_uid) if uid != item['uid']]
        if not pred_leaves:
            continue
        done = all(final[uid] == 100 for uid in pred_leaves)
        started = any(final[uid] > 0 for uid in pred_leaves)

        if link_type == FS and not done:
            percentage = 0
        elif link_type == SS and not started:
            percentage = 0
        elif link_type == FF and not done:
            percentage = min(percentage, 99)
        elif link_type == SF and not started:
            percentage = min(percentage, 99)

    if (item['milestone'] or item['duration'] == 0) and percentage < 100:
        percentage = 0
    return percentage


def compute_leaf_percentages(info, order, progress_stage, rng, noise):
    leaves = [uid for uid in order if not info[uid]['summary']]
    if progress_stage == 'complete':
        return {uid: 100 for uid in leaves}, None

    project_start = min(info[uid]['start'] for uid in leaves)
    project_finish = max(info[uid]['finish'] for uid in leaves)
    lower, upper = PROGRESS_STAGE_RANGES[progress_stage]
    status_date = project_start + (project_finish - project_start) * rng.uniform(lower, upper)

    final = {}
    for uid in dependency_order(info, order):
        item = info[uid]
        item['uid'] = uid
        percentage = planned_percentage(item, status_date)
        if noise:
            percentage = apply_noise(item, percentage, status_date, rng)
        final[uid] = enforce_dependencies(
            item, percentage, effective_links(info, uid), info, final
        )
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

    # O ProjectLibre não exporta estes campos; o percentual vem de PercentComplete/Stop.
    for tag in ('ActualDuration', 'ActualStart', 'ActualFinish'):
        remove_child(task, tag)

    start, finish = item['start'], item['finish']
    if is_summary:
        if percentage == 100:
            set_child(task, 'Stop', finish.isoformat(timespec='seconds'))
        else:
            remove_child(task, 'Stop')
        return

    # Stop marca até onde o trabalho avançou; Resume indica de onde ele continua.
    if percentage == 100:
        stop = finish
    elif percentage == 0:
        stop = None
    else:
        stop = back_to_weekday(
            start + timedelta(days=round((finish - start).days * percentage / 100))
        )
        stop = min(max(stop, start), finish)

    if stop is None:
        remove_child(task, 'Stop')
        set_child(task, 'Resume', start.isoformat(timespec='seconds'))
    else:
        set_child(task, 'Stop', stop.isoformat(timespec='seconds'))
        set_child(task, 'Resume', stop.isoformat(timespec='seconds'))


def assign_completion_percentages(root, progress_stage, rng, noise=True):
    info, order = load_schedule(root)
    leaf_pct, status_date = compute_leaf_percentages(
        info, order, progress_stage, rng, noise
    )

    for uid, percentage in leaf_pct.items():
        info[uid]['uid'] = uid
        write_progress(info[uid], percentage, is_summary=False)

    for uid in order:
        item = info[uid]
        if not item['summary']:
            continue
        children = item['leaves']
        total = sum(info[child]['duration'] for child in children)
        if children and all(leaf_pct[child] == 100 for child in children):
            percentage = 100
        elif total:
            weighted = sum(
                leaf_pct[child] * info[child]['duration'] for child in children
            )
            percentage = min(99, int(weighted / total))
            if percentage == 0 and any(leaf_pct[child] > 0 for child in children):
                percentage = 1
        else:
            percentage = 0
        write_progress(item, percentage, is_summary=True)

    return status_date


def validate_cascade(root):
    """Retorna lista de violações da regra de cascata no XML gerado."""
    info, _ = load_schedule(root)
    percentages = {
        uid: int(item['task'].findtext('p:PercentComplete', namespaces=NS))
        for uid, item in info.items()
    }
    errors = []
    for uid, item in info.items():
        if item['summary']:
            continue
        for pred_uid, link_type in effective_links(info, uid):
            predecessors = [leaf for leaf in leaves_of(info, pred_uid) if leaf != uid]
            if not predecessors:
                continue
            done = all(percentages[leaf] == 100 for leaf in predecessors)
            started = any(percentages[leaf] > 0 for leaf in predecessors)
            if link_type == FS and percentages[uid] > 0 and not done:
                errors.append(
                    f'UID {uid} ({percentages[uid]}%) iniciou antes de 100% de {pred_uid} (FS)'
                )
            if link_type == SS and percentages[uid] > 0 and not started:
                errors.append(
                    f'UID {uid} ({percentages[uid]}%) iniciou antes de {pred_uid} iniciar (SS)'
                )
            if link_type == FF and percentages[uid] == 100 and not done:
                errors.append(f'UID {uid} terminou antes de {pred_uid} (FF)')
    return errors
