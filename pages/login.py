"""
pages/login.py – Page de connexion + inscription
"""
from dash import html, dcc, Input, Output, State, callback, no_update, ctx
import dash
from auth import login_user, register_user


def layout():
    return html.Div(id="login-page", children=[

        # ── Modal d'inscription ─────────────────────────────────────────────
        html.Div(id="register-modal-overlay", style={"display": "none"}, children=[
            html.Div(className="modal-card slide-up", children=[

                html.Div(className="modal-header", children=[
                    html.Div(className="login-logo", children=[
                        html.Div("✨", style={"fontSize": "36px", "marginBottom": "4px"}),
                        html.H2("Créer un compte"),
                        html.P("Rejoignez le Système de Gestion Académique"),
                    ]),
                    html.Button("✕", id="close-register-modal", className="modal-close-btn", n_clicks=0),
                ]),

                html.Div(id="register-error", style={"marginBottom": "12px"}),
                html.Div(id="register-success", style={"marginBottom": "12px"}),

                html.Div(className="form-row-2", children=[
                    html.Div(className="form-group", children=[
                        html.Label("Nom complet", className="form-label"),
                        dcc.Input(
                            id="reg-fullname", type="text",
                            placeholder="Jean Dupont",
                            className="dash-input", style={"width": "100%"},
                        ),
                    ]),
                    html.Div(className="form-group", children=[
                        html.Label("Nom d'utilisateur", className="form-label"),
                        dcc.Input(
                            id="reg-username", type="text",
                            placeholder="jean.dupont",
                            className="dash-input", style={"width": "100%"},
                        ),
                    ]),
                ]),

                html.Div(className="form-group", children=[
                    html.Label("Email", className="form-label"),
                    dcc.Input(
                        id="reg-email", type="email",
                        placeholder="jean.dupont@etablissement.fr",
                        className="dash-input", style={"width": "100%"},
                    ),
                ]),

                html.Div(className="form-row-2", children=[
                    html.Div(className="form-group", children=[
                        html.Label("Mot de passe", className="form-label"),
                        dcc.Input(
                            id="reg-password", type="password",
                            placeholder="••••••••",
                            className="dash-input", style={"width": "100%"},
                        ),
                    ]),
                    html.Div(className="form-group", children=[
                        html.Label("Confirmer le mot de passe", className="form-label"),
                        dcc.Input(
                            id="reg-password-confirm", type="password",
                            placeholder="••••••••",
                            className="dash-input", style={"width": "100%"},
                        ),
                    ]),
                ]),

                html.Div(className="form-group", children=[
                    html.Label("Rôle", className="form-label"),
                    dcc.Dropdown(
                        id="reg-role",
                        options=[
                            {"label": "👨‍🏫 Enseignant", "value": "teacher"},
                            {"label": "🛡️ Administrateur", "value": "admin"},
                        ],
                        value="teacher",
                        clearable=False,
                        className="dash-dropdown",
                        style={"width": "100%"},
                    ),
                ]),

                html.Div(className="modal-footer", children=[
                    html.Button(
                        "Annuler", id="cancel-register-btn",
                        className="btn btn-outline", n_clicks=0,
                        style={"flex": "1"},
                    ),
                    html.Button(
                        "Créer le compte →", id="register-btn",
                        className="btn btn-primary", n_clicks=0,
                        style={"flex": "2"},
                    ),
                ]),
            ]),
        ]),

        # ── Carte de connexion ──────────────────────────────────────────────
        html.Div(className="login-card slide-up", children=[

            html.Div(className="login-logo", children=[
                html.Div("🎓", style={"fontSize": "48px", "marginBottom": "8px"}),
                html.H1("SGA"),
                html.P("Système de Gestion Académique"),
            ]),

            html.Div(id="login-error", style={"marginBottom": "12px"}),

            html.Div(className="form-group", children=[
                html.Label("Identifiant", className="form-label"),
                dcc.Input(
                    id="login-username", type="text",
                    placeholder="admin ou email@domaine.fr",
                    className="dash-input", style={"width": "100%"},
                    n_submit=0,
                ),
            ]),

            html.Div(className="form-group", children=[
                html.Label("Mot de passe", className="form-label"),
                dcc.Input(
                    id="login-password", type="password",
                    placeholder="••••••••",
                    className="dash-input", style={"width": "100%"},
                    n_submit=0,
                ),
            ]),

            # ── Boutons côte à côte ─────────────────────────────────────────
            html.Div(className="login-actions", children=[
                html.Button(
                    "Se connecter →", id="login-btn",
                    className="btn btn-primary", n_clicks=0,
                    style={"flex": "2", "padding": "14px", "fontSize": "15px"},
                ),
                html.Button(
                    "S'inscrire", id="open-register-modal",
                    className="btn btn-register", n_clicks=0,
                    style={"flex": "1", "padding": "14px", "fontSize": "15px"},
                ),
            ]),

            html.Div(className="divider"),

            html.P(
                "Compte de démo: admin / admin123",
                style={"textAlign": "center", "fontSize": "12px", "color": "var(--text-muted)"},
            ),
        ]),
    ])


def register_callbacks(app):

    @app.callback(
        Output("register-modal-overlay", "style"),
        Input("open-register-modal",  "n_clicks"),
        Input("close-register-modal", "n_clicks"),
        Input("cancel-register-btn",  "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_register_modal(open_clicks, close_clicks, cancel_clicks):
        triggered = ctx.triggered_id
        if triggered == "open-register-modal":
            return {"display": "flex"}
        return {"display": "none"}

    @app.callback(
    Output("register-error",          "children"),
    Output("register-success",        "children"),
    Output("register-modal-overlay",  "style", allow_duplicate=True),
    Output("login-error",             "children", allow_duplicate=True),
    Input("register-btn", "n_clicks"),
    State("reg-fullname",         "value"),
    State("reg-username",         "value"),
    State("reg-email",            "value"),
    State("reg-password",         "value"),
    State("reg-password-confirm", "value"),
    State("reg-role",             "value"),
    prevent_initial_call=True,
    )
    def do_register(n_clicks, full_name, username, email, password, confirm, role):
        if not all([full_name, username, email, password, confirm]):
            return _error("Veuillez remplir tous les champs."), "", no_update, no_update
        if password != confirm:
            return _error("Les mots de passe ne correspondent pas."), "", no_update, no_update
        if len(password) < 6:
            return _error("Le mot de passe doit contenir au moins 6 caractères."), "", no_update, no_update
        ok, result = register_user(username, email, full_name, password, role or "teacher")
        if ok:
            # Ferme le modal et affiche le message de succès sur la page login
            return "", "", {"display": "none"}, _success(f"✅ Compte créé ! Connectez-vous avec « {username} ».")
        return _error(result), "", no_update, no_update

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
            return result, "", "/welcome"
        return no_update, _error(result), no_update


def _error(msg: str):
    return html.Div(className="alert alert-danger", children=[
        html.Span("⚠️ "), html.Span(msg)
    ])

def _success(msg: str):
    return html.Div(className="alert alert-success", children=[
        html.Span("✅ "), html.Span(msg)
    ])