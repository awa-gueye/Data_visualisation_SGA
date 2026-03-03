"""
pages/students.py – Module 3 : Gestion des Étudiants
"""
from dash import html, dcc, Input, Output, State, callback, no_update, ctx, dash_table, ALL
import dash
from datetime import date
from pages.components import sidebar, topbar, card, section_title, badge, empty_state, alert_msg, kpi_card
from utils.db import get_db
from models import Student, Attendance, Grade, Course
from config import COLORS


def layout(user: dict = None):
    return html.Div(id="app-shell", children=[
        sidebar("/students", user),
        html.Div(id="main-content", children=[
            topbar("Étudiants", "Gestion des inscriptions"),
            html.Div(id="page-content", children=[

                html.Div(className="flex-between", style={"marginBottom":"24px"}, children=[
                    section_title("Étudiants", "Fiches individuelles et suivi"),
                    html.Div(className="flex-center gap-8", children=[
                        html.Button("📤 Exporter CSV", id="export-students-btn",
                                    className="btn btn-outline", n_clicks=0),
                        html.Button("➕ Nouvel étudiant", id="open-student-modal",
                                    className="btn btn-primary", n_clicks=0),
                    ]),
                ]),

                html.Div(id="student-feedback"),

                # ── Barre de recherche ─────────────────────────────────────
                html.Div(className="card", style={"marginBottom":"20px","padding":"16px"}, children=[
                    dcc.Input(
                        id="student-search",
                        placeholder="🔍  Rechercher par nom, prénom, email ou code...",
                        debounce=True,
                        className="dash-input",
                        style={"width":"100%"},
                    ),
                ]),

                # ── Table étudiants ────────────────────────────────────────
                html.Div(id="students-table"),

                # ── Fiche individuelle ─────────────────────────────────────
                html.Div(id="student-profile-modal"),

                # ── Modal ajout/édition ────────────────────────────────────
                html.Div(id="student-modal-container"),

                # Stores
                dcc.Store(id="students-refresh",    data=0),
                dcc.Store(id="selected-student-id", data=None),
                dcc.Download(id="download-students-csv"),
            ]),
        ]),
    ])


