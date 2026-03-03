import os

# ─── Database ───────────────────────────────────────────────────────────────
DATABASE_URL = "postgresql+psycopg2://sga_user:Ag200411@localhost:5432/sga_db"

# ─── App ────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "sga-super-secret-key-2024")
APP_TITLE  = "SGA · Système de Gestion Académique"

# ─── Auth ───────────────────────────────────────────────────────────────────
SESSION_TIMEOUT_MINUTES = 60

# ─── Pagination ─────────────────────────────────────────────────────────────
PAGE_SIZE = 20

# ─── Upload ─────────────────────────────────────────────────────────────────
UPLOAD_FOLDER   = "uploads"
MAX_FILE_SIZE   = 10 * 1024 * 1024   # 10 MB

# ─── PDF ────────────────────────────────────────────────────────────────────
PDF_OUTPUT_DIR  = "exports"

# ─── Thème couleurs (utilisé aussi dans les figures Plotly) ─────────────────
COLORS = {
    "primary"    : "#6C63FF",
    "secondary"  : "#FF6584",
    "accent"     : "#43E97B",
    "dark"       : "#0F0E17",
    "surface"    : "#1A1A2E",
    "surface2"   : "#16213E",
    "text"       : "#FFFFFE",
    "text_muted" : "#A7A9BE",
    "success"    : "#43E97B",
    "warning"    : "#F7B731",
    "danger"     : "#FF4757",
    "info"       : "#45AAF2",
}

PLOTLY_TEMPLATE = {
    "layout": {
        "paper_bgcolor" : "rgba(0,0,0,0)",
        "plot_bgcolor"  : "rgba(0,0,0,0)",
        "font"          : {"color": COLORS["text"], "family": "Inter"},
        "colorway"      : [COLORS["primary"], COLORS["secondary"],
                           COLORS["accent"],  COLORS["warning"],
                           COLORS["info"]],
        "xaxis": {"gridcolor": "rgba(255,255,255,0.05)", "zerolinecolor": "rgba(255,255,255,0.1)"},
        "yaxis": {"gridcolor": "rgba(255,255,255,0.05)", "zerolinecolor": "rgba(255,255,255,0.1)"},
    }
}