"""Limpeza e padronização de endereços (vias, números e bairros) da espacialização de CNPJs.

Módulo SÓ deste projeto (não copiar para outros): as regras aqui são as da cascata de espacialização
(bloco 12 do notebook original). O texto.py, comum aos projetos, tem outra normalização (a da RAIS),
que não é usada aqui para não mudar os resultados.

Funções: normalizar_texto, normalizar_numero, converter_extenso, romano_para_int, tirar_numero_do_fim,
limpar_via, expandir_tipo_sirf, nucleo_da_via, aplicar_nucleo, nucleo_de_texto, padronizar_bairro.
A distância em metros (distancia_metros) está em geo.py.
"""
# Biblioteca para mensagens de log (tela + arquivo, configurado pelo registro.iniciar_log).
import logging
# Biblioteca para achar trechos de texto por padrão.
import re

# Biblioteca para cálculos com números.
import numpy as np
# Biblioteca para trabalhar com tabelas (DataFrames).
import pandas as pd

# Logger deste módulo: as mensagens aparecem no mesmo log do notebook.
log = logging.getLogger("enderecos")

# ===================================================================
# LISTAS USADAS NA LIMPEZA
# ===================================================================
# Números por extenso e o valor de cada um (listas minhas, ainda NÃO verificadas na sua base).
UNIDADES = {"UM": 1, "UMA": 1, "DOIS": 2, "DUAS": 2, "TRES": 3, "QUATRO": 4, "CINCO": 5,
            "SEIS": 6, "SETE": 7, "OITO": 8, "NOVE": 9}
ESPECIAIS = {"DEZ": 10, "ONZE": 11, "DOZE": 12, "TREZE": 13, "QUATORZE": 14, "CATORZE": 14,
             "QUINZE": 15, "DEZESSEIS": 16, "DEZESSETE": 17, "DEZOITO": 18, "DEZENOVE": 19}
DEZENAS = {"VINTE": 20, "TRINTA": 30, "QUARENTA": 40, "CINQUENTA": 50, "SESSENTA": 60,
           "SETENTA": 70, "OITENTA": 80, "NOVENTA": 90}

# Abreviações de títulos que serão escritas por extenso (lista minha, ainda NÃO verificada).
ABREVIACOES = {
    "DR": "DOUTOR", "DRA": "DOUTORA", "PROF": "PROFESSOR", "PROFA": "PROFESSORA",
    "CEL": "CORONEL", "STO": "SANTO", "STA": "SANTA", "MONS": "MONSENHOR",
    "CAP": "CAPITAO", "GEN": "GENERAL", "DEP": "DEPUTADO", "ENG": "ENGENHEIRO",
    "PRES": "PRESIDENTE", "SEN": "SENADOR", "TEN": "TENENTE", "MAJ": "MAJOR",
    "SGT": "SARGENTO", "GOV": "GOVERNADOR", "ALM": "ALMIRANTE", "BRIG": "BRIGADEIRO",
}

# Abreviações do TIPO da via, que no SIRF vêm no começo do "Logradouro".
# Lista montada a partir da inspeção do SIRF; CONFIRA no log do notebook 04 (seção 1) se falta alguma.
TIPOS_VIA_SIRF = {
    "R": "RUA", "AV": "AVENIDA", "PCA": "PRACA", "AL": "ALAMEDA", "TV": "TRAVESSA",
    "ESTMUN": "ESTRADA MUNICIPAL", "EST": "ESTRADA", "BUL": "BULEVAR", "VIA": "VIA",
    "RUA": "RUA", "V": "VIA", "LG": "LARGO", "CAM": "CAMINHO", "VEL": "VIELA",
    "RODV": "RODOVIA", "ROD": "RODOVIA", "PRC": "PRACA", "TRV": "TRAVESSA",
    # Siglas confirmadas pelo usuário (BAN e CMP continuam sem tradução: o significado não foi confirmado):
    "FAZ": "FAZENDA", "VLA": "VILA", "SRV": "SERVIDAO", "MRG": "MARGINAL", "ALC": "ALCA",
    "VIAD": "VIADUTO", "LD": "LADEIRA", "AC": "ACESSO",
}

