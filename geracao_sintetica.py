import os
import random
import argparse
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

NAMESPACE = 'http://schemas.microsoft.com/project'
NS = {'p': NAMESPACE}
ET.register_namespace('', NAMESPACE)

DATE_TAGS = [
    'Start',
    'Finish',
    'Resume',
    'CreateDate',
    'ConstraintDate',
    'Stop',
    'BaselineStart',
    'BaselineFinish',
]


def parse_date(value):
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def format_date(value):
    return value.isoformat(timespec='seconds') if value is not None else None


def shift_date(date_value, min_days=-5, max_days=5):
    if date_value is None:
        return None
    delta = random.randint(min_days, max_days)
    return date_value + timedelta(days=delta)


def mutate_task_dates(task, variation_days, allow_variation):
    for tag_name in DATE_TAGS:
        tag = task.find(f'p:{tag_name}', NS)
        if tag is not None and tag.text:
            parsed = parse_date(tag.text)
            if parsed is not None:
                if allow_variation:
                    new_date = shift_date(parsed, -variation_days, variation_days)
                else:
                    new_date = shift_date(parsed, -1, 1)
                tag.text = format_date(new_date)


def task_name(task):
    name = task.find('p:Name', NS)
    return name.text.strip() if name is not None and name.text else ''


def generate_synthetic_xml(source_path, output_path, variation_days):
    tree = ET.parse(source_path)
    root = tree.getroot()

    gate2_found = False
    for task in root.findall('.//p:Task', NS):
        name = task_name(task).upper()
        if 'GATE 2' in name:
            gate2_found = True

        allow_variation = not gate2_found
        mutate_task_dates(task, variation_days, allow_variation)

    project_start = root.find('p:StartDate', NS)
    project_finish = root.find('p:FinishDate', NS)
    if project_start is not None and project_start.text:
        project_start_date = parse_date(project_start.text)
        if project_start_date:
            project_start.text = format_date(shift_date(project_start_date, -variation_days, variation_days))
    if project_finish is not None and project_finish.text:
        project_finish_date = parse_date(project_finish.text)
        if project_finish_date:
            project_finish.text = format_date(shift_date(project_finish_date, -variation_days, variation_days))

    tree.write(output_path, encoding='utf-8', xml_declaration=True)


def create_synthetic_dataset(source_xml, output_dir, count, variation_days, seed=None):
    if seed is not None:
        random.seed(seed)

    os.makedirs(output_dir, exist_ok=True)
    for i in range(1, count + 1):
        output_filename = os.path.join(output_dir, f'sintetico_{i}.xml')
        generate_synthetic_xml(source_xml, output_filename, variation_days)
        print(f'Gerado: {output_filename}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Gerar arquivos XML sintéticos a partir de um modelo Project XML.'
    )
    parser.add_argument('source_xml', help='Arquivo XML de entrada, por exemplo Teste1.xml')
    parser.add_argument('--count', type=int, default=5, help='Número de arquivos sintéticos a gerar')
    parser.add_argument('--variation-days', type=int, default=5, help='Variação máxima em dias para as datas antes do GATE 2')
    parser.add_argument('--output-dir', default='Dados', help='Pasta de saída onde os arquivos .xml serão criados')
    parser.add_argument('--seed', type=int, default=None, help='Semente para gerar resultados repetíveis')
    args = parser.parse_args()

    create_synthetic_dataset(
        args.source_xml,
        args.output_dir,
        args.count,
        args.variation_days,
        args.seed,
    )
