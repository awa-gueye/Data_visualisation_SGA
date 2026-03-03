"""
pages/components.py – Composants Dash réutilisables
"""
from dash import html, dcc
import dash_bootstrap_components as dbc
from config import COLORS


# ─────────────────────────────────────────────────────────────────────────────
#  Sidebar
# ─────────────────────────────────────────────────────────────────────────────
NAV_ITEMS = [
    {"section": "PRINCIPAL"},
    {"icon": "🏠", "label": "Tableau de Bord", "href": "/"},
    {"icon": "📊", "label": "Analytics",        "href": "/analytics"},
    {"section": "GESTION"},
    {"icon": "📚", "label": "Cours",            "href": "/courses"},
    {"icon": "📅", "label": "Séances",          "href": "/sessions"},
    {"icon": "✅", "label": "Présences",        "href": "/attendance"},
    {"section": "ÉTUDIANTS"},
    {"icon": "🎓", "label": "Étudiants",        "href": "/students"},
    {"icon": "📝", "label": "Notes",            "href": "/grades"},
    {"icon": "📄", "label": "Bulletins PDF",    "href": "/reports"},
    {"section": "ADMINISTRATION"},
    {"icon": "👥", "label": "Utilisateurs",     "href": "/users"},
    {"icon": "⚙️",  "label": "Paramètres",      "href": "/settings"},
]


def sidebar(current_path: str = "/", user: dict = None) -> html.Div:
    nav_children = []
    for item in NAV_ITEMS:
        if "section" in item:
            nav_children.append(
                html.Div(item["section"], className="nav-section-label")
            )
        else:
            is_active = current_path == item["href"]
            nav_children.append(
                dcc.Link(
                    [html.Span(item["icon"], className="icon"), item["label"]],
                    href=item["href"],
                    className=f"nav-link {'active' if is_active else ''}",
                )
            )

    name   = (user or {}).get("full_name", "Utilisateur")
    role   = (user or {}).get("role",      "teacher")
    initials = "".join(w[0].upper() for w in name.split()[:2])

    return html.Div(id="sidebar", children=[
        html.Div(className="sidebar-logo", children=[
            html.H1("SGA"),
            html.Span("SYSTÈME DE GESTION"),
        ]),
        html.Div(className="sidebar-nav", children=nav_children),
        html.Div(className="sidebar-footer", children=[
            html.Div(className="user-card", children=[
                html.Div(initials, className="user-avatar"),
                html.Div(className="user-info", children=[
                    html.Div(name,  className="user-name"),
                    html.Div("Admin" if role == "admin" else "Enseignant", className="user-role"),
                ]),
                html.Span("⋯", style={"color": COLORS["text_muted"]}),
            ], id="user-menu-trigger"),
        ]),
    ])


def topbar(title: str, subtitle: str = "") -> html.Div:
    return html.Div(id="topbar", children=[
        html.Div(className="topbar-title", children=[
            title,
            html.Div(subtitle, style={"fontSize": "12px", "color": COLORS["text_muted"], "fontWeight": "400"}) if subtitle else None,
        ]),
        html.Div(className="search-box", children=[
            html.Span("🔍", className="search-icon"),
            dcc.Input(
                id="global-search",
                placeholder="Rechercher...",
                type="text",
                debounce=True,
                className="dash-input",
            ),
        ]),
        html.Div(className="flex-center gap-8", children=[
            dcc.Link(
                html.Div([html.Span("🔔"), html.Span("3", className="notif-bubble", style={"position":"absolute","top":"-4px","right":"-4px"})],
                         style={"position":"relative","cursor":"pointer","padding":"8px 10px",
                                "background":"var(--surface2)","borderRadius":"var(--radius-sm)",
                                "border":"1px solid var(--border)"}),
                href="/reports",
            ),
        ]),
    ])


def kpi_card(icon: str, value: str, label: str, trend: str = "", color: str = None) -> html.Div:
    style = {}
    if color:
        style["--kpi-color"] = color
    return html.Div(className="kpi-card", style=style, children=[
        html.Span(icon, className="kpi-icon"),
        html.Div(value, className="kpi-value"),
        html.Div(label, className="kpi-label"),
        html.Div(trend, className="kpi-trend") if trend else None,
    ])


def badge(text: str, variant: str = "primary") -> html.Span:
    return html.Span(text, className=f"badge badge-{variant}")


def alert_msg(message: str, variant: str = "info", icon: str = "ℹ️") -> html.Div:
    return html.Div(className=f"alert alert-{variant}", children=[
        html.Span(icon),
        html.Span(message),
    ])


def progress_bar(pct: float, label: str = "") -> html.Div:
    color = "var(--success)" if pct >= 80 else "var(--warning)" if pct >= 50 else "var(--danger)"
    return html.Div([
        html.Div(className="flex-between", style={"marginBottom": "4px"}, children=[
            html.Span(label, style={"fontSize": "12px", "color": "var(--text-muted)"}),
            html.Span(f"{pct}%", style={"fontSize": "12px", "fontWeight": "600"}),
        ]) if label else None,
        html.Div(className="progress-wrap", children=[
            html.Div(className="progress-bar", style={"width": f"{pct}%", "background": color}),
        ]),
    ])


def card(children, title: str = None, actions=None, id: str = None) -> html.Div:
    header = None
    if title or actions:
        header = html.Div(className="card-header", children=[
            html.Div(title, className="card-title") if title else html.Div(),
            actions or html.Div(),
        ])
    props = {"className": "card fade-in", "children": [header, html.Div(children)]}
    if id is not None:
        props["id"] = id
    return html.Div(**props)


def section_title(text: str, sub: str = "") -> html.Div:
    return html.Div(style={"marginBottom": "20px"}, children=[
        html.H2(text, style={
            "fontFamily": "'Syne',sans-serif",
            "fontSize": "22px",
            "fontWeight": "800",
            "marginBottom": "4px",
        }),
        html.P(sub, style={"color": "var(--text-muted)", "fontSize": "13px"}) if sub else None,
    ])


def empty_state(icon: str, title: str, sub: str = "") -> html.Div:
    return html.Div(style={"textAlign": "center", "padding": "60px 20px"}, children=[
        html.Div(icon, style={"fontSize": "48px", "marginBottom": "16px"}),
        html.Div(title, style={"fontSize": "16px", "fontWeight": "600", "marginBottom": "6px"}),
        html.Div(sub, style={"fontSize": "13px", "color": "var(--text-muted)"}),
    ])


def loading_spinner() -> html.Div:
    return html.Div(style={
        "display": "flex", "justifyContent": "center", "alignItems": "center",
        "padding": "40px"
    }, children=[
        dcc.Loading(type="circle", color=COLORS["primary"], children=html.Div()),
    ])