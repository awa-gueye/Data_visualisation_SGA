"""
pages/grades.py - Module 3 : Gestion des Notes
"""
import base64
from dash import html, dcc, Input, Output, State, no_update, ctx, ALL
from pages.components import sidebar, topbar, card, empty_state, alert_msg
from utils.db import get_db
from utils.excel_helper import generate_grades_template, parse_grades_excel
from models import Course, Student, Grade
from sqlalchemy.orm import joinedload

DARK  = "#0A1628"
GRAY  = "#6B7280"
LGRAY = "#9CA3AF"
BLU   = "#0EA5E9"
GRN   = "#10B981"
RED   = "#EF4444"
ORG   = "#F59E0B"
BDR   = "#E5E7EB"
BG    = "#F9FAFB"
TNR   = "'Times New Roman', Times, serif"


# ─────────────────────────────────────────────────────────────────────────────
#  Layout
# ─────────────────────────────────────────────────────────────────────────────
def layout(user: dict = None):
    db = get_db()
    try:
        courses = db.query(Course).filter_by(is_active=True).order_by(Course.code).all()
        course_opts = [{"label": f"{c.code} – {c.label}", "value": c.id} for c in courses]
    finally:
        db.close()

    return html.Div(id="app-shell", children=[
        sidebar("/grades", user),
        html.Div(id="main-content", children=[
            topbar("Notes et Evaluations", "Saisie et import des notes"),
            html.Div(id="page-content", children=[

                dcc.Store(id="grades-refresh",  data=0),
                dcc.Store(id="edit-grade-id",    data=None),
                dcc.Download(id="download-template"),

                html.Div(className="grid-2", style={"gap": "24px", "alignItems": "start"}, children=[

                    # ── Colonne gauche : Saisie + Import ──────────────────
                    html.Div(children=[

                        # Saisie manuelle
                        card(title="Saisie manuelle", children=[
                            html.Div(id="grade-form-title", style={"marginBottom": "12px"}),
                            html.Div(id="grade-feedback"),

                            html.Div(className="form-group", children=[
                                html.Label("Cours *", className="form-label"),
                                dcc.Dropdown(
                                    id="grade-course",
                                    options=course_opts,
                                    placeholder="Selectionner un cours",
                                    style={"background": "var(--bg-card)"},
                                ),
                            ]),

                            html.Div(className="form-group", children=[
                                html.Label("Etudiant *", className="form-label"),
                                dcc.Dropdown(
                                    id="grade-student",
                                    placeholder="Selectionner un etudiant",
                                    style={"background": "var(--bg-card)"},
                                ),
                            ]),

                            html.Div(className="grid-2", children=[
                                html.Div(className="form-group", children=[
                                    html.Label("Note /20 *", className="form-label"),
                                    dcc.Input(
                                        id="grade-score", type="number",
                                        min=0, max=20, step=0.25,
                                        placeholder="ex: 14.5",
                                        className="dash-input",
                                        style={"width": "100%"},
                                    ),
                                ]),
                                html.Div(className="form-group", children=[
                                    html.Label("Coefficient", className="form-label"),
                                    dcc.Input(
                                        id="grade-coeff", type="number",
                                        min=0.5, step=0.5, value=1,
                                        className="dash-input",
                                        style={"width": "100%"},
                                    ),
                                ]),
                            ]),

                            html.Div(className="form-group", children=[
                                html.Label("Libelle de l'evaluation", className="form-label"),
                                dcc.Input(
                                    id="grade-label",
                                    placeholder="ex: Examen Final, TP1, Partiel...",
                                    className="dash-input",
                                    style={"width": "100%"},
                                ),
                            ]),

                            html.Button(
                                "Enregistrer la note",
                                id="save-grade-btn",
                                className="btn btn-primary",
                                n_clicks=0,
                                style={"width": "100%", "marginTop": "8px", "padding": "12px"},
                            ),
                        ]),

                        html.Div(style={"height": "20px"}),

                        # Import Excel
                        card(title="Import Excel", children=[
                            html.Div(id="import-feedback"),

                            html.Div(className="form-group", children=[
                                html.Label("Cours pour l'import", className="form-label"),
                                dcc.Dropdown(
                                    id="import-course",
                                    options=course_opts,
                                    placeholder="Selectionner un cours",
                                    style={"background": "var(--bg-card)"},
                                ),
                            ]),

                            html.Button(
                                "Telecharger le template",
                                id="download-template-btn",
                                className="btn btn-outline",
                                n_clicks=0,
                                style={"width": "100%", "marginBottom": "14px"},
                            ),

                            html.Div(className="upload-area", children=[
                                dcc.Upload(
                                    id="upload-grades",
                                    children=html.Div([
                                        html.Div("Glissez votre fichier Excel ici",
                                                 style={"fontWeight": "600",
                                                        "marginBottom": "4px"}),
                                        html.Div("ou cliquez pour parcourir",
                                                 style={"fontSize": "12px",
                                                        "color": "var(--gris-moyen)"}),
                                    ]),
                                    accept=".xlsx,.xls",
                                    multiple=False,
                                ),
                            ]),
                        ]),
                    ]),

                    # ── Colonne droite : Tableau + Stats ──────────────────
                    card(title="Notes enregistrees", children=[

                        html.Div(className="grid-2", style={"gap": "12px",
                                                             "marginBottom": "4px"}, children=[
                            html.Div(className="form-group", children=[
                                html.Label("Filtrer par cours", className="form-label"),
                                dcc.Dropdown(
                                    id="filter-grade-course",
                                    options=[{"label": "Tous les cours", "value": "all"}]
                                             + course_opts,
                                    value="all",
                                    clearable=False,
                                    style={"background": "var(--bg-card)"},
                                ),
                            ]),
                            html.Div(className="form-group", children=[
                                html.Label("Trier par", className="form-label"),
                                dcc.Dropdown(
                                    id="sort-grades",
                                    options=[
                                        {"label": "Date (recent)",     "value": "date_desc"},
                                        {"label": "Note (croissant)",  "value": "score_asc"},
                                        {"label": "Note (decroissant)","value": "score_desc"},
                                        {"label": "Etudiant (A-Z)",    "value": "student"},
                                    ],
                                    value="date_desc",
                                    clearable=False,
                                    style={"background": "var(--bg-card)"},
                                ),
                            ]),
                        ]),

                        # Bloc stats par cours
                        html.Div(id="grades-stats"),

                        html.Div(id="grades-table"),
                    ]),
                ]),
            ]),
        ]),
    ])


