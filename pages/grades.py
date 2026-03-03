"""
pages/grades.py – Module 3 : Gestion des Notes
"""
import base64
from dash import html, dcc, Input, Output, State, callback, no_update, ctx, ALL
import dash
from pages.components import sidebar, topbar, card, section_title, badge, empty_state, alert_msg
from utils.db import get_db
from utils.excel_helper import generate_grades_template, parse_grades_excel
from models import Course, Student, Grade
from config import COLORS


def layout(user: dict = None):
    db = get_db()
    try:
        courses  = db.query(Course).filter_by(is_active=True).order_by(Course.code).all()
        course_opts = [{"label": f"{c.code} – {c.label}", "value": c.id} for c in courses]
    finally:
        db.close()

    return html.Div(id="app-shell", children=[
        sidebar("/grades", user),
        html.Div(id="main-content", children=[
            topbar("Notes & Évaluations", "Saisie et import des notes"),
            html.Div(id="page-content", children=[

                html.Div(className="grid-2", style={"gap":"24px","alignItems":"start"}, children=[

                    # ── Colonne gauche : Saisie manuelle + Import ──────────
                    html.Div(children=[

                        # Saisie manuelle
                        card(title="✏️ Saisie manuelle", children=[
                            html.Div(id="grade-feedback"),

                            html.Div(className="form-group", children=[
                                html.Label("Cours *", className="form-label"),
                                dcc.Dropdown(id="grade-course", options=course_opts,
                                             placeholder="Sélectionner un cours",
                                             style={"background":"var(--surface2)"}),
                            ]),

                            html.Div(className="form-group", children=[
                                html.Label("Étudiant *", className="form-label"),
                                dcc.Dropdown(id="grade-student",
                                             placeholder="Sélectionner un étudiant",
                                             style={"background":"var(--surface2)"}),
                            ]),

                            html.Div(className="grid-2", children=[
                                html.Div(className="form-group", children=[
                                    html.Label("Note /20 *", className="form-label"),
                                    dcc.Input(id="grade-score", type="number",
                                              min=0, max=20, step=0.25,
                                              placeholder="ex: 14.5",
                                              className="dash-input", style={"width":"100%"}),
                                ]),
                                html.Div(className="form-group", children=[
                                    html.Label("Coefficient", className="form-label"),
                                    dcc.Input(id="grade-coeff", type="number",
                                              min=0.5, step=0.5, value=1,
                                              className="dash-input", style={"width":"100%"}),
                                ]),
                            ]),

                            html.Div(className="form-group", children=[
                                html.Label("Libellé de l'évaluation", className="form-label"),
                                dcc.Input(id="grade-label",
                                          placeholder="ex: Examen Final, TP1, Partiel...",
                                          className="dash-input", style={"width":"100%"}),
                            ]),

                            html.Button(
                                "💾 Enregistrer la note",
                                id="save-grade-btn",
                                className="btn btn-primary",
                                n_clicks=0,
                                style={"width":"100%","marginTop":"8px","padding":"12px"},
                            ),
                        ]),

                        html.Div(style={"height":"20px"}),

                        # Import Excel
                        card(title="📥 Import Excel", children=[
                            html.Div(id="import-feedback"),

                            html.Div(className="form-group", children=[
                                html.Label("Cours pour l'import", className="form-label"),
                                dcc.Dropdown(id="import-course", options=course_opts,
                                             placeholder="Sélectionner un cours",
                                             style={"background":"var(--surface2)"}),
                            ]),

                            html.Button(
                                "⬇️ Télécharger le template",
                                id="download-template-btn",
                                className="btn btn-outline",
                                n_clicks=0,
                                style={"width":"100%","marginBottom":"14px"},
                            ),
                            dcc.Download(id="download-template"),

                            html.Div(className="upload-area", children=[
                                dcc.Upload(
                                    id="upload-grades",
                                    children=html.Div([
                                        html.Div("📤", style={"fontSize":"32px","marginBottom":"8px"}),
                                        html.Div("Glissez votre fichier Excel ici", style={"fontWeight":"600"}),
                                        html.Div("ou cliquez pour parcourir", style={"fontSize":"12px","color":"var(--text-muted)","marginTop":"4px"}),
                                    ]),
                                    accept=".xlsx,.xls",
                                    multiple=False,
                                ),
                            ]),
                        ]),
                    ]),

                    # ── Colonne droite : Tableau des notes ─────────────────
                    card(title="📊 Notes enregistrées", children=[
                        html.Div(className="form-group", children=[
                            html.Label("Filtrer par cours", className="form-label"),
                            dcc.Dropdown(
                                id="filter-grade-course",
                                options=[{"label":"Tous les cours","value":"all"}] + course_opts,
                                value="all",
                                clearable=False,
                                style={"background":"var(--surface2)"},
                            ),
                        ]),
                        html.Div(id="grades-table"),
                        dcc.Store(id="grades-refresh", data=0),
                    ]),
                ]),
            ]),
        ]),
    ])


