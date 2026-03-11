"""
pages/students.py – Module 3 : Gestion des Etudiants (version enrichie v3)
Nouveautes :
  - Colonne telephone dans le tableau
  - Bouton Exporter avec choix : Excel, CSV, Stata, SPSS
  - Bouton Filtrer avec panneau de filtres avances + tri
  - Fiche PDF telechargeable (belle mise en page reportlab)
  - Graphiques fiche corriges (hauteur uniforme)
"""
from dash import html, dcc, Input, Output, State, no_update, ctx, ALL
from datetime import date
import plotly.graph_objects as go
import io, base64

from pages.components import sidebar, topbar, empty_state, alert_msg
from utils.db import get_db
from models import Student, Attendance, Grade, Course, Session
from config import COLORS
from utils.format import fr, fr_pct, fr_note
TNR  = "'Times New Roman', Times, serif"
DARK = "#0A1628"
GRAY = "#6B7280"
LGRAY= "#9CA3AF"
BLU  = "#0EA5E9"
GRN  = "#10B981"
RED  = "#EF4444"
ORG  = "#F59E0B"
BG   = "rgba(0,0,0,0)"

BTN  = {"border": "none", "cursor": "pointer", "fontFamily": TNR}


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers données
# ─────────────────────────────────────────────────────────────────────────────
def _student_stats(s):
    n_abs    = sum(1 for a in s.attendances if a.is_absent)
    n_just   = sum(1 for a in s.attendances if a.is_absent and a.justified)
    n_total  = len(s.attendances)
    abs_rate = round(n_abs / n_total * 100, 1) if n_total else 0
    grades   = s.grades
    avg = round(
        sum(g.score * g.coefficient for g in grades) /
        sum(g.coefficient for g in grades), 1
    ) if grades else None
    risk = "ok"
    if abs_rate > 25 or (avg is not None and avg < 8):
        risk = "danger"
    elif abs_rate > 15 or (avg is not None and avg < 10):
        risk = "warning"
    return dict(n_abs=n_abs, n_just=n_just, n_total=n_total,
                abs_rate=abs_rate, avg=avg, risk=risk)


def _global_kpis():
    db = get_db()
    try:
        students = db.query(Student).filter_by(is_active=True).all()
        risks = {"ok": 0, "warning": 0, "danger": 0}
        avgs  = []
        for s in students:
            st = _student_stats(s)
            risks[st["risk"]] += 1
            if st["avg"] is not None:
                avgs.append(st["avg"])
        result = dict(n_total=len(students), risks=risks,
                      global_avg=round(sum(avgs)/len(avgs), 1) if avgs else 0)
    finally:
        db.close()
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Micro-composants UI
# ─────────────────────────────────────────────────────────────────────────────
def _risk_badge(risk):
    cfg = {
        "ok":      ("#ECFDF5", GRN, "Bon suivi"),
        "warning": ("#FFFBEB", ORG, "A surveiller"),
        "danger":  ("#FEF2F2", RED, "En difficulte"),
    }
    bg, clr, txt = cfg[risk]
    return html.Span(txt, style={
        "background": bg, "color": clr,
        "padding": "3px 10px", "borderRadius": "99px",
        "fontSize": "10px", "fontWeight": "bold",
        "fontFamily": TNR, "whiteSpace": "nowrap",
    })


def _kpi_box(value, label, color, bg):
    return html.Div(style={
        "background": "#fff", "borderRadius": "14px",
        "padding": "18px 20px", "boxShadow": "0 2px 10px rgba(10,22,40,0.07)",
        "borderLeft": f"4px solid {color}",
    }, children=[
        html.Div(value, style={
            "fontFamily": TNR, "fontWeight": "bold",
            "fontSize": "24px", "color": color, "lineHeight": "1",
        }),
        html.Div(label, style={
            "fontSize": "11px", "color": GRAY,
            "fontFamily": TNR, "marginTop": "5px",
        }),
    ])


def _stat_chip(value, label, color, bg):
    return html.Div(style={
        "background": bg, "borderRadius": "12px",
        "padding": "14px 16px", "textAlign": "center",
        "borderLeft": f"3px solid {color}",
    }, children=[
        html.Div(value, style={
            "fontFamily": TNR, "fontSize": "22px",
            "fontWeight": "bold", "color": DARK, "lineHeight": "1",
        }),
        html.Div(label, style={
            "fontSize": "11px", "color": GRAY,
            "marginTop": "4px", "fontFamily": TNR,
        }),
    ])


def _card_style():
    return {
        "background": "#fff", "borderRadius": "12px",
        "padding": "14px 16px", "boxShadow": "0 2px 8px rgba(10,22,40,0.06)",
        "border": "1px solid #F3F4F6",
    }


def _empty_fig(h=240):
    fig = go.Figure()
    fig.add_annotation(text="Aucune donnee", xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False,
                       font=dict(color=LGRAY, size=12, family=TNR))
    fig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG,
                      height=h, margin=dict(l=8, r=8, t=8, b=8))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  Layout
