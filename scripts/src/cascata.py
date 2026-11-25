"""Funções da cascata de espacialização de CNPJs (bloco 14 do notebook original).

Módulo SÓ deste projeto (não copiar para outros). Usado pelos notebooks 05, 06 e 07.

Antes de usar, o notebook chama:
    cascata.configurar(cfg)              -> lê os limiares de parametros.cascata do config.yaml
    cascata.definir_cep_bairro(dicionario)  -> bairro de cada CEP (só quando usa os passos 9 a 11)

As funções que mexem no resultado recebem as tabelas do notebook explicitamente:
    selecionar_pendentes(df_espacial, aux_estab, numero_passo, ...)
    gravar_resultado(df_espacial, resultado, numero_passo)   (altera o df_espacial no lugar)
    resumo_passo(df_espacial, numero_passo, nome_passo, entraram, resultado)
    rodar_cadeia_nucleo(grupos_nucleo, est, nome_passo, teto=None)
"""
# Biblioteca para mensagens de log (tela + arquivo, configurado pelo registro.iniciar_log).
import logging
# Biblioteca que compara dois textos e diz o quanto são parecidos (de 0 a 1).
from difflib import SequenceMatcher

# Biblioteca para cálculos com números.
import numpy as np
# Biblioteca para trabalhar com tabelas (DataFrames).
import pandas as pd

# Distância em metros entre pontos (lat/lon) e núcleo do nome da via.
from .enderecos import aplicar_nucleo
from .geo import distancia_metros

# Logger deste módulo: as mensagens aparecem no mesmo log do notebook.
log = logging.getLogger("cascata")

# Ordem das confianças, da melhor para a pior (usada para ordenar os resumos e limitar confianças).
ORDEM_CONFIANCA = ["muito alta", "alta", "média", "baixa", "muito baixa"]

# ===================================================================
# LIMIARES DA CASCATA (lidos do config.yaml por configurar(cfg))
# ===================================================================
# Nomes dos limiares usados pelas funções deste módulo. Os valores ficam em parametros.cascata do config.yaml
# (com o mesmo nome, em minúsculas). Enquanto configurar() não for chamado, valem None.
PARAMETROS_MODULO = [
    "ESP_CONCENTRADO", "ESP_ESPALHADO", "DIST_BASES_CONCORDAM", "ESP_MAX_VARIOS_CEPS", "LIMIAR_VIA_PARECIDA",
    "DIF_MEDIA", "DIF_MAX", "LIMITE_UM_VIZINHO", "EXTENSAO_VIA_MAX", "DIST_MAX_VIZINHOS_VIA_INTEIRA",
    "ESP_CENTRO_CEP_BAIXA", "ESP_MAX_CENTRO_CEP",
]
ESP_CONCENTRADO = ESP_ESPALHADO = DIST_BASES_CONCORDAM = ESP_MAX_VARIOS_CEPS = LIMIAR_VIA_PARECIDA = None
DIF_MEDIA = DIF_MAX = LIMITE_UM_VIZINHO = EXTENSAO_VIA_MAX = DIST_MAX_VIZINHOS_VIA_INTEIRA = None
ESP_CENTRO_CEP_BAIXA = ESP_MAX_CENTRO_CEP = None

# Bairro de cada CEP (base dos Correios), definido pelo notebook com definir_cep_bairro().
CEP_BAIRRO = None


def configurar(cfg):
    """Lê os limiares da cascata (parametros.cascata do config.yaml) para as funções deste módulo."""
    # Dicionário com todos os limiares da cascata.
    limiares = cfg.parametro("cascata")
    if not isinstance(limiares, dict):
        raise KeyError("parametros.cascata não encontrado no config.yaml.")
    # Para cada nome usado aqui, procura o valor no config (mesmo nome, em minúsculas).
    faltam = [nome for nome in PARAMETROS_MODULO if nome.lower() not in limiares]
    if faltam:
        raise KeyError(f"Faltam em parametros.cascata do config.yaml: {[n.lower() for n in faltam]}")
    for nome in PARAMETROS_MODULO:
        globals()[nome] = limiares[nome.lower()]
    log.info("Limiares da cascata carregados do config.yaml!")


def definir_cep_bairro(cep_bairro):
    """Guarda o dicionário CEP -> bairro (base de CEPs dos Correios), usado para desempatar CEPs da mesma via."""
    global CEP_BAIRRO
    CEP_BAIRRO = cep_bairro


def _conferir_configurado():
    """Para com uma mensagem clara se configurar(cfg) ainda não foi chamado."""
    if any(globals()[nome] is None for nome in PARAMETROS_MODULO):
        raise RuntimeError("Chame cascata.configurar(cfg) antes de usar as funções da cascata.")

