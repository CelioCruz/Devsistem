def format_currency(value):
    """Formata um número como moeda brasileira (R$)."""
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")