# ─────────────────────────────────────────────────────────────────────────────
def layout(user: dict = None):
    kpis = _global_kpis()
    return html.Div(id="app-shell", children=[
        sidebar("/students", user),
        html.Div(id="main-content", children=[
            topbar("Etudiants", "Gestion des inscriptions"),
            html.Div(id="page-content", children=[

                # En-tete
                html.Div(style={
                    "display": "flex", "alignItems": "center",
                    "justifyContent": "space-between", "marginBottom": "20px",
                }, children=[
                    html.Div([
                        html.Div("Gestion des Etudiants", style={
                            "fontFamily": TNR, "fontSize": "22px",
                            "fontWeight": "bold", "color": DARK,
                        }),
                        html.Div("Suivi individuel · Absences · Notes · Indicateurs de risque",
                                 style={"fontSize": "12px", "color": LGRAY, "fontFamily": TNR}),
                    ]),
                    html.Div(style={"display": "flex", "gap": "8px", "position": "relative"}, children=[
                        # Bouton Exporter
                        html.Div(style={"position": "relative"}, children=[
                            html.Button("Exporter", id="export-btn-toggle", n_clicks=0, style={
                                **BTN,
                                "padding": "9px 18px", "borderRadius": "8px",
                                "background": "#fff", "color": DARK,
                                "border": "1px solid #E5E7EB", "fontSize": "12px",
                                "fontWeight": "bold",
                            }),
                            # Menu dropdown export
                            html.Div(id="export-dropdown-menu", style={
                                "display": "none", "position": "absolute",
                                "top": "100%", "right": "0", "marginTop": "4px",
                                "background": "#fff", "borderRadius": "10px",
                                "boxShadow": "0 8px 24px rgba(10,22,40,0.12)",
                                "border": "1px solid #E5E7EB",
                                "minWidth": "160px", "zIndex": "999", "overflow": "hidden",
                            }, children=[
                                _export_item("Excel (.xlsx)",  "export-excel"),
                                _export_item("CSV (.csv)",     "export-csv"),
                                _export_item("Stata (.dta)",   "export-stata"),
                                _export_item("SPSS (.sav)",    "export-spss"),
                            ]),
                        ]),
                        html.Button("+ Nouvel etudiant", id="open-student-modal",
                                    className="btn btn-primary", n_clicks=0,
                                    style={"fontFamily": TNR, "fontSize": "12px"}),
                    ]),
                ]),

                html.Div(id="student-feedback"),

                # KPIs
                html.Div(style={
                    "display": "grid", "gridTemplateColumns": "repeat(4, 1fr)",
                    "gap": "12px", "marginBottom": "20px",
                }, children=[
                    _kpi_box(str(kpis["n_total"]),          "Etudiants actifs", BLU, "#E0F2FE"),
                    _kpi_box(str(kpis["risks"]["ok"]),       "Bon suivi",        GRN, "#ECFDF5"),
                    _kpi_box(str(kpis["risks"]["warning"]),  "A surveiller",     ORG, "#FFFBEB"),
                    _kpi_box(str(kpis["risks"]["danger"]),   "En difficulte",    RED, "#FEF2F2"),
                ]),

                # Barre recherche + filtrer
                html.Div(style={
                    "background": "#fff", "borderRadius": "12px",
                    "padding": "12px 18px", "marginBottom": "10px",
                    "boxShadow": "0 2px 8px rgba(10,22,40,0.06)",
                    "display": "flex", "alignItems": "center", "gap": "12px",
                }, children=[
                    dcc.Input(id="student-search",
                              placeholder="Rechercher par nom, prenom, email ou code...",
                              debounce=True, className="dash-input",
                              style={"flex": "1", "fontFamily": TNR, "fontSize": "12px"}),
                    html.Div(style={"width": "1px", "height": "26px", "background": "#E5E7EB"}),
                    html.Button("Filtrer", id="filter-panel-toggle", n_clicks=0, style={
                        **BTN,
                        "padding": "7px 16px", "borderRadius": "8px",
                        "background": "#F0F9FF", "color": BLU,
                        "border": f"1px solid {BLU}", "fontSize": "12px",
                        "fontWeight": "bold",
                    }),
                ]),

                # Panneau filtres avances (caché par défaut)
                html.Div(id="filter-panel", style={"display": "none"}, children=[
                    html.Div(style={
                        "background": "#fff", "borderRadius": "12px",
                        "padding": "18px", "marginBottom": "10px",
                        "boxShadow": "0 2px 12px rgba(10,22,40,0.08)",
                        "border": f"1px solid {BLU}",
                    }, children=[
                        html.Div("Filtres avances", style={
                            "fontFamily": TNR, "fontWeight": "bold",
                            "fontSize": "13px", "color": DARK, "marginBottom": "14px",
                        }),
                        html.Div(style={
                            "display": "grid",
                            "gridTemplateColumns": "1fr 1fr 1fr 1fr",
                            "gap": "14px", "marginBottom": "14px",
                        }, children=[
                            # Filtre profil de risque
                            html.Div([
                                html.Label("Profil de risque", style={
                                    "fontSize": "11px", "fontWeight": "bold",
                                    "color": GRAY, "fontFamily": TNR,
                                    "display": "block", "marginBottom": "5px",
                                }),
                                dcc.Dropdown(
                                    id="student-risk-filter",
                                    options=[
                                        {"label": "Tous", "value": "all"},
                                        {"label": "Bon suivi", "value": "ok"},
                                        {"label": "A surveiller", "value": "warning"},
                                        {"label": "En difficulte", "value": "danger"},
                                    ],
                                    value="all", clearable=False,
                                    style={"fontSize": "12px"},
                                ),
                            ]),
                            # Filtre moyenne min
                            html.Div([
                                html.Label("Moyenne minimum", style={
                                    "fontSize": "11px", "fontWeight": "bold",
                                    "color": GRAY, "fontFamily": TNR,
                                    "display": "block", "marginBottom": "5px",
                                }),
                                dcc.Input(id="filter-avg-min", type="number",
                                          placeholder="Ex: 10", min=0, max=20,
                                          className="dash-input",
                                          style={"width": "100%", "fontFamily": TNR, "fontSize": "12px"}),
                            ]),
                            # Filtre absences max
                            html.Div([
                                html.Label("Absences maximum", style={
                                    "fontSize": "11px", "fontWeight": "bold",
                                    "color": GRAY, "fontFamily": TNR,
                                    "display": "block", "marginBottom": "5px",
                                }),
                                dcc.Input(id="filter-abs-max", type="number",
                                          placeholder="Ex: 5", min=0,
                                          className="dash-input",
                                          style={"width": "100%", "fontFamily": TNR, "fontSize": "12px"}),
                            ]),
                            # Tri
                            html.Div([
                                html.Label("Trier par", style={
                                    "fontSize": "11px", "fontWeight": "bold",
                                    "color": GRAY, "fontFamily": TNR,
                                    "display": "block", "marginBottom": "5px",
                                }),
                                dcc.Dropdown(
                                    id="filter-sort",
                                    options=[
                                        {"label": "Nom (A-Z)",          "value": "name_asc"},
                                        {"label": "Nom (Z-A)",          "value": "name_desc"},
                                        {"label": "Moyenne (croissant)","value": "avg_asc"},
                                        {"label": "Moyenne (decroissant)","value": "avg_desc"},
                                        {"label": "Absences (croissant)","value": "abs_asc"},
                                        {"label": "Absences (decroissant)","value": "abs_desc"},
                                    ],
                                    value="name_asc", clearable=False,
                                    style={"fontSize": "12px"},
                                ),
                            ]),
                        ]),
                        html.Div(style={"display": "flex", "justifyContent": "flex-end", "gap": "8px"}, children=[
                            html.Button("Reinitialiser", id="filter-reset-btn", n_clicks=0, style={
                                **BTN,
                                "padding": "7px 14px", "borderRadius": "7px",
                                "background": "#F3F4F6", "color": GRAY,
                                "border": "1px solid #E5E7EB", "fontSize": "11px",
                            }),
                            html.Button("Appliquer les filtres", id="filter-apply-btn", n_clicks=0, style={
                                **BTN,
                                "padding": "7px 16px", "borderRadius": "7px",
                                "background": BLU, "color": "#fff",
                                "fontSize": "11px", "fontWeight": "bold",
                            }),
                        ]),
                    ]),
                ]),

                html.Div(id="students-table"),

                # Overlay fiche (persistant dans le DOM - evite les erreurs de callback)
                html.Div(id="student-profile-overlay", style={"display": "none"}, children=[
                    html.Div(style={
                        "position": "fixed", "inset": "0", "zIndex": "9000",
                        "background": "rgba(10,22,40,0.55)",
                        "display": "flex", "alignItems": "center", "justifyContent": "center",
                        "overflowY": "auto", "padding": "20px",
                    }, children=[
                        html.Div(style={
                            "background": "#F8FAFC", "borderRadius": "18px",
                            "maxWidth": "860px", "width": "96%",
                            "maxHeight": "90vh", "overflowY": "auto",
                            "position": "relative",
                            "boxShadow": "0 24px 64px rgba(10,22,40,0.22)",
                        }, children=[
                            html.Div(id="student-profile-content"),
                            # Boutons fixes toujours dans le DOM - overlay permanent
                            html.Div(style={
                                "position": "absolute", "top": "14px", "right": "14px",
                                "zIndex": "20", "display": "flex", "gap": "8px",
                            }, children=[
                                html.Button("Telecharger la fiche", id="download-pdf-btn-static",
                                            n_clicks=0, style={
                                                "border": "none", "cursor": "pointer",
                                                "fontFamily": TNR, "padding": "8px 16px",
                                                "borderRadius": "8px", "background": BLU,
                                                "color": "#fff", "fontSize": "11px",
                                                "fontWeight": "bold",
                                            }),
                                html.Button("✕", id="close-profile-modal", n_clicks=0, style={
                                                "border": "1px solid rgba(255,255,255,0.25)",
                                                "cursor": "pointer", "fontFamily": TNR,
                                                "background": "rgba(10,22,40,0.75)",
                                                "borderRadius": "50%", "width": "32px", "height": "32px",
                                                "fontSize": "14px", "color": "#fff",
                                            }),
                            ]),
                        ]),
                    ]),
                ]),

                html.Div(id="student-modal-container", children=[_student_modal_static()]),

                dcc.Store(id="students-refresh",    data=0),
                dcc.Store(id="selected-student-id", data=None),
                dcc.Store(id="stu-edit-id",          data=None),
                dcc.Download(id="download-students-file"),
            ]),
        ]),
    ])


def _export_item(label, btn_id):
    return html.Button(label, id=btn_id, n_clicks=0, style={
        **BTN,
        "display": "block", "width": "100%",
        "padding": "10px 16px", "textAlign": "left",
        "background": "transparent", "fontSize": "12px", "color": DARK,
        "borderBottom": "1px solid #F3F4F6",
    })


