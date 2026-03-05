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
from pages import login, courses, sessions, students, grades, reports, analytics, dashboard

_ROUTES = {
    "/":           dashboard,
    "/analytics":  analytics,
    "/courses":    courses,
    "/sessions":   sessions,
    "/attendance": sessions,
    "/students":   students,
    "/grades":     grades,
    "/reports":    reports,
    "/login":      login,
}

@app.callback(
    Output("page-root", "children"),
    Input("url",           "pathname"),
    State("session-store", "data"),
)
def route(pathname, session_data):
    if pathname != "/login" and not is_authenticated(session_data):
        return login.layout()

    user = session_data or {}
    page_module = _ROUTES.get(pathname, dashboard)
    return page_module.layout(user if pathname != "/login" else None)


# ─────────────────────────────────────────────────────────────────────────────
#  Logout
# ─────────────────────────────────────────────────────────────────────────────
@app.callback(
    Output("session-store", "data",    allow_duplicate=True),
    Output("url",           "href",    allow_duplicate=True),
    Input("logout-btn",     "n_clicks"),
    State("session-store",  "data"),
    prevent_initial_call=True,
)
def logout(n, session_data):
    if n:
        try:
            from utils.db import get_db
            from models import User
            db = get_db()
            user_id = (session_data or {}).get("id")
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.role != "admin":
                    db.delete(user)
                    db.commit()
            db.close()
        except Exception as e:
            print(f"⚠️ Erreur suppression user : {e}")
        return None, "/login"
    return no_update, no_update


# ─────────────────────────────────────────────────────────────────────────────
#  Register callbacks de chaque module
# ─────────────────────────────────────────────────────────────────────────────
login.register_callbacks(app)
courses.register_callbacks(app)
sessions.register_callbacks(app)
students.register_callbacks(app)
grades.register_callbacks(app)
reports.register_callbacks(app)
analytics.register_callbacks(app)
dashboard.register_callbacks(app)


# ─────────────────────────────────────────────────────────────────────────────
#  Lancement
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Initialisation de la base de données...")
    init_db()
    print(f"✅ SGA démarré : http://localhost:8050")
    print("   Compte admin : admin / admin123")
    app.run(debug=True, host="0.0.0.0", port=8050)