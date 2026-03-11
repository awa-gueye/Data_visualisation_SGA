"""
pages/welcome.py – Page de bienvenue après connexion
Design : fond blanc, typographie académique élégante, icônes SVG professionnelles
"""
from dash import html, dcc
import dash_svg as svg
from utils.db import get_db
from models import Student, Course, Grade, Attendance
from datetime import datetime

def _icon_graduation(color="#0A1628", size=32):
    return svg.Svg([
        svg.Path(d="M12 3L1 9l11 6 9-4.91V17M5 13.18v4L12 21l7-3.82v-4",
                 stroke=color, strokeWidth="2",
                 strokeLinecap="round", strokeLinejoin="round"),
    ], viewBox="0 0 24 24", fill="none",
       style={"width":f"{size}px","height":f"{size}px","flexShrink":"0"})

def _icon_users(color="#0EA5E9", size=22):
    return svg.Svg([
        svg.Path(d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2",
                 stroke=color, strokeWidth="2",
                 strokeLinecap="round", strokeLinejoin="round"),
        svg.Circle(cx="9", cy="7", r="4",
                   stroke=color, strokeWidth="2"),
        svg.Path(d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
                 stroke=color, strokeWidth="2",
                 strokeLinecap="round", strokeLinejoin="round"),
    ], viewBox="0 0 24 24", fill="none",
       style={"width":f"{size}px","height":f"{size}px"})

def _icon_book(color="#10B981", size=22):
    return svg.Svg([
        svg.Path(d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20",
                 stroke=color, strokeWidth="2",
                 strokeLinecap="round", strokeLinejoin="round"),
        svg.Path(d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z",
                 stroke=color, strokeWidth="2",
                 strokeLinecap="round", strokeLinejoin="round"),
    ], viewBox="0 0 24 24", fill="none",
       style={"width":f"{size}px","height":f"{size}px"})

def _icon_chart(color="#D4AF37", size=22):
    return svg.Svg([
        svg.Line(x1="18", y1="20", x2="18", y2="10",
                 stroke=color, strokeWidth="2", strokeLinecap="round"),
        svg.Line(x1="12", y1="20", x2="12", y2="4",
                 stroke=color, strokeWidth="2", strokeLinecap="round"),
        svg.Line(x1="6",  y1="20", x2="6",  y2="14",
                 stroke=color, strokeWidth="2", strokeLinecap="round"),
    ], viewBox="0 0 24 24", fill="none",
       style={"width":f"{size}px","height":f"{size}px"})

def _icon_alert(color="#EF4444", size=22):
    return svg.Svg([
        svg.Path(d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z",
                 stroke=color, strokeWidth="2",
                 strokeLinecap="round", strokeLinejoin="round"),
        svg.Line(x1="12", y1="9",  x2="12",   y2="13",
                 stroke=color, strokeWidth="2", strokeLinecap="round"),
        svg.Line(x1="12", y1="17", x2="12.01", y2="17",
                 stroke=color, strokeWidth="2", strokeLinecap="round"),
    ], viewBox="0 0 24 24", fill="none",
       style={"width":f"{size}px","height":f"{size}px"})

def _icon_arrow(color="#FFFFFF", size=18):
    return svg.Svg([
        svg.Line(x1="5", y1="12", x2="19", y2="12",
                 stroke=color, strokeWidth="2", strokeLinecap="round"),
        svg.Polyline(points="12 5 19 12 12 19",
                     stroke=color, strokeWidth="2",
                     strokeLinecap="round", strokeLinejoin="round"),
    ], viewBox="0 0 24 24", fill="none",
       style={"width":f"{size}px","height":f"{size}px"})


