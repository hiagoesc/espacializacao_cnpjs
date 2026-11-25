"""Leitura do config.yaml e montagem de caminhos a partir da raiz do projeto."""
from pathlib import Path

import yaml                                      # leitor de arquivos YAML (vem com o Anaconda; no pip: pyyaml)


def achar_raiz(inicio=None) -> Path:
    """Sobe pelas pastas, a partir de 'inicio' (ou da pasta atual), até achar o config.yaml. Devolve essa pasta."""
    inicio = Path(inicio or Path.cwd()).resolve()
    for pasta in [inicio, *inicio.parents]:      # a própria pasta e todas as pastas acima dela
        if (pasta / "config.yaml").exists():
            return pasta
    raise FileNotFoundError(f"config.yaml não encontrado a partir de {inicio}")


class Config:
    """Acesso ao config.yaml: caminhos absolutos, camadas e parâmetros por chave pontuada ('brutos.cnefe')."""

    def __init__(self, raiz: Path, dados: dict):
        self.raiz = Path(raiz)                   # pasta raiz do projeto
        self.dados = dados                       # conteúdo do config.yaml (dicionário)

    def _buscar(self, chave: str):
        """Navega no dicionário por uma chave do tipo 'a.b.c'. Erro claro se a chave não existir."""
        valor = self.dados
        for parte in chave.split("."):
            if not isinstance(valor, dict) or parte not in valor:
                raise KeyError(f"Chave '{chave}' não existe no config.yaml (parou em '{parte}')")
            valor = valor[parte]
        return valor

    def caminho(self, chave: str) -> Path:
        """Caminho absoluto de um arquivo/pasta do config. Aceita valor texto ou dicionário com 'arquivo'."""
        valor = self._buscar(chave)
        if isinstance(valor, dict):
            valor = valor["arquivo"]
        return self.raiz / valor

    def camada(self, chave: str):
        """Nome da camada de um GeoPackage do config (None se não informado)."""
        valor = self._buscar(chave)
        return valor.get("camada") if isinstance(valor, dict) else None

    def parametro(self, chave: str, padrao=None):
        """Valor de um parâmetro em 'parametros.<chave>'. Devolve 'padrao' se não existir."""
        try:
            return self._buscar("parametros." + chave)
        except KeyError:
            return padrao

    def projeto(self, chave: str):
        """Valor da seção 'projeto' (ex.: 'crs_metrico')."""
        return self._buscar("projeto." + chave)

    def pasta(self, nome: str) -> Path:
        """Pasta padrão (brutos, editados, backup, processamento, logs, entrega), criada se não existir."""
        p = self.raiz / self._buscar("pastas." + nome)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def pasta_etapa(self, nome_notebook: str) -> Path:
        """Subpasta da etapa em 03_processamento (mesmo nome do notebook), criada se não existir."""
        p = self.pasta("processamento") / nome_notebook
        p.mkdir(parents=True, exist_ok=True)
        return p


def carregar(raiz=None) -> Config:
    """Acha a raiz (se não for informada), lê o config.yaml e devolve um objeto Config."""
    raiz = Path(raiz) if raiz else achar_raiz()
    with open(raiz / "config.yaml", encoding="utf-8") as arq:
        dados = yaml.safe_load(arq)
    return Config(raiz, dados)
