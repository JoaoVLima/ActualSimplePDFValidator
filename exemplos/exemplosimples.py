"""
Configurações para validação do pdf.

Opções:
- extrair_texto (bool): Habilita a extração de texto do documento.
- gerar_sumario (bool): Gera um sumário do conteúdo do documento.
- detectar_ciclos (bool): Detecta possíveis referências cíclicas no documento.
- nivel_detalhe (str): Define o nível de detalhe da análise ('Completo', 'Basico', 'Nulo').
- validar_xref (bool): Valida as referências cruzadas dentro do documento.
"""

extrair_texto=True
gerar_sumario=True
detectar_ciclos=True
nivel_detalhe='Completo'
validar_xref=True
