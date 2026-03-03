"""
pages/analytics.py – Bonus : Analytics avancées
"""
from dash import html, dcc, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy import func
from pages.components import sidebar, topbar, card, section_title
from utils.db import get_db
from models import Student, Course, Session, Attendance, Grade
from config import PLOTLY_TEMPLATE, COLORS
import pandas as pd


def layout(user: dict = None):
    db = get_db()
    try:
        courses = db.query(Course).filter_by(is_active=True).all()
        opts = [{"label": f"{c.code} – {c.label}", "value": c.id} for c in courses]
    finally:
        db.close()

    return html.Div(id="app-shell", children=[
        sidebar("/analytics", user),
        html.Div(id="main-content", children=[
            topbar("Analytics", "Visualisation & Statistiques avancées"),
            html.Div(id="page-content", children=[

                section_title("Analyse des données", "Graphiques interactifs pour piloter votre établissement"),

                # ── Filtres globaux ──────────────────────────────────────
                html.Div(className="card", style={"marginBottom":"20px","padding":"16px"}, children=[
                    html.Div(className="flex-center gap-16", children=[
                        html.Div(className="form-group", style={"flex":"1","margin":"0"}, children=[
                            html.Label("Cours", className="form-label"),
                            dcc.Dropdown(id="ana-course-filter",
                                         options=[{"label":"Tous","value":"all"}] + opts,
                                         value="all", clearable=False,
                                         style={"background":"var(--surface2)"}),
                        ]),
                    ]),
                ]),

                # ── Rangée 1 : Distrib notes + Évolution moyennes ────────
                html.Div(className="grid-2", style={"marginBottom":"20px"}, children=[
                    html.Div(className="chart-card", children=[
                        html.Div("Distribution des notes", className="chart-title"),
                        html.Div("Histogramme par tranche", className="chart-sub"),
                        dcc.Graph(id="chart-grades-dist", config={"displayModeBar":False}),
                    ]),
                    html.Div(className="chart-card", children=[
                        html.Div("Moyenne par cours", className="chart-title"),
                        html.Div("Comparaison inter-matières", className="chart-sub"),
                        dcc.Graph(id="chart-avg-per-course", config={"displayModeBar":False}),
                    ]),
                ]),

                # ── Rangée 2 : Absences timeline + Radar étudiant ────────
                html.Div(className="grid-2", style={"marginBottom":"20px"}, children=[
                    html.Div(className="chart-card", children=[
                        html.Div("Taux d'absence par cours", className="chart-title"),
                        html.Div("Comparatif", className="chart-sub"),
                        dcc.Graph(id="chart-abs-by-course", config={"displayModeBar":False}),
                    ]),
                    html.Div(className="chart-card", children=[
                        html.Div("Top 5 étudiants", className="chart-title"),
                        html.Div("Par moyenne générale", className="chart-sub"),
                        dcc.Graph(id="chart-top-students", config={"displayModeBar":False}),
                    ]),
                ]),

                # ── Rangée 3 : Heatmap présences ─────────────────────────
                html.Div(className="chart-card", style={"marginBottom":"20px"}, children=[
                    html.Div("Heatmap des absences", className="chart-title"),
                    html.Div("Étudiant × Cours", className="chart-sub"),
                    dcc.Graph(id="chart-heatmap", config={"displayModeBar":False}),
                ]),

                # ── Boîte à moustaches notes ─────────────────────────────
                html.Div(className="chart-card", children=[
                    html.Div("Dispersion des notes par cours", className="chart-title"),
                    html.Div("Boîte à moustaches", className="chart-sub"),
                    dcc.Graph(id="chart-boxplot", config={"displayModeBar":False}),
                ]),
            ]),
        ]),
    ])


