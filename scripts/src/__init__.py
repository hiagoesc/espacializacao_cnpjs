"""Funções comuns do padrão de projetos (cópia própria deste projeto).

Módulos comuns (iguais em todos os projetos):
    config     - lê o config.yaml, acha a raiz do projeto e resolve caminhos
    registro   - log na tela e em arquivo (03_processamento/logs) e formatar_tempo
    validacao  - bloco padrão de validação de tabelas
    texto      - normalização de nomes de logradouro (a da RAIS; não usada na cascata deste projeto)
    geo        - tipos compatíveis com GeoPackage, conferência de CRS e distância em metros
    fontes     - arquivos editados à mão: existência, prioridade e backup
    planilha   - formatação de abas do Excel
    cache      - cache de leitura de bases pesadas (Parquet + manifesto)

Módulos SÓ deste projeto (não copiar para outros):
    enderecos  - limpeza de vias, números e bairros da cascata (bloco 12 do notebook original)
    cascata    - funções da cascata de espacialização (bloco 14 do notebook original)
    descricoes - descrições dos códigos da Receita (natureza jurídica, motivo, país, CNAE, situação...)
    datas      - datas da Receita (AAAAMMDD) para datas de verdade, e colunas de ano e mês
    saldo      - aberturas, encerramentos e saldo de estabelecimentos por mês e por ano (notebook 10)
"""
