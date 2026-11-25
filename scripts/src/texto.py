"""Normalização de nomes de logradouro e bairro (para comparar textos de bases diferentes).

Usada nas sugestões e nas comparações de nome. O pareamento principal (etapa 02) tem a sua
própria normalização, mais completa, dentro do notebook.
"""
import re
import unicodedata

import pandas as pd

# --- Tipos de logradouro dos Correios (os de duas palavras primeiro) e dicionários de padronização ---
TIPOS_CORREIOS = ["AREA VERDE", "AREA RURAL", "COMUNIDADE URBANA", "RUA", "AVENIDA", "PRACA", "TRAVESSA",
                  "ALAMEDA", "ESTRADA", "VIELA", "RODOVIA", "COMUNIDADE", "AREA", "LARGO", "PONTE", "ACESSO",
                  "BULEVAR", "LADEIRA", "LOTEAMENTO", "MARGINAL", "PASSARELA", "ROTATORIA", "TREVO", "VIA", "VILA"]
ABREVIACOES = {"DR": "DOUTOR", "DRA": "DOUTORA", "PROF": "PROFESSOR", "PROFA": "PROFESSORA", "ENG": "ENGENHEIRO",
               "CEL": "CORONEL", "MAJ": "MAJOR", "CAP": "CAPITAO", "PE": "PADRE", "STO": "SANTO", "STA": "SANTA",
               "TV": "TRAVESSA", "AV": "AVENIDA", "PC": "PRACA", "EST": "ESTRADA", "ROD": "RODOVIA",
               "SGT": "SARGENTO", "TEN": "TENENTE", "GEN": "GENERAL", "MONS": "MONSENHOR", "DEP": "DEPUTADO",
               "GOV": "GOVERNADOR", "PRES": "PRESIDENTE"}
TITULOS = {"DOUTOR", "DOUTORA", "DR", "DRA", "PROFESSOR", "PROFESSORA", "PROF", "ENGENHEIRO", "CORONEL", "CEL",
           "PADRE", "PE", "MAJOR", "CAPITAO", "SENADOR", "DEPUTADO", "GOVERNADOR", "PRESIDENTE", "MONSENHOR", "FREI"}
NUMERAIS = {"UM": "1", "DOIS": "2", "TRES": "3", "QUATRO": "4", "CINCO": "5", "SEIS": "6", "SETE": "7", "OITO": "8",
            "NOVE": "9", "DEZ": "10", "ONZE": "11", "DOZE": "12", "TREZE": "13", "QUATORZE": "14", "CATORZE": "14",
            "QUINZE": "15", "DEZESSEIS": "16", "DEZESSETE": "17", "DEZOITO": "18", "DEZENOVE": "19", "VINTE": "20"}
PREPOSICOES = {"DE", "DA", "DO", "DAS", "DOS"}


def normalizar_nome(texto):
    """Normaliza um nome de rua: maiúsculas, sem acento/pontuação/preposições; abreviações e números por extenso viram padrão."""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().upper()
    t = re.sub(r"\([^)]*\)", " ", t)                                   # tira o que está entre parênteses
    if "," in t:                                                       # "Fulano, Doutor" -> "Doutor Fulano"
        antes, depois = t.rsplit(",", 1)
        if depois.strip().split(" ")[0] in TITULOS:
            t = depois + " " + antes
    t = re.sub(r"[^A-Z0-9 ]", " ", t)                                  # pontuação vira espaço
    palavras = [ABREVIACOES.get(w, w) for w in t.split()]              # DR -> DOUTOR etc.
    palavras = [NUMERAIS.get(w, w) for w in palavras if w not in PREPOSICOES]   # tira DE/DA/DO e converte números
    return " ".join(palavras)


def normalizar(serie: pd.Series) -> pd.Series:
    """Aplica a normalização só nos valores distintos (rápido) e devolve a série normalizada (nulo vira vazio)."""
    mapa = {v: normalizar_nome(v) for v in serie.dropna().unique()}
    return serie.map(mapa).fillna("").astype(object)


def tirar_tipo(texto_normalizado: str) -> str:
    """Remove o tipo (RUA, AVENIDA...) do início de um logradouro já normalizado."""
    for tipo in sorted(TIPOS_CORREIOS, key=len, reverse=True):         # tipos de duas palavras primeiro
        if texto_normalizado == tipo:
            return ""
        if texto_normalizado.startswith(tipo + " "):
            return texto_normalizado[len(tipo) + 1:]
    return texto_normalizado