def register_callbacks(app):

    @app.callback(
        Output("chart-grades-dist",   "figure"),
        Output("chart-avg-per-course","figure"),
        Output("chart-abs-by-course", "figure"),
        Output("chart-top-students",  "figure"),
        Output("chart-heatmap",       "figure"),
        Output("chart-boxplot",       "figure"),
        Input("ana-course-filter",    "value"),
    )
    def update_charts(course_filter):
        db = get_db()
        try:
            # ── Données notes ──────────────────────────────────────────
            q_grades = db.query(Grade)
            if course_filter != "all":
                q_grades = q_grades.filter(Grade.course_id == int(course_filter))
            grades = q_grades.all()

            # ── Données absences ───────────────────────────────────────
            courses  = db.query(Course).filter_by(is_active=True).all()
            students = db.query(Student).filter_by(is_active=True).all()

            # ── Fig 1 : Histogramme notes ──────────────────────────────
            scores = [g.score for g in grades]
            fig1 = go.Figure()
            if scores:
                fig1.add_trace(go.Histogram(
                    x=scores, nbinsx=10,
                    marker_color=COLORS["primary"],
                    marker_line_color="rgba(108,99,255,0.6)",
                    marker_line_width=1,
                    name="Notes",
                ))
                # Ligne moyenne
                avg = sum(scores) / len(scores)
                fig1.add_vline(x=avg, line_dash="dash",
                               line_color=COLORS["accent"], line_width=2,
                               annotation_text=f"Moy: {avg:.1f}",
                               annotation_font_color=COLORS["accent"])
            else:
                _add_no_data(fig1)
            fig1.update_layout(**PLOTLY_TEMPLATE["layout"], height=280,
                               margin=dict(l=8,r=8,t=8,b=32), showlegend=False)

            # ── Fig 2 : Moyenne par cours ──────────────────────────────
            course_avgs = {}
            for g in grades:
                cid = g.course_id
                if cid not in course_avgs:
                    course_avgs[cid] = {"scores":[],"label":"","color":""}
                course_avgs[cid]["scores"].append(g.score)
                if g.course:
                    course_avgs[cid]["label"] = g.course.code
                    course_avgs[cid]["color"] = g.course.color

            fig2 = go.Figure()
            if course_avgs:
                labels = [v["label"] for v in course_avgs.values()]
                avgs   = [round(sum(v["scores"])/len(v["scores"]),1) for v in course_avgs.values()]
                colors = [v["color"] or COLORS["primary"] for v in course_avgs.values()]
                fig2.add_trace(go.Bar(
                    x=labels, y=avgs,
                    marker_color=colors,
                    text=[f"{a}/20" for a in avgs],
                    textposition="outside",
                ))
                fig2.add_hline(y=10, line_dash="dot", line_color=COLORS["warning"], line_width=1.5)
            else:
                _add_no_data(fig2)
            fig2.update_layout(**PLOTLY_TEMPLATE["layout"], height=280,
                               margin=dict(l=8,r=8,t=24,b=8), showlegend=False,
                               yaxis_range=[0,22])

            # ── Fig 3 : Absences par cours ─────────────────────────────
            abs_labels, abs_vals, abs_colors = [], [], []
            for c in courses:
                total = sum(len(s.attendances) for s in c.sessions)
                absences = sum(1 for s in c.sessions for a in s.attendances if a.is_absent)
                rate = round(absences / total * 100, 1) if total else 0
                abs_labels.append(c.code)
                abs_vals.append(rate)
                abs_colors.append(COLORS["danger"] if rate > 20 else COLORS["warning"] if rate > 10 else COLORS["accent"])

            fig3 = go.Figure(go.Bar(
                x=abs_vals, y=abs_labels, orientation="h",
                marker_color=abs_colors,
                text=[f"{v}%" for v in abs_vals],
                textposition="outside",
            )) if abs_labels else go.Figure()
            if not abs_labels:
                _add_no_data(fig3)
            fig3.update_layout(**PLOTLY_TEMPLATE["layout"], height=280,
                               margin=dict(l=8,r=56,t=8,b=8), showlegend=False)

            # ── Fig 4 : Top 5 étudiants ───────────────────────────────
            student_avgs = []
            for s in students:
                g_list = s.grades
                if g_list:
                    wa = sum(g.score * g.coefficient for g in g_list)
                    wt = sum(g.coefficient for g in g_list)
                    student_avgs.append({"name": s.full_name, "avg": round(wa/wt, 1)})
            student_avgs.sort(key=lambda x: x["avg"], reverse=True)
            top5 = student_avgs[:5]

            fig4 = go.Figure()
            if top5:
                fig4.add_trace(go.Bar(
                    x=[t["avg"] for t in top5],
                    y=[t["name"] for t in top5],
                    orientation="h",
                    marker=dict(
                        color=[t["avg"] for t in top5],
                        colorscale=[[0,"#FF4757"],[0.5,"#F7B731"],[1,"#43E97B"]],
                        showscale=False,
                    ),
                    text=[f"{t['avg']}/20" for t in top5],
                    textposition="outside",
                ))
            else:
                _add_no_data(fig4)
            fig4.update_layout(**PLOTLY_TEMPLATE["layout"], height=280,
                               margin=dict(l=8,r=56,t=8,b=8), showlegend=False,
                               xaxis_range=[0,22])

            # ── Fig 5 : Heatmap ────────────────────────────────────────
            matrix = {}
            for s in students[:15]:
                matrix[s.full_name] = {}
                for c in courses:
                    total_s = sum(1 for sess in c.sessions
                                  for a in sess.attendances if a.student_id == s.id)
                    abs_s   = sum(1 for sess in c.sessions
                                  for a in sess.attendances if a.student_id == s.id and a.is_absent)
                    matrix[s.full_name][c.code] = round(abs_s / total_s * 100, 0) if total_s else 0

            if matrix:
                df = pd.DataFrame(matrix).T
                fig5 = go.Figure(go.Heatmap(
                    z=df.values.tolist(),
                    x=list(df.columns),
                    y=list(df.index),
                    colorscale=[[0,"#43E97B"],[0.3,"#F7B731"],[0.7,"#FF7675"],[1,"#FF4757"]],
                    text=[[f"{v:.0f}%" for v in row] for row in df.values.tolist()],
                    texttemplate="%{text}",
                    colorbar=dict(title="Absences %", tickfont=dict(color=COLORS["text"])),
                    zmin=0, zmax=50,
                ))
            else:
                fig5 = go.Figure()
                _add_no_data(fig5)
            fig5.update_layout(**PLOTLY_TEMPLATE["layout"], height=380,
                               margin=dict(l=8,r=8,t=8,b=8))

            # ── Fig 6 : Boxplot ────────────────────────────────────────
            fig6 = go.Figure()
            for c in courses:
                c_scores = [g.score for g in c.grades]
                if c_scores:
                    hex_color = (c.color or "#6C63FF").lstrip("#")
                    r  = int(hex_color[0:2], 16)
                    gv = int(hex_color[2:4], 16)
                    b  = int(hex_color[4:6], 16)
                    fill = f"rgba({r},{gv},{b},0.2)"
                    fig6.add_trace(go.Box(
                        y=c_scores, name=c.code,
                        marker_color=c.color,
                        line_color=c.color,
                        fillcolor=fill,
                        boxmean=True,
                    ))
            if not any(c.grades for c in courses):
                _add_no_data(fig6)
            fig6.update_layout(**PLOTLY_TEMPLATE["layout"], height=320,
                               margin=dict(l=8,r=8,t=8,b=32), showlegend=False)

        finally:
            db.close()

        return fig1, fig2, fig3, fig4, fig5, fig6


def _add_no_data(fig):
    fig.add_annotation(
        text="Aucune donnée disponible",
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font={"color": COLORS["text_muted"], "size": 14},
    )