def preparar_grupos(ref, rotulo):
    """
    Recebe uma base de endereços (CEP, via, número, latitude e longitude) e devolve
    um dicionário com as tabelas já agrupadas que os passos da cascata usam.
    """
    log.info(f"    [{rotulo}] agrupando...")
    grupos = {}
    # Verdadeiro para as linhas que têm CEP e para as que têm número.
    tem_cep = ref["cep"].notna()
    tem_num = ref["num"].notna()

    # (a) CEP + via + número: usado nos passos 1 e 2 (número exato com o CEP da Receita).
    grupos["cep_via_num"] = (
        ref[tem_cep & tem_num]
        .groupby(["cep", "via", "num"], as_index=False)
        .agg(n=("lat", "size"), soma_lat=("lat", "sum"), soma_lon=("lon", "sum"),
             lat_min=("lat", "min"), lat_max=("lat", "max"),
             lon_min=("lon", "min"), lon_max=("lon", "max"))
    )

    # (b) via + número, sem olhar o CEP: usado nos passos 3 e 5 (CEP corrigido).
    # "ceps" conta quantos CEPs diferentes a combinação tem; "cep_min" guarda um deles.
    grupos["via_num"] = (
        ref[tem_num]
        .groupby(["via", "num"], as_index=False)
        .agg(n=("lat", "size"), ceps=("cep", "nunique"), cep_min=("cep", "min"),
             soma_lat=("lat", "sum"), soma_lon=("lon", "sum"),
             lat_min=("lat", "min"), lat_max=("lat", "max"),
             lon_min=("lon", "min"), lon_max=("lon", "max"))
    )

    # (c) CEP + via (sem exigir número): usado no passo 8 (centro da via).
    grupos["cep_via"] = (
        ref[tem_cep]
        .groupby(["cep", "via"], as_index=False)
        .agg(n=("lat", "size"), soma_lat=("lat", "sum"), soma_lon=("lon", "sum"),
             lat_min=("lat", "min"), lat_max=("lat", "max"),
             lon_min=("lon", "min"), lon_max=("lon", "max"))
    )

    # (d) Um ponto por CEP + via + número: usado nas interpolações (passos 4, 6 e 7).
    pontos = grupos["cep_via_num"].copy()
    pontos["lat"] = pontos["soma_lat"] / pontos["n"]
    pontos["lon"] = pontos["soma_lon"] / pontos["n"]
    # O número vira número de verdade, para podermos comparar "maior" e "menor".
    pontos["num"] = pd.to_numeric(pontos["num"], errors="coerce")
    pontos = pontos.dropna(subset=["num"])
    # Paridade: o resto da divisão por 2 diz se o número é par (0) ou ímpar (1).
    pontos["par"] = pontos["num"] % 2
    # merge_asof (usado nas interpolações) exige a tabela ordenada pelo número.
    grupos["pontos"] = pontos[["cep", "via", "num", "par", "lat", "lon"]].sort_values("num")

    # (e) Listas de apoio.
    # Todas as vias que existem na base.
    grupos["vias"] = set(ref["via"].dropna().unique())
    # Para cada CEP, a lista de vias que ele tem (usada no passo 6).
    pares = ref[tem_cep].drop_duplicates(["cep", "via"])
    grupos["vias_por_cep"] = pares.groupby("cep")["via"].apply(list).to_dict()
    # Para cada via, o conjunto de CEPs em que ela aparece (usada no passo 7).
    grupos["ceps_por_via"] = pares.groupby("via")["cep"].apply(set).to_dict()
    # Conjunto de pares (CEP, via) que existem na base (usado para confirmar o CEP no passo 7).
    grupos["pares_cep_via"] = set(zip(pares["cep"], pares["via"]))
    # Para cada número, a lista de vias que têm aquele número (usada no fuzzy do passo 5).
    grupos["vias_por_num"] = grupos["via_num"].groupby("num")["via"].apply(list).to_dict()
    return grupos

# Colunas que os passos podem gravar (usada pela função gravar_resultado).
COLUNAS_RESULTADO = ["lat", "lon", "espalhamento_m", "distancia_bases_m", "nota_fuzzy",
                     "base", "metodo", "confianca", "cep_usado", "via_candidata"]
COLUNAS_NUMERICAS_RESULTADO = ["lat", "lon", "espalhamento_m", "distancia_bases_m", "nota_fuzzy"]
COLUNAS_TEXTO_RESULTADO = ["base", "metodo", "confianca", "cep_usado", "via_candidata"]