# Valor das letras de algarismo romano (só as que fazem sentido em nomes de rua).
ROMANOS = {"I": 1, "V": 5, "X": 10, "L": 50}
# Nomes dos meses (sem acento). O algarismo romano só é trocado quando vem antes de "DE" + mês.
MESES = "JANEIRO|FEVEREIRO|MARCO|ABRIL|MAIO|JUNHO|JULHO|AGOSTO|SETEMBRO|OUTUBRO|NOVEMBRO|DEZEMBRO"
# Padrão de texto procurado. Exemplo: "XV DE NOVEMBRO".
PADRAO_ROMANO = rf"\b([IVXL]+)\s+DE\s+({MESES})\b"


# ===================================================================
# FUNÇÕES
# ===================================================================


def normalizar_texto(serie):
    """
    Recebe uma coluna de textos e devolve os textos padronizados:
    maiúsculas, sem acentos, sem pontuação e com espaços únicos.
    Exemplo: "Av. São João " vira "AV SAO JOAO".
    """
    # Troca células vazias por texto vazio e passa tudo para maiúsculas.
    texto = serie.fillna("").astype(str).str.upper()
    # Separa as letras dos acentos (NFKD), descarta o que não é ASCII (os acentos) e volta para texto.
    texto = texto.str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii")
    # Troca tudo que não for letra, número ou espaço (pontos, vírgulas, hífens...) por um espaço.
    texto = texto.str.replace(r"[^A-Z0-9 ]", " ", regex=True)
    # Troca espaços repetidos por um só e tira os espaços das pontas.
    texto = texto.str.replace(r"\s+", " ", regex=True).str.strip()
    return texto


def normalizar_numero(serie):
    """
    Recebe uma coluna de números de endereço (texto) e devolve só o número normalizado:
    primeiro grupo de dígitos, sem ponto de milhar e sem zeros à esquerda.
    Quando não há dígitos (como "S/N") ou o valor é zero, devolve vazio (NaN).
    """
    # Troca células vazias por texto vazio, tira espaços das pontas e passa para maiúsculas.
    texto = serie.fillna("").astype(str).str.strip().str.upper()
    # Tira o ponto de milhar: um ponto depois de um dígito e antes de exatamente 3 dígitos.
    texto = texto.str.replace(r"(?<=\d)\.(?=\d{3}(?!\d))", "", regex=True)
    # Fica só com o PRIMEIRO grupo de dígitos (exemplo: "123A" vira "123").
    numero = texto.str.extract(r"(\d+)")[0]
    # Remove os zeros à esquerda (exemplo: "0045" vira "45").
    numero = numero.str.lstrip("0")
    # Se sobrou texto vazio (era só zero, como "0" ou "000"), marca como "sem número" (NaN).
    return numero.mask(numero == "")


def converter_extenso(texto):
    """Troca números escritos por extenso por dígitos. Exemplo: 'VINTE E CINCO DE JULHO' vira '25 DE JULHO'."""
    # Separa o texto em palavras.
    palavras = texto.split()
    # Lista onde vamos montar o texto novo.
    saida = []
    # "i" é a posição da palavra que estamos olhando.
    i = 0
    while i < len(palavras):
        p = palavras[i]
        if p in DEZENAS:
            # Achou uma dezena (VINTE, TRINTA...). Começa com o valor dela.
            valor = DEZENAS[p]
            i += 1
            # Se vier "E" + unidade ("VINTE E CINCO"), soma a unidade.
            if i + 1 < len(palavras) and palavras[i] == "E" and palavras[i + 1] in UNIDADES:
                valor += UNIDADES[palavras[i + 1]]
                i += 2
            # Se vier unidade direto ("VINTE TRES"), soma também.
            elif i < len(palavras) and palavras[i] in UNIDADES:
                valor += UNIDADES[palavras[i]]
                i += 1
            saida.append(str(valor))
        elif p in ESPECIAIS:
            # Números de 10 a 19.
            saida.append(str(ESPECIAIS[p]))
            i += 1
        elif p in UNIDADES:
            # Números de 1 a 9.
            saida.append(str(UNIDADES[p]))
            i += 1
        else:
            # Palavra comum: copia do jeito que está.
            saida.append(p)
            i += 1
    return " ".join(saida)


