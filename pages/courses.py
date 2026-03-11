"""
pages/courses.py  Module 1 : Gestion des Cours (CRUD + progression)
"""
from dash import html, dcc, Input, Output, State, callback, no_update, ctx
import dash
from pages.components import sidebar, topbar, card, kpi_card, section_title, badge, empty_state, alert_msg, progress_bar
from utils.db import get_db, safe_commit
from models import Course
from config import COLORS
from sqlalchemy.orm import joinedload

COURSE_COLORS = ["#6C63FF","#FF6584","#43E97B","#F7B731","#45AAF2","#FF7675","#A29BFE","#FDCB6E"]


# 
#  Layout
# 
def layout(user: dict = None):
    return html.Div(id="app-shell", children=[
        sidebar("/courses", user),
        html.Div(id="main-content", children=[
            topbar("Gestion des Cours", "Curriculum · Progression"),
            html.Div(id="page-content", children=[
                #  Actions 
                html.Div(className="flex-between", style={"marginBottom":"24px"}, children=[
                    section_title("Cours", "Gérez votre catalogue de cours"),
                    html.Button(
                        "Nouveau cours",
                        id="open-course-modal",
                        className="btn btn-primary",
                        n_clicks=0,
                    ),
                ]),

                #  Feedback 
                html.Div(id="course-feedback"),

                #  Liste des cours 
                html.Div(id="courses-list"),

                #  Store 
                dcc.Store(id="edit-course-id",    data=None),
                dcc.Store(id="courses-refresh",   data=0),
                dcc.Store(id="modal-open",        data=False),

                #  Modal CRUD 
                html.Div(id="course-modal-container"),
            ]),
        ]),
    ])


