# 2026-11-25 — Descrições, datas, saldo e ajuste ao limite

## O que foi feito
- Implementação (08, 09, 10, 07, diagnósticos de 02 e 03) e depois rodada real do 07 ao 10 (450 s), conferida pelos logs.
- Detalhes das decisões em `docs/decisoes.md` (seção de 25/11/2026).
- Manual atualizado para a v1.3: seção 4.1 (avisos do cache) e aviso de que as pastas de dados não vêm no `git clone`.
- README: aviso das pastas de dados e do cache do geocoding fora do Git.

## Resultados da rodada real
- 322.684 CNPJs, todos com coordenada; 136 pontos ajustados ao limite (133 normais, 3 a conferir, mesmo endereço a 1.227 m).
- 154.108 baixados; saldo em 15/11/2026: 168.576. Por ano (saldo): 2021 120.055, 2022 131.582, 2023 139.822, 2024 148.549, 2025 157.921, 2026 168.576.
- Motivo de situação 32 sem descrição (36 CNPJs): mantido como "(código fora da tabela)".
- Aviso `Connection reset by peer [10054]` (zmq) ao fim do 09: ruído do Windows; os arquivos foram gravados e conferidos.

## Pendências
Ver `docs/handoff/STATUS.md`.