def layout(user: dict = None):
    name     = (user or {}).get("full_name", "Utilisateur")
    role     = (user or {}).get("role", "teacher")
    initials = "".join(w[0].upper() for w in name.split()[:2])
    hour     = datetime.now().hour
    greeting = ("Bonne nuit"    if hour < 6  else
                "Bonjour"       if hour < 12 else
                "Bon après-midi" if hour < 18 else
                "Bonsoir")
    role_lbl = "Administrateur" if role == "admin" else "Enseignant"
    role_clr = "#8B5CF6"        if role == "admin" else "#0EA5E9"

    db = get_db()
    try:
        n_students = db.query(Student).filter_by(is_active=True).count()
        n_courses  = db.query(Course).filter_by(is_active=True).count()
        n_att      = db.query(Attendance).count()
        n_abs      = db.query(Attendance).filter_by(is_absent=True).count()
        abs_rate   = round(n_abs / n_att * 100, 1) if n_att else 0
        scores     = [g.score for g in db.query(Grade).all()]
        avg_gen    = round(sum(scores) / len(scores), 1) if scores else 0
    finally:
        db.close()

    abs_color = "#EF4444" if abs_rate > 20 else "#F59E0B" if abs_rate > 10 else "#10B981"
    avg_color = "#10B981" if avg_gen >= 12 else "#F59E0B" if avg_gen >= 10 else "#EF4444"
    date_str  = datetime.now().strftime("%A %d %B %Y").capitalize()

    return html.Div(id="welcome-page", style={
        "minHeight": "100vh",
        "background": "#FFFFFF",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "fontFamily": "'Times New Roman', Times, serif",
        "padding": "40px 20px",
        "boxSizing": "border-box",
    }, children=[

        html.Div(style={"width":"100%","maxWidth":"860px"}, children=[

            # ── En-tête ──────────────────────────────────────────────────
            html.Div(style={
                "display":"flex","justifyContent":"space-between",
                "alignItems":"center","marginBottom":"56px",
                "animation":"fadeDown 0.6s ease both",
            }, children=[
                html.Div(style={"display":"flex","alignItems":"center","gap":"12px"}, children=[
                    html.Div(style={
                        "width":"42px","height":"42px","borderRadius":"10px",
                        "background":"#0A1628","display":"flex",
                        "alignItems":"center","justifyContent":"center",
                    }, children=[_icon_graduation("#FFFFFF", 22)]),
                    html.Div(children=[
                        html.Div("SGA", style={
                            "fontWeight":"bold","fontSize":"18px",
                            "color":"#0A1628","letterSpacing":"3px",
                        }),
                        html.Div("Système de Gestion Académique", style={
                            "fontSize":"10px","color":"#9CA3AF","letterSpacing":"1px",
                        }),
                    ]),
                ]),
                html.Div(date_str, style={
                    "fontSize":"12px","color":"#9CA3AF","letterSpacing":"1px",
                }),
            ]),

            # ── Avatar + message ─────────────────────────────────────────
            html.Div(style={
                "display":"flex","flexDirection":"column","alignItems":"center",
                "textAlign":"center","gap":"20px",
                "marginBottom":"48px",
                "animation":"fadeUp 0.7s ease 0.1s both",
            }, children=[
                html.Div(initials, style={
                    "width":"100px","height":"100px",
                    "borderRadius":"50%","background":"#0A1628",
                    "color":"#FFFFFF","fontSize":"32px","fontWeight":"bold",
                    "display":"flex","alignItems":"center","justifyContent":"center",
                    "boxShadow":"0 8px 32px rgba(10,22,40,0.12)",
                    "letterSpacing":"2px",
                }),
                html.Div(children=[
                    html.Div(greeting, style={
                        "fontSize":"12px","color":"#9CA3AF",
                        "letterSpacing":"3px","textTransform":"uppercase",
                        "marginBottom":"8px",
                    }),
                    html.H1(name, style={
                        "fontSize":"clamp(26px, 4vw, 42px)",
                        "fontWeight":"bold","color":"#0A1628",
                        "margin":"0 0 14px","lineHeight":"1.1",
                    }),
                    html.Div(style={
                        "display":"flex","alignItems":"center",
                        "justifyContent":"center","gap":"8px",
                    }, children=[
                        html.Div(style={
                            "width":"6px","height":"6px",
                            "borderRadius":"50%","background":role_clr,
                        }),
                        html.Span(role_lbl, style={
                            "fontSize":"12px","color":role_clr,
                            "letterSpacing":"2px","fontWeight":"bold",
                        }),
                    ]),
                    html.P(
                        "Bienvenue sur votre espace de gestion académique. "
                        "Retrouvez ici toutes vos informations, suivez les performances "
                        "de vos étudiants et gérez vos cours en toute simplicité.",
                        style={
                            "fontSize":"14px","color":"#6B7280",
                            "lineHeight":"1.8","maxWidth":"480px",
                            "margin":"0 auto 14px","fontStyle":"italic",
                        }
                    ),
                ]),
            ]),

            # ── Séparateur ───────────────────────────────────────────────
            html.Div(style={
                "height":"1px",
                "background":"linear-gradient(90deg, #0A1628 0%, #E5E7EB 50%, transparent 100%)",
                "marginBottom":"48px",
                "animation":"expandLine 0.8s ease 0.3s both",
            }),

            # ── KPIs ─────────────────────────────────────────────────────
            html.Div(style={
                "display":"grid","gridTemplateColumns":"repeat(4, 1fr)",
                "gap":"16px","marginBottom":"48px",
                "animation":"fadeUp 0.7s ease 0.4s both",
            }, children=[
                _kpi(str(n_students), "Étudiants actifs",  _icon_users("#0EA5E9"),  "#0EA5E9"),
                _kpi(str(n_courses),  "Cours actifs",      _icon_book("#10B981"),   "#10B981"),
                _kpi(f"{avg_gen}/20", "Moyenne générale",  _icon_chart(avg_color),  avg_color),
                _kpi(f"{abs_rate}%",  "Taux d'absence",    _icon_alert(abs_color),  abs_color),
            ]),

            # ── Citation + bouton ────────────────────────────────────────
            html.Div(style={
                "display":"flex","alignItems":"center",
                "justifyContent":"space-between","gap":"40px",
                "animation":"fadeUp 0.7s ease 0.6s both",
            }, children=[
                html.Div(style={"flex":"1"}, children=[
                    html.Div(style={
                        "width":"28px","height":"3px",
                        "background":"#0A1628","marginBottom":"16px",
                    }),
                    html.Div(
                        "L'éducation est l'arme la plus puissante que vous puissiez utiliser pour changer le monde.",
                        style={
                            "fontSize":"14px","color":"#374151",
                            "fontStyle":"italic","lineHeight":"1.8","marginBottom":"10px",
                        }
                    ),
                    html.Div("— Nelson Mandela", style={
                        "fontSize":"11px","color":"#9CA3AF",
                        "letterSpacing":"2px","textTransform":"uppercase",
                    }),
                ]),
                html.Div(style={
                    "width":"1px","height":"80px",
                    "background":"#E5E7EB","flexShrink":"0",
                }),
                html.Div(style={"flexShrink":"0"}, children=[
                    dcc.Link(
                        html.Button(
                            style={
                                "background":"#0A1628","color":"#FFFFFF",
                                "border":"none","borderRadius":"10px",
                                "padding":"16px 28px","fontSize":"12px",
                                "fontWeight":"bold",
                                "fontFamily":"'Times New Roman', Times, serif",
                                "cursor":"pointer","letterSpacing":"2px",
                                "textTransform":"uppercase",
                                "display":"flex","alignItems":"center","gap":"10px",
                                "boxShadow":"0 4px 20px rgba(10,22,40,0.18)",
                                "transition":"all 0.25s ease","whiteSpace":"nowrap",
                            },
                            children=[html.Span("Tableau de bord"), _icon_arrow("#FFFFFF", 16)],
                        ),
                        href="/",
                    ),
                ]),
            ]),
        ]),
    ])


def _kpi(value, label, icon, color):
    return html.Div(style={
        "background":"#FAFAFA","borderRadius":"12px","padding":"20px 18px",
        "border":"1px solid #F3F4F6","borderTop":f"3px solid {color}",
        "display":"flex","flexDirection":"column","gap":"12px",
    }, children=[
        html.Div(style={
            "width":"38px","height":"38px","borderRadius":"8px",
            "background":"#FFFFFF","border":"1px solid #F3F4F6",
            "display":"flex","alignItems":"center","justifyContent":"center",
            "boxShadow":"0 1px 4px rgba(10,22,40,0.06)",
        }, children=[icon]),
        html.Div(children=[
            html.Div(value, style={
                "fontSize":"24px","fontWeight":"bold",
                "color":color,"lineHeight":"1",
            }),
            html.Div(label, style={
                "fontSize":"11px","color":"#9CA3AF",
                "marginTop":"4px","letterSpacing":"0.5px",
            }),
        ]),
    ])