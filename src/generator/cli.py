import argparse
from pathlib import Path

from .dataset import DEFAULT_MASTER_LIST_PATH, create_synthetic_dataset


def main():
    project_root = Path(__file__).resolve().parents[2]
    default_source = project_root / 'data' / 'raw' / 'Cronograma Completo XML.xml'
    default_output = project_root / 'data' / 'synthetic'

    parser = argparse.ArgumentParser(
        description='Gerar arquivos XML sintéticos a partir de um modelo Project XML.'
    )
    parser.add_argument(
        'source_xml', nargs='?', default=str(default_source), help='Arquivo XML de entrada'
    )
    parser.add_argument(
        '--count', type=int, default=5, help='Número de arquivos sintéticos a gerar'
    )
    parser.add_argument(
        '--output-dir',
        default=str(default_output),
        help='Pasta de saída onde os arquivos .xml serão criados',
    )
    parser.add_argument(
        '--master-list',
        default=str(DEFAULT_MASTER_LIST_PATH),
        help='Arquivo CSV da lista mestre de projetos',
    )
    parser.add_argument('--seed', type=int, default=None, help='Semente')
    parser.add_argument(
        '--no-noise',
        action='store_true',
        help='Desliga os atrasos aleatórios (segue o plano à risca)',
    )
    args = parser.parse_args()

    create_synthetic_dataset(
        args.source_xml,
        args.output_dir,
        args.count,
        args.seed,
        noise=not args.no_noise,
        master_list_path=args.master_list,
    )
