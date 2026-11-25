"""Cache de leitura de bases pesadas: Parquet + manifesto (JSON) na pasta da etapa, em 03_processamento.

Ideia: ler 20 GB da Receita leva muito tempo. Na primeira leitura, a tabela pronta é gravada em Parquet,
junto com um "manifesto" que descreve de onde ela veio (nome, tamanho e data dos arquivos de origem),
com quais parâmetros foi lida e qual versão da lógica de leitura foi usada. Nas rodadas seguintes,
se nada disso mudou, a tabela é carregada do Parquet em segundos. Se algo mudou, o bruto é lido de novo.

Como 03_processamento é descartável, apagar a pasta só obriga a reler os brutos.

Uso nos notebooks:
    cache = CacheTabelas(pasta, versoes, descrever, forcar, idade_maxima_dias, colunas_proibidas)
    usar, motivo = cache.verificar("df_estab")
    df = cache.carregar("df_estab") se usar, senão lê o bruto e chama cache.salvar("df_estab", df)
"""
import datetime
import importlib.util
import json
import logging
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .registro import formatar_tempo

log = logging.getLogger("cache")


def impressao_arquivos(pasta, padrao):
    """Lista nome, tamanho e data de modificação dos arquivos da pasta que seguem o padrão (ordem alfabética)."""
    # Lista onde guardamos uma linha por arquivo.
    lista = []
    # Passa por cada arquivo (só arquivos, não pastas), em ordem alfabética.
    for arquivo in sorted(p for p in Path(pasta).glob(padrao) if p.is_file()):
        # stat() devolve as informações do arquivo (tamanho, datas).
        info = arquivo.stat()
        lista.append({
            "nome": arquivo.name,
            "tamanho_bytes": int(info.st_size),
            "modificado": datetime.datetime.fromtimestamp(info.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return lista


def assinatura_valores(serie):
    """Impressão digital curta do CONJUNTO de valores distintos de uma coluna (não depende da ordem das linhas)."""
    # Valores distintos, sem vazios.
    valores = pd.Series(serie.dropna().unique())
    # Número de 64 bits para cada valor (a regra é sempre a mesma, então o resultado se repete em outra sessão).
    hashes = pd.util.hash_pandas_object(valores, index=False).to_numpy(dtype="uint64")
    # Soma dos números (a soma não depende da ordem), guardada como texto para caber no JSON.
    soma = int(np.sum(hashes, dtype=np.uint64)) if len(hashes) else 0
    return {"distintos": int(len(valores)), "hash": str(soma)}


def normalizar_json(valor):
    """Passa um valor por ida e volta ao JSON, para comparar sem diferença boba (lista x tupla, int x numpy)."""
    return json.loads(json.dumps(valor, sort_keys=True, default=str))


def pyarrow_instalado() -> bool:
    """True se a biblioteca pyarrow (que lê e grava Parquet) está instalada."""
    return importlib.util.find_spec("pyarrow") is not None


class CacheTabelas:
    """Cache das tabelas lidas por um notebook (uma pasta, várias tabelas, cada uma com o seu manifesto)."""

    def __init__(self, pasta, versoes, descrever, forcar=(), idade_maxima_dias=None, colunas_proibidas=None):
        """
        pasta: onde ficam os arquivos do cache (a pasta da etapa em 03_processamento).
        versoes: versão da lógica de cada tabela, ex.: {"df_estab": 1}. Aumentar o número invalida o cache.
        descrever: função nome -> (origem, parâmetros, dependências); é isso que decide se o cache vale.
        forcar: tabelas a reler mesmo com cache válido (ex.: ["df_lotes"] ou ["todos"]).
        idade_maxima_dias: idade máxima por tabela, ex.: {"df_lotes": 30} (ausente ou None = sem limite).
        colunas_proibidas: colunas que NUNCA podem ir para o disco, por tabela (dados pessoais).
        """
        self.pasta = Path(pasta)                          # pasta do cache
        self.versoes = dict(versoes)                      # versão da lógica de cada tabela
        self.descrever = descrever                        # função que descreve origem/parâmetros/dependências
        self.forcar = list(forcar or [])                  # tabelas a reler à força
        self.idade_maxima_dias = dict(idade_maxima_dias or {})
        self.colunas_proibidas = dict(colunas_proibidas or {})

    # ------------------------------------------------------------------ caminhos e descrição
    def caminhos(self, nome):
        """Devolve o caminho do arquivo Parquet e o do manifesto de uma tabela."""
        return self.pasta / f"{nome}.parquet", self.pasta / f"{nome}.manifesto.json"

    def descricao_atual(self, nome, origem, parametros, depende_de):
        """Monta a parte do manifesto que decide se o cache ainda vale."""
        return {
            "versao_logica": self.versoes[nome],
            "origem": normalizar_json(origem),
            "parametros": normalizar_json(parametros),
            "depende_de": normalizar_json(depende_de or {}),
        }

    # ------------------------------------------------------------------ conferência
    def valido(self, nome, origem, parametros, depende_de=None, idade_maxima_dias=None):
        """
        Diz se o cache de uma tabela ainda vale. Devolve (verdadeiro/falso, motivo).
        Vale quando: os dois arquivos existem, e versão da lógica, origem, parâmetros e dependências são iguais
        aos de quando foi gravado (e, se pedido, o cache não é mais velho que idade_maxima_dias).
        """
        caminho_parquet, caminho_manifesto = self.caminhos(nome)
        # Sem os dois arquivos, não há cache.
        if not (caminho_parquet.is_file() and caminho_manifesto.is_file()):
            return False, "ainda não existe cache"
        # Lê o manifesto; se estiver estragado, o cache não vale.
        try:
            manifesto = json.loads(caminho_manifesto.read_text(encoding="utf-8"))
        except Exception:
            return False, "manifesto ilegível"
        atual = self.descricao_atual(nome, origem, parametros, depende_de)
        # Compara cada parte, na ordem; a primeira diferente vira o motivo.
        for chave, motivo in [("versao_logica", "a versão da lógica mudou"),
                              ("origem", "os arquivos de origem mudaram"),
                              ("parametros", "os parâmetros mudaram"),
                              ("depende_de", "a tabela da qual ele depende mudou")]:
            if normalizar_json(manifesto.get(chave)) != atual[chave]:
                return False, motivo
        # Idade máxima (só se pedida).
        if idade_maxima_dias is not None:
            gravado = datetime.datetime.strptime(manifesto["gravado_em"], "%Y-%m-%d %H:%M:%S")
            idade = (datetime.datetime.now() - gravado).days
            if idade > idade_maxima_dias:
                return False, f"o cache tem {idade} dias (máximo: {idade_maxima_dias})"
        return True, f"cache de {manifesto['gravado_em']}"

    def verificar(self, nome):
        """Diz se o cache da tabela pode ser usado agora. Devolve (verdadeiro/falso, motivo)."""
        # Sem a biblioteca pyarrow não há como ler o Parquet: lê os arquivos originais.
        if not pyarrow_instalado():
            return False, "a biblioteca pyarrow não está instalada (py -m pip install --user pyarrow)"
        # Reprocessamento pedido no config.yaml.
        if "todos" in self.forcar or nome in self.forcar:
            return False, "reprocessamento pedido em parametros.cache.forcar_reprocessar (config.yaml)"
        origem, parametros, depende_de = self.descrever(nome)
        # Se a pasta de origem não tem nenhum arquivo, o cache não pode ser conferido: lê de novo (e o notebook acusa o erro).
        if isinstance(origem, list) and not origem:
            return False, "nenhum arquivo de origem encontrado"
        return self.valido(nome, origem, parametros, depende_de, self.idade_maxima_dias.get(nome))

    # ------------------------------------------------------------------ leitura e gravação
    def carregar(self, nome):
        """Lê o Parquet de uma tabela e devolve o DataFrame."""
        caminho_parquet, _ = self.caminhos(nome)
        return pd.read_parquet(caminho_parquet, engine="pyarrow")

    def gravar(self, nome, df, origem, parametros, depende_de=None, conferir=True):
        """
        Grava a tabela em Parquet e, POR ÚLTIMO, o manifesto (se a gravação for interrompida no meio,
        o cache simplesmente não vale e será refeito). Com conferir=True, reabre o arquivo e compara.
        Devolve o tamanho do Parquet em bytes.
        """
        import pyarrow as pa  # só para registrar a versão no manifesto
        caminho_parquet, caminho_manifesto = self.caminhos(nome)
        # Cria a pasta, se ainda não existir.
        self.pasta.mkdir(parents=True, exist_ok=True)

        # O Parquet não guarda a numeração das linhas: ela precisa ser a padrão (0, 1, 2...), senão paramos.
        if not df.index.equals(pd.RangeIndex(len(df))):
            raise ValueError(f"[{nome}] a numeração das linhas não é a padrão (0, 1, 2...). Nada foi gravado.")
        # O Parquet não aceita nomes de coluna repetidos.
        if df.columns.duplicated().any():
            raise ValueError(f"[{nome}] há nomes de coluna repetidos. Nada foi gravado.")

        # Apaga o manifesto antigo ANTES de mexer no Parquet (o cache fica "inválido" enquanto grava).
        if caminho_manifesto.exists():
            caminho_manifesto.unlink()
        # Grava num arquivo temporário e só depois troca pelo definitivo (nunca fica um Parquet pela metade).
        caminho_tmp = caminho_parquet.with_name(caminho_parquet.name + ".tmp")
        try:
            df.to_parquet(caminho_tmp, engine="pyarrow", compression="snappy", index=False)
        except Exception as erro:
            # Se a gravação falhar (por exemplo, coluna com tipos misturados), apaga o temporário e explica.
            if caminho_tmp.exists():
                caminho_tmp.unlink()
            raise RuntimeError(f"[{nome}] falha ao gravar o Parquet ({type(erro).__name__}): {str(erro)[:200]}. "
                               "Nada foi gravado.") from None
        os.replace(caminho_tmp, caminho_parquet)

        # Conferência: reabre o arquivo e compara com a tabela da memória.
        if conferir:
            volta = self.carregar(nome)
            if len(volta) != len(df) or list(volta.columns) != list(df.columns):
                raise ValueError(f"[{nome}] o arquivo reaberto tem formato diferente (linhas ou colunas). "
                                 "Manifesto NÃO gravado.")
            try:
                # Vazio (NaN) e None são tratados como iguais; os tipos podem diferir um pouco (texto x objeto).
                pd.testing.assert_frame_equal(df, volta, check_dtype=False, check_exact=True)
            except AssertionError as erro:
                raise ValueError(f"[{nome}] o arquivo reaberto tem valores diferentes: {str(erro)[:200]}. "
                                 "Manifesto NÃO gravado.") from None
            del volta

        # Manifesto, gravado por último.
        manifesto = self.descricao_atual(nome, origem, parametros, depende_de)
        manifesto.update({
            "dataframe": nome,
            "gravado_em": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "linhas": int(len(df)),
            "colunas": [str(c) for c in df.columns],
            "versao_pandas": pd.__version__,
            "versao_pyarrow": getattr(pa, "__version__", "desconhecida"),
        })
        caminho_manifesto.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2, sort_keys=True),
                                     encoding="utf-8")
        return caminho_parquet.stat().st_size

    def salvar(self, nome, df):
        """Grava a tabela no cache (com conferência) e mostra no log. Sem pyarrow, só avisa e segue."""
        if not pyarrow_instalado():
            log.warning(f"    [{nome}] cache NÃO gravado: falta a biblioteca pyarrow (py -m pip install --user pyarrow).")
            return
        # Segurança: colunas com dados pessoais nunca podem ir para o disco.
        pessoais = [c for c in self.colunas_proibidas.get(nome, []) if c in df.columns]
        if pessoais:
            raise ValueError(f"[{nome}] tem colunas com dados pessoais {pessoais}: o cache NÃO foi gravado.")
        log.info(f"    [{nome}] gravando o cache (e conferindo o arquivo gravado)...")
        inicio_gravacao = time.time()
        origem, parametros, depende_de = self.descrever(nome)
        tamanho = self.gravar(nome, df, origem, parametros, depende_de)
        log.info(f"    [{nome}] cache gravado! {tamanho / 1e6:.1f} MB ({formatar_tempo(time.time() - inicio_gravacao)}).")
