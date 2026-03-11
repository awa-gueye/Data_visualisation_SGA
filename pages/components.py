"""
pages/components.py – Composants v2
Header + Navbar gérés par app.py
Les fonctions sidebar/topbar sont des aliases vides pour compatibilité
"""
from dash import html, dcc
from config import COLORS


# ── Navigation links (sans emojis) ───────────────────────────────────────────
NAV_LINKS = [
    ("/",           "Tableau de bord"),
    ("/students",   "Étudiants"),
    ("/courses",    "Cours"),
    ("/sessions",   "Séances"),
    ("/grades",     "Notes"),
    ("/analytics",  "Analyses"),
    ("/reports",    "Rapports"),
]

TNR = "'Times New Roman', Times, serif"


def sidebar(current_path: str = "/", user: dict = None) -> html.Div:
    """Header fixe (bande noire) + Navbar (bande bleue)."""
    user = user or {}
    full_name = user.get("full_name", "Utilisateur")
    role      = user.get("role", "")
    initials  = "".join(p[0].upper() for p in full_name.split()[:2]) if full_name else "U"

    # Liens navbar — style bouton visible
    nav_items = []
    for path, label in NAV_LINKS:
        is_active = current_path == path
        nav_items.append(
            dcc.Link(
                children=html.Span(label, style={"fontFamily": TNR, "fontSize": "11px"}),
                href=path,
                className="nav-link active" if is_active else "nav-link",
            )
        )

    # Séparateur + bouton logout
    nav_items.append(html.Div(className="nav-sep"))
    nav_items.append(
        html.Button(
            children=[html.Span("Déconnexion", style={"fontFamily": TNR, "fontSize": "11px"})],
            id="logout-btn",
            n_clicks=0,
            className="nav-logout",
        )
    )

    return html.Div([
        # ── Bande 1 : Header noir (hauteur augmentée) ────────────────────
        html.Header(id="site-header", children=[
            html.Div(className="header-brand", children=[
                # Zone logo — image si disponible, sinon carré bleu
                html.Div(className="header-logo", children=[
                    html.Img(
                        src="/assets/logo.png",
                        style={
                            "width": "100%", "height": "100%",
                            "objectFit": "contain", "borderRadius": "10px",
                        },
                        # Si l'image est absente, on affiche un texte fallback
                        id="header-logo-img",
                    ),
                ]),
                html.Div(className="header-brand-text", children=[
                    html.H1(
                        "SGA · Système de Gestion Académique",
                        style={"fontFamily": TNR},
                    ),
                    # Slogan en italique (remplace le texte ENSAE précédent)
                    html.Div(
                        "Piloter, analyser, décider.",
                        className="header-slogan",
                        style={
                            "fontStyle": "italic",
                            "fontFamily": TNR,
                            "fontSize": "12px",
                            "color": "rgba(255,255,255,0.65)",
                            "letterSpacing": "0.5px",
                            "marginTop": "3px",
                            "textTransform": "none",
                        },
                    ),
                ]),
            ]),
            html.Div(className="header-right", children=[
                html.Div(className="header-user-info", children=[
                    html.Div(full_name, className="header-user-name",
                             style={"fontFamily": TNR}),
                    html.Div(role.capitalize(), style={
                        "fontSize": "11px",
                        "color": "rgba(255,255,255,0.5)",
                        "marginTop": "1px",
                        "fontFamily": TNR,
                    }),
                ]),
                html.Div(initials, style={
                    "width": "42px", "height": "42px",
                    "borderRadius": "10px",
                    "background": "var(--bleu)",
                    "display": "flex", "alignItems": "center", "justifyContent": "center",
                    "fontFamily": TNR,
                    "fontWeight": "bold", "fontSize": "15px", "color": "#fff",
                    "border": "2px solid rgba(56,189,248,0.4)",
                    "flexShrink": "0",
                }),
            ]),
        ]),

        # ── Bande 2 : Navbar bleue ───────────────────────────────────────
        html.Nav(id="site-navbar", children=nav_items),

        # ── Spacer pour compenser les 2 barres fixes ─────────────────────
        html.Div(style={"height": "calc(var(--header-h) + var(--navbar-h))"}),
    ])


