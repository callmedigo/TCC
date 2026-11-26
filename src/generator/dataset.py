import os
import random
import re
import string
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from .generation import generate_synthetic_xml
from .project_metadata import (
    append_master_project,
    generate_opening_date,
    generate_project_name,
    latest_master_sequence,
    read_master_projects,
)

DEFAULT_MASTER_LIST_PATH = (
    Path(__file__).resolve().parents[2]
    / 'data'
    / 'processed'
    / 'lista_mestre_projetos.csv'
)

def get_max_sequence(output_dir, master_list_path=None):
    """Lê a pasta de saída e descobre qual foi o último número gerado."""
    max_sequence = 0
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            match = re.search(r'-(\d{3})-26\.xml$', filename)
            if match:
                max_sequence = max(max_sequence, int(match.group(1)))
    if master_list_path is not None:
        max_sequence = max(max_sequence, latest_master_sequence(master_list_path))
    return max_sequence

def create_synthetic_dataset(
    source_xml, output_dir, count, seed=None, noise=True, master_list_path=None
):
    if count < 1:
        raise ValueError('A quantidade de cronogramas deve ser maior que zero.')
    rng = random.Random(seed)
    os.makedirs(output_dir, exist_ok=True)

    try:
        source_root = ET.parse(source_xml).getroot()
    except FileNotFoundError:
        raise FileNotFoundError(f'Arquivo modelo não encontrado: {source_xml}')

    source_start_text = source_root.findtext('{http://schemas.microsoft.com/project}StartDate')
    if not source_start_text:
        raise ValueError('O modelo XML precisa ter a tag StartDate do projeto.')
    source_start = datetime.fromisoformat(source_start_text)

    master_path = Path(master_list_path) if master_list_path else DEFAULT_MASTER_LIST_PATH
    existing_projects = read_master_projects(master_path)
    existing_names = {project['Projeto'] for project in existing_projects}

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
    start_sequence = get_max_sequence(output_dir, master_path)

    for index in range(1, count + 1):
        current_sequence = start_sequence + index
        prefix = ''.join(rng.choices(string.ascii_uppercase, k=2))

        project_code = f'{prefix}-{current_sequence:03d}-26'
        output_filename = os.path.join(output_dir, f'{project_code}.xml')
        progress_stage = progress_stages[index - 1]
        project_name = generate_project_name(rng, existing_names)
        existing_names.add(project_name)
        opening_date = generate_opening_date(source_start, rng)

        generate_synthetic_xml(
            source_xml,
            output_filename,
            project_name,
            progress_stage,
            rng,
            noise,
            opening_date=opening_date,
        )
        append_master_project(master_path, project_code, project_name, opening_date)

        print(
            f'Gerado: {output_filename} | Estágio: {progress_stage} | '
            f'Projeto: {project_name} | Código: {project_code}'
        )