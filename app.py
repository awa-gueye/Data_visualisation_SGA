"""
app.py – Point d'entrée principal du SGA (Système de Gestion Académique)
"""
import dash
from dash import html, dcc, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc

from config import APP_TITLE, SECRET_KEY
from auth import is_authenticated
from utils.db import init_db

# ─────────────────────────────────────────────────────────────────────────────
#  Initialisation Dash
# ─────────────────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    use_pages=False,
    suppress_callback_exceptions=True,
    title=APP_TITLE,
    update_title=None,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "theme-color", "content": "#0F0E17"},
    ],
)
server = app.server
server.secret_key = SECRET_KEY


# ─────────────────────────────────────────────────────────────────────────────
#  Layout racine
# ─────────────────────────────────────────────────────────────────────────────
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="session-store", storage_type="session"),   # Persiste la session
    html.Div(id="page-root"),
])


# ─────────────────────────────────────────────────────────────────────────────
#  Router principal
# ─────────────────────────────────────────────────────────────────────────────
@app.callback(
    Output("page-root", "children"),
    Input("url",           "pathname"),
    State("session-store", "data"),
)
def route(pathname, session_data):
    # ── Auth guard ──────────────────────────────────────────────────────────
    if pathname != "/login" and not is_authenticated(session_data):
        from pages.login import layout as login_layout
        return login_layout()

    user = session_data or {}

    routes = {
        "/":           _lazy("dashboard"),
        "/analytics":  _lazy("analytics"),
        "/courses":    _lazy("courses"),
        "/sessions":   _lazy("sessions"),
        "/attendance": _lazy("sessions"),   # alias
        "/students":   _lazy("students"),
        "/grades":     _lazy("grades"),
        "/reports":    _lazy("reports"),
        "/login":      _lazy("login"),
    }

    page_module = routes.get(pathname, routes["/"])
    return page_module.layout(user if pathname != "/login" else None)


def _lazy(module_name: str):
    """Import paresseux des modules de pages."""
    import importlib
    return importlib.import_module(f"pages.{module_name}")


# ─────────────────────────────────────────────────────────────────────────────
#  Logout
# ─────────────────────────────────────────────────────────────────────────────
@app.callback(
    Output("session-store", "data",    allow_duplicate=True),
    Output("url",           "pathname", allow_duplicate=True),
    Input("logout-btn",     "n_clicks"),
    prevent_initial_call=True,
)
def logout(n):
    if n:
        return None, "/login"
    return no_update, no_update


# ─────────────────────────────────────────────────────────────────────────────
#  Register callbacks de chaque module
# ─────────────────────────────────────────────────────────────────────────────
from pages import login, courses, sessions, students, grades, reports, analytics

login.register_callbacks(app)
courses.register_callbacks(app)
sessions.register_callbacks(app)
students.register_callbacks(app)
grades.register_callbacks(app)
reports.register_callbacks(app)
analytics.register_callbacks(app)


# ─────────────────────────────────────────────────────────────────────────────
#  Lancement
# ─────────────────────────────────────────────────────────────────────────────
# Initialisation automatique au démarrage (local + production)
try:
    init_db()
    print("✅ Base de données initialisée.")
    # Créer le compte admin par défaut s'il n'existe pas
    from utils.db import get_db
    from models import User
    from auth import hash_password
    from datetime import datetime
    db = get_db()
    if not db.query(User).filter(User.username == "admin").first():
        admin = User(
            username="admin", email="admin@sga.fr",
            full_name="Administrateur",
            password=hash_password("admin123"),
            role="admin", is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(admin)
        db.commit()
        print("✅ Compte admin créé.")
    db.close()
except Exception as e:
    print(f"⚠️ Erreur init DB : {e}")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)