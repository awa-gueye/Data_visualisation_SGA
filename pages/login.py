"""
pages/login.py – Page de connexion
"""
from dash import html, dcc, Input, Output, State, callback, no_update
import dash
from auth import login_user


def layout():
    return html.Div(id="login-page", children=[
        html.Div(className="login-card slide-up", children=[

            # ── Logo ──────────────────────────────────────────────────────
            html.Div(className="login-logo", children=[
                html.Div("🎓", style={"fontSize":"48px","marginBottom":"8px"}),
                html.H1("SGA"),
                html.P("Système de Gestion Académique"),
            ]),

            # ── Alerte erreur ───────────────────────────────────────────
            html.Div(id="login-error", style={"marginBottom":"12px"}),

            # ── Formulaire ──────────────────────────────────────────────
            html.Div(className="form-group", children=[
                html.Label("Identifiant", className="form-label"),
                dcc.Input(
                    id="login-username",
                    type="text",
                    placeholder="admin ou email@domaine.fr",
                    className="dash-input",
                    style={"width":"100%"},
                    n_submit=0,
                ),
            ]),

            html.Div(className="form-group", children=[
                html.Label("Mot de passe", className="form-label"),
                dcc.Input(
                    id="login-password",
                    type="password",
                    placeholder="••••••••",
                    className="dash-input",
                    style={"width":"100%"},
                    n_submit=0,
                ),
            ]),

            html.Button(
                "Se connecter →",
                id="login-btn",
                className="btn btn-primary",
                n_clicks=0,
                style={"width":"100%", "marginTop":"8px", "padding":"14px", "fontSize":"15px"},
            ),

            html.Div(className="divider"),

            html.P(
                "Compte de démo: admin / admin123",
                style={"textAlign":"center","fontSize":"12px","color":"var(--text-muted)"},
            ),
        ]),
    ])


def register_callbacks(app):
    @app.callback(
        Output("session-store", "data"),
        Output("login-error",   "children"),
        Output("url",           "pathname"),
        Input("login-btn",      "n_clicks"),
        Input("login-username", "n_submit"),
        Input("login-password", "n_submit"),
        State("login-username", "value"),
        State("login-password", "value"),
        prevent_initial_call=True,
    )
    def do_login(n_clicks, n_sub_user, n_sub_pass, username, password):
        if not username or not password:
            return no_update, _error("Veuillez remplir tous les champs."), no_update

        ok, result = login_user(username, password)
        if ok:
            return result, "", "/"
        return no_update, _error(result), no_update


def _error(msg: str):
    return html.Div(className="alert alert-danger", children=[
        html.Span("⚠️"), html.Span(msg)
    ])