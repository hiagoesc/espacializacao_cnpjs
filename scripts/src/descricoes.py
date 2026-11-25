"""Descrições dos códigos da Receita Federal (natureza jurídica, motivo da situação, país, CNAE, situação...).

Os arquivos de descrição da Receita (ex.: F.K03200$Z.D61114.NATJUCSV) não têm linha de títulos:
a 1ª coluna é o código e a 2ª é a descrição, separadas por ponto e vírgula e com aspas.
"""
import pandas as pd                                  # tabelas

TEXTO_FORA_DA_TABELA = "(código fora da tabela)"     # código que existe na base, mas não está no arquivo de descrições
SEPARADOR_LISTA = " | "                              # separa os itens da lista de CNAEs secundários
TRAVESSAO = " – "                                    # separa o código da descrição ("4781400 – Comércio...")


def achar_arquivo(pasta, padrao):
    """Acha o arquivo da pasta que combina com o padrão (ex.: '*NATJUCSV'). Para com erro se não achar ou se achar mais de um."""
    achados = sorted(p for p in pasta.glob(padrao) if p.is_file())
    if not achados:
        raise FileNotFoundError(f"Nenhum arquivo '{padrao}' em {pasta}. Copie o arquivo de descrições da Receita para essa pasta.")
    if len(achados) > 1:
        nomes = ", ".join(p.name for p in achados)
        raise ValueError(f"Mais de um arquivo '{padrao}' em {pasta}: {nomes}. Deixe só o que vale.")
    return achados[0]


def normalizar_codigo(serie, digitos):
    """Código como texto de tamanho fixo: tira espaços, completa com zeros à esquerda ('2' vira '02'). Sem código fica vazio.

    Só aceita texto de dígitos; qualquer outra coisa vira vazio (e não vai achar descrição).
    """
    texto = serie.astype("object").where(serie.notna(), "").astype(str).str.strip()
    # Valores lidos como número podem vir com ".0" no fim (ex.: "2062.0"): tira.
    texto = texto.str.replace(r"\.0+$", "", regex=True)
    # Só vale texto feito de dígitos; o resto fica sem código.
    so_digitos = texto.str.fullmatch(r"\d+")
    return texto.str.zfill(digitos).where(so_digitos, None).astype(object)


def ler_tabela_codigos(arquivo, digitos, separador=";", codificacoes=("utf-8", "latin-1")):
    """Lê um arquivo de descrições (código;descrição, sem títulos). Devolve (tabela, codificação usada).

    A tabela é uma Series: o índice é o código normalizado e o valor é a descrição.
    Tenta as codificações na ordem; a primeira que lê sem erro vale.
    """
    ultima_falha = None
    for codificacao in codificacoes:
        try:
            bruto = pd.read_csv(arquivo, sep=separador, header=None, usecols=[0, 1], names=["codigo", "descricao"],
                                dtype=str, encoding=codificacao, keep_default_na=False)
            break
        except UnicodeDecodeError as falha:
            ultima_falha = falha
    else:
        raise ValueError(f"Não foi possível ler {arquivo.name} com {list(codificacoes)}: {ultima_falha}")

    bruto["codigo"] = normalizar_codigo(bruto["codigo"], digitos)
    bruto["descricao"] = bruto["descricao"].str.strip()
    # Linhas sem código (por exemplo, linha em branco no fim do arquivo) saem.
    bruto = bruto[bruto["codigo"].notna()]
    # Linhas exatamente iguais (mesmo código e mesma descrição) contam uma vez.
    bruto = bruto.drop_duplicates()
    # O mesmo código com descrições diferentes não dá para resolver sozinho: para com erro.
    repetidos = bruto[bruto["codigo"].duplicated(keep=False)]
    if len(repetidos):
        raise ValueError(f"{arquivo.name}: código com mais de uma descrição: {sorted(repetidos['codigo'].unique())[:10]}")
    return bruto.set_index("codigo")["descricao"], codificacao


