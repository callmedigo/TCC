import logging

if __package__:
    from .extraction.extracao import CAMINHOS_ENTRADA, PASTA_SAIDA, gerar_relatorios
else:
    from extraction.extracao import CAMINHOS_ENTRADA, PASTA_SAIDA, gerar_relatorios


def main():
    logger = logging.getLogger(__name__)
    logger.info("Iniciando processamento dos cronogramas.")
    gerar_relatorios(CAMINHOS_ENTRADA, PASTA_SAIDA)
    logger.info("Processamento dos cronogramas concluído.")


if __name__ == "__main__":
    main()
