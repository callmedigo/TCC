import csv
from datetime import datetime, timedelta
from pathlib import Path
import random

MASTER_LIST_COLUMNS = ('Código', 'Projeto', 'Data Abertura')
PROJECT_NAME_PARTS = (
    'Aurora',
    'Horizonte',
    'Ipê',
    'Origem',
    'Essência',
    'Conexão',
    'Raízes',
    'Caminhos',
    'Pioneiro',
    'Inovação',
    'Alvorada',
    'Integração',
    'Expansão',
    'Renovação',
    'Semente',
    'Equilíbrio',
)

def read_master_projects(master_list_path):
    path = Path(master_list_path)
    if not path.is_file():
        return []

    with path.open('r', encoding='utf-8-sig', newline='') as master_file:
        reader = csv.DictReader(master_file)
        missing_columns = set(MASTER_LIST_COLUMNS) - set(reader.fieldnames or ())
        if missing_columns:
            missing = ', '.join(sorted(missing_columns))
            raise ValueError(
                f'A lista mestre {path} não contém as colunas obrigatórias: {missing}.'
            )
        return list(reader)

def generate_project_name(rng, existing_names):
    available_names = {
        f'Projeto {first} {second}'
        for first in PROJECT_NAME_PARTS
        for second in PROJECT_NAME_PARTS
        if first != second
    } - existing_names
    if not available_names:
        raise ValueError('Não há nomes únicos disponíveis para novos projetos.')
    return rng.choice(sorted(available_names))

def generate_opening_date(source_start, rng):
    """Escolhe uma data em outra semana do ano, preservando o dia da semana do modelo."""
    return source_start + timedelta(weeks=rng.randint(0, 51))

def append_master_project(master_list_path, project_code, project_name, opening_date):
    path = Path(master_list_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_projects = read_master_projects(path)
    if any(project['Código'] == project_code for project in existing_projects):
        raise ValueError(f'O código {project_code} já existe na lista mestre {path}.')

    needs_header = not path.exists() or path.stat().st_size == 0
    columns = MASTER_LIST_COLUMNS
    if not needs_header:
        with path.open('r', encoding='utf-8-sig', newline='') as master_file:
            columns = csv.DictReader(master_file).fieldnames
    with path.open('a', encoding='utf-8-sig', newline='') as master_file:
        writer = csv.DictWriter(master_file, fieldnames=columns)
        if needs_header:
            writer.writeheader()
        writer.writerow({
            'Código': project_code,
            'Projeto': project_name,
            'Data Abertura': opening_date.date().isoformat(),
            **{column: '' for column in columns if column not in MASTER_LIST_COLUMNS},
        })

def latest_master_sequence(master_list_path):
    sequence = 0
    for project in read_master_projects(master_list_path):
        code = project['Código']
        if len(code) == 9 and code[:2].isalpha() and code[2] == '-' and code[6:] == '-26':
            try:
                sequence = max(sequence, int(code[3:6]))
            except ValueError:
                continue
    return sequence