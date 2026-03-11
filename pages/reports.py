"""
pages/reports.py – Bonus : Génération de rapports PDF
"""
from dash import html, dcc, Input, Output, State, callback, no_update
import dash
from pages.components import sidebar, topbar, card, section_title, badge, empty_state, alert_msg
from utils.db import get_db
from utils.pdf_gen import generate_student_report, generate_attendance_report
from models import Student, Course, Session, Attendance, Grade
from config import COLORS
from utils.format import fr, fr_pct, fr_note

def layout(user: dict = None):
    db = get_db()
    try:
        students = db.query(Student).filter_by(is_active=True).order_by(Student.last_name).all()
        courses  = db.query(Course).filter_by(is_active=True).order_by(Course.code).all()
        stu_opts = [{"label": f"{s.full_name} ({s.student_code})", "value": s.id} for s in students]
        crs_opts = [{"label": f"{c.code} – {c.label}", "value": c.id} for c in courses]
    finally:
        db.close()

    return html.Div(id="app-shell", children=[
        sidebar("/reports", user),
        html.Div(id="main-content", children=[
            topbar("Bulletins & Rapports", "Export PDF"),
            html.Div(id="page-content", children=[

                section_title("Génération de documents", "Bulletins de notes et rapports de présence"),

                html.Div(className="grid-2", style={"gap":"24px"}, children=[

                    # ── Bulletin de notes ──────────────────────────────────
                    card(title=" Bulletin de notes individuel", children=[
                        html.Div(id="bulletin-feedback"),
                        html.P("Sélectionnez un étudiant pour générer son bulletin de notes complet au format PDF.",
                               style={"color":"var(--text-muted)","fontSize":"13px","marginBottom":"16px"}),

                        html.Div(className="form-group", children=[
                            html.Label("Étudiant *", className="form-label"),
                            dcc.Dropdown(id="bulletin-student", options=stu_opts,
                                         placeholder="Sélectionner un étudiant",
                                         style={"background":"var(--surface2)"}),
                        ]),

                        html.Div(id="student-preview", style={"margin":"16px 0"}),

                        html.Button(
                            " Générer le bulletin PDF",
                            id="gen-bulletin-btn",
                            className="btn btn-primary",
                            n_clicks=0,
                            style={"width":"100%","padding":"14px"},
                        ),
                        dcc.Download(id="download-bulletin"),
                    ]),

                    # ── Rapport de présences ───────────────────────────────
                    card(title=" Rapport de présences", children=[
                        html.Div(id="attendance-report-feedback"),
                        html.P("Générez un rapport de présence complet pour un cours.",
                               style={"color":"var(--text-muted)","fontSize":"13px","marginBottom":"16px"}),

                        html.Div(className="form-group", children=[
                            html.Label("Cours *", className="form-label"),
                            dcc.Dropdown(id="report-course", options=crs_opts,
                                         placeholder="Sélectionner un cours",
                                         style={"background":"var(--surface2)"}),
                        ]),

                        html.Button(
                            " Générer le rapport PDF",
                            id="gen-report-btn",
                            className="btn btn-success",
                            n_clicks=0,
                            style={"width":"100%","padding":"14px"},
                        ),
                        dcc.Download(id="download-report"),
                    ]),
                ]),

                # ── Bulletins en masse ─────────────────────────────────────
                html.Div(style={"marginTop":"24px"}, children=[
                    card(title=" Export en masse", children=[
                        html.P("Générez tous les bulletins d'une classe en un seul fichier ZIP.",
                               style={"color":"var(--text-muted)","fontSize":"13px","marginBottom":"16px"}),
                        html.Div(id="bulk-feedback"),
                        html.Div(className="flex-center gap-12", children=[
                            html.Button(
                                " Télécharger tous les bulletins (ZIP)",
                                id="bulk-bulletins-btn",
                                className="btn btn-outline",
                                n_clicks=0,
                                style={"padding":"12px 20px"},
                            ),
                            dcc.Download(id="download-bulk"),
                        ]),
                    ]),
                ]),
            ]),
        ]),
    ])