def nomear(codigos, tabela, texto_fora=TEXTO_FORA_DA_TABELA):
    """Descrição de cada código. Sem código fica vazio; código que não está na tabela recebe 'texto_fora'.

    'codigos' precisa já estar normalizado (normalizar_codigo).
    """
    nomes = codigos.map(tabela)
    fora = codigos.notna() & nomes.isna()
    return nomes.where(~fora, texto_fora).astype(object)


def codigos_sem_descricao(codigos, tabela):
    """Contagem (código -> quantidade de linhas) dos códigos que existem na base mas não estão na tabela."""
    sem = codigos[codigos.notna() & ~codigos.isin(tabela.index)]
    return sem.value_counts()


def nomear_por_dicionario(serie, legenda, texto_fora):
    """Nome de cada código numérico, por um dicionário {1: 'Nula', 2: 'Ativa', ...}.

    Os códigos da Receita vêm como texto ('01', '2'): são lidos como número. Sem código fica vazio;
    código que não está no dicionário recebe 'texto_fora'.
    """
    numero = pd.to_numeric(serie, errors="coerce")
    nomes = numero.map(legenda)
    fora = numero.notna() & nomes.isna()
    return nomes.where(~fora, texto_fora).astype(object)


def nomear_sim_nao(serie, tem_registro, legenda, texto_branco, texto_fora):
    """Nome da opção pelo Simples ou pelo MEI (S, N ou em branco).

    - CNPJ sem registro no arquivo do Simples: vazio (a Receita não informa nada);
    - registro com o campo em branco: 'texto_branco' (o "outros" do layout da Receita);
    - registro com letra fora de S e N: 'texto_fora'.
    """
    valor = serie.fillna("").astype(str).str.strip().str.upper()
    nomes = valor.map(legenda).astype(object)
    branco = valor == ""
    nomes = nomes.where(~(tem_registro & branco), texto_branco)
    fora = tem_registro & ~branco & nomes.isna()
    nomes = nomes.where(~fora, texto_fora)
    # Sem registro no arquivo do Simples: vazio.
    return nomes.where(tem_registro, None)


def lista_cnae_secundaria(serie, tabela):
    """CNAEs secundários (códigos separados por vírgula) viram texto 'código – descrição | código – descrição'.

    Devolve (texto por linha, contagem dos códigos que não estão na tabela). Sem CNAE secundário fica vazio.
    """
    # Só as linhas que têm algum texto (a maioria dos CNPJs não tem CNAE secundário).
    com_texto = serie[serie.notna() & (serie.astype(str).str.strip() != "")]
    # Uma linha por código (explode repete o número da linha original para cada código da lista).
    itens = com_texto.astype(str).str.split(",").explode().str.strip()
    itens = normalizar_codigo(itens, 7)
    itens = itens[itens.notna()]
    descricao = itens.map(tabela)
    # Código fora da tabela: mostra o código mesmo assim, com o aviso no lugar da descrição.
    sem_descricao = descricao.isna()
    descricao = descricao.where(~sem_descricao, TEXTO_FORA_DA_TABELA)
    texto_item = itens + TRAVESSAO + descricao
    # Junta de volta: um texto por linha original, na ordem em que os códigos apareciam.
    por_linha = texto_item.groupby(level=0, sort=False).agg(SEPARADOR_LISTA.join)
    resultado = pd.Series(None, index=serie.index, dtype=object)
    resultado.loc[por_linha.index] = por_linha
    return resultado, itens[sem_descricao].value_counts()


def colocar_ao_lado(df, pares):
    """Reordena as colunas: cada grupo de colunas novas fica logo depois da coluna indicada.

    pares: lista de (coluna_existente, [colunas_novas]). Ex.: [("situacao_cadastral", ["situacao_nome"])].
    """
    novas = {c for _, lista in pares for c in lista}
    ordem = [c for c in df.columns if c not in novas]
    for coluna, lista in pares:
        posicao = ordem.index(coluna) + 1
        ordem[posicao:posicao] = lista
    return df[ordem]
