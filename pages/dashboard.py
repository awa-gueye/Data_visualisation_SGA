"""
pages/dashboard.py – Tableau de bord principal
"""
from dash import html, dcc, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from sqlalchemy import func

from pages.components import sidebar, topbar, kpi_card, card, section_title, empty_state
from utils.db import get_db, SessionFactory
from models import Student, Course, Session, Attendance, Grade
from config import PLOTLY_TEMPLATE, COLORS


# ─────────────────────────────────────────────────────────────────────────────
#  Données dashboard
# ─────────────────────────────────────────────────────────────────────────────
def _get_stats():
    db = get_db()
    try:
        n_students = db.query(Student).filter_by(is_active=True).count()
        n_courses  = db.query(Course).filter_by(is_active=True).count()
        n_sessions = db.query(Session).count()

        # Taux d'absence global
        total_att = db.query(Attendance).count()
        abs_att   = db.query(Attendance).filter_by(is_absent=True).count()
        abs_rate  = round(abs_att / total_att * 100, 1) if total_att else 0

        # Moyenne générale
        avg_result = db.query(func.avg(Grade.score)).scalar()
        avg_score  = round(avg_result, 2) if avg_result else 0

        # Séances cette semaine
        week_ago   = date.today() - timedelta(days=7)
        n_this_week = db.query(Session).filter(Session.date >= week_ago).count()

        return {
            "n_students":   n_students,
            "n_courses":    n_courses,
            "n_sessions":   n_sessions,
            "abs_rate":     abs_rate,
            "avg_score":    avg_score,
            "n_this_week":  n_this_week,
        }
    finally:
        db.close()


def _get_recent_sessions(limit=6):
    db = get_db()
    try:
        sessions = (db.query(Session)
                    .order_by(Session.date.desc())
                    .limit(limit).all())
        result = []
        for s in sessions:
            n_absent = sum(1 for a in s.attendances if a.is_absent)
            result.append({
                "id":       s.id,
                "course":   s.course.code if s.course else "–",
                "label":    s.course.label if s.course else "–",
                "date":     s.date.strftime("%d/%m/%Y"),
                "theme":    s.theme or "Sans thème",
                "absent":   n_absent,
                "duration": s.duration,
                "color":    s.course.color if s.course else COLORS["primary"],
            })
        return result
    finally:
        db.close()


def _get_courses_progress():
    db = get_db()
    try:
        courses = db.query(Course).filter_by(is_active=True).all()
        return [
            {
                "code":     c.code,
                "label":    c.label,
                "done":     c.hours_done,
                "total":    c.total_hours,
                "pct":      c.progress_pct,
                "color":    c.color,
                "teacher":  c.teacher or "–",
            }
            for c in courses
        ]
    finally:
        db.close()


def _get_absence_chart_data():
    db = get_db()
    try:
        # Absences par cours
        courses = db.query(Course).filter_by(is_active=True).all()
        labels, values = [], []
        for c in courses:
            total = sum(len(s.attendances) for s in c.sessions)
            absences = sum(1 for s in c.sessions for a in s.attendances if a.is_absent)
            if total > 0:
                labels.append(c.code)
                values.append(round(absences / total * 100, 1))
        return labels, values
    finally:
        db.close()


def _get_grades_distribution():
    db = get_db()
    try:
        scores = [g.score for g in db.query(Grade).all()]
        return scores
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
#  Layout
# ─────────────────────────────────────────────────────────────────────────────
def layout(user: dict = None):
    stats    = _get_stats()
    sessions = _get_recent_sessions()
    courses  = _get_courses_progress()
    abs_lbls, abs_vals = _get_absence_chart_data()
    scores   = _get_grades_distribution()

    return html.Div(id="app-shell", children=[
        sidebar("/", user),
        html.Div(id="main-content", children=[
            topbar("Tableau de Bord", f"Bonjour, {(user or {}).get('full_name','')  } 👋"),
            html.Div(id="page-content", children=[

                # ── KPI Cards ───────────────────────────────────────────
                html.Div(className="kpi-grid", children=[
                    kpi_card("🎓", str(stats["n_students"]),  "Étudiants actifs",  f"+{stats['n_this_week']} cette semaine"),
                    kpi_card("📚", str(stats["n_courses"]),   "Cours actifs",      ""),
                    kpi_card("📅", str(stats["n_sessions"]),  "Séances totales",   f"{stats['n_this_week']} cette semaine"),
                    kpi_card("✅", f"{stats['abs_rate']}%",   "Taux d'absence",    ""),
                    kpi_card("⭐", f"{stats['avg_score']}/20", "Moyenne générale",  ""),
                ]),

                # ── Graphiques ──────────────────────────────────────────
                html.Div(className="grid-2", style={"marginBottom":"24px"}, children=[
                    html.Div(className="chart-card", children=[
                        html.Div("Distribution des notes", className="chart-title"),
                        html.Div("Répartition par tranche", className="chart-sub"),
                        dcc.Graph(figure=_make_grades_hist(scores), config={"displayModeBar":False}),
                    ]),
                    html.Div(className="chart-card", children=[
                        html.Div("Taux d'absence par cours", className="chart-title"),
                        html.Div("Pourcentage d'absences", className="chart-sub"),
                        dcc.Graph(figure=_make_abs_bar(abs_lbls, abs_vals), config={"displayModeBar":False}),
                    ]),
                ]),

                # ── Progression des cours ───────────────────────────────
                html.Div(className="grid-2", children=[
                    card(
                        title="Progression des cours",
                        children=html.Div([
                            _course_progress_row(c) for c in courses
                        ] or [empty_state("📚", "Aucun cours", "Ajoutez des cours pour voir la progression")]),
                    ),
                    card(
                        title="Séances récentes",
                        children=html.Div([
                            _session_row(s) for s in sessions
                        ] or [empty_state("📅", "Aucune séance", "")]),
                    ),
                ]),

            ]),
        ]),
    ])