def selecionar_pendentes(df_espacial, aux_estab, numero_passo, exigir_num=True, exigir_cep=True, coluna_via="via_limpa",
                         exigir_via=True, incluir_bairro=False):
    """
    Monta a tabela de trabalho do passo: uma linha por estabelecimento ainda sem coordenada.
    df_espacial e aux_estab: as tabelas do notebook (resultado da cascata e dados tratados da Receita).
    Os que o próprio passo resolveu antes (passo == numero_passo) voltam a ser tratados,
    para o bloco poder ser rodado de novo sem deixar sobras.
    O "idx" guarda o número da linha no df_estab, para sabermos onde gravar o resultado.
    coluna_via: "via_limpa" (passos 1 a 8 e 13) ou "nucleo" (passos 9 a 11).
    exigir_via=False: usado nos passos que não comparam a via (centro do CEP, do bairro e do município).
    incluir_bairro=True: traz também o bairro padronizado (usado para desempatar CEPs).
    """
    _conferir_configurado()
    pendentes = df_espacial["passo"].isna() | (df_espacial["passo"] == numero_passo)
    # Sem via não há como cruzar endereço: a via é exigida (menos nos passos que não a usam).
    ok = aux_estab[coluna_via].notna() if exigir_via else pd.Series(True, index=aux_estab.index)
    if exigir_num:
        ok = ok & aux_estab["num"].notna()
    if exigir_cep:
        ok = ok & aux_estab["cep"].notna()
    selecionados = pendentes & ok
    est = pd.DataFrame({
        "idx": aux_estab.index[selecionados.values],
        "cep": aux_estab.loc[selecionados, "cep"].values,
        "num": aux_estab.loc[selecionados, "num"].values,
        "via_e": aux_estab.loc[selecionados, coluna_via].values,
    })
    if incluir_bairro:
        est["bairro"] = aux_estab.loc[selecionados, "bairro"].values
    log.info(f"    {int(pendentes.sum()):,} estabelecimentos sem coordenada; "
          f"{len(est):,} entram neste passo ({int((pendentes & ~ok).sum()):,} ficam de fora "
          f"por não terem via, número ou CEP).")
    return pendentes, est


def sufixo_espalhamento(esp):
    """Transforma o espalhamento (em metros) em um texto e em uma confiança."""
    sufixo = np.select(
        [esp <= ESP_CONCENTRADO, esp <= ESP_ESPALHADO],
        ["pontos concentrados", "pontos espalhados"],
        default="pontos muito espalhados",
    )
    confianca = np.select(
        [esp <= ESP_CONCENTRADO, esp <= ESP_ESPALHADO],
        ["alta", "média"],
        default="baixa",
    )
    return sufixo, confianca


def media_e_espalhamento(tabela):
    """Calcula a média das coordenadas e o espalhamento (distância entre os cantos da caixa)."""
    lat = tabela["soma_lat"] / tabela["n"]
    lon = tabela["soma_lon"] / tabela["n"]
    esp = distancia_metros(tabela["lat_min"], tabela["lon_min"], tabela["lat_max"], tabela["lon_max"])
    return lat, lon, esp


def resolver_exato_com_cep(est, grupos, parecida):
    """
    Passos 1 e 2: procura na base as linhas com o MESMO CEP e o MESMO número da Receita
    e confere o nome da via (igual, quando parecida=False; parecida, quando parecida=True).
    Devolve uma tabela indexada pelo idx, com lat, lon, espalhamento, sufixo e confiança.
    """
    cn = grupos["cep_via_num"].rename(columns={"via": "via_c"})
    cruz = est.merge(cn, on=["cep", "num"], how="inner")
    if cruz.empty:
        return pd.DataFrame()

    if not parecida:
        # Via igual: os dois nomes são exatamente iguais.
        sel = cruz[cruz["via_e"] == cruz["via_c"]].copy()
        sel["ratio"] = 1.0
    else:
        # Pares de nomes diferentes, sem repetição (para não comparar a mesma coisa várias vezes).
        pares = cruz.loc[cruz["via_e"] != cruz["via_c"], ["via_e", "via_c"]].drop_duplicates()
        if pares.empty:
            return pd.DataFrame()
        log.info(f"        comparando {len(pares):,} pares de nomes diferentes...")
        # SequenceMatcher devolve de 0 (nada em comum) a 1 (idênticos).
        pares["ratio"] = [SequenceMatcher(None, a, b).ratio() for a, b in zip(pares["via_e"], pares["via_c"])]
        cruz = cruz.merge(pares, on=["via_e", "via_c"], how="left")
        # Onde o nome é igual, a semelhança vale 1; essas linhas já foram tratadas no passo 1.
        cruz["ratio"] = cruz["ratio"].fillna(1.0)
        cruz = cruz[cruz["ratio"] < 1.0]
        if cruz.empty:
            return pd.DataFrame()
        # Para cada estabelecimento, fica só com os candidatos de MELHOR semelhança.
        cruz["melhor"] = cruz.groupby("idx")["ratio"].transform("max")
        sel = cruz[(cruz["ratio"] == cruz["melhor"]) & (cruz["melhor"] >= LIMIAR_VIA_PARECIDA)].copy()

    if sel.empty:
        return pd.DataFrame()

    # Junta os candidatos escolhidos de cada estabelecimento.
    ag = sel.groupby("idx").agg(
        n=("n", "sum"), soma_lat=("soma_lat", "sum"), soma_lon=("soma_lon", "sum"),
        lat_min=("lat_min", "min"), lat_max=("lat_max", "max"),
        lon_min=("lon_min", "min"), lon_max=("lon_max", "max"),
    )
    res = pd.DataFrame(index=ag.index)
    res["lat"], res["lon"], res["espalhamento_m"] = media_e_espalhamento(ag)
    res["sufixo"], res["confianca"] = sufixo_espalhamento(res["espalhamento_m"])
    if parecida:
        # Guarda a via escolhida e a nota (de 0 a 100) do estabelecimento.
        melhor_linha = sel.sort_values("ratio", ascending=False).drop_duplicates("idx").set_index("idx")
        res["via_candidata"] = melhor_linha["via_c"]
        res["nota_fuzzy"] = (melhor_linha["ratio"] * 100).round(1)
    return res