def romano_para_int(romano):
    """Converte um algarismo romano em número. Exemplo: 'XV' vira 15."""
    total = 0
    for i, letra in enumerate(romano):
        valor = ROMANOS[letra]
        # Se a próxima letra vale mais (como o I em "IX"), esta letra é subtraída; senão, somada.
        if i + 1 < len(romano) and ROMANOS[romano[i + 1]] > valor:
            total -= valor
        else:
            total += valor
    return total


def tirar_numero_do_fim(via, num):
    """
    Tira do fim do nome da via o número do próprio imóvel, quando ele aparece lá.
    Exemplo: via 'AVENIDA SAO JOAO 323' com número '323' vira 'AVENIDA SAO JOAO'.
    Só age se o que sobra ainda tiver pelo menos duas palavras.
    """
    # Lista onde guardamos o resultado de cada linha.
    resultado = []
    # Passa por cada par (via, número), linha a linha.
    for v, n in zip(via, num):
        # Só age quando existe número (texto) e a via é texto.
        if isinstance(n, str) and isinstance(v, str):
            # O trecho a procurar no fim da via: um espaço + o número.
            sufixo = " " + n
            # Repete enquanto a via termina com o número e o que sobra tem espaço (tipo + nome).
            while v.endswith(sufixo) and " " in v[: -len(sufixo)]:
                v = v[: -len(sufixo)]
        resultado.append(v)
    # Devolve como coluna, com a mesma numeração de linhas da entrada.
    return pd.Series(resultado, index=via.index)


def limpar_via(serie, rotulo):
    """
    Recebe a coluna de vias JÁ normalizadas e devolve a versão limpa.
    Mostra quantas linhas cada regra alterou. O 'rotulo' só aparece nos logs.
    """
    # Trabalha só nos valores únicos (são muito menos que as linhas) e depois devolve para todas.
    unicos = pd.Series(serie.dropna().unique())
    # "t" guarda a versão atual dos textos únicos, que vai sendo melhorada a cada regra.
    t = unicos.copy()

    def aplicar(nome, novo):
        """Guarda o resultado de uma regra e conta quantas linhas ela alterou."""
        nonlocal t
        # Para cada texto único: verdadeiro se esta regra o alterou.
        alterou = novo != t
        # Leva o verdadeiro/falso para todas as linhas e soma, para contar linhas (e não textos únicos).
        qtd = int(serie.map(dict(zip(unicos, alterou))).fillna(False).astype(bool).sum())
        log.info(f"    [{rotulo}] {nome}: {qtd:,} linhas alteradas")
        t = novo

    # Regra 1: corta o texto descritivo do fim. Exemplo: 'OURO FINO DE 1265 1266 AO FIM' vira 'OURO FINO'.
    aplicar("texto descritivo cortado", t.str.replace(r"\s(DE|ATE|AO)\s+\d+.*$", "", regex=True))

    # Regra 2: tira o tipo duplicado no começo. Exemplo: 'AVENIDA AVENIDA SAO JOSE' vira 'AVENIDA SAO JOSE'.
    novo = t.str.replace(r"^(\S+\s+\S+)\s+\1(\s|$)", r"\1\2", regex=True)
    novo = novo.str.replace(r"^(\S+)\s+\1(\s|$)", r"\1\2", regex=True)
    aplicar("tipo duplicado removido", novo)

    # Regra 3: troca 'AVEN' por 'AVENIDA' (só a palavra inteira, por causa do \b).
    aplicar("AVEN trocado por AVENIDA", t.str.replace(r"\bAVEN\b", "AVENIDA", regex=True))

    # Regra 4: escreve as abreviações de títulos por extenso.
    novo = t
    for abrev, completo in ABREVIACOES.items():
        novo = novo.str.replace(rf"\b{abrev}\b", completo, regex=True)
    aplicar("abreviações escritas por extenso", novo)

    # Regra 5: troca algarismo romano por número, só antes de 'DE' + mês.
    aplicar(
        "algarismo romano trocado por número",
        t.str.replace(PADRAO_ROMANO, lambda m: f"{romano_para_int(m.group(1))} DE {m.group(2)}", regex=True),
    )

    # Regra 6: troca números por extenso por dígitos.
    aplicar("número por extenso trocado por dígitos", t.apply(converter_extenso))

    # Regra 7: tira o 'HUM' que vem depois do dígito. Exemplo: '1 HUM' (que era '1 (HUM)') vira '1'.
    aplicar("'HUM' removido", t.str.replace(r"(\d+)\s+HUM\b", r"\1", regex=True))

    # Regra 8 (não conta): espaços repetidos viram um só.
    t = t.str.replace(r"\s+", " ", regex=True).str.strip()

    # Devolve o resultado para todas as linhas, usando um dicionário "texto original -> texto limpo".
    return serie.map(dict(zip(unicos, t)))


