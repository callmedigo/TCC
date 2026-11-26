import xml.etree.ElementTree as ET
from datetime import datetime
from .constants import NS
from .progress import assign_completion_percentages, validate_cascade

SCHEDULE_DATE_TAGS = {
    'StartDate',
    'FinishDate',
    'CurrentDate',
    'Start',
    'Finish',
    'Stop',
    'Resume',
    'ConstraintDate',
    'FromDate',
    'ToDate',
}

def shift_schedule_dates(root, opening_date):
    start_date_tag = root.find('p:StartDate', NS)
    if start_date_tag is None or not start_date_tag.text:
        raise ValueError('O modelo XML precisa ter a tag StartDate do projeto.')

    original_start = datetime.fromisoformat(start_date_tag.text)
    offset = opening_date - original_start
    for element in root.iter():
        tag = element.tag.rsplit('}', 1)[-1]
        if tag not in SCHEDULE_DATE_TAGS or not element.text:
            continue
        value = datetime.fromisoformat(element.text)
        if tag == 'ConstraintDate' and value.year == 1970:
            continue
        element.text = (value + offset).isoformat()

def generate_synthetic_xml(
    source_path, output_path, project_name, progress_stage, rng, noise=True,
    opening_date=None,
):
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

    if opening_date is not None:
        shift_schedule_dates(root, opening_date)

    tree.write(output_path, encoding='utf-8', xml_declaration=True)