def achar_vizinho(est, pontos, chaves, direcao, por_paridade, sufixo):
    """
    Para cada estabelecimento, acha o ponto da base (nas mesmas chaves) com o número
    imediatamente menor ("backward") ou imediatamente maior ("forward").
    """
    chaves_uso = chaves + (["par"] if por_paridade else [])
    p = (pontos[chaves_uso + ["num", "lat", "lon"]]
         .rename(columns={"num": "num_viz", "lat": "lat_viz", "lon": "lon_viz"})
         .sort_values("num_viz"))
    # merge_asof procura, para cada estabelecimento, o número mais próximo na direção pedida.
    # allow_exact_matches=False ignora o mesmo número (que já teria sido resolvido antes).
    r = pd.merge_asof(est, p, left_on="num", right_on="num_viz", by=chaves_uso,
                      direction=direcao, allow_exact_matches=False)
    r = r.set_index("idx")[["num_viz", "lat_viz", "lon_viz"]]
    r.columns = [f"num_{sufixo}", f"lat_{sufixo}", f"lon_{sufixo}"]
    return r


def interpolar(est, pontos, chaves, confiancas):
    """
    Estima a posição entre dois endereços vizinhos da base, proporcionalmente ao número.
    "est" precisa ter idx, num (número), par e as colunas de "chaves", já ordenado por num.
    "confiancas" diz a confiança de cada regra: A_perto, A_longe, B e C.
    """
    if est.empty or pontos.empty:
        return pd.DataFrame()

    # Vizinhos da MESMA paridade e de QUALQUER paridade, de cada lado.
    viz_ant_p = achar_vizinho(est, pontos, chaves, "backward", True, "ant_p")
    viz_prox_p = achar_vizinho(est, pontos, chaves, "forward", True, "prox_p")
    viz_ant = achar_vizinho(est, pontos, chaves, "backward", False, "ant")
    viz_prox = achar_vizinho(est, pontos, chaves, "forward", False, "prox")

    # Junta tudo em uma tabela só: uma linha por estabelecimento.
    t = est.set_index("idx")[["num"]].rename(columns={"num": "num_est"})
    t = t.join([viz_ant_p, viz_prox_p, viz_ant, viz_prox])

    # Verdadeiro/falso para cada estabelecimento.
    tem_par_mesma = t["num_ant_p"].notna() & t["num_prox_p"].notna()
    tem_par_qualquer = t["num_ant"].notna() & t["num_prox"].notna()
    tem_um = t["num_ant"].notna() ^ t["num_prox"].notna()     # "^" = só de um lado

    # Diferença entre os números dos dois vizinhos.
    dif_mesma = t["num_prox_p"] - t["num_ant_p"]
    dif_qualquer = t["num_prox"] - t["num_ant"]
    # Quando só há um vizinho: o número dele e a diferença para o número do estabelecimento.
    num_unico = t["num_ant"].fillna(t["num_prox"])
    dist_unico = (t["num_est"] - num_unico).abs()

    # As três regras, em ordem de preferência.
    regra_a = tem_par_mesma & (dif_mesma <= DIF_MAX)
    regra_b = ~tem_par_mesma & tem_par_qualquer & (dif_qualquer <= DIF_MAX)
    regra_c = ~tem_par_mesma & ~tem_par_qualquer & tem_um & (dist_unico <= LIMITE_UM_VIZINHO)

    # Posição proporcional entre os dois vizinhos: 0 = no menor, 1 = no maior.
    prop_mesma = (t["num_est"] - t["num_ant_p"]) / dif_mesma
    prop_qualquer = (t["num_est"] - t["num_ant"]) / dif_qualquer
    # Interpolação: parte do vizinho menor e anda a proporção calculada em direção ao maior.
    lat_a = t["lat_ant_p"] + prop_mesma * (t["lat_prox_p"] - t["lat_ant_p"])
    lon_a = t["lon_ant_p"] + prop_mesma * (t["lon_prox_p"] - t["lon_ant_p"])
    lat_b = t["lat_ant"] + prop_qualquer * (t["lat_prox"] - t["lat_ant"])
    lon_b = t["lon_ant"] + prop_qualquer * (t["lon_prox"] - t["lon_ant"])
    # Regra C: copia o ponto do único vizinho.
    lat_c = t["lat_ant"].fillna(t["lat_prox"])
    lon_c = t["lon_ant"].fillna(t["lon_prox"])

    # Distância em metros entre os dois vizinhos (serve de "espalhamento" nas regras A e B).
    esp_a = distancia_metros(t["lat_ant_p"], t["lon_ant_p"], t["lat_prox_p"], t["lon_prox_p"])
    esp_b = distancia_metros(t["lat_ant"], t["lon_ant"], t["lat_prox"], t["lon_prox"])

    # Monta o resultado: a primeira condição verdadeira de cada lista vale.
    a_perto = regra_a & (dif_mesma <= DIF_MEDIA)
    a_longe = regra_a & (dif_mesma > DIF_MEDIA)
    res = pd.DataFrame(index=t.index)
    res["lat"] = np.select([regra_a, regra_b, regra_c], [lat_a, lat_b, lat_c], default=np.nan)
    res["lon"] = np.select([regra_a, regra_b, regra_c], [lon_a, lon_b, lon_c], default=np.nan)
    # Na regra C não há dois pontos para medir, então o espalhamento fica vazio.
    res["espalhamento_m"] = np.select([regra_a, regra_b], [esp_a, esp_b], default=np.nan)
    res["sufixo"] = np.select(
        [a_perto, a_longe, regra_b, regra_c],
        [f"vizinhos de mesma paridade, até {DIF_MEDIA} números",
         f"vizinhos de mesma paridade, de {DIF_MEDIA + 1} a {DIF_MAX} números",
         "vizinhos de qualquer paridade",
         "um vizinho só"],
        default="",
    )
    res["confianca"] = np.select(
        [a_perto, a_longe, regra_b, regra_c],
        [confiancas["A_perto"], confiancas["A_longe"], confiancas["B"], confiancas["C"]],
        default="",
    )
    # Fica só com os resolvidos.
    return res[regra_a | regra_b | regra_c]