def expandir_tipo_sirf(serie, rotulo):
    """
    Troca a abreviação do TIPO da via, que no SIRF vem no começo do logradouro,
    pelo nome completo. Exemplo: 'R MAL RONDON' vira 'RUA MAL RONDON'.
    Antes de trocar, mostra no log todas as abreviações encontradas, para você conferir.
    """
    # Primeira palavra de cada logradouro já normalizado.
    primeira = serie.fillna("").str.split(" ").str[0]
    # Quantas vezes cada primeira palavra aparece.
    contagem = primeira.value_counts()
    log.info(f"    [{rotulo}] primeiras palavras encontradas no logradouro (CONFIRA a tradução):")
    for palavra, qtd in contagem.items():
        # Mostra para o que cada uma será trocada; "(não traduzida)" quando não está na tabela.
        destino = TIPOS_VIA_SIRF.get(palavra, "(não traduzida, fica como está)")
        log.info(f"        {palavra}: {qtd:,} -> {destino}")

    # Troca só a PRIMEIRA palavra, e só quando ela está na tabela de tipos.
    def trocar(texto):
        if not texto:
            return texto
        partes = texto.split(" ", 1)
        tipo = TIPOS_VIA_SIRF.get(partes[0])
        if tipo is None:
            return texto
        return tipo if len(partes) == 1 else tipo + " " + partes[1]

    return serie.fillna("").map(trocar)


# ===================================================================
# NÚCLEO DO NOME DA VIA E BAIRRO PADRONIZADO (usados nos passos 9 em diante)
# ===================================================================
# Preposições que não ajudam a comparar nomes (JORGE ZARUR DA SILVA = JORGE ZARUR SILVA).
PREPOSICOES = {"DE", "DA", "DO", "DAS", "DOS", "E"}
# Tipos de via que ficam no começo do nome (RUA, AVENIDA, ESTRADA DE RODAGEM...). Lista minha, NÃO validada.
TIPOS_NUCLEO = {"RUA", "AVENIDA", "ESTRADA", "RODOVIA", "PRACA", "TRAVESSA", "ALAMEDA", "VIA", "VIELA",
                "LARGO", "MUNICIPAL", "RODAGEM", "ACESSO", "BULEVAR", "CAMINHO", "VIADUTO"}
