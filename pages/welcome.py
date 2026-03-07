"""
pages/welcome.py – Page de bienvenue après connexion
Design : élégance sombre, typographie académique, animations CSS
"""
from dash import html, dcc
from utils.db import get_db
from models import Student, Course, Grade, Attendance
from datetime import datetime


def layout(user: dict = None):
    name     = (user or {}).get("full_name", "Utilisateur")
    role     = (user or {}).get("role", "teacher")
    initials = "".join(w[0].upper() for w in name.split()[:2])
    hour     = datetime.now().hour
    greeting = "Bonne nuit" if hour < 6 else "Bonjour" if hour < 12 else "Bon après-midi" if hour < 18 else "Bonsoir"
    role_lbl = "Administrateur" if role == "admin" else "Enseignant"

    # Stats rapides
    db = get_db()
    try:
        n_students = db.query(Student).filter_by(is_active=True).count()
        n_courses  = db.query(Course).filter_by(is_active=True).count()
        n_grades   = db.query(Grade).count()
        n_att      = db.query(Attendance).count()
        n_abs      = db.query(Attendance).filter_by(is_absent=True).count()
        abs_rate   = round(n_abs / n_att * 100, 1) if n_att else 0
        scores     = [g.score for g in db.query(Grade).all()]
        avg_gen    = round(sum(scores) / len(scores), 1) if scores else 0
    finally:
        db.close()

    return html.Div(id="welcome-page", style={
        "minHeight": "100vh",
        "background": "linear-gradient(135deg, #0A1628 0%, #0F2040 40%, #0A1628 100%)",
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "center",
        "justifyContent": "center",
        "fontFamily": "'Times New Roman', Times, serif",
        "position": "relative",
        "overflow": "hidden",
    }, children=[

        # ── Particules déco ──────────────────────────────────────────────
        html.Div(style={
            "position": "absolute", "inset": "0", "overflow": "hidden",
            "pointerEvents": "none",
        }, children=[
            *[html.Div(style={
                "position": "absolute",
                "width": f"{6 + i*3}px", "height": f"{6 + i*3}px",
                "borderRadius": "50%",
                "background": f"rgba(212, 175, 55, {0.05 + i*0.03})",
                "left": f"{10 + i*15}%", "top": f"{20 + (i*17)%60}%",
                "animation": f"float {4 + i*0.7}s ease-in-out infinite",
                "animationDelay": f"{i*0.4}s",
            }) for i in range(8)],
            # Lignes décoratives
            html.Div(style={
                "position": "absolute", "top": "0", "left": "0",
                "width": "100%", "height": "100%",
                "backgroundImage": "linear-gradient(rgba(212,175,55,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(212,175,55,0.03) 1px, transparent 1px)",
                "backgroundSize": "80px 80px",
            }),
            # Grand cercle déco
            html.Div(style={
                "position": "absolute",
                "width": "600px", "height": "600px",
                "borderRadius": "50%",
                "border": "1px solid rgba(212,175,55,0.06)",
                "right": "-200px", "top": "-200px",
            }),
            html.Div(style={
                "position": "absolute",
                "width": "400px", "height": "400px",
                "borderRadius": "50%",
                "border": "1px solid rgba(212,175,55,0.08)",
                "left": "-100px", "bottom": "-100px",
            }),
        ]),

        # ── Contenu principal ────────────────────────────────────────────
        html.Div(style={
            "position": "relative",
            "zIndex": "1",
            "textAlign": "center",
            "padding": "0 20px",
            "maxWidth": "900px",
            "width": "100%",
        }, children=[

            # Logo + badge
            html.Div(style={
                "display": "flex", "alignItems": "center",
                "justifyContent": "center", "gap": "16px",
                "marginBottom": "48px",
                "animation": "slideDown 0.7s cubic-bezier(0.4,0,0.2,1)",
            }, children=[
                html.Div("🎓", style={"fontSize": "52px"}),
                html.Div(children=[
                    html.Div("S·G·A", style={
                        "fontSize": "42px", "fontWeight": "bold",
                        "color": "#D4AF37",
                        "letterSpacing": "12px",
                        "lineHeight": "1",
                        "textShadow": "0 0 40px rgba(212,175,55,0.4)",
                    }),
                    html.Div("SYSTÈME DE GESTION ACADÉMIQUE", style={
                        "fontSize": "10px", "letterSpacing": "4px",
                        "color": "rgba(255,255,255,0.4)",
                        "marginTop": "4px",
                    }),
                ]),
            ]),

            # Ligne dorée séparatrice
            html.Div(style={
                "width": "120px", "height": "1px",
                "background": "linear-gradient(90deg, transparent, #D4AF37, transparent)",
                "margin": "0 auto 48px",
                "animation": "expandWidth 1s ease 0.3s both",
            }),

            # Avatar + message de bienvenue
            html.Div(style={
                "animation": "fadeUp 0.8s ease 0.2s both",
            }, children=[
                # Avatar
                html.Div(initials, style={
                    "width": "80px", "height": "80px",
                    "borderRadius": "50%",
                    "background": "linear-gradient(135deg, #D4AF37, #B8860B)",
                    "color": "#0A1628",
                    "fontSize": "28px", "fontWeight": "bold",
                    "display": "flex", "alignItems": "center",
                    "justifyContent": "center",
                    "margin": "0 auto 24px",
                    "boxShadow": "0 0 40px rgba(212,175,55,0.35), 0 0 0 4px rgba(212,175,55,0.15)",
                }),

                # Salutation
                html.Div(greeting + ",", style={
                    "fontSize": "18px", "color": "rgba(255,255,255,0.5)",
                    "letterSpacing": "2px", "marginBottom": "8px",
                }),

                # Nom
                html.H1(name, style={
                    "fontSize": "clamp(32px, 5vw, 52px)",
                    "fontWeight": "bold",
                    "color": "#FFFFFF",
                    "margin": "0 0 8px",
                    "letterSpacing": "1px",
                    "textShadow": "0 2px 20px rgba(255,255,255,0.1)",
                }),

                # Badge rôle
                html.Span(role_lbl, style={
                    "display": "inline-block",
                    "background": "rgba(212,175,55,0.12)",
                    "border": "1px solid rgba(212,175,55,0.3)",
                    "color": "#D4AF37",
                    "padding": "4px 16px",
                    "borderRadius": "20px",
                    "fontSize": "12px",
                    "letterSpacing": "2px",
                    "marginBottom": "48px",
                }),
            ]),

            # ── KPIs ────────────────────────────────────────────────────
            html.Div(style={
                "display": "grid",
                "gridTemplateColumns": "repeat(4, 1fr)",
                "gap": "16px",
                "marginBottom": "48px",
                "animation": "fadeUp 0.8s ease 0.5s both",
            }, children=[
                _stat(str(n_students), "Étudiants actifs",   "🎓", "#0EA5E9", 0),
                _stat(str(n_courses),  "Cours en cours",     "📚", "#10B981", 1),
                _stat(f"{avg_gen}/20", "Moyenne générale",   "📊", "#D4AF37", 2),
                _stat(f"{abs_rate}%",  "Taux d'absence",     "📋", "#EF4444" if abs_rate > 20 else "#F59E0B" if abs_rate > 10 else "#10B981", 3),
            ]),

            # ── Message inspirant ────────────────────────────────────────
            html.Div(style={
                "marginBottom": "48px",
                "animation": "fadeUp 0.8s ease 0.7s both",
            }, children=[
                html.Div(style={
                    "background": "rgba(255,255,255,0.03)",
                    "border": "1px solid rgba(212,175,55,0.15)",
                    "borderRadius": "16px",
                    "padding": "24px 32px",
                    "maxWidth": "600px",
                    "margin": "0 auto",
                }, children=[
                    html.Div("❝", style={
                        "fontSize": "32px", "color": "#D4AF37",
                        "opacity": "0.5", "lineHeight": "1",
                        "marginBottom": "8px",
                    }),
                    html.Div(
                        "L'éducation est l'arme la plus puissante que vous puissiez utiliser pour changer le monde.",
                        style={
                            "fontSize": "15px", "color": "rgba(255,255,255,0.7)",
                            "fontStyle": "italic", "lineHeight": "1.7",
                            "marginBottom": "8px",
                        }
                    ),
                    html.Div("— Nelson Mandela", style={
                        "fontSize": "11px", "color": "#D4AF37",
                        "letterSpacing": "2px",
                    }),
                ]),
            ]),

            # ── Bouton Accéder ───────────────────────────────────────────
            html.Div(style={"animation": "fadeUp 0.8s ease 0.9s both"}, children=[
                dcc.Link(
                    html.Button(children=[
                        html.Span("Accéder au tableau de bord"),
                        html.Span(" →", style={"marginLeft": "8px", "fontSize": "18px"}),
                    ], style={
                        "background": "linear-gradient(135deg, #D4AF37, #B8860B)",
                        "color": "#0A1628",
                        "border": "none",
                        "borderRadius": "12px",
                        "padding": "16px 40px",
                        "fontSize": "15px",
                        "fontWeight": "bold",
                        "fontFamily": "'Times New Roman', Times, serif",
                        "cursor": "pointer",
                        "letterSpacing": "1px",
                        "boxShadow": "0 8px 32px rgba(212,175,55,0.35)",
                        "transition": "all 0.3s ease",
                    }),
                    href="/",
                ),
            ]),

            # ── Footer ───────────────────────────────────────────────────
            html.Div(style={
                "marginTop": "60px",
                "color": "rgba(255,255,255,0.2)",
                "fontSize": "11px",
                "letterSpacing": "2px",
                "animation": "fadeUp 0.8s ease 1.1s both",
            }, children=[
                f"SGA · {datetime.now().strftime('%A %d %B %Y').capitalize()}"
            ]),
        ]),
    ])


def _stat(value, label, icon, color, delay):
    return html.Div(style={
        "background": "rgba(255,255,255,0.04)",
        "border": f"1px solid rgba(255,255,255,0.08)",
        "borderTop": f"2px solid {color}",
        "borderRadius": "12px",
        "padding": "20px 16px",
        "textAlign": "center",
        "transition": "all 0.3s ease",
        "animationDelay": f"{delay * 0.1}s",
    }, children=[
        html.Div(icon, style={"fontSize": "24px", "marginBottom": "8px"}),
        html.Div(value, style={
            "fontSize": "26px", "fontWeight": "bold",
            "color": color, "lineHeight": "1",
            "textShadow": f"0 0 20px {color}40",
        }),
        html.Div(label, style={
            "fontSize": "10px", "color": "rgba(255,255,255,0.4)",
            "letterSpacing": "1px", "marginTop": "6px",
        }),
    ])