# ─────────────────────────────────────────────────────────────────────────────
#  Callbacks
# ─────────────────────────────────────────────────────────────────────────────
def register_callbacks(app):

    # ── Charger liste etudiants selon cours ──────────────────────────────
    @app.callback(
        Output("grade-student", "options"),
        Input("grade-course",   "value"),
    )
    def load_students(course_id):
        db = get_db()
        try:
            students = (db.query(Student)
                        .filter_by(is_active=True)
                        .order_by(Student.last_name)
                        .all())
            return [{"label": f"{s.full_name} ({s.student_code})", "value": s.id}
                    for s in students]
        finally:
            db.close()

    # ── Enregistrer une note ──────────────────────────────────────────────
    @app.callback(
        Output("grade-feedback",  "children"),
        Output("grades-refresh",  "data"),
        Output("edit-grade-id",   "data", allow_duplicate=True),
        Output("grade-form-title","children"),
        Input("save-grade-btn",  "n_clicks"),
        State("grade-course",    "value"),
        State("grade-student",   "value"),
        State("grade-score",     "value"),
        State("grade-coeff",     "value"),
        State("grade-label",     "value"),
        State("grades-refresh",  "data"),
        State("edit-grade-id",   "data"),
        prevent_initial_call=True,
    )
    def save_grade(n, course_id, student_id, score, coeff, label, refresh, edit_id):
        NUP4 = (no_update, no_update, no_update, no_update)
        if not n:
            return NUP4
        if not all([course_id, student_id, score is not None]):
            return alert_msg("Cours, etudiant et note obligatoires.", "danger"), no_update, no_update, no_update
        if not (0 <= float(score) <= 20):
            return alert_msg("La note doit etre entre 0 et 20.", "danger"), no_update, no_update, no_update

        db = get_db()
        try:
            if edit_id:
                # Modification
                g = db.query(Grade).get(int(edit_id))
                if not g:
                    return alert_msg("Note introuvable.", "danger"), no_update, no_update, no_update
                g.course_id   = int(course_id)
                g.student_id  = int(student_id)
                g.score       = float(score)
                g.coefficient = float(coeff or 1)
                g.label       = label or "Note"
                db.commit()
                return (
                    alert_msg("Note modifiee avec succes.", "success"),
                    (refresh or 0) + 1,
                    None,
                    html.Div(),
                )
            else:
                # Creation
                g = Grade(
                    student_id=int(student_id),
                    course_id=int(course_id),
                    score=float(score),
                    coefficient=float(coeff or 1),
                    label=label or "Note",
                )
                db.add(g)
                db.commit()
                return (
                    alert_msg("Note enregistree avec succes.", "success"),
                    (refresh or 0) + 1,
                    None,
                    html.Div(),
                )
        except Exception as e:
            db.rollback()
            return alert_msg(f"Erreur : {e}", "danger"), no_update, no_update, no_update
        finally:
            db.close()

    # ── Supprimer une note ────────────────────────────────────────────────
    @app.callback(
        Output("grade-feedback", "children", allow_duplicate=True),
        Output("grades-refresh", "data",     allow_duplicate=True),
        Input({"type": "delete-grade-btn", "index": ALL}, "n_clicks"),
        State("grades-refresh", "data"),
        prevent_initial_call=True,
    )
    def delete_grade(n_clicks_list, refresh):
        triggered_value = ctx.triggered[0]["value"] if ctx.triggered else 0
        if not triggered_value:
            return no_update, no_update
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            return no_update, no_update

        grade_id = triggered["index"]
        db = get_db()
        try:
            g = db.query(Grade).get(grade_id)
            if g:
                db.delete(g)
                db.commit()
            return (
                alert_msg("Note supprimee.", "warning"),
                (refresh or 0) + 1,
            )
        except Exception as e:
            db.rollback()
            return alert_msg(f"Erreur : {e}", "danger"), no_update
        finally:
            db.close()

    # ── Pre-remplir formulaire pour modification ─────────────────────────
    @app.callback(
        Output("grade-course",    "value"),
        Output("grade-student",   "value"),
        Output("grade-score",     "value"),
        Output("grade-coeff",     "value"),
        Output("grade-label",     "value"),
        Output("edit-grade-id",   "data"),
        Output("grade-form-title","children", allow_duplicate=True),
        Input({"type": "edit-grade-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def prefill_grade_form(n_clicks_list):
        triggered_value = ctx.triggered[0]["value"] if ctx.triggered else 0
        if not triggered_value:
            return (no_update,) * 7
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            return (no_update,) * 7

        grade_id = triggered["index"]
        db = get_db()
        try:
            g = db.query(Grade).get(grade_id)
            if not g:
                return (no_update,) * 7
            banner = html.Div(style={
                "background": "#FFFBEB",
                "border": "1px solid #F59E0B",
                "borderRadius": "8px",
                "padding": "8px 12px",
                "fontSize": "12px",
                "color": "#92400E",
                "fontFamily": TNR,
            }, children=[
                html.Strong("Mode modification — "),
                f"note #{g.id} selectionnee. Modifiez les champs puis cliquez sur Enregistrer.",
            ])
            return (
                g.course_id,
                g.student_id,
                g.score,
                g.coefficient,
                g.label,
                g.id,
                banner,
            )
        finally:
            db.close()

    # ── Telecharger template Excel ────────────────────────────────────────
    @app.callback(
        Output("download-template", "data"),
        Input("download-template-btn", "n_clicks"),
        State("import-course",         "value"),
        prevent_initial_call=True,
    )
    def download_template(n, course_id):
        if not n or not course_id:
            return no_update
        db = get_db()
        try:
            course   = db.query(Course).get(course_id)
            students = (db.query(Student)
                        .filter_by(is_active=True)
                        .order_by(Student.last_name)
                        .all())
            xlsx = generate_grades_template(students, course.code, course.label)
            return dcc.send_bytes(xlsx, f"notes_{course.code}.xlsx")
        finally:
            db.close()

    # ── Importer notes depuis Excel ───────────────────────────────────────
    @app.callback(
        Output("import-feedback", "children"),
        Output("grades-refresh",  "data", allow_duplicate=True),
        Input("upload-grades",    "contents"),
        State("upload-grades",    "filename"),
        State("import-course",    "value"),
        State("grades-refresh",   "data"),
        prevent_initial_call=True,
    )
    def import_grades(contents, filename, course_id, refresh):
        if not contents or not course_id:
            return alert_msg("Selectionnez un cours et un fichier.", "warning"), no_update
        try:
            _, content_str = contents.split(",")
            import base64 as b64
            file_bytes = b64.b64decode(content_str)
            grades_data, errors = parse_grades_excel(file_bytes)
        except Exception as e:
            return alert_msg(f"Lecture impossible : {e}", "danger"), no_update

        if errors:
            return html.Div([
                alert_msg(f"{len(errors)} erreur(s) dans le fichier :", "warning"),
                html.Ul([html.Li(e, style={"fontSize": "12px"}) for e in errors[:5]]),
            ]), no_update

        db = get_db()
        try:
            for gd in grades_data:
                g = Grade(
                    student_id=gd["student_id"],
                    course_id=int(course_id),
                    score=gd["score"],
                    coefficient=gd["coefficient"],
                    label=gd["label"],
                )
                db.add(g)
            db.commit()
            return (
                alert_msg(f"{len(grades_data)} notes importees avec succes.", "success"),
                (refresh or 0) + 1,
            )
        except Exception as e:
            db.rollback()
            return alert_msg(f"Erreur d'import : {e}", "danger"), no_update
        finally:
            db.close()

    # ── Tableau + stats ───────────────────────────────────────────────────
    @app.callback(
        Output("grades-stats", "children"),
        Output("grades-table", "children"),
        Input("filter-grade-course", "value"),
        Input("sort-grades",         "value"),
        Input("grades-refresh",      "data"),
    )
    def refresh_grades_table(course_filter, sort_by, _):
        db = get_db()
        try:
            q = (db.query(Grade)
                 .options(
                     joinedload(Grade.student),
                     joinedload(Grade.course),
                 ))

            if course_filter and course_filter != "all":
                q = q.filter(Grade.course_id == int(course_filter))

            if sort_by == "score_asc":
                q = q.order_by(Grade.score.asc())
            elif sort_by == "score_desc":
                q = q.order_by(Grade.score.desc())
            elif sort_by == "student":
                q = q.join(Student).order_by(Student.last_name.asc())
            else:
                q = q.order_by(Grade.graded_at.desc())

            grades = q.limit(200).all()

            # Charger les relations avant fermeture
            rows_data = []
            for g in grades:
                rows_data.append({
                    "id":           g.id,
                    "student_name": g.student.full_name if g.student else "?",
                    "course_code":  g.course.code       if g.course  else "?",
                    "course_color": g.course.color      if g.course  else BLU,
                    "label":        g.label or "—",
                    "score":        g.score,
                    "coeff":        g.coefficient,
                })
        finally:
            db.close()

        if not rows_data:
            return html.Div(), empty_state(
                "", "Aucune note", "Saisissez ou importez des notes."
            )

        # ── Bloc stats ────────────────────────────────────────────────
        scores = [r["score"] for r in rows_data]
        avg    = round(sum(scores) / len(scores), 1) if scores else 0
        mn     = min(scores) if scores else 0
        mx     = max(scores) if scores else 0
        above  = sum(1 for s in scores if s >= 10)
        below  = len(scores) - above

        avg_color = GRN if avg >= 14 else BLU if avg >= 10 else RED

        stats_block = html.Div(style={
            "display": "grid", "gridTemplateColumns": "repeat(5, 1fr)",
            "gap": "8px", "marginBottom": "16px",
        }, children=[
            _stat_box(str(len(scores)), "Notes",          DARK),
            _stat_box(f"{avg}/20",      "Moyenne",        avg_color),
            _stat_box(f"{mn}/20",       "Minimum",        RED),
            _stat_box(f"{mx}/20",       "Maximum",        GRN),
            _stat_box(f"{above}/{len(scores)}", "Admis (>=10)", BLU),
        ])

        # ── En-tete tableau ───────────────────────────────────────────
        cols = "2fr 1.2fr 1.5fr 0.7fr 1.4fr 0.1fr auto"
        header = html.Div(style={
            "display": "grid", "gridTemplateColumns": cols,
            "gap": "8px", "padding": "10px 14px",
            "background": DARK, "borderRadius": "10px 10px 0 0",
        }, children=[
            html.Span(h, style={
                "fontSize": "10px", "fontWeight": "bold",
                "textTransform": "uppercase",
                "color": "rgba(255,255,255,0.5)",
                "letterSpacing": "0.8px", "fontFamily": TNR,
            }) for h in ["Etudiant", "Cours", "Evaluation", "Coeff", "Note", "", ""]
        ])

        # ── Lignes tableau ────────────────────────────────────────────
        table_rows = []
        for i, r in enumerate(rows_data):
            score_color = GRN if r["score"] >= 14 else BLU if r["score"] >= 10 else RED
            bg = BG if i % 2 == 0 else "#FFFFFF"

            table_rows.append(html.Div(style={
                "display": "grid", "gridTemplateColumns": cols,
                "alignItems": "center", "gap": "8px",
                "padding": "10px 14px",
                "background": bg,
                "borderBottom": f"1px solid {BDR}",
            }, children=[

                # Etudiant
                html.Div(r["student_name"], style={
                    "fontSize": "13px", "fontWeight": "600",
                    "color": DARK, "fontFamily": TNR,
                }),

                # Cours (badge coloré)
                html.Span(r["course_code"], style={
                    "background": r["course_color"], "color": "white",
                    "padding": "2px 9px", "borderRadius": "99px",
                    "fontSize": "11px", "fontWeight": "700",
                    "fontFamily": TNR,
                }),

                # Libelle
                html.Div(r["label"], style={
                    "fontSize": "12px", "color": GRAY, "fontFamily": TNR,
                }),

                # Coefficient
                html.Div(f"x{r['coeff']}", style={
                    "fontSize": "12px", "color": LGRAY, "fontFamily": TNR,
                }),

                # Note avec barre visuelle
                html.Div(style={"display": "flex", "alignItems": "center",
                                "gap": "8px"}, children=[
                    html.Span(f"{r['score']}/20", style={
                        "fontWeight": "bold", "fontSize": "14px",
                        "color": score_color, "fontFamily": TNR,
                        "minWidth": "50px",
                    }),
                    html.Div(style={
                        "flex": "1", "height": "4px",
                        "borderRadius": "2px", "background": BDR,
                        "overflow": "hidden", "minWidth": "40px",
                    }, children=[
                        html.Div(style={
                            "width": f"{r['score'] / 20 * 100}%",
                            "height": "100%",
                            "background": score_color,
                            "borderRadius": "2px",
                        })
                    ]),
                ]),

                # Placeholder colonne vide (alignement)
                html.Div(),

                # Boutons modifier + supprimer
                html.Div(style={"display": "flex", "gap": "4px"}, children=[
                    html.Button(
                        "Modif.",
                        id={"type": "edit-grade-btn", "index": r["id"]},
                        n_clicks=0,
                        style={
                            "border": "1px solid #BFDBFE",
                            "background": "#EFF6FF", "color": "#1D4ED8",
                            "borderRadius": "6px", "padding": "4px 8px",
                            "fontSize": "10px", "cursor": "pointer",
                            "fontFamily": TNR, "whiteSpace": "nowrap",
                        },
                    ),
                    html.Button(
                        "Suppr.",
                        id={"type": "delete-grade-btn", "index": r["id"]},
                        n_clicks=0,
                        style={
                            "border": "1px solid #FECACA",
                            "background": "#FEF2F2", "color": RED,
                            "borderRadius": "6px", "padding": "4px 8px",
                            "fontSize": "10px", "cursor": "pointer",
                            "fontFamily": TNR, "whiteSpace": "nowrap",
                        },
                    ),
                ]),
            ]))

        table = html.Div(style={
            "borderRadius": "10px", "overflow": "hidden",
            "border": f"1px solid {BDR}",
        }, children=[header, html.Div(table_rows)])

        return stats_block, table


# ─────────────────────────────────────────────────────────────────────────────
#  Composants
# ─────────────────────────────────────────────────────────────────────────────
def _stat_box(value, label, color):
    return html.Div(style={
        "background": "#fff",
        "borderRadius": "10px",
        "padding": "12px 14px",
        "boxShadow": "0 2px 8px rgba(10,22,40,0.06)",
        "borderLeft": f"3px solid {color}",
    }, children=[
        html.Div(value, style={
            "fontFamily": TNR, "fontWeight": "bold",
            "fontSize": "18px", "color": color, "lineHeight": "1",
        }),
        html.Div(label, style={
            "fontSize": "10px", "color": LGRAY,
            "fontFamily": TNR, "marginTop": "4px",
        }),
    ])