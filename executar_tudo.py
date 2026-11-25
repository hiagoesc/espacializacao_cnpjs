"""Roda as etapas do fluxo (scripts/NN_*.ipynb ou NN_*.py) em ordem.

Uso (no terminal, na pasta do projeto, com o ambiente ativado):
    python executar_tudo.py                  # todas as etapas
    python executar_tudo.py --de 05          # da 05 em diante
    python executar_tudo.py --de 02 --ate 04 # da 02 até a 04
    python executar_tudo.py --ciclo          # só as etapas de execucao.ciclo do config.yaml
    python executar_tudo.py --listar         # só mostra as etapas encontradas

Cada notebook executado (com as saídas) é salvo em 03_processamento/notebooks_executados/.
A execução para no primeiro erro. Os logs de cada etapa ficam em 03_processamento/logs/.
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent                      # pasta deste arquivo = raiz do projeto
PASTA_SCRIPTS = RAIZ / "scripts"
PASTA_EXECUTADOS = RAIZ / "03_processamento" / "notebooks_executados"


def listar_etapas():
    """Etapas do fluxo: arquivos 'NN_nome.ipynb' ou 'NN_nome.py' em scripts/ (NN = 2 dígitos), em ordem."""
    etapas = [p for p in PASTA_SCRIPTS.iterdir() if re.match(r"^\d{2}_.+\.(ipynb|py)$", p.name)]
    return sorted(etapas, key=lambda p: p.name)


def rodar(etapa: Path):
    """Executa uma etapa. Notebook: via nbconvert, salvando a cópia executada. Script .py: via python."""
    if etapa.suffix == ".ipynb":
        PASTA_EXECUTADOS.mkdir(parents=True, exist_ok=True)
        comando = [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
                   "--ExecutePreprocessor.timeout=-1", "--output-dir", str(PASTA_EXECUTADOS),
                   "--output", etapa.name, str(etapa)]
    else:
        comando = [sys.executable, str(etapa)]
    return subprocess.run(comando, cwd=PASTA_SCRIPTS).returncode


def main():
    parser = argparse.ArgumentParser(description="Roda as etapas do projeto em ordem.")
    parser.add_argument("--de", help="número da primeira etapa (ex.: 05)")
    parser.add_argument("--ate", help="número da última etapa (ex.: 06)")
    parser.add_argument("--ciclo", action="store_true", help="roda só as etapas de execucao.ciclo do config.yaml")
    parser.add_argument("--listar", action="store_true", help="só lista as etapas")
    args = parser.parse_args()

    etapas = listar_etapas()
    if args.ciclo:
        with open(RAIZ / "config.yaml", encoding="utf-8") as arq:
            ciclo = [str(n).zfill(2) for n in yaml.safe_load(arq)["execucao"]["ciclo"]]
        etapas = [e for e in etapas if e.name[:2] in ciclo]
    if args.de:
        etapas = [e for e in etapas if e.name[:2] >= args.de.zfill(2)]
    if args.ate:
        etapas = [e for e in etapas if e.name[:2] <= args.ate.zfill(2)]

    print(f"Etapas selecionadas ({len(etapas)}):")
    for e in etapas:
        print("  -", e.name)
    if args.listar or not etapas:
        return

    inicio_total = time.time()
    for i, etapa in enumerate(etapas, start=1):
        print(f"\n[{i}/{len(etapas)}] Rodando {etapa.name}...", flush=True)
        inicio = time.time()
        if rodar(etapa) != 0:
            print(f"ERRO em {etapa.name}. Execução interrompida. Veja o log em 03_processamento/logs/.")
            sys.exit(1)
        print(f"[{i}/{len(etapas)}] {etapa.name} concluída em {time.time() - inicio:.0f}s!")
    print(f"\nTodas as etapas concluídas em {time.time() - inicio_total:.0f}s!")


if __name__ == "__main__":
    main()