# Títulos que aparecem numa base e não na outra (DOUTOR JORGE ZARUR = JORGE ZARUR). Lista minha, NÃO validada.
TITULOS_NUCLEO = {"DOUTOR", "DOUTORA", "PRESIDENTE", "ENGENHEIRO", "PROFESSOR", "PROFESSORA", "CAPITAO",
                  "CORONEL", "GENERAL", "MARECHAL", "AR", "TENENTE", "SARGENTO", "MAJOR", "PADRE", "DOM",
                  "FREI", "IRMA", "MADRE", "DEPUTADO", "VEREADOR", "SENADOR", "PREFEITO", "GOVERNADOR",
                  "BRIGADEIRO", "COMENDADOR", "ALMIRANTE", "MONSENHOR", "CONEGO", "DONA", "SENHOR",
                  "MINISTRO", "DESEMBARGADOR", "CABO", "SOLDADO"}
# Abreviações que mudam a comparação do fim do nome (JOAO QUEIROZ JR = JOAO QUEIROZ JUNIOR).
ABREV_NUCLEO = {"JR": "JUNIOR"}


def nucleo_da_via(texto):
    """Devolve o núcleo do nome da via. Exemplo: 'AVENIDA DOUTOR JORGE ZARUR' vira 'JORGE ZARUR'."""
    # Se não for texto (vazio), não há núcleo.
    if not isinstance(texto, str):
        return None
    # Separa em palavras, troca as abreviações e tira as preposições.
    palavras = [ABREV_NUCLEO.get(p, p) for p in texto.split() if p not in PREPOSICOES]
    # Tira os tipos de via do começo (pode ser mais de um: ESTRADA MUNICIPAL).
    while palavras and palavras[0] in TIPOS_NUCLEO:
        palavras.pop(0)
    # Tira os títulos, em qualquer posição.
    palavras = [p for p in palavras if p not in TITULOS_NUCLEO]
    # Se não sobrou nada, devolve vazio.
    return " ".join(palavras) if palavras else None


def aplicar_nucleo(serie):
    """Aplica nucleo_da_via numa coluna inteira, calculando só uma vez para cada texto diferente."""
    # Textos diferentes (são muito menos que as linhas).
    unicos = serie.dropna().unique()
    # Dicionário "texto -> núcleo".
    dicionario = {v: nucleo_da_via(v) for v in unicos}
    # Leva o resultado para todas as linhas.
    return serie.map(dicionario)


def nucleo_de_texto(texto):
    """Núcleo de um texto solto, ainda não normalizado (usado no geocoding). Exemplo: 'Av. Dr. Jorge Zarur'."""
    # Padroniza (maiúsculas, sem acento, sem pontuação) e escreve as abreviações por extenso.
    normalizado = normalizar_texto(pd.Series([texto if isinstance(texto, str) else ""]))
    for abrev, completo in ABREVIACOES.items():
        normalizado = normalizado.str.replace(rf"\b{abrev}\b", completo, regex=True)
    return nucleo_da_via(normalizado.iloc[0])


# Abreviações de bairro (JD vira JARDIM). Lista minha, NÃO validada.
ABREV_BAIRRO = {"JD": "JARDIM", "JARD": "JARDIM", "VL": "VILA", "PQ": "PARQUE", "PRQ": "PARQUE",
                "CJ": "CONJUNTO", "CONJ": "CONJUNTO", "RES": "RESIDENCIAL", "RESID": "RESIDENCIAL",
                "STA": "SANTA", "STO": "SANTO", "CH": "CHACARA", "CHAC": "CHACARAS", "LOT": "LOTEAMENTO"}


def padronizar_bairro(serie):
    """Bairro em maiúsculas, sem acento, sem preposições e com abreviações por extenso (JD vira JARDIM)."""
    # Padroniza o texto (maiúsculas, sem acento e sem pontuação).
    texto = normalizar_texto(serie)
    # Trabalha só nos textos diferentes e depois devolve para todas as linhas.
    unicos = texto.dropna().unique()
    dicionario = {v: " ".join(ABREV_BAIRRO.get(p, p) for p in v.split() if p not in PREPOSICOES) for v in unicos}
    # Texto vazio vira "sem bairro" (NaN).
    return texto.map(dicionario).mask(lambda s: s == "")