# 
#  Callbacks
# 
def register_callbacks(app):

    @app.callback(
        Output("courses-list", "children"),
        Input("courses-refresh", "data"),
    )
    def refresh_courses(n):
        db = get_db()
        try:
            courses = (
                db.query(Course)
                .options(joinedload(Course.sessions), joinedload(Course.grades))
                .order_by(Course.id)
                .all()
            )
            # Forcer le chargement des relations tant que la session est ouverte
            for c in courses:
                _ = c.sessions
                _ = c.grades
        finally:
            db.close()

        if not courses:
            return empty_state("", "Aucun cours", "Cliquez sur '+ Nouveau cours' pour commencer.")

        return html.Div(
            className="grid-2",
            children=[_course_card(c) for c in courses],
        )

    @app.callback(
        Output("modal-open",      "data"),
        Output("edit-course-id",  "data"),
        Input("open-course-modal",                               "n_clicks"),
        Input({"type": "edit-course-btn",   "index": dash.ALL}, "n_clicks"),
        Input({"type": "close-modal-trigger","index": dash.ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_modal_state(new_click, edit_clicks, close_clicks):
        triggered = ctx.triggered_id

        # Ignorer si aucun vrai clic (n_clicks == 0 = initialisation du composant dynamique)
        triggered_value = ctx.triggered[0]["value"] if ctx.triggered else 0
        if not triggered_value:
            return no_update, no_update

        if triggered == "open-course-modal":
            return True, None

        if isinstance(triggered, dict) and triggered.get("type") == "edit-course-btn":
            return True, triggered["index"]

        if isinstance(triggered, dict) and triggered.get("type") == "close-modal-trigger":
            return False, None

        return no_update, no_update

    @app.callback(
        Output("course-modal-container", "children"),
        Input("modal-open",    "data"),
        State("edit-course-id","data"),
    )
    def render_modal(is_open, edit_id):
        if not is_open:
            return html.Div()
        if edit_id:
            db = get_db()
            try:
                c = db.query(Course).get(edit_id)
                return _course_modal(c)
            finally:
                db.close()
        return _course_modal()

    @app.callback(
        Output("course-feedback",     "children"),
        Output("courses-refresh",     "data"),
        Output("modal-open",          "data", allow_duplicate=True),
        Input("save-course-btn",      "n_clicks"),
        State("course-code",          "value"),
        State("course-label",         "value"),
        State("course-hours",         "value"),
        State("course-teacher",       "value"),
        State("course-teacher-email", "value"),
        State("course-desc",          "value"),
        State("course-color",         "value"),
        State("edit-course-id",       "data"),
        State("courses-refresh",      "data"),
        prevent_initial_call=True,
    )
    def save_course(n_clicks, code, label, hours, teacher, t_email, desc, color, edit_id, refresh):
        if not n_clicks:
            return no_update, no_update, no_update
        if not code or not label:
            return alert_msg("Code et libellé obligatoires.", "danger"), no_update, no_update

        db = get_db()
        try:
            if edit_id:
                c = db.query(Course).get(edit_id)
                if not c:
                    return alert_msg("Cours introuvable.", "danger"), no_update, no_update
            else:
                # Vérifier doublon
                if db.query(Course).filter_by(code=code).first():
                    return alert_msg(f"Le code {code} existe déjà.", "danger"), no_update, no_update
                c = Course()
                db.add(c)

            c.code          = code.upper().strip()
            c.label         = label.strip()
            c.total_hours   = float(hours or 0)
            c.teacher       = teacher
            c.teacher_email = t_email
            c.description   = desc
            c.color         = color or COLORS["primary"]

            db.commit()
            return (
                alert_msg(f"Cours {'modifié' if edit_id else 'créé'} avec succès.", "success"),
                (refresh or 0) + 1,
                False,
            )
        except Exception as e:
            db.rollback()
            return alert_msg(f"Erreur : {e}", "danger"), no_update, no_update
        finally:
            db.close()

    @app.callback(
        Output("course-feedback",  "children", allow_duplicate=True),
        Output("courses-refresh",  "data",     allow_duplicate=True),
        Input({"type": "delete-course-btn", "index": dash.ALL}, "n_clicks"),
        State("courses-refresh", "data"),
        prevent_initial_call=True,
    )
    def delete_course(n_clicks_list, refresh):
        if not any(n_clicks_list):
            return no_update, no_update
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            return no_update, no_update

        course_id = triggered["index"]
        db = get_db()
        try:
            c = db.query(Course).get(course_id)
            if c:
                c.is_active = False   # Soft delete
                db.commit()
            return alert_msg("Cours supprimé.", "warning"), (refresh or 0) + 1
        except Exception as e:
            db.rollback()
            return alert_msg(f"Erreur : {e}", "danger"), no_update
        finally:
            db.close()




# 
#  Composants
# 
def _course_card(c: Course) -> html.Div:
    pct   = c.progress_pct
    p_color = "var(--success)" if pct >= 80 else "var(--warning)" if pct >= 50 else "var(--danger)"
    status_badge = badge("Actif", "success") if c.is_active else badge("Inactif", "danger")

    return html.Div(className="card", style={"borderTop":f"4px solid {c.color}"}, children=[
        html.Div(className="flex-between", style={"marginBottom":"12px"}, children=[
            html.Div(className="flex-center gap-8", children=[
                html.Span(c.code, style={
                    "background":c.color,"color":"white","padding":"3px 10px",
                    "borderRadius":"99px","fontSize":"12px","fontWeight":"700",
                }),
                status_badge,
            ]),
            html.Div(className="flex-center gap-8", children=[
                html.Button("Modifier", id={"type":"edit-course-btn","index":c.id},
                           className="btn btn-sm btn-outline btn-icon", n_clicks=0),
                html.Button("Suppr.", id={"type":"delete-course-btn","index":c.id},
                           className="btn btn-sm btn-outline btn-icon", n_clicks=0),
            ]),
        ]),

        html.H3(c.label, style={"fontSize":"16px","fontWeight":"700","marginBottom":"4px"}),
        html.P(c.teacher or "", style={"fontSize":"12px","color":"var(--text-muted)","marginBottom":"14px"}),

        html.Div(className="flex-between", style={"marginBottom":"6px"}, children=[
            html.Span("Progression", style={"fontSize":"11px","color":"var(--text-muted)"}),
            html.Span(f"{c.hours_done}h / {c.total_hours}h",
                      style={"fontSize":"11px","fontWeight":"600"}),
        ]),
        html.Div(className="progress-wrap", children=[
            html.Div(className="progress-bar",
                     style={"width":f"{pct}%","background":p_color}),
        ]),
        html.Div(f"{pct}%", style={"fontSize":"11px","color":p_color,"marginTop":"4px","textAlign":"right"}),

        html.Div(style={"marginTop":"12px","display":"flex","gap":"16px"}, children=[
            html.Div(children=[
                html.Div(str(len(c.sessions)), style={"fontSize":"20px","fontWeight":"800"}),
                html.Div("séances", style={"fontSize":"10px","color":"var(--text-muted)"}),
            ]),
            html.Div(children=[
                html.Div(f"{c.total_hours}h", style={"fontSize":"20px","fontWeight":"800"}),
                html.Div("volume total", style={"fontSize":"10px","color":"var(--text-muted)"}),
            ]),
            html.Div(children=[
                html.Div(len(c.grades), style={"fontSize":"20px","fontWeight":"800"}),
                html.Div("notes", style={"fontSize":"10px","color":"var(--text-muted)"}),
            ]),
        ]),
    ])


def _course_modal(course: Course = None) -> html.Div:
    is_edit = course is not None
    title   = "Modifier le cours" if is_edit else "Nouveau cours"

    return html.Div(className="modal-overlay", style={"position":"fixed","inset":"0","zIndex":"9999","display":"flex","alignItems":"center","justifyContent":"center","padding":"20px","background":"rgba(10,22,40,0.65)"}, children=[
        html.Div(className="modal-box", style={"background":"white","width":"min(600px, 100%)","maxHeight":"88vh","overflowY":"auto","overflowX":"hidden","borderRadius":"12px","padding":"28px","position":"relative","boxShadow":"0 24px 64px rgba(10,22,40,0.3)"}, children=[
            html.Div(className="flex-between", style={"marginBottom":"24px"}, children=[
                html.H2(title, style={"fontFamily":"'Syne',sans-serif","fontSize":"20px","fontWeight":"800"}),
                html.Button("Fermer", id={"type":"close-modal-trigger","index":"header"}, className="btn btn-outline btn-icon", n_clicks=0),
            ]),

            html.Div(className="grid-2", children=[
                html.Div(className="form-group", children=[
                    html.Label("Code cours *", className="form-label"),
                    dcc.Input(id="course-code", value=course.code if is_edit else "",
                              placeholder="ex: MATH101", className="dash-input",
                              style={"width":"100%"}, disabled=is_edit),
                ]),
                html.Div(className="form-group", children=[
                    html.Label("Volume horaire (h) *", className="form-label"),
                    dcc.Input(id="course-hours", type="number", min=0,
                              value=course.total_hours if is_edit else "",
                              placeholder="ex: 60", className="dash-input",
                              style={"width":"100%"}),
                ]),
            ]),

            html.Div(className="form-group", children=[
                html.Label("Libellé *", className="form-label"),
                dcc.Input(id="course-label", value=course.label if is_edit else "",
                          placeholder="ex: Mathématiques Avancées", className="dash-input",
                          style={"width":"100%"}),
            ]),

            html.Div(className="grid-2", children=[
                html.Div(className="form-group", children=[
                    html.Label("Enseignant", className="form-label"),
                    dcc.Input(id="course-teacher", value=course.teacher if is_edit else "",
                              placeholder="Nom de l'enseignant", className="dash-input",
                              style={"width":"100%"}),
                ]),
                html.Div(className="form-group", children=[
                    html.Label("Email enseignant", className="form-label"),
                    dcc.Input(id="course-teacher-email", type="email",
                              value=course.teacher_email if is_edit else "",
                              placeholder="email@domaine.fr", className="dash-input",
                              style={"width":"100%"}),
                ]),
            ]),

            html.Div(className="form-group", children=[
                html.Label("Description", className="form-label"),
                dcc.Textarea(id="course-desc",
                             value=course.description if is_edit else "",
                             placeholder="Description du cours...",
                             className="dash-input",
                             style={"width":"100%","minHeight":"80px"}),
            ]),

            html.Div(className="form-group", children=[
                html.Label("Couleur", className="form-label"),
                dcc.Dropdown(
                    id="course-color",
                    value=course.color if is_edit else COURSE_COLORS[0],
                    options=[{"label":html.Div(className="flex-center gap-8", children=[
                        html.Div(style={"width":"14px","height":"14px","borderRadius":"50%","background":c,"flexShrink":"0"}),
                        html.Span(c),
                    ]), "value":c} for c in COURSE_COLORS],
                    clearable=False,
                    style={"background":"var(--surface2)"},
                ),
            ]),

            html.Div(className="flex-center gap-12", style={"marginTop":"24px","justifyContent":"flex-end"}, children=[
                html.Button("Annuler", id={"type":"close-modal-trigger","index":"footer"}, className="btn btn-outline", n_clicks=0),
                html.Button(
                    "Enregistrer" if is_edit else "Créer le cours",
                    id="save-course-btn",
                    className="btn btn-primary",
                    n_clicks=0,
                ),
            ]),
        ]),
    ])