def preparar_para_interpolar(est, coluna_via="via_e", coluna_cep="cep"):
    """Deixa a tabela de trabalho no formato que a interpolação exige (número e paridade)."""
    t = est.copy()
    # O número vira número de verdade; quem não tiver número sai.
    t["num"] = pd.to_numeric(t[ "num"], errors="coerce")
    t = t.dropna(subset=["num"])
    t["par"] = t["num"] % 2
    t = t.rename(columns={coluna_via: "via", coluna_cep: "cep"})
    # merge_asof exige a tabela ordenada pelo número.
    return t.sort_values("num")


def combinar(res_pref, res_cnefe, nome_passo, concordancia=False):
    """
    Junta os resultados das duas bases e monta o nome do método e a confiança.
    Com concordancia=True (passos 1 e 2), quem foi resolvido pelas DUAS bases é comparado:
    pontos próximos viram "concordam" (confiança muito alta); distantes ficam com o da Prefeitura.
    Sem concordancia, a Prefeitura tem prioridade e o CNEFE resolve só o que sobrou.
    """
    partes = []
    idx_p = res_pref.index if len(res_pref) else pd.Index([])
    idx_c = res_cnefe.index if len(res_cnefe) else pd.Index([])
    ambos = idx_p.intersection(idx_c) if (concordancia and len(idx_p) and len(idx_c)) else pd.Index([])

    if len(ambos):
        p = res_pref.loc[ambos].copy()
        c = res_cnefe.loc[ambos]
        # Distância, em metros, entre o ponto da Prefeitura e o do CNEFE.
        dist = distancia_metros(p["lat"].values, p["lon"].values, c["lat"].values, c["lon"].values)
        concordam = dist <= DIST_BASES_CONCORDAM
        # Fica com o ponto da Prefeitura (a base mais confiável) nos dois casos.
        p["distancia_bases_m"] = dist
        # O espalhamento guardado é o pior dos dois (o mais cauteloso).
        p["espalhamento_m"] = np.maximum(p["espalhamento_m"].values, c["espalhamento_m"].values)
        p["metodo"] = np.where(concordam,
                               f"Prefeitura + CNEFE concordam: {nome_passo}",
                               f"Prefeitura (CNEFE discorda): {nome_passo}")
        p["confianca"] = np.where(concordam, "muito alta", "média")
        p["base"] = np.where(concordam, "Prefeitura + CNEFE", "Prefeitura")
        partes.append(p.drop(columns=["sufixo"]))

    # Resolvidos só pela Prefeitura.
    so_p = idx_p.difference(ambos)
    if len(so_p):
        p = res_pref.loc[so_p].copy()
        p["metodo"] = "Prefeitura: " + nome_passo + " — " + p["sufixo"].astype(str)
        p["base"] = "Prefeitura"
        partes.append(p.drop(columns=["sufixo"]))

    # Resolvidos pelo CNEFE e que a Prefeitura não resolveu.
    so_c = idx_c.difference(idx_p)
    if len(so_c):
        c = res_cnefe.loc[so_c].copy()
        c["metodo"] = "CNEFE: " + nome_passo + " — " + c["sufixo"].astype(str)
        c["base"] = "CNEFE"
        partes.append(c.drop(columns=["sufixo"]))

    if not partes:
        return pd.DataFrame()
    return pd.concat(partes)