# ─────────────────────────────────────────────────────────────────────────────
#  Callbacks
# ─────────────────────────────────────────────────────────────────────────────
def register_callbacks(app):

    # ── Toggle export dropdown ────────────────────────────────────────────────
    @app.callback(
        Output("export-dropdown-menu", "style"),
        Input("export-btn-toggle", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_export(n):
        if n and n % 2 == 1:
            return {
                "display": "block", "position": "absolute",
                "top": "100%", "right": "0", "marginTop": "4px",
                "background": "#fff", "borderRadius": "10px",
                "boxShadow": "0 8px 24px rgba(10,22,40,0.12)",
                "border": "1px solid #E5E7EB",
                "minWidth": "160px", "zIndex": "999", "overflow": "hidden",
            }
        return {"display": "none"}

    # ── Toggle panneau filtres ────────────────────────────────────────────────
    @app.callback(
        Output("filter-panel", "style"),
        Input("filter-panel-toggle", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_filter(n):
        if n and n % 2 == 1:
            return {"display": "block"}
        return {"display": "none"}

    # ── Reinitialiser filtres ─────────────────────────────────────────────────
    @app.callback(
        Output("student-risk-filter", "value"),
        Output("filter-avg-min",      "value"),
        Output("filter-abs-max",      "value"),
        Output("filter-sort",         "value"),
        Input("filter-reset-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_filters(n):
        return "all", None, None, "name_asc"

    # ── Tableau ───────────────────────────────────────────────────────────────
    @app.callback(
        Output("students-table", "children"),
        Input("students-refresh",    "data"),
        Input("student-search",      "value"),
        Input("student-risk-filter", "value"),
        Input("filter-avg-min",      "value"),
        Input("filter-abs-max",      "value"),
        Input("filter-sort",         "value"),
        Input("filter-apply-btn",    "n_clicks"),
    )
    def refresh_table(_, search, risk_filter, avg_min, abs_max, sort_by, _apply):
        db = get_db()
        try:
            q = db.query(Student).filter_by(is_active=True)
            if search:
                sv = f"%{search.lower()}%"
                from sqlalchemy import or_, func as sqlfunc
                q = q.filter(or_(
                    sqlfunc.lower(Student.first_name).like(sv),
                    sqlfunc.lower(Student.last_name).like(sv),
                    sqlfunc.lower(Student.email).like(sv),
                    sqlfunc.lower(Student.student_code).like(sv),
                ))
            students = q.order_by(Student.last_name, Student.first_name).all()
            enriched = [(s, _student_stats(s)) for s in students]
        finally:
            db.close()

        # Filtres
        if risk_filter and risk_filter != "all":
            enriched = [(s, st) for s, st in enriched if st["risk"] == risk_filter]
        if avg_min is not None:
            enriched = [(s, st) for s, st in enriched
                        if st["avg"] is not None and st["avg"] >= float(avg_min)]
        if abs_max is not None:
            enriched = [(s, st) for s, st in enriched if st["n_abs"] <= int(abs_max)]

        # Tri
        if sort_by == "name_asc":
            enriched.sort(key=lambda x: x[0].last_name)
        elif sort_by == "name_desc":
            enriched.sort(key=lambda x: x[0].last_name, reverse=True)
        elif sort_by == "avg_asc":
            enriched.sort(key=lambda x: x[1]["avg"] or 0)
        elif sort_by == "avg_desc":
            enriched.sort(key=lambda x: x[1]["avg"] or 0, reverse=True)
        elif sort_by == "abs_asc":
            enriched.sort(key=lambda x: x[1]["n_abs"])
        elif sort_by == "abs_desc":
            enriched.sort(key=lambda x: x[1]["n_abs"], reverse=True)

        if not enriched:
            return empty_state("", "Aucun etudiant trouve",
                               "Modifiez votre recherche ou les filtres.")

        # Colonnes : Etudiant | Email | Tel | Absences | Assiduite | Moyenne | Profil | Actions
        cols = "1.4fr 1.4fr 0.9fr 0.8fr 1.1fr 0.8fr 0.9fr auto"
        headers = ["Etudiant", "Email", "Telephone", "Absences", "Assiduite", "Moyenne", "Profil", "Actions"]

        header = html.Div(style={
            "display": "grid", "gridTemplateColumns": cols,
            "gap": "8px", "padding": "10px 16px",
            "background": DARK, "borderRadius": "12px 12px 0 0",
        }, children=[
            html.Span(h, style={
                "fontSize": "10px", "fontWeight": "bold",
                "textTransform": "uppercase", "color": "rgba(255,255,255,0.55)",
                "letterSpacing": "0.8px", "fontFamily": TNR,
            }) for h in headers
        ])

        rows = []
        for i, (s, st) in enumerate(enriched):
            abs_color = RED if st["abs_rate"] > 20 else ORG if st["abs_rate"] > 10 else GRN
            avg_color = RED if (st["avg"] or 0) < 10 else GRN if (st["avg"] or 0) >= 14 else BLU
            pres_pct  = 100 - st["abs_rate"]
            bar_color = GRN if pres_pct >= 85 else ORG if pres_pct >= 75 else RED
            phone_txt = s.phone or "—"

            rows.append(html.Div(style={
                "display": "grid", "gridTemplateColumns": cols,
                "alignItems": "center", "gap": "8px",
                "padding": "10px 16px",
                "background": "#F9FAFB" if i % 2 == 0 else "#fff",
                "borderBottom": "1px solid #F3F4F6",
            }, id={"type": "student-row", "index": s.id}, children=[

                # Nom + initiales
                html.Div(style={"display": "flex", "alignItems": "center", "gap": "9px"}, children=[
                    html.Div((s.first_name[0] + s.last_name[0]).upper(), style={
                        "width": "34px", "height": "34px", "borderRadius": "9px",
                        "background": f"linear-gradient(135deg,{BLU},{COLORS['secondary']})",
                        "display": "flex", "alignItems": "center", "justifyContent": "center",
                        "fontWeight": "bold", "fontSize": "12px", "color": "#fff",
                        "flexShrink": "0", "fontFamily": TNR,
                    }),
                    html.Div([
                        html.Div(s.full_name, style={
                            "fontWeight": "bold", "fontSize": "12px",
                            "color": DARK, "fontFamily": TNR,
                        }),
                        html.Div(s.student_code, style={
                            "fontSize": "10px", "color": LGRAY, "fontFamily": TNR,
                        }),
                    ]),
                ]),

                # Email
                html.Div(s.email, style={
                    "fontSize": "11px", "color": GRAY, "fontFamily": TNR,
                    "overflow": "hidden", "textOverflow": "ellipsis",
                }),

                # Telephone
                html.Div(phone_txt, style={
                    "fontSize": "11px", "color": GRAY, "fontFamily": TNR,
                }),

                # Absences
                html.Div(style={"display": "flex", "alignItems": "center", "gap": "5px"}, children=[
                    html.Div(style={"width": "7px", "height": "7px",
                                    "borderRadius": "50%", "background": abs_color}),
                    html.Span(f"{st['n_abs']}", style={
                        "fontSize": "12px", "fontWeight": "bold",
                        "color": abs_color, "fontFamily": TNR,
                    }),
                ]),

                # Barre assiduite
                html.Div(style={"display": "flex", "flexDirection": "column", "gap": "3px"}, children=[
                    html.Div(style={
                        "background": "#F3F4F6", "borderRadius": "99px",
                        "height": "5px", "overflow": "hidden",
                    }, children=[
                        html.Div(style={
                            "width": f"{pres_pct}%", "height": "100%",
                            "borderRadius": "99px", "background": bar_color,
                        }),
                    ]),
                    html.Span(f"{pres_pct:.0f}%", style={
                        "fontSize": "10px", "color": LGRAY, "fontFamily": TNR,
                    }),
                ]),

                # Moyenne
                html.Div(f"{st['avg']}/20" if st["avg"] else "–", style={
                    "fontWeight": "bold", "fontSize": "12px",
                    "color": avg_color, "fontFamily": TNR,
                }),

                # Badge risque
                _risk_badge(st["risk"]),

                # Actions
                html.Div(style={"display": "flex", "gap": "4px"}, children=[
                    html.Button("Fiche", id={"type": "view-student-btn", "index": s.id},
                                n_clicks=0, style={
                                    **BTN, "padding": "5px 9px", "borderRadius": "6px",
                                    "background": BLU, "color": "#fff",
                                    "fontSize": "10px", "fontWeight": "bold",
                                }),
                    html.Button("Edit", id={"type": "edit-student-btn", "index": s.id},
                                n_clicks=0, style={
                                    **BTN, "padding": "5px 9px", "borderRadius": "6px",
                                    "background": "#F3F4F6", "color": DARK,
                                    "border": "1px solid #E5E7EB", "fontSize": "10px",
                                }),
                    html.Button("X", id={"type": "del-student-btn", "index": s.id},
                                n_clicks=0, style={
                                    **BTN, "padding": "5px 7px", "borderRadius": "6px",
                                    "background": "#FEF2F2", "color": RED,
                                    "border": "1px solid #FECACA", "fontSize": "11px",
                                }),
                ]),
            ]))

        return html.Div(style={
            "background": "#fff", "borderRadius": "12px",
            "boxShadow": "0 2px 10px rgba(10,22,40,0.07)", "overflow": "hidden",
        }, children=[header, html.Div(rows)])

    # ── Fiche individuelle ────────────────────────────────────────────────────
    @app.callback(
        Output("student-profile-overlay",  "style"),
        Output("student-profile-content",  "children"),
        Output("selected-student-id",      "data"),
        Input({"type": "view-student-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def show_profile(n_clicks_list):
        HIDE = {"display": "none"}
        if not any(n_clicks_list):
            return HIDE, no_update, no_update
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            return HIDE, no_update, no_update
        sid = triggered["index"]
        profile_content = _student_profile_content(sid)
        return {"display": "block"}, profile_content, sid

    # ── Ouvrir modal ajout/edit ───────────────────────────────────────────────
    @app.callback(
        Output("student-modal-inner", "style"),
        Output("modal-title",  "children"),
        Output("stu-first",    "value"),
        Output("stu-last",     "value"),
        Output("stu-email",    "value"),
        Output("stu-code",     "value"),
        Output("stu-phone",    "value"),
        Output("stu-birth",    "date"),
        Output("stu-edit-id",  "data"),
        Input("open-student-modal", "n_clicks"),
        Input({"type": "edit-student-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def open_modal(new_click, edit_clicks):
        SHOW = {"display": "block"}
        NUP  = [no_update] * 9
        triggered = ctx.triggered_id
        if triggered == "open-student-modal":
            if not new_click: return NUP
            return SHOW, "Nouvel etudiant", "", "", "", "", "", None, None
        if isinstance(triggered, dict) and triggered.get("type") == "edit-student-btn":
            if not any(edit_clicks): return NUP
            db = get_db()
            try:
                s = db.query(Student).get(triggered["index"])
                if s:
                    return (SHOW, "Modifier l'etudiant",
                            s.first_name, s.last_name, s.email,
                            s.student_code, s.phone or "",
                            str(s.birth_date) if s.birth_date else None, s.id)
            finally:
                db.close()
        return NUP

    # ── Sauvegarder etudiant ──────────────────────────────────────────────────
    @app.callback(
        Output("student-feedback",    "children"),
        Output("students-refresh",    "data"),
        Output("student-modal-inner", "style", allow_duplicate=True),
        Input("save-student-btn", "n_clicks"),
        State("stu-first",    "value"),
        State("stu-last",     "value"),
        State("stu-email",    "value"),
        State("stu-code",     "value"),
        State("stu-birth",    "date"),
        State("stu-phone",    "value"),
        State("stu-edit-id",  "data"),
        State("students-refresh", "data"),
        prevent_initial_call=True,
    )
    def save_student(n, first, last, email, code, birth, phone, edit_id, refresh):
        if not n:
            return no_update, no_update, no_update
        if not first or not last or not email:
            return alert_msg("Prenom, nom et email obligatoires.", "danger", ""), no_update, no_update
        db = get_db()
        try:
            if edit_id:
                s = db.query(Student).get(edit_id)
            else:
                if db.query(Student).filter_by(email=email).first():
                    return alert_msg("Email deja utilise.", "danger", ""), no_update, no_update
                n_stu = db.query(Student).count() + 1
                s = Student(student_code=code or f"ETU-{date.today().year}-{n_stu:03d}")
                db.add(s)
            s.first_name = first; s.last_name = last
            s.email = email; s.phone = phone
            if birth:
                from datetime import datetime
                s.birth_date = datetime.strptime(birth, "%Y-%m-%d").date()
            db.commit()
            msg = "modifie" if edit_id else "ajoute"
            return (alert_msg(f"Etudiant {msg} avec succes.", "success", ""),
                    (refresh or 0) + 1, {"display": "none"})
        except Exception as e:
            db.rollback()
            return alert_msg(f"Erreur: {e}", "danger"), no_update, no_update
        finally:
            db.close()

    # ── Supprimer etudiant ────────────────────────────────────────────────────
    @app.callback(
        Output("student-feedback", "children", allow_duplicate=True),
        Output("students-refresh", "data",     allow_duplicate=True),
        Input({"type": "del-student-btn", "index": ALL}, "n_clicks"),
        State("students-refresh", "data"),
        prevent_initial_call=True,
    )
    def delete_student(clicks, refresh):
        if not any(clicks): return no_update, no_update
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict): return no_update, no_update
        db = get_db()
        try:
            s = db.query(Student).get(triggered["index"])
            if s: s.is_active = False; db.commit()
            return alert_msg("Etudiant desactive.", "warning", ""), (refresh or 0) + 1
        except Exception as e:
            db.rollback(); return alert_msg(str(e), "danger"), no_update
        finally:
            db.close()

    # ── Fermer modal form ─────────────────────────────────────────────────────
    @app.callback(
        Output("student-modal-inner", "style", allow_duplicate=True),
        Input("close-student-modal",  "n_clicks"),
        Input("cancel-student-modal", "n_clicks"),
        prevent_initial_call=True,
    )
    def close_modal(n1, n2):
        if not n1 and not n2: return no_update
        return {"display": "none"}

    # ── Fermer fiche ──────────────────────────────────────────────────────────
    @app.callback(
        Output("student-profile-overlay", "style", allow_duplicate=True),
        Input("close-profile-modal", "n_clicks"),
        prevent_initial_call=True,
    )
    def close_profile(n):
        if not n:
            return no_update
        return {"display": "none"}

    # ── Export fichiers ───────────────────────────────────────────────────────
    @app.callback(
        Output("download-students-file", "data"),
        Input("export-excel", "n_clicks"),
        Input("export-csv",   "n_clicks"),
        Input("export-stata", "n_clicks"),
        Input("export-spss",  "n_clicks"),
        prevent_initial_call=True,
    )
    def export_file(n_excel, n_csv, n_stata, n_spss):
        if not ctx.triggered_id: return no_update
        db = get_db()
        try:
            students = db.query(Student).filter_by(is_active=True).all()
            rows = []
            for s in students:
                st = _student_stats(s)
                rows.append({
                    "Code": s.student_code,
                    "Prenom": s.first_name,
                    "Nom": s.last_name,
                    "Email": s.email,
                    "Telephone": s.phone or "",
                    "Date_naissance": str(s.birth_date) if s.birth_date else "",
                    "Absences": st["n_abs"],
                    "Absences_justifiees": st["n_just"],
                    "Taux_absence_pct": st["abs_rate"],
                    "Moyenne": st["avg"] or "",
                    "Profil_risque": st["risk"],
                })
        finally:
            db.close()

        import pandas as pd
        df = pd.DataFrame(rows)
        buf = io.BytesIO()

        tid = ctx.triggered_id
        if tid == "export-excel":
            df.to_excel(buf, index=False)
            return dcc.send_bytes(buf.getvalue(), "etudiants.xlsx")
        elif tid == "export-csv":
            csv_str = df.to_csv(index=False)
            return dcc.send_string(csv_str, "etudiants.csv")
        elif tid == "export-stata":
            df.to_stata(buf, write_index=False)
            return dcc.send_bytes(buf.getvalue(), "etudiants.dta")
        elif tid == "export-spss":
            try:
                import pyreadstat
                with io.BytesIO() as tmp:
                    pyreadstat.write_sav(df, tmp)
                    return dcc.send_bytes(tmp.getvalue(), "etudiants.sav")
            except ImportError:
                # Fallback CSV si pyreadstat absent
                return dcc.send_string(df.to_csv(index=False), "etudiants.csv")
        return no_update

    # ── Telecharger fiche PDF ─────────────────────────────────────────────────
    @app.callback(
        Output("download-students-file", "data", allow_duplicate=True),
        Input("download-pdf-btn-static", "n_clicks"),
        State("selected-student-id", "data"),
        prevent_initial_call=True,
    )
    def download_pdf(n, student_id):
        if not n or not student_id:
            return no_update
        pdf_bytes = _generate_student_pdf(student_id)
        return dcc.send_bytes(pdf_bytes, "fiche_etudiant.pdf")


# ─────────────────────────────────────────────────────────────────────────────
#  Fiche individuelle (modal)
# ─────────────────────────────────────────────────────────────────────────────
def _student_profile_content(student_id: int):
    db = get_db()
    try:
        s = db.query(Student).get(student_id)
        if not s: return html.Div()
        st = _student_stats(s)
        grades  = s.grades
        courses = db.query(Course).filter_by(is_active=True).all()

        session_ids  = [a.session_id for a in s.attendances]
        sessions_map = {}
        if session_ids:
            for sess in db.query(Session).filter(Session.id.in_(session_ids)).all():
                sessions_map[sess.id] = sess.course_id

        course_data = {}
        for c in courses:
            g_list  = [g for g in grades if g.course_id == c.id]
            n_abs_c = sum(1 for a in s.attendances
                          if a.is_absent and sessions_map.get(a.session_id) == c.id)
            avg_c = round(
                sum(g.score * g.coefficient for g in g_list) /
                sum(g.coefficient for g in g_list), 1
            ) if g_list else None
            course_data[c.id] = dict(
                label=c.label, code=c.code, color=c.color,
                avg=avg_c, n_abs=n_abs_c, grades=g_list,
            )

        CHART_H = 260
        CARD_H  = f"{CHART_H + 60}px"  # hauteur uniforme des 3 cartes

        # Radar
        rd = [(d["code"], d["avg"]) for d in course_data.values() if d["avg"] is not None]
        if rd:
            lbls = [r[0] for r in rd] + [rd[0][0]]
            vals = [r[1] for r in rd] + [rd[0][1]]
            fig_radar = go.Figure(go.Scatterpolar(
                r=vals, theta=lbls, fill="toself",
                fillcolor="rgba(14,165,233,0.15)",
                line=dict(color=BLU, width=2),
                marker=dict(size=5, color=BLU),
            ))
            fig_radar.update_layout(
                paper_bgcolor=BG, autosize=True,
                margin=dict(l=40, r=40, t=50, b=80),
                polar=dict(
                    bgcolor=BG,
                    radialaxis=dict(visible=True, range=[0, 20],
                                    tickfont=dict(size=8, color=LGRAY, family=TNR),
                                    gridcolor="rgba(0,0,0,0.06)"),
                    angularaxis=dict(tickfont=dict(size=9, color=DARK, family=TNR),
                                     gridcolor="rgba(0,0,0,0.06)"),
                ),
                font=dict(family=TNR), showlegend=False,
            )
        else:
            fig_radar = _empty_fig(CHART_H)

        # Jauge presence
        pres_pct  = 100 - st["abs_rate"]
        gauge_clr = GRN if pres_pct >= 85 else ORG if pres_pct >= 75 else RED
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta", value=pres_pct,
            delta=dict(reference=85, valueformat=".1f",
                       increasing=dict(color=GRN), decreasing=dict(color=RED)),
            number=dict(suffix="%", font=dict(size=28, family=TNR, color=DARK)),
            gauge=dict(
                axis=dict(range=[0, 100], tickfont=dict(size=8, color=LGRAY, family=TNR),
                           nticks=6),
                bar=dict(color=gauge_clr, thickness=0.6),
                bgcolor="#F9FAFB", borderwidth=0,
                steps=[
                    dict(range=[0, 75],  color="rgba(239,68,68,0.06)"),
                    dict(range=[75, 85], color="rgba(245,158,11,0.06)"),
                    dict(range=[85, 100],color="rgba(16,185,129,0.06)"),
                ],
                threshold=dict(line=dict(color=RED, width=2),
                               thickness=0.8, value=75),
            ),
        ))
        fig_gauge.update_layout(
            paper_bgcolor=BG, autosize=True,
            margin=dict(l=20, r=20, t=30, b=20),
            font=dict(family=TNR),
        )

        # Barres notes (horizontal)
        bd = [(d["code"], d["avg"], d["color"])
              for d in course_data.values() if d["avg"] is not None]
        if bd:
            fig_bars = go.Figure(go.Bar(
                y=[b[0] for b in bd], x=[b[1] for b in bd],
                orientation="h",
                marker=dict(
                    color=[b[2] for b in bd],
                    line=dict(width=0),
                    cornerradius=3,
                ),
                text=[f"{b[1]}" for b in bd],
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(size=9, family=TNR, color="#fff"),
            ))
            fig_bars.add_vline(x=10, line_dash="dot",
                               line_color="rgba(239,68,68,0.5)", line_width=1.5,
                               annotation_text="Seuil 10",
                               annotation_font=dict(size=9, color=RED, family=TNR))
            fig_bars.update_layout(
                paper_bgcolor=BG, plot_bgcolor=BG, autosize=True,
                margin=dict(l=8, r=30, t=8, b=80),
                xaxis=dict(range=[1, 15], gridcolor="rgba(0,0,0,0.04)",
                           tickfont=dict(size=7, color=LGRAY, family=TNR),
                           zeroline=False),
                yaxis=dict(tickfont=dict(size=9, color=DARK, family=TNR),
                           autorange="reversed"),
                showlegend=False, font=dict(family=TNR),
                bargap=0.50,
            )
        else:
            fig_bars = _empty_fig(CHART_H)

        risk_cfg = {
            "ok":      ("#ECFDF5", GRN, "Bon suivi — aucune action requise"),
            "warning": ("#FFFBEB", ORG, "Attention — suivi renforce recommande"),
            "danger":  ("#FEF2F2", RED, "Alerte — etudiant en difficulte"),
        }
        r_bg, r_clr, r_msg = risk_cfg[st["risk"]]

        age_str = ""
        if s.birth_date:
            age = (date.today() - s.birth_date).days // 365
            age_str = f" · {age} ans"

        note_rows = []
        for cid, data in course_data.items():
            if not data["grades"]: continue
            clr = GRN if (data["avg"] or 0) >= 14 else BLU if (data["avg"] or 0) >= 10 else RED
            note_rows.append(html.Div(style={
                "display": "flex", "alignItems": "center",
                "justifyContent": "space-between",
                "padding": "9px 12px", "borderBottom": "1px solid #F3F4F6",
            }, children=[
                html.Div(style={"display": "flex", "alignItems": "center",
                                "gap": "7px", "flex": "1"}, children=[
                    html.Div(style={"width": "8px", "height": "8px",
                                    "borderRadius": "50%", "background": data["color"]}),
                    html.Span(data["label"], style={"fontSize": "12px",
                                                    "color": DARK, "fontFamily": TNR}),
                ]),
                html.Div(style={"display": "flex", "gap": "6px"}, children=[
                    html.Span(f"{g.score}/20 (x{g.coefficient})", style={
                        "fontSize": "10px", "color": LGRAY, "fontFamily": TNR,
                        "background": "#F9FAFB", "padding": "2px 6px", "borderRadius": "4px",
                    }) for g in data["grades"]
                ]),
                html.Span(f"{data['avg']}/20", style={
                    "fontWeight": "bold", "fontSize": "13px",
                    "color": clr, "fontFamily": TNR,
                    "minWidth": "55px", "textAlign": "right",
                }),
            ]))

        return html.Div(style={
                "background": "#F8FAFC", "borderRadius": "18px",
                "padding": "0",
            }, children=[

                # Bandeau header colore
                html.Div(style={
                    "background": f"linear-gradient(135deg, {DARK} 0%, #1E3A5F 100%)",
                    "borderRadius": "18px 18px 0 0",
                    "padding": "24px 28px 20px 28px",
                }, children=[
                    html.Div(style={"display": "flex", "alignItems": "center",
                                    "justifyContent": "space-between"}, children=[
                        html.Div(style={"display": "flex", "alignItems": "center",
                                        "gap": "16px"}, children=[
                            html.Div((s.first_name[0] + s.last_name[0]).upper(), style={
                                "width": "56px", "height": "56px", "borderRadius": "14px",
                                "background": f"linear-gradient(135deg,{BLU},#8B5CF6)",
                                "display": "flex", "alignItems": "center",
                                "justifyContent": "center",
                                "fontWeight": "bold", "fontSize": "20px",
                                "color": "#fff", "flexShrink": "0", "fontFamily": TNR,
                            }),
                            html.Div([
                                html.Div(s.full_name, style={
                                    "fontFamily": TNR, "fontSize": "20px",
                                    "fontWeight": "bold", "color": "#fff", "marginBottom": "4px",
                                }),
                                html.Div(f"{s.student_code} · {s.email}{age_str}", style={
                                    "fontSize": "12px", "color": "rgba(255,255,255,0.65)",
                                    "fontFamily": TNR,
                                }),
                            ]),
                        ]),
                        html.Div(style={"display": "flex", "gap": "8px",
                                        "alignItems": "center"}, children=[
                            _risk_badge(st["risk"]),
                        ]),
                    ]),
                ]),

                # Corps de la fiche
                html.Div(style={"padding": "20px 28px 28px 28px"}, children=[

                    # Bandeau alerte risque
                    html.Div(style={
                        "background": r_bg, "borderRadius": "10px",
                        "padding": "10px 16px", "marginBottom": "18px",
                        "borderLeft": f"4px solid {r_clr}",
                    }, children=[
                        html.Span(r_msg, style={
                            "fontSize": "12px", "color": r_clr,
                            "fontWeight": "bold", "fontFamily": TNR,
                        }),
                    ]),

                    # 4 indicateurs
                    html.Div(style={
                        "display": "grid", "gridTemplateColumns": "repeat(4, 1fr)",
                        "gap": "10px", "marginBottom": "18px",
                    }, children=[
                        _stat_chip(str(st["n_total"]), "Seances suivies", BLU, "#E0F2FE"),
                        _stat_chip(str(st["n_abs"]),   "Absences",        RED, "#FEF2F2"),
                        _stat_chip(str(st["n_just"]),  "Justifiees",      ORG, "#FFFBEB"),
                        _stat_chip(f"{st['avg']}/20" if st["avg"] else "–",
                                   "Moyenne generale", GRN, "#ECFDF5"),
                    ]),

                    # 3 graphiques alignes a la meme hauteur
                    html.Div(style={
                        "display": "grid",
                        "gridTemplateColumns": "1fr 1fr 1fr",
                        "gap": "6px", "marginBottom": "18px",
                        "alignItems": "stretch",
                    }, children=[
                        # Carte 1 — Radar
                        html.Div(style={**_card_style(), "height": CARD_H, "display":"flex","flexDirection":"column"}, children=[
                            html.Div("Radar des matieres", style={
                                "fontFamily": TNR, "fontWeight": "bold",
                                "fontSize": "12px", "color": DARK, "marginBottom": "2px",
                            }),
                            html.Div("Moyenne /20 par cours", style={
                                "fontFamily": TNR, "fontSize": "10px",
                                "color": LGRAY, "marginBottom": "6px",
                            }),
                            html.Div(style={"flex":"1","minHeight":"0"}, children=[
                                dcc.Graph(figure=fig_radar, config={"displayModeBar": False}, responsive=True,
                                          style={"height": "100%", "width": "100%"}),
                            ]),
                        ]),
                        # Carte 2 — Présence (CSS pur)
                        html.Div(style={**_card_style(), "height": CARD_H, "display":"flex","flexDirection":"column"}, children=[
                            html.Div("Taux de presence", style={
                                "fontFamily": TNR, "fontWeight": "bold",
                                "fontSize": "12px", "color": DARK, "marginBottom": "2px",
                            }),
                            html.Div(f"Objectif : 85% — actuel : {pres_pct:.0f}%", style={
                                "fontFamily": TNR, "fontSize": "10px",
                                "color": LGRAY, "marginBottom": "8px",
                            }),
                            html.Div(style={"flex":"1","display":"flex","flexDirection":"column","alignItems":"center","justifyContent":"space-between","gap":"10px"}, children=[
                                # Cercle
                                html.Div(style={
                                    "width":"120px","height":"120px","borderRadius":"50%","flexShrink":"0",
                                    "background": f"conic-gradient({gauge_clr} 0% {pres_pct}%, #F3F4F6 {pres_pct}% 100%)",
                                    "display":"flex","alignItems":"center","justifyContent":"center",
                                    "boxShadow":"0 4px 16px rgba(0,0,0,0.07)",
                                }, children=[
                                    html.Div(style={
                                        "width":"90px","height":"90px","borderRadius":"50%",
                                        "background":"#fff","display":"flex","flexDirection":"column",
                                        "alignItems":"center","justifyContent":"center",
                                    }, children=[
                                        html.Div(f"{pres_pct:.0f}%", style={"fontFamily":TNR,"fontSize":"24px","fontWeight":"bold","color":gauge_clr,"lineHeight":"1"}),
                                        html.Div("présence", style={"fontFamily":TNR,"fontSize":"9px","color":LGRAY,"marginTop":"2px"}),
                                    ]),
                                ]),
                                # 3 compteurs
                                html.Div(style={"display":"grid","gridTemplateColumns":"1fr 1fr 1fr","gap":"6px","width":"100%"}, children=[
                                    html.Div(style={"textAlign":"center","background":"#F0FDF4","borderRadius":"8px","padding":"7px 4px"}, children=[
                                        html.Div(str(st["n_total"]-st["n_abs"]), style={"fontFamily":TNR,"fontWeight":"bold","fontSize":"15px","color":GRN}),
                                        html.Div("Présents", style={"fontFamily":TNR,"fontSize":"9px","color":LGRAY}),
                                    ]),
                                    html.Div(style={"textAlign":"center","background":"#FEF2F2","borderRadius":"8px","padding":"7px 4px"}, children=[
                                        html.Div(str(st["n_abs"]), style={"fontFamily":TNR,"fontWeight":"bold","fontSize":"15px","color":RED}),
                                        html.Div("Absences", style={"fontFamily":TNR,"fontSize":"9px","color":LGRAY}),
                                    ]),
                                    html.Div(style={"textAlign":"center","background":"#FFFBEB","borderRadius":"8px","padding":"7px 4px"}, children=[
                                        html.Div(str(st["n_just"]), style={"fontFamily":TNR,"fontWeight":"bold","fontSize":"15px","color":ORG}),
                                        html.Div("Justifiées", style={"fontFamily":TNR,"fontSize":"9px","color":LGRAY}),
                                    ]),
                                ]),
                                # Barre
                                html.Div(style={"width":"100%"}, children=[
                                    html.Div(style={"display":"flex","justifyContent":"space-between","marginBottom":"3px"}, children=[
                                        html.Span("Assiduité", style={"fontSize":"9px","color":LGRAY,"fontFamily":TNR}),
                                        html.Span("Objectif 85%", style={"fontSize":"9px","color":LGRAY,"fontFamily":TNR}),
                                    ]),
                                    html.Div(style={"background":"#F3F4F6","borderRadius":"99px","height":"6px","overflow":"hidden","position":"relative"}, children=[
                                        html.Div(style={"width":f"{min(pres_pct,100)}%","height":"100%","borderRadius":"99px","background":gauge_clr}),
                                        html.Div(style={"position":"absolute","left":"85%","top":"0","width":"2px","height":"100%","background":DARK,"opacity":"0.25"}),
                                    ]),
                                ]),
                            ]),
                        ]),
                        # Carte 3 — Barres notes
                        html.Div(style={**_card_style(), "height": CARD_H, "display":"flex","flexDirection":"column"}, children=[
                            html.Div("Notes par cours", style={
                                "fontFamily": TNR, "fontWeight": "bold",
                                "fontSize": "12px", "color": DARK, "marginBottom": "2px",
                            }),
                            html.Div("Comparaison des moyennes", style={
                                "fontFamily": TNR, "fontSize": "10px",
                                "color": LGRAY, "marginBottom": "6px",
                            }),
                            html.Div(style={"height":"120px"}, children=[
                                dcc.Graph(figure=fig_bars, config={"displayModeBar": False}, responsive=True,
                                          style={"height": "100%", "width": "100%"}),
                            ]),
                        ]),
                    ]),

                    # Tableau detail notes
                    html.Div(style=_card_style(), children=[
                        html.Div("Detail des notes par matiere", style={
                            "fontFamily": TNR, "fontWeight": "bold",
                            "fontSize": "13px", "color": DARK,
                            "marginBottom": "12px", "paddingBottom": "10px",
                            "borderBottom": "1px solid #F3F4F6",
                        }),
                        html.Div(note_rows or [
                            html.P("Aucune note enregistree.", style={
                                "color": LGRAY, "fontSize": "12px",
                                "fontFamily": TNR, "padding": "12px 0",
                            })
                        ]),
                    ]),
                ]),
        ])
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
#  Generation PDF fiche etudiant (reportlab)
# ─────────────────────────────────────────────────────────────────────────────
def _generate_student_pdf(student_id: int) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    db = get_db()
    try:
        s  = db.query(Student).get(student_id)
        if not s:
            return b""
        st = _student_stats(s)
        courses = db.query(Course).filter_by(is_active=True).all()
        session_ids  = [a.session_id for a in s.attendances]
        sessions_map = {}
        if session_ids:
            for sess in db.query(Session).filter(Session.id.in_(session_ids)).all():
                sessions_map[sess.id] = sess.course_id
        course_data = {}
        for c in courses:
            g_list = [g for g in s.grades if g.course_id == c.id]
            n_abs_c = sum(1 for a in s.attendances
                          if a.is_absent and sessions_map.get(a.session_id) == c.id)
            avg_c = round(
                sum(g.score * g.coefficient for g in g_list) /
                sum(g.coefficient for g in g_list), 1
            ) if g_list else None
            course_data[c.id] = dict(
                label=c.label, avg=avg_c, n_abs=n_abs_c, grades=g_list,
            )
        age_str = ""
        if s.birth_date:
            age = (date.today() - s.birth_date).days // 365
            age_str = f"{age} ans"
    finally:
        db.close()

    buf = io.BytesIO()

    # ── Couleurs ──
    C_DARK  = colors.HexColor("#0A1628")
    C_BLU   = colors.HexColor("#0EA5E9")
    C_GRN   = colors.HexColor("#10B981")
    C_RED   = colors.HexColor("#EF4444")
    C_ORG   = colors.HexColor("#F59E0B")
    C_LGRAY = colors.HexColor("#9CA3AF")
    C_BG    = colors.HexColor("#F8FAFC")
    C_WHITE = colors.white

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=0, bottomMargin=1.5*cm,
                            leftMargin=1.8*cm, rightMargin=1.8*cm)
    W = A4[0] - 3.6*cm
    story = []

    # ── Styles typographiques ──
    def S(name, **kw):
        base = ParagraphStyle(name, fontName="Times-Roman", **kw)
        return base
    def SB(name, **kw):
        return ParagraphStyle(name, fontName="Times-Bold", **kw)

    TITLE   = SB("title",  fontSize=22, textColor=C_WHITE, leading=26)
    SUB     = S("sub",     fontSize=10, textColor=colors.HexColor("#CBD5E1"), leading=14)
    H2      = SB("h2",     fontSize=13, textColor=C_DARK,  spaceAfter=4, leading=16)
    BODY    = S("body",    fontSize=10, textColor=C_DARK,  leading=14)
    SMALL   = S("small",   fontSize=9,  textColor=colors.HexColor("#6B7280"), leading=12)
    CENTER  = S("center",  fontSize=10, alignment=TA_CENTER, textColor=C_DARK, leading=14)
    BOLD_C  = SB("boldc",  fontSize=11, alignment=TA_CENTER, textColor=C_DARK, leading=14)

    # ── Header colore ─────────────────────────────────────────────────────────
    risk_colors = {"ok": C_GRN, "warning": C_ORG, "danger": C_RED}
    risk_labels = {"ok": "Bon suivi", "warning": "A surveiller", "danger": "En difficulte"}
    r_clr  = risk_colors[st["risk"]]
    r_lbl  = risk_labels[st["risk"]]

    header_data = [[
        Paragraph(f"<b>{s.full_name}</b>", TITLE),
        Paragraph(r_lbl, SB("rb", fontSize=9, textColor=r_clr,
                             backColor=colors.HexColor("#F0FDF4") if st["risk"]=="ok"
                             else colors.HexColor("#FFFBEB") if st["risk"]=="warning"
                             else colors.HexColor("#FEF2F2"),
                             borderPadding=(4,8,4,8), alignment=TA_CENTER)),
    ]]
    header_tbl = Table(header_data, colWidths=[W * 0.75, W * 0.25])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), C_DARK),
        ("TOPPADDING",  (0,0), (-1,-1), 22),
        ("BOTTOMPADDING",(0,0),(-1,-1), 18),
        ("LEFTPADDING", (0,0), (-1,-1), 20),
        ("RIGHTPADDING",(0,0), (-1,-1), 16),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("ROUNDEDCORNERS", (0,0), (-1,-1), [8,8,0,0]),
    ]))
    story.append(header_tbl)

    # Sous-titre info etudiant
    info_parts = [s.student_code]
    if s.email: info_parts.append(s.email)
    if s.phone: info_parts.append(s.phone)
    if age_str: info_parts.append(age_str)
    info_tbl = Table([[Paragraph(" · ".join(info_parts), SUB)]], colWidths=[W])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), C_DARK),
        ("TOPPADDING",   (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0), (-1,-1), 16),
        ("LEFTPADDING",  (0,0), (-1,-1), 20),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 14))

    # ── 4 KPIs ────────────────────────────────────────────────────────────────
    def kpi_cell(val, lbl, clr):
        return [Paragraph(f"<b>{val}</b>",
                          SB("kv", fontSize=18, textColor=clr,
                             alignment=TA_CENTER, leading=22)),
                Paragraph(lbl, S("kl", fontSize=8, textColor=C_LGRAY,
                                 alignment=TA_CENTER, leading=11))]

    pres_pct = 100 - st["abs_rate"]
    kpi_data = [
        kpi_cell(str(st["n_total"]), "Seances suivies", C_BLU),
        kpi_cell(str(st["n_abs"]),   "Absences",        C_RED),
        kpi_cell(str(st["n_just"]),  "Justifiees",      C_ORG),
        kpi_cell(f"{st['avg']}/20" if st["avg"] else "–", "Moyenne gen.", C_GRN),
    ]
    kpi_tbl = Table([kpi_data], colWidths=[W/4]*4)
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), C_WHITE),
        ("BOX",          (0,0), (-1,-1), 1, colors.HexColor("#E5E7EB")),
        ("LINEAFTER",    (0,0), (2,0),   1, colors.HexColor("#E5E7EB")),
        ("TOPPADDING",   (0,0), (-1,-1), 12),
        ("BOTTOMPADDING",(0,0), (-1,-1), 12),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("ROUNDEDCORNERS",(0,0),(-1,-1), [6,6,6,6]),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 16))

    # ── Alerte risque ─────────────────────────────────────────────────────────
    risk_msg = {
        "ok":      "Bon suivi — aucune action particuliere requise.",
        "warning": "Attention — suivi renforce recommande pour cet etudiant.",
        "danger":  "Alerte — etudiant en difficulte, intervention necessaire.",
    }
    alert_tbl = Table([[Paragraph(risk_msg[st["risk"]], S("alert", fontSize=10,
                                                          textColor=r_clr, leading=14))]],
                      colWidths=[W])
    alert_bg = (colors.HexColor("#ECFDF5") if st["risk"]=="ok"
                else colors.HexColor("#FFFBEB") if st["risk"]=="warning"
                else colors.HexColor("#FEF2F2"))
    alert_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), alert_bg),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
        ("LEFTPADDING",  (0,0), (-1,-1), 14),
        ("LINEBEFORE",   (0,0), (0,-1), 4, r_clr),
    ]))
    story.append(alert_tbl)
    story.append(Spacer(1, 16))

    # ── Tableau des notes par matiere ─────────────────────────────────────────
    story.append(Paragraph("Notes par matiere", H2))
    story.append(HRFlowable(width=W, thickness=1, color=colors.HexColor("#E5E7EB"),
                            spaceAfter=8))

    note_header = [
        Paragraph("<b>Matiere</b>", SB("th", fontSize=9, textColor=C_LGRAY, leading=12)),
        Paragraph("<b>Notes detaillees</b>", SB("th2", fontSize=9, textColor=C_LGRAY, leading=12)),
        Paragraph("<b>Moyenne</b>", SB("th3", fontSize=9, textColor=C_LGRAY,
                                       alignment=TA_RIGHT, leading=12)),
        Paragraph("<b>Absences</b>", SB("th4", fontSize=9, textColor=C_LGRAY,
                                        alignment=TA_RIGHT, leading=12)),
    ]
    note_rows_pdf = [note_header]
    for cid, data in course_data.items():
        if not data["grades"]: continue
        avg_clr = (C_GRN if (data["avg"] or 0) >= 14
                   else C_BLU if (data["avg"] or 0) >= 10 else C_RED)
        notes_str = "  ".join([f"{g.score}/20 (x{g.coefficient})" for g in data["grades"]])
        note_rows_pdf.append([
            Paragraph(data["label"], BODY),
            Paragraph(notes_str, SMALL),
            Paragraph(f"<b>{data['avg']}/20</b>",
                      SB("avg", fontSize=11, textColor=avg_clr,
                         alignment=TA_RIGHT, leading=14)),
            Paragraph(str(data["n_abs"]),
                      S("ab", fontSize=10, alignment=TA_RIGHT,
                        textColor=C_RED if data["n_abs"] > 2 else C_DARK, leading=14)),
        ])

    if len(note_rows_pdf) > 1:
        nt = Table(note_rows_pdf, colWidths=[W*0.28, W*0.42, W*0.15, W*0.15])
        ts = TableStyle([
            ("BACKGROUND",   (0,0), (-1,0),  colors.HexColor("#F8FAFC")),
            ("TOPPADDING",   (0,0), (-1,-1), 8),
            ("BOTTOMPADDING",(0,0), (-1,-1), 8),
            ("LEFTPADDING",  (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("LINEBELOW",    (0,0), (-1,-2), 0.5, colors.HexColor("#F3F4F6")),
            ("LINEBELOW",    (0,0), (-1,0),  1,   colors.HexColor("#E5E7EB")),
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
            ("BOX",          (0,0), (-1,-1), 1,   colors.HexColor("#E5E7EB")),
        ])
        # Couleur alternee
        for row_i in range(1, len(note_rows_pdf)):
            if row_i % 2 == 0:
                ts.add("BACKGROUND", (0,row_i), (-1,row_i), colors.HexColor("#F9FAFB"))
        nt.setStyle(ts)
        story.append(nt)
    else:
        story.append(Paragraph("Aucune note enregistree.", SMALL))

    story.append(Spacer(1, 16))

    # ── Barre de presence visuelle ────────────────────────────────────────────
    story.append(Paragraph("Assiduite", H2))
    story.append(HRFlowable(width=W, thickness=1, color=colors.HexColor("#E5E7EB"),
                            spaceAfter=8))

    bar_fill = min(pres_pct / 100, 1.0)
    bar_clr  = C_GRN if pres_pct >= 85 else C_ORG if pres_pct >= 75 else C_RED
    bar_w    = W - 2*cm

    from reportlab.platypus import Flowable
    class PresenceBar(Flowable):
        def __init__(self, pct, color, width, height=14):
            super().__init__()
            self.pct = pct
            self.color = color
            self.bar_w = width
            self.bar_h = height
            self.width = width
            self.height = height + 20

        def draw(self):
            c = self.canv
            # Fond
            c.setFillColor(colors.HexColor("#F3F4F6"))
            c.roundRect(0, 10, self.bar_w, self.bar_h, 4, fill=1, stroke=0)
            # Remplissage
            fill_w = max(self.bar_w * self.pct / 100, 6)
            c.setFillColor(self.color)
            c.roundRect(0, 10, fill_w, self.bar_h, 4, fill=1, stroke=0)
            # Label
            c.setFont("Times-Bold", 9)
            c.setFillColor(colors.HexColor("#374151"))
            c.drawString(0, 0, f"Presence : {self.pct:.1f}%   |   Absences : {st['n_abs']}   |   Justifiees : {st['n_just']}")

    story.append(PresenceBar(pres_pct, bar_clr, bar_w))
    story.append(Spacer(1, 16))

    # ── Pied de page ──────────────────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#E5E7EB"),
                            spaceAfter=6))
    footer_data = [[
        Paragraph(f"Document genere le {date.today().strftime('%d/%m/%Y')}",
                  S("ft", fontSize=8, textColor=C_LGRAY, leading=11)),
        Paragraph("SGA · Systeme de Gestion Academique",
                  S("ft2", fontSize=8, textColor=C_LGRAY, alignment=TA_RIGHT, leading=11)),
    ]]
    ft = Table(footer_data, colWidths=[W/2, W/2])
    ft.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("LEFTPADDING",(0,0), (-1,-1), 0),
        ("RIGHTPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(ft)

    doc.build(story)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
#  Modal statique (toujours dans le DOM)
# ─────────────────────────────────────────────────────────────────────────────
def _student_modal_static():
    return html.Div(id="student-modal-inner", style={"display": "none"}, children=[
        html.Div(style={
            "position": "fixed", "inset": "0", "zIndex": "9999",
            "background": "rgba(10,22,40,0.55)",
            "display": "flex", "alignItems": "center", "justifyContent": "center",
        }, children=[
            html.Div(style={
                "background": "#fff", "borderRadius": "16px",
                "maxWidth": "520px", "width": "95%",
                "padding": "28px", "position": "relative",
                "boxShadow": "0 20px 60px rgba(10,22,40,0.22)",
            }, children=[
                html.Div(style={
                    "display": "flex", "alignItems": "center",
                    "justifyContent": "space-between", "marginBottom": "22px",
                }, children=[
                    html.Div(id="modal-title", style={
                        "fontFamily": TNR, "fontSize": "18px",
                        "fontWeight": "bold", "color": DARK,
                    }),
                    html.Button("X", id="close-student-modal", n_clicks=0, style={
                        **BTN, "background": "#F3F4F6", "borderRadius": "50%",
                        "width": "32px", "height": "32px", "fontSize": "14px", "color": GRAY,
                    }),
                ]),
                html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                                "gap": "12px"}, children=[
                    _mfield("Prenom *",  "stu-first", "Prenom"),
                    _mfield("Nom *",     "stu-last",  "Nom"),
                ]),
                _mfield("Email *", "stu-email", "etudiant@mail.fr", ftype="email"),
                html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                                "gap": "12px"}, children=[
                    _mfield("Code etudiant", "stu-code",  "ETU-2024-001 (auto)"),
                    _mfield("Telephone",     "stu-phone", "+221 xx xxx xx xx"),
                ]),
                html.Div(style={"marginBottom": "16px"}, children=[
                    html.Label("Date de naissance", style={
                        "fontSize": "11px", "fontWeight": "bold", "color": GRAY,
                        "fontFamily": TNR, "display": "block", "marginBottom": "5px",
                    }),
                    dcc.DatePickerSingle(id="stu-birth", display_format="DD/MM/YYYY"),
                ]),
                html.Div(style={
                    "display": "flex", "justifyContent": "flex-end", "gap": "10px",
                    "marginTop": "8px", "paddingTop": "16px",
                    "borderTop": "1px solid #F3F4F6",
                }, children=[
                    html.Button("Annuler", id="cancel-student-modal", n_clicks=0, style={
                        **BTN, "padding": "9px 18px", "borderRadius": "8px",
                        "background": "#F3F4F6", "color": DARK, "fontSize": "12px",
                    }),
                    html.Button("Enregistrer", id="save-student-btn", n_clicks=0, style={
                        **BTN, "padding": "9px 20px", "borderRadius": "8px",
                        "background": BLU, "color": "#fff",
                        "fontSize": "12px", "fontWeight": "bold",
                    }),
                ]),
            ]),
        ]),
    ])


def _mfield(label, input_id, placeholder, ftype="text"):
    return html.Div(style={"marginBottom": "14px"}, children=[
        html.Label(label, style={
            "fontSize": "11px", "fontWeight": "bold", "color": GRAY,
            "fontFamily": TNR, "display": "block", "marginBottom": "5px",
        }),
        dcc.Input(id=input_id, type=ftype, value="",
                  placeholder=placeholder, className="dash-input",
                  style={"width": "100%", "fontFamily": TNR, "fontSize": "12px"}),
    ])