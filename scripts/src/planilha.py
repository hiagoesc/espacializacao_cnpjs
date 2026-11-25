"""Formatação padrão de abas do Excel geradas com pandas + openpyxl."""


def formatar_excel(escritor, nome_aba):
    """Congela o cabeçalho, liga o filtro, deixa o cabeçalho em negrito e ajusta a largura das colunas."""
    from openpyxl.styles import Font, PatternFill
    aba = escritor.sheets[nome_aba]
    aba.freeze_panes = "A2"
    aba.auto_filter.ref = aba.dimensions
    for celula in aba[1]:
        celula.font = Font(bold=True)
        celula.fill = PatternFill("solid", fgColor="DDEBF7")
    for coluna in aba.columns:
        largura = max((len(str(c.value)) if c.value is not None else 0) for c in coluna[:200]) + 2
        aba.column_dimensions[coluna[0].column_letter].width = min(max(largura, 8), 60)