def gravar_resultado(df_espacial, resultado, numero_passo):
    """Grava o resultado do passo no df_espacial (alterado no lugar), limpando antes o que o mesmo passo gravou."""
    antigos = df_espacial.index[df_espacial["passo"] == numero_passo]
    if len(antigos):
        df_espacial.loc[antigos, COLUNAS_NUMERICAS_RESULTADO] = np.nan
        df_espacial.loc[antigos, COLUNAS_TEXTO_RESULTADO] = None
        df_espacial.loc[antigos, "passo"] = np.nan
    if len(resultado) == 0:
        return
    # Grava só as colunas que o passo preencheu. O pandas alinha pelo número da linha (idx).
    for coluna in COLUNAS_RESULTADO:
        if coluna in resultado.columns:
            df_espacial.loc[resultado.index, coluna] = resultado[coluna]
    df_espacial.loc[resultado.index, "passo"] = numero_passo


def resumo_passo(df_espacial, numero_passo, nome_passo, entraram, resultado):
    """Mostra o resumo do passo: método, confiança e total acumulado."""
    total = len(df_espacial)
    com_coordenada = int(df_espacial["lat"].notna().sum())
    log.info(f"\n--- RESUMO DO PASSO {numero_passo}: {nome_passo} ---")
    log.info(f"Estabelecimentos que entraram: {entraram:,}")
    log.info(f"Resolvidos neste passo: {len(resultado):,} ({len(resultado) / total * 100:.1f}% de {total:,})")
    if len(resultado):
        log.info("\nMétodo:")
        for nome_metodo, qtd in resultado["metodo"].value_counts().items():
            log.info(f"  {nome_metodo}: {qtd:,}")
        log.info("\nConfiança:")
        contagem = resultado["confianca"].value_counts()
        for nome in ORDEM_CONFIANCA:
            if nome in contagem.index:
                log.info(f"  {nome}: {int(contagem[nome]):,} ({int(contagem[nome]) / len(resultado) * 100:.1f}%)")
    log.info("\nTotal acumulado em df_espacial, por passo:")
    for p in sorted(df_espacial["passo"].dropna().unique()):
        log.info(f"  Passo {int(p)}: {int((df_espacial['passo'] == p).sum()):,}")
    log.info(f"Com coordenada: {com_coordenada:,} ({com_coordenada / total * 100:.1f}%)")
    log.info(f"Ainda sem coordenada: {total - com_coordenada:,} ({(total - com_coordenada) / total * 100:.1f}%)")


def base_por_nucleo(ref):
    """Cópia da base de referência com o nome da via trocado pelo núcleo (o original não é alterado)."""
    t = ref.copy()
    t["via"] = aplicar_nucleo(t["via"])
    return t.dropna(subset=["via"]).reset_index(drop=True)


def agrupar_por_cep(ref):
    """Uma linha por CEP: quantidade de endereços, soma das coordenadas e a caixa (mínimos e máximos)."""
    return (ref[ref["cep"].notna()]
            .groupby("cep")
            .agg(n=("lat", "size"), soma_lat=("lat", "sum"), soma_lon=("lon", "sum"),
                 lat_min=("lat", "min"), lat_max=("lat", "max"),
                 lon_min=("lon", "min"), lon_max=("lon", "max")))

# Confiança de cada regra da interpolação: dentro do CEP da Receita (como no passo 4) e nos casos corrigidos.
CONFIANCAS_NUCLEO_CEP = {"A_perto": "média", "A_longe": "baixa", "B": "baixa", "C": "baixa"}
CONFIANCAS_TODAS_BAIXAS = {"A_perto": "baixa", "A_longe": "baixa", "B": "baixa", "C": "baixa"}


def limitar_confianca(serie, teto):
    """Rebaixa para 'teto' as confianças melhores que ele (ex.: teto 'baixa' transforma 'alta' em 'baixa')."""
    if teto is None:
        return serie
    limite = ORDEM_CONFIANCA.index(teto)
    return serie.map(lambda c: c if (c in ORDEM_CONFIANCA and ORDEM_CONFIANCA.index(c) >= limite) else teto)


def cep_corrigido(est, grupos):
    """
    Para cada estabelecimento, escolhe o CEP da base para a sua via: o único CEP que ela tem,
    ou, se tiver vários, o único cujo bairro (pela base de CEPs) é o mesmo bairro da Receita.
    Devolve duas colunas: o CEP escolhido e o motivo (vazios quando não dá para escolher).
    """
    # O bairro de cada CEP vem da base de CEPs dos Correios (definir_cep_bairro, no notebook).
    if CEP_BAIRRO is None:
        raise RuntimeError("cascata.definir_cep_bairro(...) precisa ser chamado antes (bairro de cada CEP).")
    ceps_por_via = grupos["ceps_por_via"]
    escolhidos, motivos = [], []
    for via, bairro in zip(est["via_e"], est["bairro"]):
        # CEPs da via nesta base (em ordem, para o resultado ser sempre o mesmo).
        candidatos = sorted(ceps_por_via.get(via, set()))
        if len(candidatos) == 1:
            escolhidos.append(candidatos[0]); motivos.append("via com um CEP só na base")
            continue
        if len(candidatos) > 1 and isinstance(bairro, str):
            mesmo_bairro = [c for c in candidatos if CEP_BAIRRO.get(c) == bairro]
            if len(mesmo_bairro) == 1:
                escolhidos.append(mesmo_bairro[0]); motivos.append("CEP desempatado pelo bairro")
                continue
        escolhidos.append(None); motivos.append(None)
    return pd.Series(escolhidos, index=est.index), pd.Series(motivos, index=est.index)


