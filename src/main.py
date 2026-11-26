import argparse
import logging
import subprocess
import sys
from pathlib import Path

if __package__:
    from .extraction.extracao import CAMINHOS_ENTRADA, PASTA_SAIDA, gerar_relatorios
else:
    from extraction.extracao import CAMINHOS_ENTRADA, PASTA_SAIDA, gerar_relatorios

BSC_DIR = Path(__file__).resolve().parent / "bsc"
ETAPAS_BSC = ("bsc_previsto.py", "bsc_realizado.py", "bsc_cons.py")

def executar_etapas_bsc():
    """Roda previsto, realizado e consolidação (ICPP, IPP e IAP) em sequência."""
    for script in ETAPAS_BSC:
        subprocess.run([sys.executable, str(BSC_DIR / script), "calculate"], check=True)

def main(argv=None):
    parser = argparse.ArgumentParser(description="Extrai os cronogramas e, opcionalmente, calcula os indicadores BSC.")
    parser.add_argument(
        "--completo",
        action="store_true",
        help="Após a extração, calcula o BSC previsto/realizado e os indicadores ICPP, IPP e IAP.",
    )
    args = parser.parse_args(argv)

    logger = logging.getLogger(__name__)
    logger.info("Iniciando processamento dos cronogramas.")
    gerar_relatorios(CAMINHOS_ENTRADA, PASTA_SAIDA)
    logger.info("Processamento dos cronogramas concluído.")
    if args.completo:
        executar_etapas_bsc()
        logger.info("Indicadores BSC calculados.")

if __name__ == "__main__":
    main()
