from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from .constants import DURATION_PATTERN, NS, NAMESPACE, TASK_TAG_ORDER
ET.register_namespace('', NAMESPACE)

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
        tag_position = TASK_TAG_ORDER.index(tag)
        insert_at = len(task)
        for index, child in enumerate(task):
            name = child.tag.split('}')[-1]
            if name in TASK_TAG_ORDER and TASK_TAG_ORDER.index(name) > tag_position:
                insert_at = index
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