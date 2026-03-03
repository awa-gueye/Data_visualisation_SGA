"""
pages/sessions.py – Module 2 : Cahier de texte & Présences
"""
from dash import html, dcc, Input, Output, State, callback, no_update, ctx, ALL
import dash
from datetime import date
from pages.components import sidebar, topbar, card, section_title, badge, empty_state, alert_msg
from utils.db import get_db
from models import Course, Session, Attendance, Student
from config import COLORS


def layout(user: dict = None):
    db = get_db()
    try:
        courses = db.query(Course).filter_by(is_active=True).order_by(Course.code).all()
        course_opts = [{"label": f"{c.code} – {c.label}", "value": c.id} for c in courses]
    finally:
        db.close()

    return html.Div(id="app-shell", children=[
        sidebar("/sessions", user),
        html.Div(id="main-content", children=[
            topbar("Séances & Présences", "Cahier de texte numérique"),
            html.Div(id="page-content", children=[

                html.Div(className="grid-2", style={"gap":"24px","alignItems":"start"}, children=[

                    # ── Formulaire nouvelle séance ─────────────────────────
                    card(title="📅 Nouvelle séance", children=[
                        html.Div(id="session-feedback"),

                        html.Div(className="form-group", children=[
                            html.Label("Cours *", className="form-label"),
                            dcc.Dropdown(id="sess-course", options=course_opts,
                                         placeholder="Sélectionner un cours",
                                         style={"background":"var(--surface2)"}),
                        ]),

                        html.Div(className="grid-2", children=[
                            html.Div(className="form-group", children=[
                                html.Label("Date *", className="form-label"),
                                dcc.DatePickerSingle(
                                    id="sess-date",
                                    date=date.today(),
                                    display_format="DD/MM/YYYY",
                                    style={"width":"100%"},
                                ),
                            ]),
                            html.Div(className="form-group", children=[
                                html.Label("Durée (h) *", className="form-label"),
                                dcc.Input(id="sess-duration", type="number", value=2,
                                          min=0.5, step=0.5, className="dash-input",
                                          style={"width":"100%"}),
                            ]),
                        ]),

                        html.Div(className="form-group", children=[
                            html.Label("Thème abordé", className="form-label"),
                            dcc.Input(id="sess-theme", placeholder="ex: Introduction aux intégrales",
                                      className="dash-input", style={"width":"100%"}),
                        ]),

                        html.Div(className="form-group", children=[
                            html.Label("Salle", className="form-label"),
                            dcc.Input(id="sess-room", placeholder="ex: Salle A101",
                                      className="dash-input", style={"width":"100%"}),
                        ]),

                        html.Div(className="form-group", children=[
                            html.Label("Notes pédagogiques", className="form-label"),
                            dcc.Textarea(id="sess-notes", placeholder="Contenu du cours, remarques...",
                                         className="dash-input",
                                         style={"width":"100%","minHeight":"80px"}),
                        ]),

                        html.Div(className="divider"),

                        # Appel numérique
                        html.Div(className="form-label", style={"marginBottom":"10px"}, children=[
                            "✅ Appel numérique",
                            html.Span(" · Cochez les absents", style={"color":"var(--text-muted)","textTransform":"none","fontWeight":"400"}),
                        ]),
                        html.Div(id="attendance-checklist",
                                 children=[html.P("← Sélectionnez un cours",
                                                  style={"color":"var(--text-muted)","fontSize":"13px"})]),

                        html.Button(
                            "💾 Enregistrer la séance",
                            id="save-session-btn",
                            className="btn btn-primary",
                            n_clicks=0,
                            style={"width":"100%","marginTop":"16px","padding":"14px"},
                        ),

                        dcc.Store(id="sessions-refresh", data=0),
                    ]),

                    # ── Historique ─────────────────────────────────────────
                    card(title="📋 Historique des séances", children=[
                        html.Div(className="form-group", children=[
                            html.Label("Filtrer par cours", className="form-label"),
                            dcc.Dropdown(
                                id="filter-course-sess",
                                options=[{"label":"Tous les cours","value":"all"}] + course_opts,
                                value="all",
                                clearable=False,
                                style={"background":"var(--surface2)"},
                            ),
                        ]),
                        html.Div(id="sessions-history"),
                    ]),
                ]),
            ]),
        ]),
    ])


