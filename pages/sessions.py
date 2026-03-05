"""
pages/sessions.py  Module 2 : Cahier de texte & Présences
"""
from dash import html, dcc, Input, Output, State, no_update, ctx, ALL
import dash
from datetime import date
from pages.components import sidebar, topbar, card, section_title, badge, empty_state, alert_msg
from utils.db import get_db
from models import Course, Session, Attendance, Student
from config import COLORS
from sqlalchemy.orm import joinedload


def layout(user: dict = None):
    db = get_db()
    try:
        courses = db.query(Course).filter_by(is_active=True).order_by(Course.code).all()
        course_opts = [{"label": f"{c.code}  {c.label}", "value": c.id} for c in courses]
    finally:
        db.close()

    return html.Div(id="app-shell", children=[
        sidebar("/sessions", user),
        html.Div(id="main-content", children=[
            topbar("Séances & Présences", "Cahier de texte numérique"),
            html.Div(id="page-content", children=[

                dcc.Store(id="sessions-refresh", data=0),

                html.Div(className="grid-2", style={"gap": "24px", "alignItems": "start"}, children=[

                    card(title="Nouvelle séance", children=[
                        html.Div(id="session-feedback"),

                        html.Div(className="form-group", children=[
                            html.Label("Cours *", className="form-label"),
                            dcc.Dropdown(id="sess-course", options=course_opts,
                                         placeholder="Sélectionner un cours",
                                         style={"background": "var(--bg-card)"}),
                        ]),

                        html.Div(className="grid-2", children=[
                            html.Div(className="form-group", children=[
                                html.Label("Date *", className="form-label"),
                                dcc.DatePickerSingle(
                                    id="sess-date",
                                    date=date.today(),
                                    display_format="DD/MM/YYYY",
                                    style={"width": "100%"},
                                ),
                            ]),
                            html.Div(className="form-group", children=[
                                html.Label("Durée (h) *", className="form-label"),
                                dcc.Input(id="sess-duration", type="number", value=2,
                                          min=0.5, step=0.5, className="dash-input",
                                          style={"width": "100%"}),
                            ]),
                        ]),

                        html.Div(className="form-group", children=[
                            html.Label("Thème abordé", className="form-label"),
                            dcc.Input(id="sess-theme",
                                      placeholder="ex: Introduction aux intégrales",
                                      className="dash-input", style={"width": "100%"}),
                        ]),

                        html.Div(className="form-group", children=[
                            html.Label("Salle", className="form-label"),
                            dcc.Input(id="sess-room", placeholder="ex: Salle A101",
                                      className="dash-input", style={"width": "100%"}),
                        ]),

                        html.Div(className="form-group", children=[
                            html.Label("Notes pédagogiques", className="form-label"),
                            dcc.Textarea(id="sess-notes",
                                         placeholder="Contenu du cours, remarques...",
                                         className="dash-input",
                                         style={"width": "100%", "minHeight": "80px"}),
                        ]),

                        html.Div(style={"borderTop": "1px solid var(--border-gris)", "margin": "16px 0 12px"}),
                        html.Div(style={"marginBottom": "10px", "display": "flex", "alignItems": "center", "gap": "8px"}, children=[
                            html.Span("Appel numérique",
                                      style={"fontWeight": "700", "fontSize": "13px",
                                             "textTransform": "uppercase", "letterSpacing": "1px"}),
                            html.Span("· Cochez les absents",
                                      style={"color": "var(--gris-moyen)", "fontSize": "12px"}),
                        ]),
                        html.Div(id="attendance-checklist",
                                 children=[html.P("Sélectionnez un cours",
                                                  style={"color": "var(--gris-moyen)", "fontSize": "13px"})]),

                        html.Button(
                            "Enregistrer la séance",
                            id="save-session-btn",
                            className="btn btn-primary",
                            n_clicks=0,
                            style={"width": "100%", "marginTop": "16px", "padding": "14px"},
                        ),
                    ]),

                    card(title="Historique des séances", children=[
                        html.Div(className="grid-2", style={"gap": "12px", "marginBottom": "4px"}, children=[
                            html.Div(className="form-group", children=[
                                html.Label("Filtrer par cours", className="form-label"),
                                dcc.Dropdown(
                                    id="filter-course-sess",
                                    options=[{"label": "Tous les cours", "value": "all"}] + course_opts,
                                    value="all",
                                    clearable=False,
                                    style={"background": "var(--bg-card)"},
                                ),
                            ]),
                            html.Div(className="form-group", children=[
                                html.Label("Trier par", className="form-label"),
                                dcc.Dropdown(
                                    id="sort-sess",
                                    options=[
                                        {"label": "Date (récent)", "value": "date_desc"},
                                        {"label": "Date (ancien)", "value": "date_asc"},
                                        {"label": "Cours (AZ)",  "value": "course"},
                                    ],
                                    value="date_desc",
                                    clearable=False,
                                    style={"background": "var(--bg-card)"},
                                ),
                            ]),
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
            return html.P("Sélectionnez un cours",
                          style={"color": "var(--gris-moyen)", "fontSize": "13px"})
        db = get_db()
        try:
            students = (db.query(Student)
                        .filter_by(is_active=True)
                        .order_by(Student.last_name)
                        .all())
            student_data = [
                {"id": s.id, "full_name": s.full_name,
                 "code": s.student_code,
                 "initials": (s.first_name[0] + s.last_name[0]).upper()}
                for s in students
            ]
        finally:
            db.close()

        if not student_data:
            return html.P("Aucun étudiant actif.",
                          style={"color": "var(--gris-moyen)", "fontSize": "13px"})

        items = []
        for s in student_data:
            items.append(
                html.Div(className="attendance-item",
                         id={"type": "att-item", "index": s["id"]},
                         children=[
                    dcc.Checklist(
                        id={"type": "att-absent", "index": s["id"]},
                        options=[{"label": "", "value": "absent"}],
                        value=[],
                        style={"margin": "0"},
                    ),
                    html.Div(className="flex-between", style={"flex": "1"}, children=[
                        html.Div(className="flex-center gap-8", children=[
                            html.Div(
                                s["initials"],
                                style={
                                    "width": "32px", "height": "32px",
                                    "borderRadius": "50%",
                                    "background": "linear-gradient(135deg,#6C63FF,#FF6584)",
                                    "display": "flex", "alignItems": "center",
                                    "justifyContent": "center",
                                    "fontSize": "12px", "fontWeight": "700",
                                    "color": "white", "flexShrink": "0",
                                }
                            ),
                            html.Div(children=[
                                html.Div(s["full_name"],
                                         style={"fontWeight": "600", "fontSize": "13px"}),
                                html.Div(s["code"],
                                         style={"fontSize": "11px", "color": "var(--gris-moyen)"}),
                            ]),
                        ]),
                        dcc.Checklist(
                            id={"type": "att-late", "index": s["id"]},
                            options=[{"label": "En retard", "value": "late"}],
                            value=[],
                            style={"fontSize": "11px", "color": "var(--warning)"},
                        ),
                    ]),
                ])
            )
        return html.Div(className="attendance-list", children=items)

    @app.callback(
        Output("session-feedback", "children"),
        Output("sessions-refresh", "data"),
        Input("save-session-btn",  "n_clicks"),
        State("sess-course",       "value"),
        State("sess-date",         "date"),
        State("sess-duration",     "value"),
        State("sess-theme",        "value"),
        State("sess-room",         "value"),
        State("sess-notes",        "value"),
        State({"type": "att-absent", "index": ALL}, "value"),
        State({"type": "att-absent", "index": ALL}, "id"),
        State({"type": "att-late",   "index": ALL}, "value"),
        State("sessions-refresh",  "data"),
        prevent_initial_call=True,
    )
    def save_session(n_clicks, course_id, sess_date, duration,
                     theme, room, notes,
                     absent_values, absent_ids, late_values, refresh):
        if not n_clicks:
            return no_update, no_update
        if not course_id:
            return alert_msg("Sélectionnez un cours.", "danger"), no_update
        if not sess_date:
            return alert_msg("Date obligatoire.", "danger"), no_update

        from datetime import datetime
        db = get_db()
        try:
            sess = Session(
                course_id=course_id,
                date=datetime.strptime(sess_date, "%Y-%m-%d").date(),
                duration=float(duration or 2),
                theme=theme or "",
                room=room or "",
                notes=notes or "",
            )
            db.add(sess)
            db.flush()

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
                alert_msg(f"Séance enregistrée  {n_absent} absent(s) noté(s).", "success"),
                (refresh or 0) + 1,
            )
        except Exception as e:
            db.rollback()
            return alert_msg(f"Erreur : {e}", "danger"), no_update
        finally:
            db.close()

    @app.callback(
        Output("session-feedback", "children", allow_duplicate=True),
        Output("sessions-refresh", "data",     allow_duplicate=True),
        Input({"type": "delete-session-btn", "index": ALL}, "n_clicks"),
        State("sessions-refresh", "data"),
        prevent_initial_call=True,
    )
    def delete_session(n_clicks_list, refresh):
        triggered_value = ctx.triggered[0]["value"] if ctx.triggered else 0
        if not triggered_value:
            return no_update, no_update
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            return no_update, no_update

        session_id = triggered["index"]
        db = get_db()
        try:
            s = db.query(Session).get(session_id)
            if s:
                db.delete(s)
                db.commit()
            return (
                alert_msg("Séance supprimée.", "warning"),
                (refresh or 0) + 1,
            )
        except Exception as e:
            db.rollback()
            return alert_msg(f"Erreur : {e}", "danger"), no_update
        finally:
            db.close()

    @app.callback(
        Output("sessions-history", "children"),
        Input("filter-course-sess", "value"),
        Input("sort-sess",          "value"),
        Input("sessions-refresh",   "data"),
    )
    def load_history(course_filter, sort_by, _):
        db = get_db()
        try:
            q = (db.query(Session)
                 .options(
                     joinedload(Session.course),
                     joinedload(Session.attendances),
                 ))

            if course_filter and course_filter != "all":
                q = q.filter(Session.course_id == int(course_filter))

            if sort_by == "date_asc":
                q = q.order_by(Session.date.asc())
            elif sort_by == "course":
                q = q.join(Course).order_by(Course.code.asc(), Session.date.desc())
            else:
                q = q.order_by(Session.date.desc())

            sessions = q.limit(50).all()

            # Forcer le chargement des relations avant fermeture
            rows = []
            for s in sessions:
                _ = s.course
                _ = s.attendances
                rows.append(_session_history_row(s))
        finally:
            db.close()

        if not rows:
            return empty_state("", "Aucune séance", "Créez votre première séance via le formulaire.")

        return html.Div(rows)


def _session_history_row(s: Session) -> html.Div:
    n_total   = len(s.attendances)
    n_absent  = sum(1 for a in s.attendances if a.is_absent)
    n_present = n_total - n_absent
    pct_presence = round(n_present / n_total * 100) if n_total > 0 else 100

    abs_color    = "var(--danger)"  if n_absent > 2 else \
                   "var(--warning)" if n_absent > 0 else "var(--success)"
    course_color = s.course.color if s.course else COLORS["primary"]
    pct_color    = "var(--success)" if pct_presence >= 80 else \
                   "var(--warning)" if pct_presence >= 60 else "var(--danger)"

    return html.Div(style={
        "padding": "14px 0",
        "borderBottom": "1px solid var(--border-gris)",
    }, children=[
        html.Div(style={"display": "flex", "gap": "14px", "alignItems": "flex-start"}, children=[

            html.Div(style={
                "minWidth": "4px", "width": "4px", "borderRadius": "2px",
                "background": course_color, "alignSelf": "stretch",
            }),

            html.Div(style={"flex": "1"}, children=[

                html.Div(className="flex-between", style={"marginBottom": "4px"}, children=[
                    html.Div(style={"display": "flex", "gap": "8px",
                                    "alignItems": "center", "flexWrap": "wrap"}, children=[
                        html.Span(
                            s.course.code if s.course else "?",
                            style={
                                "background": course_color, "color": "white",
                                "padding": "2px 10px", "borderRadius": "99px",
                                "fontSize": "11px", "fontWeight": "700",
                            }
                        ),
                        html.Span(s.date.strftime("%d/%m/%Y"),
                                  style={"fontSize": "12px", "color": "var(--gris-moyen)"}),
                        html.Span(f"{s.duration}h",
                                  style={"fontSize": "11px", "color": "var(--gris-moyen)"}),
                        html.Span(s.room,
                                  style={"fontSize": "11px", "color": "var(--gris-moyen)"}) if s.room else None,
                    ]),
                    html.Button(
                        "Suppr.",
                        id={"type": "delete-session-btn", "index": s.id},
                        className="btn btn-sm btn-outline btn-icon",
                        n_clicks=0,
                        title="Supprimer cette séance",
                    ),
                ]),

                html.Div(s.theme or "Sans thème",
                         style={"fontSize": "13px", "fontWeight": "600", "margin": "2px 0 6px"}),

                html.Div(style={"display": "flex", "gap": "12px", "alignItems": "center"}, children=[
                    html.Span(f"{n_present} présent(s)",
                              style={"fontSize": "12px", "color": "var(--success)"}),
                    html.Span(f"{n_absent} absent(s)",
                              style={"fontSize": "12px", "color": abs_color}),
                    html.Div(style={"flex": "1", "maxWidth": "120px"}, children=[
                        html.Div(style={
                            "height": "4px", "borderRadius": "2px",
                            "background": "var(--border-gris)", "overflow": "hidden",
                        }, children=[
                            html.Div(style={
                                "height": "100%", "width": f"{pct_presence}%",
                                "background": pct_color, "borderRadius": "2px",
                            })
                        ]),
                        html.Div(f"{pct_presence}%",
                                 style={"fontSize": "10px", "color": pct_color,
                                        "textAlign": "right", "marginTop": "2px",
                                        "fontWeight": "600"}),
                    ]) if n_total > 0 else None,
                ]),
            ]),
        ]),
    ])