def sub_cep_numero(est, grupos):
    """CEP + número, com o núcleo do nome igual."""
    res = resolver_exato_com_cep(est[est["cep"].notna()], grupos, parecida=False)
    if len(res):
        res["sufixo"] = "CEP + número, " + res["sufixo"].astype(str)
        res["cep_usado"] = est.set_index("idx")["cep"].reindex(res.index)
    return res


def sub_interp_cep(est, grupos):
    """Interpolação entre números vizinhos, no CEP da Receita."""
    t = preparar_para_interpolar(est[est["cep"].notna()])
    res = interpolar(t, grupos["pontos"], ["cep", "via"], CONFIANCAS_NUCLEO_CEP)
    if len(res):
        res["sufixo"] = "interpolação no CEP, " + res["sufixo"].astype(str)
        res["cep_usado"] = est.set_index("idx")["cep"].reindex(res.index)
    return res


def sub_numero_cep_corrigido(est, grupos):
    """Mesmo núcleo e mesmo número, em outro CEP (como o passo 3)."""
    cn = grupos["via_num"].rename(columns={"via": "via_e"})
    cruz = est.merge(cn, on=["via_e", "num"], how="inner")
    if cruz.empty:
        return pd.DataFrame()
    cruz["lat"], cruz["lon"], cruz["espalhamento_m"] = media_e_espalhamento(cruz)
    um_cep = cruz["ceps"] <= 1
    aceito = um_cep | (cruz["espalhamento_m"] <= ESP_MAX_VARIOS_CEPS)
    perto = cruz["espalhamento_m"] <= ESP_ESPALHADO
    cruz["sufixo"] = np.select(
        [um_cep & perto, um_cep],
        ["número exato, CEP corrigido, um CEP na base, pontos próximos",
         "número exato, CEP corrigido, um CEP na base, pontos espalhados"],
        default=f"número exato, CEP corrigido, vários CEPs na base, pontos a até {ESP_MAX_VARIOS_CEPS} m")
    cruz["confianca"] = np.select([um_cep & perto, um_cep], ["média", "baixa"], default="média")
    cruz["cep_usado"] = cruz["cep_min"].where(um_cep)
    res = cruz[aceito].drop_duplicates("idx").set_index("idx")
    return res[["lat", "lon", "espalhamento_m", "sufixo", "confianca", "cep_usado"]]


def sub_interp_cep_corrigido(est, grupos):
    """Interpolação no CEP corrigido (único CEP da via, ou desempatado pelo bairro)."""
    cep_novo, motivo = cep_corrigido(est, grupos)
    t = est.assign(cep=cep_novo, motivo_cep=motivo)
    t = t[t["cep"].notna()]
    if t.empty:
        return pd.DataFrame()
    t_i = preparar_para_interpolar(t)
    res = interpolar(t_i, grupos["pontos"], ["cep", "via"], CONFIANCAS_TODAS_BAIXAS)
    if len(res):
        dados = t_i.set_index("idx")
        res["sufixo"] = ("interpolação, " + dados["motivo_cep"].reindex(res.index).astype(str)
                         + ", " + res["sufixo"].astype(str))
        res["cep_usado"] = dados["cep"].reindex(res.index)
    return res


def sub_interp_via_inteira(est, grupos):
    """
    Interpolação ao longo da via inteira, sem olhar o CEP (avenidas longas com vários CEPs).
    Só vale com vizinhos dos dois lados e a até DIST_MAX_VIZINHOS_VIA_INTEIRA metros um do outro:
    isso descarta ruas de mesmo nome em bairros diferentes, que ficam longe umas das outras.
    """
    t_i = preparar_para_interpolar(est)
    res = interpolar(t_i, grupos["pontos"], ["via"], CONFIANCAS_TODAS_BAIXAS)
    if len(res):
        res = res[(res["sufixo"] != "um vizinho só") & (res["espalhamento_m"] <= DIST_MAX_VIZINHOS_VIA_INTEIRA)].copy()
        res["sufixo"] = "interpolação na via inteira (CEP ignorado), " + res["sufixo"].astype(str)
    return res


def centro_da_via(t, grupos, rotulo, confianca_curta, confianca_longa):
    """Ponto central da via no CEP indicado na coluna 'cep' (média dos endereços da base)."""
    cn = grupos["cep_via"].rename(columns={"via": "via_e"})
    cruz = t.merge(cn, on=["cep", "via_e"], how="inner")
    if cruz.empty:
        return pd.DataFrame()
    cruz["lat"], cruz["lon"], cruz["espalhamento_m"] = media_e_espalhamento(cruz)
    via_curta = cruz["espalhamento_m"] <= EXTENSAO_VIA_MAX
    cruz["sufixo"] = (rotulo + np.where(cruz["num"].notna(), ", com número", ", sem número")
                      + np.where(via_curta, f", via até {EXTENSAO_VIA_MAX} m", f", via acima de {EXTENSAO_VIA_MAX} m"))
    cruz["confianca"] = np.where(via_curta, confianca_curta, confianca_longa)
    cruz["cep_usado"] = cruz["cep"]
    res = cruz.drop_duplicates("idx").set_index("idx")
    return res[["lat", "lon", "espalhamento_m", "sufixo", "confianca", "cep_usado"]]


