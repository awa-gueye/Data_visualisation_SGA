"""
pages/analytics.py - Analyse & Visualisation
"""
from dash import html, dcc, Input, Output
import plotly.graph_objects as go
from pages.components import sidebar, topbar, section_title
from utils.db import get_db
from models import Student, Course, Session, Attendance, Grade
from config import COLORS

C_BLU   = "#0EA5E9"
C_GRN   = "#10B981"
C_RED   = "#EF4444"
C_ORG   = "#F59E0B"
C_PURP  = "#8B5CF6"
C_LGRAY = "#9CA3AF"
C_DARK  = "#0A1628"
C_BDR   = "#E5E7EB"
TNR     = "'Times New Roman', Times, serif"


def _base_layout(**extra):
    """Layout Plotly de base sans xaxis/yaxis pour éviter les doublons."""
    d = dict(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family=TNR, color=C_DARK, size=11),
        showlegend=False,
    )
    d.update(extra)
    return d


def _ax(title_text=None, **kw):
    """Dictionnaire d'axe standard."""
    d = dict(
        gridcolor="#F3F4F6",
        zerolinecolor="#E5E7EB",
        linecolor=C_BDR,
        tickfont=dict(family=TNR, color=C_LGRAY, size=10),
    )
    d.update(kw)
    if title_text:
        d["title"] = dict(text=title_text,
                          font=dict(family=TNR, color=C_DARK, size=11))
    return d