def register_callbacks(app):

    @app.callback(
        Output("attendance-checklist", "children"),
        Input("sess-course", "value"),
    )
    def load_students_checklist(course_id):
        if not course_id:
            return html.P("← Sélectionnez un cours", style={"color":"var(--text-muted)","fontSize":"13px"})
        db = get_db()
        try:
            students = db.query(Student).filter_by(is_active=True).order_by(Student.last_name).all()
        finally:
            db.close()

        if not students:
            return html.P("Aucun étudiant actif.", style={"color":"var(--text-muted)","fontSize":"13px"})

        items = []
        for s in students:
            items.append(
                html.Div(className="attendance-item", id={"type":"att-item","index":s.id}, children=[
                    dcc.Checklist(
                        id={"type":"att-absent","index":s.id},
                        options=[{"label":"","value":"absent"}],
                        value=[],
                        style={"margin":"0"},
                    ),
                    html.Div(className="flex-between", style={"flex":"1"}, children=[
                        html.Div(className="flex-center gap-8", children=[
                            html.Div(
                                (s.first_name[0] + s.last_name[0]).upper(),
                                style={
                                    "width":"32px","height":"32px","borderRadius":"50%",
                                    "background":"linear-gradient(135deg,var(--primary),var(--secondary))",
                                    "display":"flex","alignItems":"center","justifyContent":"center",
                                    "fontSize":"12px","fontWeight":"700","flexShrink":"0",
                                }
                            ),
                            html.Div(children=[
                                html.Div(s.full_name, style={"fontWeight":"600","fontSize":"13px"}),
                                html.Div(s.student_code, style={"fontSize":"11px","color":"var(--text-muted)"}),
                            ]),
                        ]),
                        dcc.Checklist(
                            id={"type":"att-late","index":s.id},
                            options=[{"label":"En retard","value":"late"}],
                            value=[],
                            style={"fontSize":"11px","color":"var(--warning)"},
                        ),
                    ]),
                ])
            )
        return html.Div(className="attendance-list", children=items)

    @app.callback(
        Output("session-feedback", "children"),
        Output("sessions-refresh", "data"),
        Input("save-session-btn", "n_clicks"),
        State("sess-course",   "value"),
        State("sess-date",     "date"),
        State("sess-duration", "value"),
        State("sess-theme",    "value"),
        State("sess-room",     "value"),
        State("sess-notes",    "value"),
        State({"type": "att-absent", "index": ALL}, "value"),
        State({"type": "att-absent", "index": ALL}, "id"),
        State({"type": "att-late",   "index": ALL}, "value"),
        State("sessions-refresh", "data"),
        prevent_initial_call=True,
    )
    def save_session(n_clicks, course_id, sess_date, duration,
                     theme, room, notes,
                     absent_values, absent_ids, late_values,
                     refresh):
        if not n_clicks:
            return no_update, no_update
        if not course_id:
            return alert_msg("Sélectionnez un cours.", "danger", "⚠️"), no_update
        if not sess_date:
            return alert_msg("Date obligatoire.", "danger", "⚠️"), no_update

        from datetime import datetime
        db = get_db()
        try:
            sess = Session(
                course_id=course_id,
                date=datetime.strptime(sess_date, "%Y-%m-%d").date(),
                duration=float(duration or 2),
                theme=theme,
                room=room,
                notes=notes,
            )
            db.add(sess)
            db.flush()

            # Enregistrer les présences
            for abs_val, abs_id, late_val in zip(absent_values, absent_ids, late_values):
                student_id = abs_id["index"]
                is_absent  = "absent" in (abs_val or [])
                is_late    = "late"   in (late_val or [])
                att = Attendance(
                    session_id=sess.id,
                    student_id=student_id,
                    is_absent=is_absent,
                    is_late=is_late,
                )
                db.add(att)

            db.commit()
            n_absent = sum(1 for v in absent_values if "absent" in (v or []))
            return (
                alert_msg(f"Séance enregistrée ! {n_absent} absent(s) noté(s).", "success", "✅"),
                (refresh or 0) + 1,
            )
        except Exception as e:
            db.rollback()
            return alert_msg(f"Erreur : {e}", "danger", "❌"), no_update
        finally:
            db.close()

    @app.callback(
        Output("sessions-history", "children"),
        Input("filter-course-sess", "value"),
        Input("sessions-refresh",   "data"),
    )
    def load_history(course_filter, _):
        db = get_db()
        try:
            q = db.query(Session).order_by(Session.date.desc())
            if course_filter and course_filter != "all":
                q = q.filter(Session.course_id == int(course_filter))
            sessions = q.limit(30).all()
        finally:
            db.close()

        if not sessions:
            return empty_state("📅", "Aucune séance", "Créez votre première séance.")

        return html.Div([_session_history_row(s) for s in sessions])


def _session_history_row(s: Session) -> html.Div:
    n_total  = len(s.attendances)
    n_absent = sum(1 for a in s.attendances if a.is_absent)
    n_present = n_total - n_absent
    abs_color = "var(--danger)" if n_absent > 0 else "var(--success)"
    course_color = s.course.color if s.course else COLORS["primary"]

    return html.Div(style={
        "padding":"14px 0","borderBottom":"1px solid var(--border)",
        "display":"flex","gap":"14px","alignItems":"flex-start",
    }, children=[
        html.Div(style={
            "minWidth":"3px","width":"3px","borderRadius":"2px",
            "background":course_color,"alignSelf":"stretch",
        }),
        html.Div(style={"flex":"1"}, children=[
            html.Div(className="flex-between", children=[
                html.Div(className="flex-center gap-8", children=[
                    html.Span(s.course.code if s.course else "?", style={
                        "background":course_color,"color":"white","padding":"2px 8px",
                        "borderRadius":"99px","fontSize":"11px","fontWeight":"700",
                    }),
                    html.Span(s.date.strftime("%d/%m/%Y"),
                              style={"fontSize":"12px","color":"var(--text-muted)"}),
                    html.Span(f"⏱ {s.duration}h",
                              style={"fontSize":"11px","color":"var(--text-muted)"}),
                ]),
                html.Div(className="flex-center gap-8", children=[
                    html.Span(f"✅ {n_present}", style={"fontSize":"12px","color":"var(--success)"}),
                    html.Span(f"❌ {n_absent}", style={"fontSize":"12px","color":abs_color}),
                ]),
            ]),
            html.Div(s.theme or "Sans thème",
                     style={"fontSize":"13px","fontWeight":"500","margin":"4px 0 2px"}),
            html.Div(s.room or "",
                     style={"fontSize":"11px","color":"var(--text-muted)"}),
        ]),
    ])