# ─────────────────────────────────────────────────────────────────────────────
#  Composants internes
# ─────────────────────────────────────────────────────────────────────────────
def _course_progress_row(c: dict) -> html.Div:
    pct   = c["pct"]
    color = "var(--success)" if pct >= 80 else "var(--warning)" if pct >= 50 else "var(--danger)"
    return html.Div(style={"marginBottom":"16px"}, children=[
        html.Div(className="flex-between", style={"marginBottom":"6px"}, children=[
            html.Div(className="flex-center gap-8", children=[
                html.Div(style={
                    "width":"10px","height":"10px","borderRadius":"50%",
                    "background":c["color"],"flexShrink":"0",
                }),
                html.Span(c["code"], style={"fontWeight":"600","fontSize":"13px"}),
                html.Span(c["label"], style={"color":"var(--text-muted)","fontSize":"12px"}),
            ]),
            html.Span(f"{c['done']}h / {c['total']}h",
                      style={"fontSize":"12px","color":"var(--text-muted)"}),
        ]),
        html.Div(className="progress-wrap", children=[
            html.Div(className="progress-bar",
                     style={"width":f"{pct}%","background":color}),
        ]),
    ])


def _session_row(s: dict) -> html.Div:
    abs_color = "var(--danger)" if s["absent"] > 0 else "var(--success)"
    return html.Div(style={
        "display":"flex","gap":"12px","alignItems":"center",
        "padding":"10px 0","borderBottom":"1px solid var(--border)",
    }, children=[
        html.Div(style={
            "width":"8px","height":"40px","borderRadius":"4px",
            "background":s["color"],"flexShrink":"0",
        }),
        html.Div(style={"flex":"1","minWidth":"0"}, children=[
            html.Div(className="flex-center gap-8", children=[
                html.Span(s["course"], style={"fontWeight":"700","fontSize":"13px"}),
                html.Span(s["date"],   style={"color":"var(--text-muted)","fontSize":"11px"}),
            ]),
            html.Div(s["theme"], style={
                "fontSize":"12px","color":"var(--text-muted)",
                "whiteSpace":"nowrap","overflow":"hidden","textOverflow":"ellipsis",
            }),
        ]),
        html.Div(className="flex-center gap-8", children=[
            html.Span(f"⏱ {s['duration']}h", style={"fontSize":"11px","color":"var(--text-muted)"}),
            html.Span(
                f"❌ {s['absent']}" if s["absent"] else "✅ Tous",
                style={"fontSize":"11px","color":abs_color,"fontWeight":"600"},
            ),
        ]),
    ])


# ─────────────────────────────────────────────────────────────────────────────
#  Figures Plotly
# ─────────────────────────────────────────────────────────────────────────────
def _make_grades_hist(scores):
    if not scores:
        fig = go.Figure()
        fig.add_annotation(text="Aucune donnée", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font={"color":"#A7A9BE"})
    else:
        fig = px.histogram(
            x=scores, nbins=10,
            labels={"x": "Note /20", "y": "Nb étudiants"},
            color_discrete_sequence=[COLORS["primary"]],
        )
        fig.update_traces(marker_line_color="rgba(108,99,255,0.5)", marker_line_width=1)

    fig.update_layout(
        **PLOTLY_TEMPLATE["layout"],
        height=240,
        margin=dict(l=8, r=8, t=8, b=32),
        showlegend=False,
    )
    return fig


def _make_abs_bar(labels, values):
    if not labels:
        fig = go.Figure()
        fig.add_annotation(text="Aucune donnée", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font={"color":"#A7A9BE"})
    else:
        bar_colors = [
            COLORS["danger"] if v > 20 else COLORS["warning"] if v > 10 else COLORS["accent"]
            for v in values
        ]
        fig = go.Figure(go.Bar(
            x=labels, y=values,
            marker_color=bar_colors,
            text=[f"{v}%" for v in values],
            textposition="outside",
        ))

    fig.update_layout(
        **PLOTLY_TEMPLATE["layout"],
        height=240,
        margin=dict(l=8, r=8, t=24, b=8),
        showlegend=False,
        yaxis_range=[0, max(values or [0]) * 1.3 + 5],
    )
    return fig