def register_callbacks(app):

    @app.callback(
        Output("grade-student", "options"),
        Input("grade-course", "value"),
    )
    def load_students(course_id):
        db = get_db()
        try:
            students = db.query(Student).filter_by(is_active=True).order_by(Student.last_name).all()
            return [{"label": f"{s.full_name} ({s.student_code})", "value": s.id} for s in students]
        finally:
            db.close()

    @app.callback(
        Output("grade-feedback", "children"),
        Output("grades-refresh", "data"),
        Input("save-grade-btn", "n_clicks"),
        State("grade-course",   "value"),
        State("grade-student",  "value"),
        State("grade-score",    "value"),
        State("grade-coeff",    "value"),
        State("grade-label",    "value"),
        State("grades-refresh", "data"),
        prevent_initial_call=True,
    )
    def save_grade(n, course_id, student_id, score, coeff, label, refresh):
        if not n:
            return no_update, no_update
        if not all([course_id, student_id, score is not None]):
            return alert_msg("Cours, étudiant et note obligatoires.", "danger", "⚠️"), no_update
        if not (0 <= float(score) <= 20):
            return alert_msg("La note doit être entre 0 et 20.", "danger", "⚠️"), no_update

        db = get_db()
        try:
            g = Grade(
                student_id=int(student_id),
                course_id=int(course_id),
                score=float(score),
                coefficient=float(coeff or 1),
                label=label or "Note",
            )
            db.add(g)
            db.commit()
            return alert_msg("Note enregistrée ✅", "success", "✅"), (refresh or 0) + 1
        except Exception as e:
            db.rollback()
            return alert_msg(f"Erreur : {e}", "danger"), no_update
        finally:
            db.close()

    @app.callback(
        Output("download-template", "data"),
        Input("download-template-btn", "n_clicks"),
        State("import-course", "value"),
        prevent_initial_call=True,
    )
    def download_template(n, course_id):
        if not n or not course_id:
            return no_update
        db = get_db()
        try:
            course   = db.query(Course).get(course_id)
            students = db.query(Student).filter_by(is_active=True).order_by(Student.last_name).all()
            xlsx     = generate_grades_template(students, course.code, course.label)
            return dcc.send_bytes(xlsx, f"notes_{course.code}.xlsx")
        finally:
            db.close()

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
            return alert_msg("Sélectionnez un cours et un fichier.", "warning", "⚠️"), no_update
        try:
            _, content_str = contents.split(",")
            file_bytes = base64.b64decode(content_str)
            grades_data, errors = parse_grades_excel(file_bytes)
        except Exception as e:
            return alert_msg(f"Lecture impossible : {e}", "danger", "❌"), no_update

        if errors:
            return html.Div([
                alert_msg(f"{len(errors)} erreur(s) dans le fichier :", "warning", "⚠️"),
                html.Ul([html.Li(e, style={"fontSize":"12px"}) for e in errors[:5]]),
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
            return alert_msg(f"{len(grades_data)} notes importées ✅", "success", "✅"), (refresh or 0) + 1
        except Exception as e:
            db.rollback()
            return alert_msg(f"Erreur d'import : {e}", "danger", "❌"), no_update
        finally:
            db.close()

    @app.callback(
        Output("grades-table", "children"),
        Input("filter-grade-course", "value"),
        Input("grades-refresh",      "data"),
    )
    def refresh_grades_table(course_filter, _):
        db = get_db()
        try:
            q = db.query(Grade)
            if course_filter and course_filter != "all":
                q = q.filter(Grade.course_id == int(course_filter))
            grades = q.order_by(Grade.graded_at.desc()).limit(100).all()
        finally:
            db.close()

        if not grades:
            return empty_state("📝", "Aucune note", "Saisissez ou importez des notes.")

        rows = []
        for g in grades:
            color = "var(--success)" if g.score >= 10 else "var(--danger)"
            rows.append(html.Div(style={
                "display":"grid","gridTemplateColumns":"2fr 2fr 1fr 1fr 1fr",
                "gap":"8px","alignItems":"center",
                "padding":"10px 12px","borderBottom":"1px solid var(--border)",
            }, children=[
                html.Div(g.student.full_name if g.student else "?", style={"fontSize":"13px","fontWeight":"500"}),
                html.Div(g.course.code if g.course else "?", style={"fontSize":"12px","color":"var(--text-muted)"}),
                html.Div(g.label or "–", style={"fontSize":"12px","color":"var(--text-muted)"}),
                html.Div(f"×{g.coefficient}", style={"fontSize":"12px","color":"var(--text-muted)"}),
                html.Div(f"{g.score}/20", style={"fontWeight":"700","color":color,"fontSize":"14px"}),
            ]))

        header = html.Div(style={
            "display":"grid","gridTemplateColumns":"2fr 2fr 1fr 1fr 1fr",
            "gap":"8px","padding":"10px 12px",
            "background":"var(--surface2)","borderRadius":"var(--radius-sm) var(--radius-sm) 0 0",
        }, children=[
            html.Span(h, style={"fontSize":"10px","fontWeight":"700","textTransform":"uppercase","color":"var(--text-muted)","letterSpacing":"0.5px"})
            for h in ["Étudiant","Cours","Évaluation","Coeff","Note"]
        ])

        return html.Div(style={"borderRadius":"var(--radius-md)","overflow":"hidden",
                                "border":"1px solid var(--border)"}, children=[
            header, html.Div(rows)
        ])