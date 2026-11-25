"""Log padrão: mensagens na tela E gravadas em 03_processamento/logs/AAAA-MM-DD_HHMM_<etapa>.log.

Convenção: texto que termina em "..." = etapa começando; texto que termina em "!" = etapa concluída.
"""
import logging
import sys
from datetime import datetime

FORMATO = "%(asctime)s | %(levelname)-7s | %(message)s"


def iniciar_log(nome_etapa: str, cfg) -> logging.Logger:
    """Configura o log (tela + arquivo) para uma etapa e devolve o logger.

    Pode ser chamado de novo na mesma sessão do Jupyter: os destinos anteriores são trocados.
    """
    raiz = logging.getLogger()                       # logger principal (todos os outros passam por ele)
    for destino in list(raiz.handlers):              # remove destinos de uma execução anterior
        raiz.removeHandler(destino)
        destino.close()
    raiz.setLevel(logging.INFO)
    formato = logging.Formatter(FORMATO, datefmt="%H:%M:%S")

    tela = logging.StreamHandler(sys.stdout)         # mensagens na tela (célula do notebook)
    tela.setFormatter(formato)
    raiz.addHandler(tela)

    arquivo_log = cfg.pasta("logs") / f"{datetime.now():%Y-%m-%d_%H%M}_{nome_etapa}.log"
    em_arquivo = logging.FileHandler(arquivo_log, encoding="utf-8")   # as mesmas mensagens no arquivo
    em_arquivo.setFormatter(formato)
    raiz.addHandler(em_arquivo)

    log = logging.getLogger(nome_etapa)
    log.info("Log iniciado: %s", arquivo_log.name)
    return log


def formatar_tempo(segundos) -> str:
    """Transforma segundos em um texto fácil de ler, como '3min 25s' (para os logs de tempo das etapas)."""
    minutos, resto = divmod(int(segundos), 60)       # minutos inteiros e os segundos que sobraram
    return f"{minutos}min {resto}s"