def register_callbacks(app):

    @app.callback(
        Output("student-preview", "children"),
        Input("bulletin-student", "value"),
    )
    def preview_student(student_id):
        if not student_id:
            return html.Div()
        db = get_db()
        try:
            s = db.query(Student).get(student_id)
            if not s:
                return html.Div()
            n_abs  = sum(1 for a in s.attendances if a.is_absent)
            n_tot  = len(s.attendances)
            avg = None
            if s.grades:
                wa = sum(g.score * g.coefficient for g in s.grades)
                wt = sum(g.coefficient for g in s.grades)
                avg = round(wa/wt, 1) if wt else None

            return html.Div(style={
                "background":"var(--surface2)","borderRadius":"var(--radius-md)",
                "padding":"16px","display":"flex","gap":"16px","alignItems":"center",
            }, children=[
                html.Div(
                    (s.first_name[0] + s.last_name[0]).upper(),
                    style={
                        "width":"48px","height":"48px","borderRadius":"50%",
                        "background":f"linear-gradient(135deg,{COLORS['primary']},{COLORS['secondary']})",
                        "display":"flex","alignItems":"center","justifyContent":"center",
                        "fontWeight":"700","fontSize":"16px","flexShrink":"0",
                    }
                ),
                html.Div([
                    html.Div(s.full_name, style={"fontWeight":"700","fontSize":"16px"}),
                    html.Div(s.student_code, style={"fontSize":"12px","color":"var(--text-muted)"}),
                    html.Div(className="flex-center gap-16", style={"marginTop":"6px"}, children=[
                        html.Span(f" {avg}/20" if avg else " –",
                                  style={"fontSize":"12px","color":"var(--accent)","fontWeight":"600"}),
                        html.Span(f" {n_abs}/{n_tot} absences",
                                  style={"fontSize":"12px","color":"var(--danger)" if n_abs > 3 else "var(--text-muted)"}),
                        html.Span(f" {len(s.grades)} note(s)",
                                  style={"fontSize":"12px","color":"var(--text-muted)"}),
                    ]),
                ]),
            ])
        finally:
            db.close()

    @app.callback(
        Output("bulletin-feedback", "children"),
        Output("download-bulletin", "data"),
        Input("gen-bulletin-btn",   "n_clicks"),
        State("bulletin-student",   "value"),
        prevent_initial_call=True,
    )
    def generate_bulletin(n, student_id):
        if not n or not student_id:
            return alert_msg("Sélectionnez un étudiant.", "warning", "⚠️"), no_update
        db = get_db()
        try:
            s        = db.query(Student).get(student_id)
            grades   = db.query(Grade).filter_by(student_id=student_id).all()
            atts     = db.query(Attendance).filter_by(student_id=student_id).all()
            courses  = db.query(Course).all()

            pdf_bytes = generate_student_report(s, grades, atts, courses)
            filename  = f"bulletin_{s.student_code}_{s.last_name}.pdf"
            return (
                alert_msg(f"Bulletin de {s.full_name} généré ", "success", "✅"),
                dcc.send_bytes(pdf_bytes, filename),
            )
        except Exception as e:
            return alert_msg(f"Erreur PDF : {e}", "danger", ""), no_update
        finally:
            db.close()

    @app.callback(
        Output("attendance-report-feedback", "children"),
        Output("download-report",            "data"),
        Input("gen-report-btn",              "n_clicks"),
        State("report-course",               "value"),
        prevent_initial_call=True,
    )
    def generate_report(n, course_id):
        if not n or not course_id:
            return alert_msg("Sélectionnez un cours.", "warning", ""), no_update
        db = get_db()
        try:
            course = db.query(Course).get(course_id)
            sessions_data = []
            for sess in sorted(course.sessions, key=lambda s: s.date):
                sessions_data.append({
                    "session":     sess,
                    "attendances": sess.attendances,
                })

            pdf_bytes = generate_attendance_report(course, sessions_data)
            filename  = f"presences_{course.code}.pdf"
            return (
                alert_msg(f"Rapport {course.code} généré ", "success", ""),
                dcc.send_bytes(pdf_bytes, filename),
            )
        except Exception as e:
            return alert_msg(f"Erreur PDF : {e}", "danger", ""), no_update
        finally:
            db.close()

    @app.callback(
        Output("bulk-feedback",   "children"),
        Output("download-bulk",   "data"),
        Input("bulk-bulletins-btn","n_clicks"),
        prevent_initial_call=True,
    )
    def bulk_download(n):
        if not n:
            return no_update, no_update
        import io, zipfile
        db = get_db()
        try:
            students = db.query(Student).filter_by(is_active=True).all()
            courses  = db.query(Course).all()
            zip_buf  = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for s in students:
                    grades = db.query(Grade).filter_by(student_id=s.id).all()
                    atts   = db.query(Attendance).filter_by(student_id=s.id).all()
                    try:
                        pdf_b = generate_student_report(s, grades, atts, courses)
                        zf.writestr(f"bulletin_{s.student_code}_{s.last_name}.pdf", pdf_b)
                    except Exception:
                        pass
            return (
                alert_msg(f"{len(students)} bulletins générés ", "success", "✅"),
                dcc.send_bytes(zip_buf.getvalue(), "bulletins_tous.zip"),
            )
        except Exception as e:
            return alert_msg(f"Erreur : {e}", "danger"), no_update
        finally:
            db.close()