def register_callbacks(app):

    @app.callback(
        Output("students-table", "children"),
        Input("students-refresh", "data"),
        Input("student-search",   "value"),
    )
    def refresh_table(_, search):
        db = get_db()
        try:
            q = db.query(Student).filter_by(is_active=True)
            if search:
                s = f"%{search.lower()}%"
                from sqlalchemy import or_, func as sqlfunc
                q = q.filter(or_(
                    sqlfunc.lower(Student.first_name).like(s),
                    sqlfunc.lower(Student.last_name).like(s),
                    sqlfunc.lower(Student.email).like(s),
                    sqlfunc.lower(Student.student_code).like(s),
                ))
            students = q.order_by(Student.last_name, Student.first_name).all()
        finally:
            db.close()

        if not students:
            return empty_state("🎓", "Aucun étudiant trouvé", "Modifiez votre recherche ou ajoutez un étudiant.")

        rows = []
        for s in students:
            n_abs   = sum(1 for a in s.attendances if a.is_absent)
            n_total = len(s.attendances)
            abs_rate = round(n_abs / n_total * 100) if n_total else 0
            grades_list = s.grades
            avg = round(
                sum(g.score * g.coefficient for g in grades_list) /
                sum(g.coefficient for g in grades_list), 1
            ) if grades_list else None

            rows.append(html.Div(style={
                "display":"grid",
                "gridTemplateColumns":"2fr 2fr 1fr 1fr 1fr auto",
                "alignItems":"center","gap":"12px",
                "padding":"12px 16px","borderBottom":"1px solid var(--border)",
                "cursor":"pointer","transition":"background 0.15s",
            }, id={"type":"student-row","index":s.id}, children=[
                html.Div(className="flex-center gap-10", children=[
                    html.Div(
                        (s.first_name[0] + s.last_name[0]).upper(),
                        style={
                            "width":"38px","height":"38px","borderRadius":"50%",
                            "background":f"linear-gradient(135deg,{COLORS['primary']},{COLORS['secondary']})",
                            "display":"flex","alignItems":"center","justifyContent":"center",
                            "fontWeight":"700","fontSize":"13px","flexShrink":"0",
                        }
                    ),
                    html.Div([
                        html.Div(s.full_name, style={"fontWeight":"600","fontSize":"14px"}),
                        html.Div(s.student_code, style={"fontSize":"11px","color":"var(--text-muted)"}),
                    ]),
                ]),
                html.Div(s.email, style={"fontSize":"12px","color":"var(--text-muted)","overflow":"hidden","textOverflow":"ellipsis"}),
                html.Div(
                    f"{abs_rate}%",
                    style={"color":"var(--danger)" if abs_rate > 20 else "var(--warning)" if abs_rate > 10 else "var(--success)","fontWeight":"600","fontSize":"13px"}
                ),
                html.Div(
                    f"{avg}/20" if avg else "–",
                    style={"fontWeight":"600","fontSize":"13px","color":"var(--accent)" if (avg or 0) >= 10 else "var(--danger)"}
                ),
                badge("Actif", "success"),
                html.Div(className="flex-center gap-6", children=[
                    html.Button("👁", id={"type":"view-student-btn","index":s.id},
                               className="btn btn-sm btn-outline btn-icon", n_clicks=0,
                               title="Voir la fiche"),
                    html.Button("✏️", id={"type":"edit-student-btn","index":s.id},
                               className="btn btn-sm btn-outline btn-icon", n_clicks=0),
                    html.Button("🗑️", id={"type":"del-student-btn","index":s.id},
                               className="btn btn-sm btn-outline btn-icon", n_clicks=0),
                ]),
            ]))

        header = html.Div(style={
            "display":"grid",
            "gridTemplateColumns":"2fr 2fr 1fr 1fr 1fr auto",
            "gap":"12px","padding":"10px 16px",
            "background":"var(--surface2)","borderRadius":"var(--radius-sm) var(--radius-sm) 0 0",
        }, children=[
            html.Span("Étudiant",  style={"fontSize":"11px","fontWeight":"700","textTransform":"uppercase","color":"var(--text-muted)","letterSpacing":"0.5px"}),
            html.Span("Email",     style={"fontSize":"11px","fontWeight":"700","textTransform":"uppercase","color":"var(--text-muted)","letterSpacing":"0.5px"}),
            html.Span("Absences",  style={"fontSize":"11px","fontWeight":"700","textTransform":"uppercase","color":"var(--text-muted)","letterSpacing":"0.5px"}),
            html.Span("Moyenne",   style={"fontSize":"11px","fontWeight":"700","textTransform":"uppercase","color":"var(--text-muted)","letterSpacing":"0.5px"}),
            html.Span("Statut",    style={"fontSize":"11px","fontWeight":"700","textTransform":"uppercase","color":"var(--text-muted)","letterSpacing":"0.5px"}),
            html.Span("Actions",   style={"fontSize":"11px","fontWeight":"700","textTransform":"uppercase","color":"var(--text-muted)","letterSpacing":"0.5px"}),
        ])

        return html.Div(className="card", style={"padding":"0","overflow":"hidden"}, children=[
            header, html.Div(rows)
        ])

    @app.callback(
        Output("student-profile-modal", "children"),
        Input({"type": "view-student-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def show_profile(n_clicks_list):
        if not any(n_clicks_list):
            return html.Div()
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            return html.Div()
        return _student_profile(triggered["index"])

    @app.callback(
        Output("student-modal-container", "children"),
        Input("open-student-modal", "n_clicks"),
        Input({"type": "edit-student-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def open_modal(new_click, edit_clicks):
        triggered = ctx.triggered_id
        if triggered == "open-student-modal":
            return _student_modal()
        if isinstance(triggered, dict) and triggered.get("type") == "edit-student-btn":
            db = get_db()
            try:
                s = db.query(Student).get(triggered["index"])
                return _student_modal(s)
            finally:
                db.close()
        return no_update

    @app.callback(
        Output("student-feedback",       "children"),
        Output("students-refresh",       "data"),
        Output("student-modal-container","children", allow_duplicate=True),
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
            return alert_msg("Prénom, nom et email obligatoires.", "danger", "⚠️"), no_update, no_update

        db = get_db()
        try:
            if edit_id:
                s = db.query(Student).get(edit_id)
            else:
                if db.query(Student).filter_by(email=email).first():
                    return alert_msg("Email déjà utilisé.", "danger", "⚠️"), no_update, no_update
                # Générer code auto
                n_stu = db.query(Student).count() + 1
                s = Student(student_code=code or f"ETU-{date.today().year}-{n_stu:03d}")
                db.add(s)

            s.first_name = first
            s.last_name  = last
            s.email      = email
            s.phone      = phone
            if birth:
                from datetime import datetime
                s.birth_date = datetime.strptime(birth, "%Y-%m-%d").date()

            db.commit()
            return (
                alert_msg(f"Étudiant {'modifié' if edit_id else 'ajouté'} ✅", "success", "✅"),
                (refresh or 0) + 1,
                html.Div(),
            )
        except Exception as e:
            db.rollback()
            return alert_msg(f"Erreur : {e}", "danger"), no_update, no_update
        finally:
            db.close()

    @app.callback(
        Output("student-feedback",   "children", allow_duplicate=True),
        Output("students-refresh",   "data",     allow_duplicate=True),
        Input({"type": "del-student-btn", "index": ALL}, "n_clicks"),
        State("students-refresh", "data"),
        prevent_initial_call=True,
    )
    def delete_student(n_clicks_list, refresh):
        if not any(n_clicks_list):
            return no_update, no_update
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            return no_update, no_update
        db = get_db()
        try:
            s = db.query(Student).get(triggered["index"])
            if s:
                s.is_active = False
                db.commit()
            return alert_msg("Étudiant désactivé.", "warning", "🗑️"), (refresh or 0) + 1
        except Exception as e:
            db.rollback()
            return alert_msg(str(e), "danger"), no_update
        finally:
            db.close()

    @app.callback(
        Output("student-modal-container", "children", allow_duplicate=True),
        Output("student-profile-modal",   "children", allow_duplicate=True),
        Input("close-student-modal",  "n_clicks"),
        Input("close-profile-modal",  "n_clicks"),
        prevent_initial_call=True,
    )
    def close_modals(n1, n2):
        return html.Div(), html.Div()


def _student_profile(student_id: int) -> html.Div:
    db = get_db()
    try:
        s = db.query(Student).get(student_id)
        if not s:
            return html.Div()

        n_abs    = sum(1 for a in s.attendances if a.is_absent)
        n_total  = len(s.attendances)
        abs_rate = round(n_abs / n_total * 100, 1) if n_total else 0

        grades   = s.grades
        avg = round(
            sum(g.score * g.coefficient for g in grades) /
            sum(g.coefficient for g in grades), 1
        ) if grades else None

        # Notes par cours
        course_grades = {}
        for g in grades:
            if g.course_id not in course_grades:
                course_grades[g.course_id] = {"label": g.course.label if g.course else "?",
                                               "color": g.course.color if g.course else COLORS["primary"],
                                               "grades": []}
            course_grades[g.course_id]["grades"].append(g)

        grade_rows = []
        for cid, data in course_grades.items():
            g_list = data["grades"]
            w_sum = sum(g.score * g.coefficient for g in g_list)
            c_sum = sum(g.coefficient for g in g_list)
            course_avg = round(w_sum / c_sum, 1) if c_sum else 0
            color = "var(--success)" if course_avg >= 10 else "var(--danger)"
            grade_rows.append(html.Div(style={
                "display":"grid","gridTemplateColumns":"3fr 2fr 1fr",
                "gap":"8px","alignItems":"center",
                "padding":"8px 0","borderBottom":"1px solid var(--border)",
            }, children=[
                html.Div(className="flex-center gap-8", children=[
                    html.Div(style={"width":"8px","height":"8px","borderRadius":"50%","background":data["color"]}),
                    html.Span(data["label"], style={"fontSize":"13px"}),
                ]),
                html.Div(className="flex-center gap-4", children=[
                    html.Span(f"{g.score}/20", style={"fontSize":"11px","color":"var(--text-muted)"})
                    for g in g_list
                ]),
                html.Span(f"{course_avg}/20", style={"fontWeight":"700","color":color,"fontSize":"14px"}),
            ]))

        return html.Div(className="modal-overlay", children=[
            html.Div(className="modal-box", style={"maxWidth":"640px"}, children=[
                html.Div(className="flex-between", style={"marginBottom":"24px"}, children=[
                    html.H2("Fiche étudiant", style={"fontFamily":"'Syne',sans-serif","fontSize":"20px","fontWeight":"800"}),
                    html.Button("✕", id="close-profile-modal", className="btn btn-outline btn-icon", n_clicks=0),
                ]),

                # Infos
                html.Div(className="flex-center gap-16", style={"marginBottom":"24px"}, children=[
                    html.Div(
                        (s.first_name[0] + s.last_name[0]).upper(),
                        style={
                            "width":"64px","height":"64px","borderRadius":"50%",
                            "background":f"linear-gradient(135deg,{COLORS['primary']},{COLORS['secondary']})",
                            "display":"flex","alignItems":"center","justifyContent":"center",
                            "fontWeight":"800","fontSize":"22px","flexShrink":"0",
                        }
                    ),
                    html.Div([
                        html.H3(s.full_name, style={"fontFamily":"'Syne',sans-serif","fontSize":"20px","fontWeight":"800","marginBottom":"4px"}),
                        html.Div(s.student_code, style={"fontSize":"12px","color":"var(--text-muted)"}),
                        html.Div(s.email, style={"fontSize":"12px","color":"var(--text-muted)"}),
                    ]),
                ]),

                html.Div(className="grid-3", style={"marginBottom":"24px"}, children=[
                    html.Div(style={
                        "background":"var(--surface2)","borderRadius":"var(--radius-md)",
                        "padding":"14px","textAlign":"center",
                    }, children=[
                        html.Div(str(n_total), style={"fontSize":"24px","fontWeight":"800"}),
                        html.Div("Séances", style={"fontSize":"11px","color":"var(--text-muted)"}),
                    ]),
                    html.Div(style={
                        "background":"rgba(255,71,87,0.1)","borderRadius":"var(--radius-md)",
                        "padding":"14px","textAlign":"center",
                    }, children=[
                        html.Div(f"{abs_rate}%", style={"fontSize":"24px","fontWeight":"800","color":"var(--danger)"}),
                        html.Div("Absences", style={"fontSize":"11px","color":"var(--text-muted)"}),
                    ]),
                    html.Div(style={
                        "background":"rgba(67,233,123,0.1)","borderRadius":"var(--radius-md)",
                        "padding":"14px","textAlign":"center",
                    }, children=[
                        html.Div(f"{avg}/20" if avg else "–",
                                 style={"fontSize":"24px","fontWeight":"800","color":"var(--accent)"}),
                        html.Div("Moyenne", style={"fontSize":"11px","color":"var(--text-muted)"}),
                    ]),
                ]),

                html.Div("Notes par matière", style={"fontWeight":"700","marginBottom":"12px","fontSize":"14px"}),
                html.Div(grade_rows or [html.P("Aucune note.", style={"color":"var(--text-muted)","fontSize":"13px"})]),
            ]),
        ])
    finally:
        db.close()


def _student_modal(student: Student = None) -> html.Div:
    is_edit = student is not None
    return html.Div(className="modal-overlay", children=[
        html.Div(className="modal-box", children=[
            html.Div(className="flex-between", style={"marginBottom":"24px"}, children=[
                html.H2("Modifier l'étudiant" if is_edit else "Nouvel étudiant",
                        style={"fontFamily":"'Syne',sans-serif","fontSize":"20px","fontWeight":"800"}),
                html.Button("✕", id="close-student-modal", className="btn btn-outline btn-icon", n_clicks=0),
            ]),

            dcc.Store(id="stu-edit-id", data=student.id if is_edit else None),

            html.Div(className="grid-2", children=[
                html.Div(className="form-group", children=[
                    html.Label("Prénom *", className="form-label"),
                    dcc.Input(id="stu-first", value=student.first_name if is_edit else "",
                              placeholder="Prénom", className="dash-input", style={"width":"100%"}),
                ]),
                html.Div(className="form-group", children=[
                    html.Label("Nom *", className="form-label"),
                    dcc.Input(id="stu-last", value=student.last_name if is_edit else "",
                              placeholder="Nom de famille", className="dash-input", style={"width":"100%"}),
                ]),
            ]),

            html.Div(className="form-group", children=[
                html.Label("Email *", className="form-label"),
                dcc.Input(id="stu-email", type="email",
                          value=student.email if is_edit else "",
                          placeholder="etudiant@mail.fr", className="dash-input",
                          style={"width":"100%"}),
            ]),

            html.Div(className="grid-2", children=[
                html.Div(className="form-group", children=[
                    html.Label("Code étudiant", className="form-label"),
                    dcc.Input(id="stu-code",
                              value=student.student_code if is_edit else "",
                              placeholder="ETU-2024-001 (auto si vide)",
                              className="dash-input", style={"width":"100%"}),
                ]),
                html.Div(className="form-group", children=[
                    html.Label("Téléphone", className="form-label"),
                    dcc.Input(id="stu-phone",
                              value=student.phone if is_edit else "",
                              placeholder="+33 6 xx xx xx xx",
                              className="dash-input", style={"width":"100%"}),
                ]),
            ]),

            html.Div(className="form-group", children=[
                html.Label("Date de naissance", className="form-label"),
                dcc.DatePickerSingle(
                    id="stu-birth",
                    date=str(student.birth_date) if (is_edit and student.birth_date) else None,
                    display_format="DD/MM/YYYY",
                    max_date_allowed=str(date.today()),
                ),
            ]),

            html.Div(className="flex-center gap-12", style={"marginTop":"24px","justifyContent":"flex-end"}, children=[
                html.Button("Annuler", id="close-student-modal", className="btn btn-outline", n_clicks=0),
                html.Button("Enregistrer" if is_edit else "Ajouter l'étudiant",
                           id="save-student-btn", className="btn btn-primary", n_clicks=0),
            ]),
        ]),
    ])