def topbar(title: str, subtitle: str = "") -> html.Div:
    """Conservé pour compatibilité — retourne un div vide (header géré par sidebar)."""
    return html.Div()


# ── Composants réutilisables ──────────────────────────────────────────────────

def kpi_card(icon: str, value: str, label: str,
             trend: str = "", color: str = "") -> html.Div:
    return html.Div(className=f"kpi-card {color}", children=[
        html.Span(icon, className="kpi-icon-wrap"),
        html.Div(value, className="kpi-value"),
        html.Div(label, className="kpi-label"),
        html.Div(trend, className="kpi-trend") if trend else None,
    ])


def badge(text: str, variant: str = "primary") -> html.Span:
    return html.Span(text, className=f"badge badge-{variant}")


def alert_msg(message: str, variant: str = "info",
              icon: str = "ℹ️") -> html.Div:
    return html.Div(className=f"alert alert-{variant}", children=[
        html.Span(icon, style={"fontSize": "16px"}),
        html.Span(message),
    ])


def progress_bar(pct: float, label: str = "") -> html.Div:
    if pct >= 80:
        color = "linear-gradient(90deg,#059669,var(--success))"
    elif pct >= 50:
        color = "linear-gradient(90deg,#D97706,var(--warning))"
    else:
        color = "linear-gradient(90deg,#DC2626,var(--danger))"

    return html.Div([
        html.Div(className="flex-between", style={"marginBottom": "5px"}, children=[
            html.Span(label, style={"fontSize": "12px", "color": "var(--white-40)"}),
            html.Span(f"{pct}%", style={
                "fontSize": "12px", "fontWeight": "700",
                "color": "var(--sky-light)"
            }),
        ]) if label else None,
        html.Div(className="progress-wrap", children=[
            html.Div(className="progress-bar",
                     style={"width": f"{pct}%", "background": color}),
        ]),
    ])


def card(children, title: str = None, actions=None, id: str = None) -> html.Div:
    header_el = None
    if title or actions:
        header_el = html.Div(className="card-header", children=[
            html.Div(className="card-title", children=[
                html.Div(title[0], className="card-title-icon") if title and title[0] in "📚📅🎓📝📊📄👥⚙️✅❌⭐🏠⚠️" else None,
                html.Span(title[2:] if title and title[0] in "📚📅🎓📝📊📄👥⚙️✅❌⭐🏠⚠️" else title),
            ]) if title else html.Div(),
            actions or html.Div(),
        ])

    props = {
        "className": "card fade-in",
        "children": [header_el, html.Div(children)],
    }
    if id:
        props["id"] = id
    return html.Div(**props)


def section_title(text: str, sub: str = "") -> html.Div:
    return html.Div(className="page-header-left", children=[
        html.H2(text, style={
            "fontFamily": "'Poppins',sans-serif",
            "fontSize": "25px", "fontWeight": "800",
            "letterSpacing": "-0.5px", "marginBottom": "3px",
        }),
        html.P(sub, style={"fontSize": "13px", "color": "var(--white-40)"}) if sub else None,
    ])


def empty_state(icon: str, title: str, sub: str = "") -> html.Div:
    return html.Div(style={"textAlign": "center", "padding": "60px 20px"}, children=[
        html.Div(icon, style={"fontSize": "52px", "marginBottom": "14px"}),
        html.Div(title, style={
            "fontSize": "17px", "fontWeight": "700",
            "color": "var(--white)", "marginBottom": "6px"
        }),
        html.Div(sub, style={"fontSize": "13px", "color": "var(--white-40)"}),
    ])