def _empty(h=290):
    fig = go.Figure()
    fig.add_annotation(text="Aucune donnee disponible",
                       xref="paper", yref="paper", x=0.5, y=0.5,
                       showarrow=False,
                       font=dict(color=C_LGRAY, size=13, family=TNR))
    fig.update_layout(
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(family=TNR),
        margin=dict(l=16, r=16, t=16, b=16),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def _hex_rgba(h, a=0.15):
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


def _chart(title, subtitle, graph_id, height=290):
    return html.Div(className="chart-card", children=[
        html.Div(title,    className="chart-title"),
        html.Div(subtitle, className="chart-sub"),
        dcc.Graph(id=graph_id, config={"displayModeBar": False},
                  style={"height": f"{height}px"}),
    ])


def _kpi_band(items):
    cards = []
    for val, label, color in items:
        cards.append(html.Div(style={
            "background": "#FFFFFF", "borderRadius": "12px",
            "padding": "16px 20px",
            "boxShadow": "0 2px 10px rgba(10,22,40,0.06)",
            "borderLeft": f"4px solid {color}", "flex": "1",
        }, children=[
            html.Div(val, style={
                "fontFamily": TNR, "fontWeight": "bold",
                "fontSize": "24px", "color": color, "lineHeight": "1",
            }),
            html.Div(label, style={
                "fontSize": "11px", "color": C_LGRAY,
                "fontFamily": TNR, "marginTop": "5px",
            }),
        ]))
    return html.Div(style={"display": "flex", "gap": "14px",
                           "marginBottom": "22px"}, children=cards)


# ─────────────────────────────────────────────────────────────────────────────
#  Layout
# ─────────────────────────────────────────────────────────────────────────────
def layout(user: dict = None):
    db = get_db()
    try:
        courses  = db.query(Course).filter_by(is_active=True).all()
        students = db.query(Student).filter_by(is_active=True).all()
        all_grades = db.query(Grade).all()
        all_att    = db.query(Attendance).all()
        all_scores = [g.score for g in all_grades]
        n_abs      = sum(1 for a in all_att if a.is_absent)
        abs_rate   = round(n_abs / len(all_att) * 100, 1) if all_att else 0
        avg_g      = round(sum(all_scores)/len(all_scores), 1) if all_scores else 0
        n_above    = sum(1 for s in all_scores if s >= 10)
        opts = [{"label": f"{c.code} – {c.label}", "value": c.id} for c in courses]
    finally:
        db.close()

    avg_color = C_GRN if avg_g >= 12 else C_ORG if avg_g >= 10 else C_RED
    abs_color = C_RED if abs_rate > 20 else C_ORG if abs_rate > 10 else C_GRN

    kpis = _kpi_band([
        (str(len(students)),
         "Etudiants actifs", C_BLU),
        (f"{avg_g}/20",
         "Moyenne generale", avg_color),
        (f"{n_above}/{len(all_scores)}" if all_scores else "—",
         "Admis (>= 10)", C_GRN),
        (f"{abs_rate}%",
         "Taux absenteisme", abs_color),
        (str(len(all_grades)),
         "Notes saisies", C_PURP),
    ])

    return html.Div(id="app-shell", children=[
        sidebar("/analytics", user),
        html.Div(id="main-content", children=[
            topbar("Analyse", "Visualisation et statistiques avancees"),
            html.Div(id="page-content", children=[

                section_title("Tableau de bord analytique",
                              "Graphiques interactifs pour piloter votre etablissement"),
                kpis,

                # Filtre
                html.Div(className="card",
                         style={"marginBottom": "20px", "padding": "14px 18px"},
                         children=[
                    html.Div(style={"display": "flex", "alignItems": "center",
                                    "gap": "14px"}, children=[
                        html.Label("Filtrer par cours :", style={
                            "fontFamily": TNR, "fontSize": "12px",
                            "fontWeight": "bold", "color": C_DARK,
                            "whiteSpace": "nowrap",
                        }),
                        dcc.Dropdown(
                            id="ana-course-filter",
                            options=[{"label": "Tous les cours", "value": "all"}] + opts,
                            value="all", clearable=False,
                            style={"flex": "1", "maxWidth": "340px"},
                        ),
                    ]),
                ]),

                # Ligne 1
                html.Div(className="grid-2", style={"marginBottom": "18px"}, children=[
                    _chart("Distribution des notes",
                           "Repartition par tranche · seuil 10 en pointille",
                           "chart-grades-dist", 300),
                    _chart("Moyenne par cours",
                           "Comparaison inter-matieres",
                           "chart-avg-per-course", 300),
                ]),

                # Ligne 2 — Boxplot large
                html.Div(className="chart-card", style={"marginBottom": "18px"}, children=[
                    html.Div("Dispersion des notes par cours", className="chart-title"),
                    html.Div("Boite a moustaches — mediane, quartiles, valeurs extremes",
                             className="chart-sub"),
                    dcc.Graph(id="chart-boxplot", config={"displayModeBar": False},
                              style={"height": "320px"}),
                ]),

                # Ligne 3
                html.Div(className="grid-2", style={"marginBottom": "18px"}, children=[
                    _chart("Taux d'absence par cours",
                           "Pourcentage d'absences sur le total des seances",
                           "chart-abs-by-course", 300),
                    _chart("Classement des etudiants",
                           "Top 8 par moyenne generale ponderee",
                           "chart-top-students", 300),
                ]),

                # Ligne 4 — Heatmap large
                html.Div(className="chart-card", style={"marginBottom": "18px"}, children=[
                    html.Div("Heatmap des absences", className="chart-title"),
                    html.Div("Taux d'absence par etudiant et par cours",
                             className="chart-sub"),
                    dcc.Graph(id="chart-heatmap", config={"displayModeBar": False},
                              style={"height": "380px"}),
                ]),

                # Ligne 5
                html.Div(className="grid-2", style={"marginBottom": "18px"}, children=[
                    _chart("Carte de risque — Absence vs Moyenne",
                           "Chaque point = 1 etudiant · zones colorees par profil",
                           "chart-scatter-risk", 340),
                    _chart("Profils de risque",
                           "Repartition des etudiants par niveau de suivi",
                           "chart-donut-risk", 340),
                ]),
            ]),
        ]),
    ])


# ─────────────────────────────────────────────────────────────────────────────
#  Callback
# ─────────────────────────────────────────────────────────────────────────────
def register_callbacks(app):

    @app.callback(
        Output("chart-grades-dist",    "figure"),
        Output("chart-avg-per-course", "figure"),
        Output("chart-abs-by-course",  "figure"),
        Output("chart-top-students",   "figure"),
        Output("chart-heatmap",        "figure"),
        Output("chart-boxplot",        "figure"),
        Output("chart-scatter-risk",   "figure"),
        Output("chart-donut-risk",     "figure"),
        Input("ana-course-filter",     "value"),
    )
    def update_charts(course_filter):
        db = get_db()
        try:
            courses  = db.query(Course).filter_by(is_active=True).all()
            students = db.query(Student).filter_by(is_active=True).all()

            q = db.query(Grade)
            if course_filter != "all":
                q = q.filter(Grade.course_id == int(course_filter))
            grades = q.all()

            # ── Tout extraire avant db.close() ────────────────────────
            scores = [g.score for g in grades]

            course_avgs = {}
            for g in grades:
                cid = g.course_id
                if cid not in course_avgs:
                    course_avgs[cid] = {"scores": [], "label": "", "color": ""}
                course_avgs[cid]["scores"].append(g.score)
                if g.course:
                    course_avgs[cid]["label"] = g.course.code
                    course_avgs[cid]["color"] = g.course.color or COLORS["primary"]

            abs_data = []
            for c in courses:
                total    = sum(len(s.attendances) for s in c.sessions)
                absences = sum(1 for s in c.sessions
                               for a in s.attendances if a.is_absent)
                rate = round(absences / total * 100, 1) if total else 0
                abs_data.append({"code": c.code, "rate": rate})

            student_avgs = []
            for s in students:
                g_list = s.grades
                if g_list:
                    wa = sum(g.score * g.coefficient for g in g_list)
                    wt = sum(g.coefficient for g in g_list)
                    student_avgs.append({
                        "name": s.last_name,
                        "full": s.full_name,
                        "avg":  round(wa / wt, 1),
                    })
            student_avgs.sort(key=lambda x: x["avg"], reverse=True)
            top8 = student_avgs[:8]

            box_data = []
            for c in courses:
                c_scores = [g.score for g in c.grades]
                if c_scores:
                    box_data.append({
                        "code":   c.code,
                        "scores": c_scores,
                        "color":  c.color or COLORS["primary"],
                    })

            stu_names    = [s.last_name for s in students[:14]]
            course_codes = [c.code for c in courses]
            matrix = []
            for s in students[:14]:
                row = []
                for c in courses:
                    total_s = sum(1 for sess in c.sessions
                                  for a in sess.attendances
                                  if a.student_id == s.id)
                    abs_s   = sum(1 for sess in c.sessions
                                  for a in sess.attendances
                                  if a.student_id == s.id and a.is_absent)
                    row.append(round(abs_s / total_s * 100, 0) if total_s else 0)
                matrix.append(row)

            scatter_pts = []
            risk_counts = {"Bon suivi": 0, "A surveiller": 0, "En difficulte": 0}
            for s in students:
                g_list  = s.grades
                n_tot   = len(s.attendances)
                n_abs   = sum(1 for a in s.attendances if a.is_absent)
                abs_pct = round(n_abs / n_tot * 100, 1) if n_tot else 0
                avg_s   = None
                if g_list:
                    wa = sum(g.score * g.coefficient for g in g_list)
                    wt = sum(g.coefficient for g in g_list)
                    avg_s = round(wa / wt, 1)

                if abs_pct > 25 or (avg_s is not None and avg_s < 8):
                    risk = "En difficulte"; clr = C_RED; sz = 13
                elif abs_pct > 15 or (avg_s is not None and avg_s < 10):
                    risk = "A surveiller";  clr = C_ORG; sz = 11
                else:
                    risk = "Bon suivi";     clr = C_GRN; sz = 9
                risk_counts[risk] += 1

                if avg_s is not None:
                    scatter_pts.append({
                        "x": abs_pct, "y": avg_s,
                        "name": s.last_name, "full": s.full_name,
                        "color": clr, "size": sz,
                    })
        finally:
            db.close()

        # ══════════════════════════════════════════════════════════════
        #  Fig 1 — Histogramme
        # ══════════════════════════════════════════════════════════════
        if scores:
            bins   = list(range(0, 22, 2))
            counts = [0] * (len(bins) - 1)
            for s in scores:
                for i in range(len(bins) - 1):
                    if bins[i] <= s < bins[i + 1]:
                        counts[i] += 1; break
            bar_clrs = []
            for b in bins[:-1]:
                if b < 8:    bar_clrs.append(C_RED)
                elif b < 10: bar_clrs.append(C_ORG)
                elif b < 14: bar_clrs.append(C_BLU)
                else:        bar_clrs.append(C_GRN)

            fig1 = go.Figure()
            fig1.add_trace(go.Bar(
                x=[(bins[i]+bins[i+1])/2 for i in range(len(bins)-1)],
                y=counts, width=1.7,
                marker=dict(color=bar_clrs, line=dict(width=0)),
                hovertemplate="%{x:.0f}/20 : %{y} etudiant(s)<extra></extra>",
            ))
            avg = sum(scores) / len(scores)
            fig1.add_vline(x=avg,  line_dash="dash", line_color=C_DARK, line_width=1.5,
                           annotation_text=f"Moy. {avg:.1f}",
                           annotation_font=dict(family=TNR, size=11, color=C_DARK),
                           annotation_position="top right")
            fig1.add_vline(x=10, line_dash="dot", line_color=C_RED, line_width=1.2,
                           annotation_text="Seuil 10",
                           annotation_font=dict(family=TNR, size=10, color=C_RED),
                           annotation_position="bottom left")
            fig1.update_layout(
                **_base_layout(margin=dict(l=16, r=16, t=16, b=36), bargap=0.08),
                xaxis=_ax("Note /20", tickvals=list(range(0, 21, 2))),
                yaxis=_ax("Nb etudiants"),
            )
        else:
            fig1 = _empty()

        # ══════════════════════════════════════════════════════════════
        #  Fig 2 — Moyenne par cours
        # ══════════════════════════════════════════════════════════════
        if course_avgs:
            items  = sorted(course_avgs.values(),
                            key=lambda v: sum(v["scores"])/len(v["scores"]),
                            reverse=True)
            labels = [v["label"] for v in items]
            avgs   = [round(sum(v["scores"])/len(v["scores"]), 1) for v in items]
            clrs   = [C_GRN if a >= 14 else C_BLU if a >= 10 else C_RED for a in avgs]

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                y=labels, x=avgs, orientation="h",
                marker=dict(color=clrs, line=dict(width=0)),
                text=[f"{a}/20" for a in avgs],
                textposition="outside",
                textfont=dict(family=TNR, size=11, color=C_DARK),
                hovertemplate="<b>%{y}</b> : %{x}/20<extra></extra>",
            ))
            fig2.add_vline(x=10, line_dash="dot", line_color=C_RED, line_width=1.2,
                           annotation_text="10",
                           annotation_font=dict(size=9, color=C_RED, family=TNR))
            fig2.update_layout(
                **_base_layout(margin=dict(l=16, r=56, t=16, b=16)),
                xaxis=_ax("Moyenne /20", range=[0, 23]),
                yaxis=_ax(),
            )
        else:
            fig2 = _empty()

        # ══════════════════════════════════════════════════════════════
        #  Fig 3 — Absences par cours
        # ══════════════════════════════════════════════════════════════
        if abs_data:
            srt    = sorted(abs_data, key=lambda d: d["rate"], reverse=True)
            a_clrs = [C_RED if d["rate"] > 20 else C_ORG if d["rate"] > 10 else C_GRN
                      for d in srt]
            max_r  = max(d["rate"] for d in srt)

            fig3 = go.Figure()
            fig3.add_trace(go.Bar(
                y=[d["code"] for d in srt],
                x=[d["rate"] for d in srt],
                orientation="h",
                marker=dict(color=a_clrs, line=dict(width=0)),
                text=[f"{d['rate']}%" for d in srt],
                textposition="outside",
                textfont=dict(family=TNR, size=11, color=C_DARK),
                hovertemplate="<b>%{y}</b> : %{x}% d'absences<extra></extra>",
            ))
            fig3.add_vline(x=15, line_dash="dot", line_color=C_RED, line_width=1.2,
                    annotation_text="Seuil 15%",
                    annotation_font=dict(size=9, color=C_RED, family=TNR),
                    annotation_position="bottom right")
            fig3.update_layout(
                **_base_layout(margin=dict(l=16, r=56, t=16, b=16)),
                xaxis=_ax("Taux d'absence (%)", range=[0, max_r + 8]),
                yaxis=_ax(),
            )
        else:
            fig3 = _empty()

        # ══════════════════════════════════════════════════════════════
        #  Fig 4 — Top 8 etudiants
        # ══════════════════════════════════════════════════════════════
        if top8:
            t_clrs = [C_GRN if t["avg"] >= 14 else C_BLU if t["avg"] >= 10 else C_RED
                      for t in top8]
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(
                y=[t["name"] for t in top8],
                x=[t["avg"]  for t in top8],
                orientation="h",
                marker=dict(color=t_clrs, line=dict(width=0)),
                text=[f"{t['avg']}/20" for t in top8],
                textposition="outside",
                textfont=dict(family=TNR, size=11, color=C_DARK),
                customdata=[t["full"] for t in top8],
                hovertemplate="<b>%{customdata}</b> : %{x}/20<extra></extra>",
            ))
            fig4.add_vline(x=10, line_dash="dot", line_color=C_RED, line_width=1.2)
            fig4.update_layout(
                **_base_layout(margin=dict(l=16, r=56, t=16, b=16)),
                xaxis=_ax("Moyenne /20", range=[0, 23]),
                yaxis=_ax(),
            )
        else:
            fig4 = _empty()

        # ══════════════════════════════════════════════════════════════
        #  Fig 5 — Heatmap
        # ══════════════════════════════════════════════════════════════
        if matrix and course_codes:
            text_m = [[f"{v:.0f}%" for v in row] for row in matrix]
            fig5 = go.Figure(go.Heatmap(
                z=matrix, x=course_codes, y=stu_names,
                colorscale=[
                    [0.00, "#ECFDF5"], [0.20, "#6EE7B7"],
                    [0.45, "#FCD34D"], [0.70, C_ORG],
                    [1.00, "#B91C1C"],
                ],
                text=text_m, texttemplate="%{text}",
                textfont=dict(family=TNR, size=10, color=C_DARK),
                zmin=0, zmax=40,
                colorbar=dict(
                    title=dict(text="Abs %",
                               font=dict(family=TNR, size=11, color=C_DARK)),
                    tickfont=dict(family=TNR, size=9, color=C_LGRAY),
                    thickness=12,
                ),
                hovertemplate="<b>%{y}</b> — %{x}<br>Absence : %{z}%<extra></extra>",
            ))
            fig5.update_layout(
                paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                font=dict(family=TNR, color=C_DARK, size=11),
                margin=dict(l=16, r=80, t=16, b=16),
                xaxis=dict(tickfont=dict(family=TNR, color=C_DARK, size=10),
                           side="top", linecolor=C_BDR,
                           gridcolor="#F3F4F6", zerolinecolor="#E5E7EB"),
                yaxis=dict(tickfont=dict(family=TNR, color=C_DARK, size=10),
                           autorange="reversed", linecolor=C_BDR,
                           gridcolor="#F3F4F6", zerolinecolor="#E5E7EB"),
            )
        else:
            fig5 = _empty(380)

        # ══════════════════════════════════════════════════════════════
        #  Fig 6 — Boxplot
        # ══════════════════════════════════════════════════════════════
        if box_data:
            fig6 = go.Figure()
            for bd in box_data:
                fig6.add_trace(go.Box(
                    y=bd["scores"], name=bd["code"],
                    marker=dict(color=bd["color"], size=4,
                                line=dict(width=1, color="#FFFFFF")),
                    line=dict(color=bd["color"], width=2),
                    fillcolor=_hex_rgba(bd["color"], 0.12),
                    boxmean=True, boxpoints="outliers",
                ))
            fig6.add_hline(y=10, line_dash="dot", line_color=C_RED, line_width=1.2,
                           annotation_text="Seuil 10",
                           annotation_font=dict(size=9, color=C_RED, family=TNR))
            fig6.update_layout(
                **_base_layout(margin=dict(l=16, r=16, t=40, b=16), showlegend=False),
                xaxis=_ax(),
                yaxis=_ax("Note /20", range=[-1, 22]),
            )
        else:
            fig6 = _empty(320)

        # ══════════════════════════════════════════════════════════════
        #  Fig 7 — Scatter risque
        # ══════════════════════════════════════════════════════════════
        if scatter_pts:
            fig7 = go.Figure()
            for x0, x1, y0, y1, fc in [
                (0,  15,  10, 20, "#ECFDF5"),
                (15, 100, 10, 20, "#FFFBEB"),
                (0,  15,   0, 10, "#FFF7ED"),
                (15, 100,  0, 10, "#FEF2F2"),
            ]:
                fig7.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                               fillcolor=fc, line_width=0, layer="below")
            fig7.add_hline(y=10, line_dash="dot", line_color=C_RED,  line_width=1)
            fig7.add_vline(x=15, line_dash="dot", line_color=C_ORG, line_width=1)
            fig7.add_trace(go.Scatter(
                x=[p["x"] for p in scatter_pts],
                y=[p["y"] for p in scatter_pts],
                mode="markers+text",
                text=[p["name"] for p in scatter_pts],
                textposition="top center",
                textfont=dict(family=TNR, size=9, color=C_DARK),
                marker=dict(
                    color=[p["color"] for p in scatter_pts],
                    size=[p["size"]   for p in scatter_pts],
                    line=dict(width=1.5, color="#FFFFFF"),
                    opacity=0.88,
                ),
                customdata=[p["full"] for p in scatter_pts],
                hovertemplate=(
                    "<b>%{customdata}</b><br>"
                    "Absence : %{x}%<br>"
                    "Moyenne : %{y}/20<extra></extra>"
                ),
            ))
            for lbl, x, y, c in [
                ("Bon suivi",     5,  18.5, C_GRN),
                ("A surveiller", 50,  18.5, C_ORG),
                ("En difficulte",50,   1.5, C_RED),
            ]:
                fig7.add_annotation(x=x, y=y, text=lbl, showarrow=False,
                                    font=dict(family=TNR, size=9, color=c),
                                    opacity=0.55)
            fig7.update_layout(
                **_base_layout(margin=dict(l=16, r=16, t=16, b=36), showlegend=False),
                xaxis=_ax("Taux d'absence (%)", range=[-2, None]),
                yaxis=_ax("Moyenne /20", range=[0, 21]),
            )
        else:
            fig7 = _empty(340)

        # ══════════════════════════════════════════════════════════════
        #  Fig 8 — Donut risque
        # ══════════════════════════════════════════════════════════════
        total_stu = sum(risk_counts.values())
        if total_stu > 0:
            fig8 = go.Figure(go.Pie(
                labels=list(risk_counts.keys()),
                values=list(risk_counts.values()),
                hole=0.60,
                marker=dict(colors=[C_GRN, C_ORG, C_RED],
                            line=dict(color="#FFFFFF", width=3)),
                textinfo="percent+label",
                textfont=dict(family=TNR, size=11, color=C_DARK),
                direction="clockwise", sort=False,
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "%{value} etudiant(s) — %{percent}<extra></extra>"
                ),
            ))
            fig8.add_annotation(
                x=0.5, y=0.5,
                text=f"<b>{total_stu}</b>",
                showarrow=False,
                font=dict(family=TNR, size=26, color=C_DARK),
                xref="paper", yref="paper",
            )
            fig8.update_layout(
                paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                font=dict(family=TNR, color=C_DARK, size=11),
                margin=dict(l=16, r=16, t=16, b=80),
                showlegend=True,
                legend=dict(
                    font=dict(family=TNR, size=10, color=C_DARK),
                    orientation="v",
                    yanchor="middle", y=0.5,
                    xanchor="left", x=1.05,
                ),
            )
        else:
            fig8 = _empty(340)

        return fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8