def sub_centro_via_cep(est, grupos):
    """Centro da via no CEP da Receita."""
    return centro_da_via(est[est["cep"].notna()], grupos, "centro da via no CEP", "baixa", "muito baixa")


def sub_centro_via_cep_corrigido(est, grupos):
    """Centro da via no CEP corrigido (único CEP da via, ou desempatado pelo bairro)."""
    cep_novo, motivo = cep_corrigido(est, grupos)
    t = est.assign(cep=cep_novo, motivo_cep=motivo)
    t = t[t["cep"].notna()]
    if t.empty:
        return pd.DataFrame()
    res = centro_da_via(t, grupos, "centro da via, CEP corrigido", "muito baixa", "muito baixa")
    if len(res):
        res["sufixo"] = res["sufixo"].astype(str) + " (" + t.set_index("idx")["motivo_cep"].reindex(res.index).astype(str) + ")"
    return res


# Ordem dos métodos dos passos 9 e 10 (do mais preciso para o menos preciso).
# Cada um é tentado na Prefeitura e depois no CNEFE, e só quem sobrou passa para o seguinte.
# O terceiro valor diz se o método exige número.
SUBMETODOS_NUCLEO = [
    ("CEP + número", sub_cep_numero, True),
    ("interpolação no CEP", sub_interp_cep, True),
    ("número exato, CEP corrigido", sub_numero_cep_corrigido, True),
    ("interpolação, CEP corrigido", sub_interp_cep_corrigido, True),
    ("interpolação na via inteira", sub_interp_via_inteira, True),
    ("centro da via no CEP", sub_centro_via_cep, False),
    ("centro da via, CEP corrigido", sub_centro_via_cep_corrigido, False),
]


def rodar_cadeia_nucleo(grupos_nucleo, est, nome_passo, teto=None):
    """
    Roda os métodos de SUBMETODOS_NUCLEO em ordem, com os agrupamentos por núcleo (grupos_nucleo).
    Em cada método, a Prefeitura vem primeiro
    e o CNEFE resolve só o que ela não resolveu. 'teto' limita a melhor confiança possível.
    """
    restantes = est.copy()
    partes = []
    for nome_sub, funcao, exige_num in SUBMETODOS_NUCLEO:
        sub = restantes[restantes["num"].notna()] if exige_num else restantes
        if sub.empty:
            log.info(f"    [{nome_sub}] ninguém para tentar!")
            continue
        log.info(f"    [{nome_sub}] tentando {len(sub):,} estabelecimentos...")
        por_base = {nome_base: funcao(sub, grupos) for nome_base, grupos in grupos_nucleo.items()}
        res = combinar(por_base["Prefeitura"], por_base["CNEFE"], nome_passo)
        log.info(f"    [{nome_sub}] {len(res):,} resolvidos!")
        if len(res):
            partes.append(res)
            restantes = restantes[~restantes["idx"].isin(res.index)]
    if not partes:
        return pd.DataFrame()
    resultado = pd.concat(partes)
    resultado["confianca"] = limitar_confianca(resultado["confianca"], teto)
    return resultado


def centro_do_cep(t, grupos_cep, rotulo):
    """
    Ponto central do CEP indicado na coluna 'cep' (média de todos os endereços da base com aquele CEP).
    Só vale para CEP compacto: espalhamento até ESP_MAX_CENTRO_CEP metros.
    """
    cruz = t.merge(grupos_cep, left_on="cep", right_index=True, how="inner")
    if cruz.empty:
        return pd.DataFrame()
    cruz["lat"], cruz["lon"], cruz["espalhamento_m"] = media_e_espalhamento(cruz)
    cruz = cruz[cruz["espalhamento_m"] <= ESP_MAX_CENTRO_CEP].copy()
    if cruz.empty:
        return pd.DataFrame()
    compacto = cruz["espalhamento_m"] <= ESP_CENTRO_CEP_BAIXA
    cruz["sufixo"] = rotulo + np.where(compacto, f", CEP com até {ESP_CENTRO_CEP_BAIXA} m",
                                       f", CEP de {ESP_CENTRO_CEP_BAIXA + 1} a {ESP_MAX_CENTRO_CEP} m")
    cruz["confianca"] = np.where(compacto, "baixa", "muito baixa")
    cruz["cep_usado"] = cruz["cep"]
    res = cruz.drop_duplicates("idx").set_index("idx")
    return res[["lat", "lon", "espalhamento_m", "sufixo", "confianca", "cep_usado"]]
