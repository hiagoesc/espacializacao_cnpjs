"""Arquivos editados à mão (02_dados_editados): existência, prioridade sobre o bruto e backup.

Regra do padrão:
1. existe a versão editada? -> usa ela;
2. não existe? -> o notebook indicado em 'gerado_por' cria a versão inicial (uma vez só);
3. antes de regravar um editado, faz cópia datada em 02_dados_editados/_backup.
"""
import logging
import shutil
from datetime import datetime
from pathlib import Path

log = logging.getLogger("fontes")


def existe_editado(cfg, chave: str) -> bool:
    """True se o arquivo editado 'editados.<chave>' já existe."""
    return cfg.caminho("editados." + chave).exists()


def caminho_editado(cfg, chave: str, obrigatorio: bool = True):
    """Caminho do arquivo editado. Se não existir e for obrigatório, para com a instrução de qual notebook rodar."""
    caminho = cfg.caminho("editados." + chave)
    if caminho.exists():
        log.info("Usando a versão editada: %s", caminho.name)
        return caminho
    gerador = cfg._buscar("editados." + chave).get("gerado_por", "?")
    if obrigatorio:
        raise FileNotFoundError(f"{caminho} não existe. Rode antes o notebook {gerador} (ele cria a versão inicial).")
    log.warning("Arquivo editado %s ainda não existe (é criado pelo notebook %s).", caminho.name, gerador)
    return None


def ler_processamento(cfg, chave: str):
    """Lê um intermediário (Parquet) de 'processamento.<chave>'. Se não existir, para dizendo qual etapa rodar antes."""
    import pandas as pd                                # tabelas (só carregado quando a função é usada)
    caminho = cfg.caminho("processamento." + chave)
    if not caminho.exists():
        etapa = caminho.parent.name                    # a subpasta tem o mesmo nome do notebook que a gera
        raise FileNotFoundError(f"{caminho} não existe. Rode antes o notebook {etapa}.")
    log.info("Lendo %s (de %s)...", caminho.name, caminho.parent.name)
    df = pd.read_parquet(caminho)
    log.info("%s lido! %d linhas | %d colunas.", caminho.name, len(df), df.shape[1])
    return df


def gravar_processamento(cfg, chave: str, df) -> Path:
    """Grava um intermediário em Parquet em 'processamento.<chave>' (a numeração das linhas precisa ser 0, 1, 2...)."""
    import pandas as pd
    caminho = cfg.caminho("processamento." + chave)
    # O Parquet não guarda a numeração das linhas: ela precisa ser a padrão, senão as tabelas se desalinham depois.
    if not df.index.equals(pd.RangeIndex(len(df))):
        raise ValueError(f"[{chave}] a numeração das linhas não é a padrão (0, 1, 2...). Nada foi gravado.")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    log.info("Gravando %s...", caminho.name)
    df.to_parquet(caminho, engine="pyarrow", compression="snappy", index=False)
    log.info("%s gravado! %d linhas | %.1f MB.", caminho.name, len(df), caminho.stat().st_size / 1e6)
    return caminho


def backup(cfg, caminho) -> Path:
    """Copia um arquivo para 02_dados_editados/_backup com data e hora no nome. Devolve o caminho da cópia."""
    caminho = Path(caminho)
    destino = cfg.pasta("backup") / f"{caminho.stem}_{datetime.now():%Y%m%d_%H%M%S}{caminho.suffix}"
    shutil.copy2(caminho, destino)
    log.info("Backup criado: %s", destino.name)
    return destino
