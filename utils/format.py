"""
utils/format.py – Formatage des nombres en français
"""

def fr(value, decimals=1):
    """Formate un float en notation française (virgule décimale)."""
    if value is None:
        return "—"
    return f"{value:.{decimals}f}".replace(".", ",")

def fr_pct(value, decimals=1):
    """Formate un pourcentage en français."""
    return f"{fr(value, decimals)} %"

def fr_note(value, decimals=1):
    """Formate une note /20 en français."""
    return f"{fr(value, decimals)}/20"