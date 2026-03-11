"""
pages/analytics.py – Atelier d'analyse statistique interactif
Modes : Univariée · Bivariée · Multivariée
"""
from dash import html, dcc, Input, Output, State, ctx, no_update
import plotly.graph_objects as go
import math
from pages.components import sidebar, topbar
from utils.db import get_db
from models import Student, Course, Session, Attendance, Grade
from config import COLORS
# ── Palette & constantes ───────────────────────────────────────────────────
C_BLU  = "#0EA5E9"; C_GRN  = "#10B981"; C_RED  = "#EF4444"
C_ORG  = "#F59E0B"; C_PURP = "#8B5CF6"; C_PINK = "#EC4899"
C_TEAL = "#14B8A6"; C_LGRAY= "#9CA3AF"; C_DARK = "#0A1628"
C_BDR  = "#E5E7EB"; C_BG   = "#F8FAFC"
TNR    = "'Times New Roman', Times, serif"
PAL    = [C_BLU, C_GRN, C_ORG, C_PURP, C_PINK, C_TEAL, C_RED]

def _rgba(h, a=0.15):
    h = h.lstrip("#")
    r,g,b = int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    return f"rgba({r},{g},{b},{a})"

# ── Définition des variables ───────────────────────────────────────────────
VARS = {
    "note":          {"label":"Note",                     "type":"num",  "unit":"/20"},
    "note_min":      {"label":"Note minimale",            "type":"num",  "unit":"/20"},
    "note_max":      {"label":"Note maximale",            "type":"num",  "unit":"/20"},
    "moyenne":       {"label":"Moyenne générale",         "type":"num",  "unit":"/20"},
    "nb_absences":   {"label":"Nombre d'absences",        "type":"num",  "unit":"séances"},
    "taux_absence":  {"label":"Taux d'absence",           "type":"num",  "unit":"%"},
    "nb_seances":    {"label":"Nombre de séances",        "type":"num",  "unit":"séances"},
    "coefficient":   {"label":"Coefficient",              "type":"num",  "unit":""},
    "cours":         {"label":"Cours",                    "type":"cat"},
    "etudiant":      {"label":"Étudiant",                 "type":"cat"},
    "profil_risque": {"label":"Profil de risque",         "type":"cat"},
    "statut":        {"label":"Statut d'admission",       "type":"cat"},
}

OPTS_NUM = [{"label":f"🔢 {v['label']}", "value":k} for k,v in VARS.items() if v["type"]=="num"]
OPTS_CAT = [{"label":f"🏷️ {v['label']}", "value":k} for k,v in VARS.items() if v["type"]=="cat"]
OPTS_ALL = OPTS_NUM + OPTS_CAT


# ══════════════════════════════════════════════════════════════════════════════
#  Construction du dataset (1 ligne = 1 (étudiant × cours))
# ══════════════════════════════════════════════════════════════════════════════
def _build_dataset(db):
    students = db.query(Student).filter_by(is_active=True).all()
    courses  = db.query(Course).filter_by(is_active=True).all()
    rows = []
    for s in students:
        g_all = s.grades
        a_all = s.attendances
        n_abs_g = sum(1 for a in a_all if a.is_absent)
        abs_g   = round(n_abs_g/len(a_all)*100,1) if a_all else 0
        if g_all:
            wa = sum(g.score*g.coefficient for g in g_all)
            wt = sum(g.coefficient for g in g_all)
            moy_g = round(wa/wt,1) if wt else None
        else:
            moy_g = None

        for c in courses:
            cg   = [g for g in g_all if g.course_id==c.id]
            sess = c.sessions
            c_att= [a for se in sess for a in se.attendances if a.student_id==s.id]
            c_abs= sum(1 for a in c_att if a.is_absent)
            c_tot= len(c_att)
            c_abs_pct = round(c_abs/c_tot*100,1) if c_tot else 0

            if cg:
                wa = sum(g.score*g.coefficient for g in cg)
                wt = sum(g.coefficient for g in cg)
                c_moy = round(wa/wt,1) if wt else None
                c_coef= round(sum(g.coefficient for g in cg)/len(cg),2)
                c_min = round(min(g.score for g in cg),1)
                c_max = round(max(g.score for g in cg),1)
                for g in cg:   # 1 ligne par note aussi
                    rows.append(_make_row(s, c, g.score, g.coefficient,
                                          c_moy, c_min, c_max, c_coef,
                                          c_abs, c_abs_pct, c_tot,
                                          moy_g, abs_g))
            else:
                rows.append(_make_row(s, c, None, None,
                                      None, None, None, None,
                                      c_abs, c_abs_pct, c_tot,
                                      moy_g, abs_g))
    return rows

def _make_row(s, c, note, coef, moy, mn, mx, coef_moy,
              nb_abs, taux_abs, nb_sea, moy_g, abs_g):
    if moy is None or taux_abs > 25 or (moy is not None and moy < 8):
        profil = "En difficulté"
    elif taux_abs > 15 or (moy is not None and moy < 10):
        profil = "À surveiller"
    else:
        profil = "Bon suivi"
    if moy is None:
        statut = "Sans note"
    elif moy >= 10:
        statut = "Admis"
    else:
        statut = "Non admis"
    return {
        "etudiant":     s.last_name,
        "etudiant_full":s.full_name,
        "cours":        c.code,
        "cours_label":  c.label,
        "note":         note,
        "note_min":     mn,
        "note_max":     mx,
        "moyenne":      moy,
        "coefficient":  coef,
        "nb_absences":  nb_abs,
        "taux_absence": taux_abs,
        "nb_seances":   nb_sea,
        "profil_risque":profil,
        "statut":       statut,
        "moy_global":   moy_g,
        "abs_global":   abs_g,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers Plotly
# ══════════════════════════════════════════════════════════════════════════════
def _layout(margin=None, showlegend=False, **kw):
    m = margin or dict(l=40, r=40, t=50, b=50)
    kw.pop("legend", None)
    d = dict(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
             font=dict(family=TNR, color=C_DARK, size=11),
             showlegend=showlegend, margin=m,
             title_font=dict(family=TNR, size=13, color=C_DARK))
    d.update(kw)
    return d

def _ax(title=None, **kw):
    d = dict(gridcolor="#F3F4F6", zerolinecolor="#E5E7EB", linecolor=C_BDR,
             tickfont=dict(family=TNR, color=C_LGRAY, size=10))
    if title:
        d["title"] = dict(text=title, font=dict(family=TNR, color=C_DARK, size=11))
    d.update(kw)
    return d

def _empty_fig(msg="Aucune donnée"):
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False,
                       font=dict(color=C_LGRAY, size=13, family=TNR))
    fig.update_layout(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                      margin=dict(l=20,r=20,t=20,b=20),
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig

def _stats(vals):
    if not vals: return {}
    n = len(vals); s = sum(vals); m = s/n
    sv = sorted(vals)
    med = sv[n//2] if n%2 else (sv[n//2-1]+sv[n//2])/2
    var = sum((x-m)**2 for x in vals)/n
    std = math.sqrt(var)
    q1  = sv[n//4]; q3 = sv[3*n//4]
    cv  = round(std/m*100,1) if m else 0
    return {"n":n,"mean":round(m,2),"median":round(med,2),"std":round(std,2),
            "min":round(min(vals),2),"max":round(max(vals),2),
            "q1":round(q1,2),"q3":round(q3,2),"cv":cv}

def _corr(xs, ys):
    n = len(xs)
    if n < 2: return 0
    mx, my = sum(xs)/n, sum(ys)/n
    num = sum((xs[i]-mx)*(ys[i]-my) for i in range(n))
    den = (sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))**0.5
    return round(num/den,3) if den > 0 else 0


# ══════════════════════════════════════════════════════════════════════════════
#  Composants UI
# ══════════════════════════════════════════════════════════════════════════════
def _kpi(val, label, color=C_BLU, sub=""):
    return html.Div(style={
        "background":"#fff","borderRadius":"10px","padding":"14px 18px",
        "boxShadow":"0 2px 8px rgba(10,22,40,0.07)",
        "borderLeft":f"4px solid {color}","flex":"1","minWidth":"130px",
    }, children=[
        html.Div(str(val), style={"fontFamily":TNR,"fontWeight":"bold",
                                   "fontSize":"22px","color":color,"lineHeight":"1"}),
        html.Div(label,    style={"fontSize":"11px","color":C_LGRAY,
                                   "fontFamily":TNR,"marginTop":"4px"}),
        html.Div(sub,      style={"fontSize":"10px","color":C_LGRAY,
                                   "fontFamily":TNR}) if sub else None,
    ])

def _graph_box(title, subtitle, fig, height=400):
    return html.Div(style={
        "background":"#fff","borderRadius":"12px","padding":"16px 18px 16px",
        "boxShadow":"0 2px 10px rgba(10,22,40,0.07)",
        "border":f"1px solid {C_BDR}",
        "boxSizing":"border-box",
        "minHeight":f"{height + 130}px",
    }, children=[
        html.Div(title, style={"fontFamily":TNR,"fontWeight":"bold",
                                "fontSize":"13px","color":C_DARK,"marginBottom":"2px"}),
        html.Div(subtitle, style={"fontFamily":TNR,"fontSize":"11px",
                                   "color":C_LGRAY,"marginBottom":"8px"}),
        dcc.Graph(
            figure=fig,
            config={"displayModeBar":False,"responsive":False},
            style={
                "height":f"{height}px",
                "width":"100%",
                "overflow":"hidden",
                "display":"block",
            },
        ),
    ])

def _grid(*cards, cols=2):
    return html.Div(style={
        "display":"grid",
        "gridTemplateColumns":f"repeat({cols}, 1fr)",
        "gap":"16px","marginBottom":"16px",
        "alignItems":"start",
    }, children=list(cards))

def _warn(msg):
    return html.Div(style={
        "background":_rgba(C_ORG,0.1),"border":f"1px solid {_rgba(C_ORG,0.4)}",
        "borderRadius":"8px","padding":"12px 16px","fontFamily":TNR,"fontSize":"12px","color":C_DARK,
    }, children=[html.Span("⚠️ "), msg])

def _btn(label, id_, active=False):
    if active:
        s = {"background":C_BLU,"color":"#fff","border":"none","borderRadius":"8px",
             "padding":"10px 22px","fontFamily":TNR,"fontSize":"13px","cursor":"pointer",
             "fontWeight":"bold","boxShadow":f"0 3px 10px {_rgba(C_BLU,0.35)}"}
    else:
        s = {"background":"#fff","color":C_DARK,"border":f"1px solid {C_BDR}","borderRadius":"8px",
             "padding":"10px 22px","fontFamily":TNR,"fontSize":"13px","cursor":"pointer"}
    return html.Button(label, id=id_, n_clicks=0, style=s)

def _dd(id_, opts, val=None, ph="Choisir...", multi=False):
    return dcc.Dropdown(id=id_, options=opts, value=val, placeholder=ph,
                        multi=multi, clearable=not multi,
                        style={"fontFamily":TNR,"fontSize":"12px"})

def _label(txt):
    return html.Label(txt, style={"fontFamily":TNR,"fontSize":"12px",
                                   "fontWeight":"bold","color":C_DARK,
                                   "display":"block","marginBottom":"5px"})

def _run_btn(id_):
    return html.Button("Analyser →", id=id_, n_clicks=0, style={
        "background":C_GRN,"color":"#fff","border":"none","borderRadius":"8px",
        "padding":"10px 24px","fontFamily":TNR,"fontSize":"13px",
        "cursor":"pointer","fontWeight":"bold","alignSelf":"flex-end",
    })


# ══════════════════════════════════════════════════════════════════════════════
#  Panneaux de configuration
# ══════════════════════════════════════════════════════════════════════════════
def _panel_uni():
    return html.Div([
        html.Div("① Analyse univariée — explorez une seule variable", style={
            "fontFamily":TNR,"fontWeight":"bold","fontSize":"13px","color":C_DARK,"marginBottom":"12px"}),
        html.Div(style={"display":"flex","gap":"16px","flexWrap":"wrap","alignItems":"flex-end"}, children=[
            html.Div(style={"flex":"1","minWidth":"200px"}, children=[
                _label("Variable à analyser"),
                _dd("uni-var", OPTS_ALL, ph="Choisir une variable...")]),
            html.Div(style={"flex":"1","minWidth":"200px"}, children=[
                _label("Filtrer par cours (optionnel)"),
                dcc.Dropdown(id="uni-cours", options=[], placeholder="Tous les cours",
                             clearable=True, style={"fontFamily":TNR,"fontSize":"12px"})]),
            _run_btn("btn-uni-run"),
        ]),
    ])

def _panel_bi():
    return html.Div([
        html.Div("② Analyse bivariée — relation entre deux variables", style={
            "fontFamily":TNR,"fontWeight":"bold","fontSize":"13px","color":C_DARK,"marginBottom":"12px"}),
        html.Div(style={"display":"flex","gap":"16px","flexWrap":"wrap","alignItems":"flex-end"}, children=[
            html.Div(style={"flex":"1","minWidth":"180px"}, children=[
                _label("Variable X"), _dd("bi-x", OPTS_ALL, ph="Variable X...")]),
            html.Div(style={"flex":"1","minWidth":"180px"}, children=[
                _label("Variable Y"), _dd("bi-y", OPTS_ALL, ph="Variable Y...")]),
            html.Div(style={"flex":"1","minWidth":"180px"}, children=[
                _label("Couleur par (optionnel)"), _dd("bi-col", OPTS_CAT, ph="Aucune")]),
            _run_btn("btn-bi-run"),
        ]),
    ])

def _panel_multi():
    return html.Div([
        html.Div("③ Analyse multivariée — interrelations entre plusieurs variables", style={
            "fontFamily":TNR,"fontWeight":"bold","fontSize":"13px","color":C_DARK,"marginBottom":"12px"}),
        html.Div(style={"display":"flex","gap":"16px","flexWrap":"wrap","alignItems":"flex-end"}, children=[
            html.Div(style={"flex":"2","minWidth":"260px"}, children=[
                _label("Variables à analyser (2 minimum)"),
                _dd("multi-vars", OPTS_ALL, multi=True, ph="Sélectionner...")]),
            html.Div(style={"flex":"1","minWidth":"180px"}, children=[
                _label("Grouper par"), _dd("multi-grp", OPTS_CAT, ph="Variable de groupe...")]),
            _run_btn("btn-multi-run"),
        ]),
    ])


# ══════════════════════════════════════════════════════════════════════════════
#  Layout
# ══════════════════════════════════════════════════════════════════════════════
def layout(user: dict = None):
    db = get_db()
    try:
        courses  = db.query(Course).filter_by(is_active=True).all()
        students = db.query(Student).filter_by(is_active=True).all()
        n_c, n_s = len(courses), len(students)
    finally:
        db.close()

    return html.Div(id="app-shell", children=[
        sidebar("/analytics", user),
        html.Div(id="main-content", children=[
            topbar("Analyse", "Atelier d'analyse statistique interactive"),
            html.Div(id="page-content", style={"padding":"20px 24px"}, children=[

                html.Div(style={"marginBottom":"18px"}, children=[
                    html.Div("Atelier d'analyse statistique", style={
                        "fontFamily":TNR,"fontWeight":"bold","fontSize":"20px","color":C_DARK}),
                    html.Div(f"{n_s} étudiants · {n_c} cours · sélectionnez vos variables et lancez l'analyse",
                             style={"fontFamily":TNR,"fontSize":"12px","color":C_LGRAY,"marginTop":"4px"}),
                ]),

                # Boutons de mode
                html.Div(style={"display":"flex","gap":"10px","marginBottom":"18px"}, children=[
                    _btn("① Univariée",   "btn-mode-uni",   True),
                    _btn("② Bivariée",    "btn-mode-bi",    False),
                    _btn("③ Multivariée", "btn-mode-multi", False),
                ]),

                # Panneau config
                html.Div(id="panel-config", style={
                    "background":"#fff","borderRadius":"12px","padding":"18px 20px",
                    "boxShadow":"0 2px 10px rgba(10,22,40,0.06)","marginBottom":"20px",
                    "border":f"1px solid {C_BDR}",
                }, children=[_panel_uni()]),

                # Résultats
                html.Div(id="ana-kpis",   style={"marginBottom":"16px"}),
                html.Div(id="ana-graphs", style={"marginBottom":"16px"}),
                html.Div(id="ana-note",   style={"fontFamily":TNR,"fontSize":"11px",
                                                   "color":C_LGRAY,"fontStyle":"italic",
                                                   "textAlign":"center","paddingBottom":"24px"}),

                dcc.Store(id="ana-mode", data="uni"),
            ]),
        ]),
    ])


# ══════════════════════════════════════════════════════════════════════════════
#  Callbacks
# ══════════════════════════════════════════════════════════════════════════════
def _btn_style(active):
    if active:
        return {
            "background":C_BLU,"color":"#fff","border":"none","borderRadius":"8px",
            "padding":"10px 22px","fontFamily":TNR,"fontSize":"13px","cursor":"pointer",
            "fontWeight":"bold","boxShadow":f"0 3px 10px {_rgba(C_BLU,0.35)}",
        }
    return {
        "background":"#fff","color":C_DARK,"border":f"1px solid {C_BDR}",
        "borderRadius":"8px","padding":"10px 22px","fontFamily":TNR,
        "fontSize":"13px","cursor":"pointer",
    }
    
def register_callbacks(app):

    # Charger les cours dans le filtre univarié
    @app.callback(
        Output("uni-cours", "options"),
        Input("ana-mode", "data"),
    )
    def _load_cours(_):
        db = get_db()
        try:
            cs = db.query(Course).filter_by(is_active=True).all()
            return [{"label":f"{c.code} – {c.label}","value":c.code} for c in cs]
        finally:
            db.close()

    # Changement de mode
    @app.callback(
        Output("panel-config",  "children"),
        Output("ana-mode",      "data"),
        Output("btn-mode-uni",  "style"),
        Output("btn-mode-bi",   "style"),
        Output("btn-mode-multi","style"),
        Output("ana-kpis",      "children",  allow_duplicate=True),
        Output("ana-graphs",    "children",  allow_duplicate=True),
        Output("ana-note",      "children",  allow_duplicate=True),
        Input("btn-mode-uni",   "n_clicks"),
        Input("btn-mode-bi",    "n_clicks"),
        Input("btn-mode-multi", "n_clicks"),
        prevent_initial_call=True,
    )
    def _switch_mode(a, b, c):
        t = ctx.triggered_id
        mode  = "uni" if t=="btn-mode-uni" else "bi" if t=="btn-mode-bi" else "multi"
        panel = {"uni":_panel_uni,"bi":_panel_bi,"multi":_panel_multi}[mode]()
        s_uni   = _btn_style(mode=="uni")
        s_bi    = _btn_style(mode=="bi")
        s_multi = _btn_style(mode=="multi")
        return panel, mode, s_uni, s_bi, s_multi, [], [], ""
    
    # ── Analyse univariée ──────────────────────────────────────────────────
    @app.callback(
        Output("ana-kpis",  "children",  allow_duplicate=True),
        Output("ana-graphs","children",  allow_duplicate=True),
        Output("ana-note",  "children",  allow_duplicate=True),
        Input("btn-uni-run","n_clicks"),
        State("uni-var",   "value"),
        State("uni-cours", "value"),
        prevent_initial_call=True,
    )
    def _run_uni(n, var, filtre):
        if not var:
            return _warn("Sélectionnez une variable."), [], ""
        db = get_db()
        try:
            rows = _build_dataset(db)
        finally:
            db.close()

        if filtre:
            rows = [r for r in rows if r["cours"] == filtre]

        vinfo = VARS[var]
        lbl   = vinfo["label"]
        vtype = vinfo["type"]
        unit  = vinfo.get("unit","")

        if vtype == "num":
            vals = [r[var] for r in rows if r.get(var) is not None]
            if not vals:
                return _warn("Aucune donnée pour cette sélection."), [], ""
            st = _stats(vals)
            kpis = html.Div(style={"display":"flex","gap":"12px","flexWrap":"wrap"}, children=[
                _kpi(st["n"],            "Observations",        C_BLU),
                _kpi(f"{st['mean']}{unit}", f"Moyenne",         C_GRN),
                _kpi(f"{st['median']}{unit}","Médiane",         C_TEAL),
                _kpi(f"{st['std']}",     "Écart-type",          C_ORG),
                _kpi(f"{st['min']}{unit}","Minimum",            C_RED),
                _kpi(f"{st['max']}{unit}","Maximum",            C_PURP),
                _kpi(f"{st['q1']}–{st['q3']}","Intervalle Q1–Q3", C_PINK),
                _kpi(f"{st['cv']}%",     "Coeff. de variation", C_LGRAY),
            ])
            graphs = _uni_num(vals, lbl, unit, var, rows)
        else:
            vals = [r[var] for r in rows if r.get(var) is not None]
            counts = {}
            for v in vals:
                counts[v] = counts.get(v,0)+1
            n_tot = len(vals)
            mode_v = max(counts, key=counts.get) if counts else "—"
            kpis = html.Div(style={"display":"flex","gap":"12px","flexWrap":"wrap"}, children=[
                _kpi(n_tot,               "Observations",  C_BLU),
                _kpi(len(counts),         "Modalités",     C_PURP),
                _kpi(mode_v,              "Mode",          C_GRN),
                _kpi(f"{round(counts.get(mode_v,0)/n_tot*100,1)}%" if counts else "—",
                     "Fréquence du mode", C_ORG),
            ])
            graphs = _uni_cat(counts, lbl)

        note = f"Analyse univariée · Variable : « {lbl} »" + (f" · Cours : {filtre}" if filtre else " · Tous cours")
        return kpis, graphs, note

    # ── Analyse bivariée ───────────────────────────────────────────────────
    @app.callback(
        Output("ana-kpis",  "children",  allow_duplicate=True),
        Output("ana-graphs","children",  allow_duplicate=True),
        Output("ana-note",  "children",  allow_duplicate=True),
        Input("btn-bi-run","n_clicks"),
        State("bi-x",  "value"),
        State("bi-y",  "value"),
        State("bi-col","value"),
        prevent_initial_call=True,
    )
    def _run_bi(n, vx, vy, vcol):
        if not vx or not vy:
            return _warn("Sélectionnez X et Y."), [], ""
        if vx == vy:
            return _warn("X et Y doivent être différentes."), [], ""
        db = get_db()
        try:
            rows = _build_dataset(db)
        finally:
            db.close()

        tx = VARS[vx]["type"]; ty = VARS[vy]["type"]
        lx = VARS[vx]["label"]; ly = VARS[vy]["label"]
        ux = VARS[vx].get("unit",""); uy = VARS[vy].get("unit","")

        # Si num×cat, on inverse pour avoir cat en X
        if tx == "num" and ty == "cat":
            vx,vy,tx,ty,lx,ly,ux,uy = vy,vx,ty,tx,ly,lx,uy,ux

        pairs = [(r[vx], r[vy], r.get(vcol), r.get("etudiant_full",""), r.get("cours",""))
                 for r in rows if r.get(vx) is not None and r.get(vy) is not None]

        kpis_ch = [_kpi(len(pairs), "Paires valides", C_BLU)]
        if tx=="num" and ty=="num":
            xs=[p[0] for p in pairs]; ys=[p[1] for p in pairs]
            r_val = _corr(xs,ys)
            force = "Forte" if abs(r_val)>0.7 else "Modérée" if abs(r_val)>0.4 else "Faible"
            kpis_ch += [
                _kpi(r_val, "Corrélation de Pearson", C_GRN if r_val>0 else C_RED),
                _kpi(force, "Force de liaison", C_ORG),
                _kpi("Positive" if r_val>0 else "Négative", "Sens", C_PURP),
            ]

        kpis = html.Div(style={"display":"flex","gap":"12px","flexWrap":"wrap"}, children=kpis_ch)
        graphs = _bi(pairs, vx, vy, vcol, tx, ty, lx, ly, ux, uy)
        note = f"Analyse bivariée · X : « {lx} » · Y : « {ly} »" + (f" · Couleur : {VARS[vcol]['label']}" if vcol else "")
        return kpis, graphs, note

    # ── Analyse multivariée ────────────────────────────────────────────────
    @app.callback(
        Output("ana-kpis",  "children",  allow_duplicate=True),
        Output("ana-graphs","children",  allow_duplicate=True),
        Output("ana-note",  "children",  allow_duplicate=True),
        Input("btn-multi-run","n_clicks"),
        State("multi-vars","value"),
        State("multi-grp", "value"),
        prevent_initial_call=True,
    )
    def _run_multi(n, sel_vars, grp):
        if not sel_vars or len(sel_vars) < 2:
            return _warn("Sélectionnez au moins 2 variables."), [], ""
        db = get_db()
        try:
            rows = _build_dataset(db)
        finally:
            db.close()

        num_v = [v for v in sel_vars if VARS[v]["type"]=="num"]
        cat_v = [v for v in sel_vars if VARS[v]["type"]=="cat"]
        n_obs = sum(1 for r in rows if all(r.get(v) is not None for v in sel_vars))

        kpis = html.Div(style={"display":"flex","gap":"12px","flexWrap":"wrap"}, children=[
            _kpi(n_obs,      "Observations complètes", C_BLU),
            _kpi(len(num_v), "Variables numériques",   C_GRN),
            _kpi(len(cat_v), "Variables catégorielles",C_ORG),
            _kpi(len(sel_vars),"Variables totales",    C_PURP),
        ])
        graphs = _multi(rows, num_v, cat_v, sel_vars, grp)
        labels = [VARS[v]["label"] for v in sel_vars]
        note = f"Analyse multivariée · Variables : {', '.join(labels)}"
        return kpis, graphs, note


# ══════════════════════════════════════════════════════════════════════════════
#  Graphiques — Univarié numérique
# ══════════════════════════════════════════════════════════════════════════════
def _uni_num(vals, lbl, unit, var, rows):
    mean_v = sum(vals)/len(vals)
    mn,mx  = min(vals),max(vals)

    # 1. Histogramme
    n_bins = min(12, max(5, len(vals)//3))
    step   = (mx-mn)/n_bins if mx!=mn else 1
    edges  = [mn+i*step for i in range(n_bins+1)]
    mids   = [(edges[i]+edges[i+1])/2 for i in range(n_bins)]
    counts_ = [0]*n_bins
    for v in vals:
        idx = min(int((v-mn)/step), n_bins-1)
        counts_[idx] += 1
    hist_clrs = [C_GRN if m>=10 else C_ORG if m>=8 else C_RED for m in mids]

    fig_hist = go.Figure()
    fig_hist.add_trace(go.Bar(
        x=mids, y=counts_, width=[step*0.85]*n_bins,
        marker=dict(color=hist_clrs, line=dict(width=0)),
        hovertemplate=f"{lbl} ≈ %{{x:.1f}}{unit}<br>Fréquence : %{{y}}<extra></extra>",
        name="Distribution",
    ))
    fig_hist.add_vline(x=mean_v, line_dash="dash", line_color=C_DARK, line_width=1.5)
    fig_hist.add_annotation(
        x=mean_v, y=max(counts_)*0.95, xref="x", yref="y",
        text=f"Moy. {mean_v:.1f}{unit}", showarrow=False,
        font=dict(family=TNR, size=10, color=C_DARK),
        bgcolor="white", borderpad=3, xanchor="left",
    )
    fig_hist.update_layout(
        **_layout(margin=dict(l=40,r=15,t=10,b=35)),
        xaxis=_ax(f"{lbl} ({unit})" if unit else lbl),
        yaxis=_ax("Fréquence"),
    )

    # 2. Boxplot
    fig_box = go.Figure()
    fig_box.add_trace(go.Box(
        y=vals, name=lbl,
        marker=dict(color=C_BLU, size=5, line=dict(width=1, color="#fff")),
        line=dict(color=C_BLU, width=2),
        fillcolor=_rgba(C_BLU, 0.12),
        boxmean="sd", boxpoints="outliers",
        hovertemplate=f"%{{y:.1f}}{unit}<extra></extra>",
    ))
    fig_box.update_layout(
        **_layout(margin=dict(l=45,r=20,t=20,b=30)),
        yaxis=_ax(f"{lbl} ({unit})" if unit else lbl),
        xaxis=dict(showticklabels=False),
    )

    # 3. KDE (densité empirique)
    bw = max(0.01, 1.06*(sum((v-mean_v)**2 for v in vals)/len(vals))**0.5 * len(vals)**(-0.2))
    x_kde = [mn + i*(mx-mn)/120 for i in range(121)] if mx!=mn else [mn]*2
    y_kde = [sum(math.exp(-0.5*((x-v)/bw)**2)/(bw*math.sqrt(2*math.pi)) for v in vals)/len(vals)
             for x in x_kde]
    fig_kde = go.Figure()
    fig_kde.add_trace(go.Scatter(
        x=x_kde, y=y_kde, mode="lines",
        line=dict(color=C_PURP, width=2.5),
        fill="tozeroy", fillcolor=_rgba(C_PURP, 0.1),
        name="Densité",
        hovertemplate=f"{lbl} : %{{x:.1f}}{unit}<br>Densité : %{{y:.4f}}<extra></extra>",
    ))
    fig_kde.add_vline(x=mean_v, line_dash="dash", line_color=C_DARK, line_width=1.2)
    fig_kde.update_layout(
        **_layout(margin=dict(l=45,r=20,t=20,b=45)),
        xaxis=_ax(f"{lbl} ({unit})" if unit else lbl),
        yaxis=_ax("Densité estimée"),
    )

    # 4. Comparaison par cours (boxplots)
    cours_data = {}
    for r in rows:
        if r.get(var) is not None:
            c = r["cours"]
            cours_data.setdefault(c, []).append(r[var])

    fig_cours = None
    if len(cours_data) > 1:
        fig_cours = go.Figure()
        for i,(c,vs) in enumerate(sorted(cours_data.items())):
            clr = PAL[i%len(PAL)]
            fig_cours.add_trace(go.Box(
                y=vs, name=c,
                marker=dict(color=clr, size=4, line=dict(width=1, color="#fff")),
                line=dict(color=clr, width=2),
                fillcolor=_rgba(clr, 0.12),
                boxmean=True, boxpoints="outliers",
                hovertemplate=f"Cours : {c}<br>%{{y:.1f}}{unit}<extra></extra>",
            ))
        fig_cours.update_layout(
            **_layout(margin=dict(l=45,r=20,t=20,b=45), showlegend=False),
            xaxis=_ax("Cours"),
            yaxis=_ax(f"{lbl} ({unit})" if unit else lbl),
        )

    # 5. QQ-plot (normalité)
    n = len(vals); sv = sorted(vals)
    quantiles = [sum(1 for x in sv if x<=sv[i])/n for i in range(n)]
    import math as _m
    def _qnorm(p):
        if p<=0: return -5
        if p>=1: return 5
        t = _m.sqrt(-2*_m.log(min(p,1-p)))
        c=[2.515517,0.802853,0.010328]; d=[1.432788,0.189269,0.001308]
        q=t-(c[0]+c[1]*t+c[2]*t**2)/(1+d[0]*t+d[1]*t**2+d[2]*t**3)
        return -q if p<0.5 else q
    th_q = [_qnorm(quantiles[i]) for i in range(n)]
    mx_th= max(abs(x) for x in th_q)
    # droite de référence
    mn_v,mx_v = min(sv),max(sv)
    th_line = [min(th_q),max(th_q)]
    q25_v,q75_v = sv[n//4],sv[3*n//4]
    q25_th,q75_th= _qnorm(0.25),_qnorm(0.75)
    if q75_th!=q25_th:
        slope_qq = (q75_v-q25_v)/(q75_th-q25_th)
        int_qq = q25_v - slope_qq*q25_th
        val_line = [slope_qq*t+int_qq for t in th_line]
    else:
        val_line = [mn_v, mx_v]

    fig_qq = go.Figure()
    fig_qq.add_trace(go.Scatter(
        x=th_q, y=sv, mode="markers",
        marker=dict(color=C_BLU, size=6, opacity=0.75,
                    line=dict(width=1, color="#fff")),
        name="Observations",
        hovertemplate="Quantile théorique : %{x:.2f}<br>Valeur : %{y:.2f}<extra></extra>",
    ))
    fig_qq.add_trace(go.Scatter(
        x=th_line, y=val_line, mode="lines",
        line=dict(color=C_RED, width=1.5, dash="dash"),
        name="Droite normale",showlegend=False,
    ))
    fig_qq.update_layout(
        **_layout(margin=dict(l=45,r=20,t=20,b=45)),
        xaxis=_ax("Quantiles théoriques (loi normale)"),
        yaxis=_ax(f"Quantiles empiriques ({lbl})"),
    )

    # 6. Violin
    fig_violin = go.Figure()
    fig_violin.add_trace(go.Violin(
        y=vals, name=lbl, box_visible=True, meanline_visible=True,
        line_color=C_PURP, fillcolor=_rgba(C_PURP, 0.2),
        points="outliers",
        hovertemplate=f"%{{y:.1f}}{unit}<extra></extra>",
    ))
    fig_violin.update_layout(
        **_layout(margin=dict(l=45,r=20,t=20,b=30)),
        yaxis=_ax(f"{lbl} ({unit})" if unit else lbl),
        xaxis=dict(showticklabels=False),
    )

    row1 = _grid(
        _graph_box("Distribution des valeurs", f"Histogramme de {lbl} avec la moyenne", fig_hist, 320),
        _graph_box("Boîte à moustaches", f"Médiane, quartiles et valeurs extrêmes de {lbl}", fig_box, 320),
    )
    row2 = _grid(
        _graph_box("Courbe de densité (KDE)", f"Densité empirique estimée de {lbl}", fig_kde, 320),
        _graph_box("Diagramme en violon", f"Distribution complète et densité de {lbl}", fig_violin, 320),
    )
    row3 = _grid(
        _graph_box("Q-Q Plot (normalité)", f"Adéquation de {lbl} à la loi normale", fig_qq, 320),
        _graph_box(f"Comparaison de {lbl} par cours",
                   "Boxplots par matière — permet de comparer les distributions",
                   fig_cours if fig_cours else _empty_fig("Un seul cours — pas de comparaison"), 320),
    )
    return html.Div([row1, row2, row3])


# ══════════════════════════════════════════════════════════════════════════════
#  Graphiques — Univarié catégoriel
# ══════════════════════════════════════════════════════════════════════════════
def _uni_cat(counts, lbl):
    if not counts:
        return html.Div()
    cats   = list(counts.keys())
    values = [counts[c] for c in cats]
    total  = sum(values)
    pcts   = [round(v/total*100,1) for v in values]
    clrs   = [PAL[i%len(PAL)] for i in range(len(cats))]
    srt    = sorted(zip(cats,values,pcts), key=lambda x: x[1], reverse=True)

    # 1. Barres verticales
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=cats, y=values, marker=dict(color=clrs, line=dict(width=0)),
        text=[f"{v}\n({p}%)" for v,p in zip(values,pcts)],
        textposition="outside",
        textfont=dict(family=TNR, size=10, color=C_DARK),
        hovertemplate="%{x} : %{y} (%{text})<extra></extra>",
        name=lbl,
    ))
    fig_bar.update_layout(
        **_layout(margin=dict(l=45,r=20,t=20,b=55)),
        xaxis=_ax(lbl), yaxis=_ax("Effectif"),
        uniformtext_minsize=8, uniformtext_mode="hide",
    )

    # 2. Donut
    fig_pie = go.Figure(go.Pie(
        labels=cats, values=values, hole=0.55,
        marker=dict(colors=clrs, line=dict(color="#fff", width=3)),
        textinfo="percent+label",
        textfont=dict(family=TNR, size=11, color=C_DARK),
        hovertemplate="%{label} : %{value} (%{percent})<extra></extra>",
        direction="clockwise", sort=True,
    ))
    fig_pie.add_annotation(x=0.5, y=0.5, text=f"<b>{total}</b>",
                           showarrow=False, xref="paper", yref="paper",
                           font=dict(family=TNR, size=24, color=C_DARK))
    fig_pie.update_layout(
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(family=TNR, color=C_DARK, size=11),
        margin=dict(l=20,r=20,t=20,b=20), showlegend=False,
    )

    # 3. Barres horizontales (Pareto)
    fig_hbar = go.Figure()
    fig_hbar.add_trace(go.Bar(
        y=[s[0] for s in srt], x=[s[1] for s in srt], orientation="h",
        marker=dict(color=[PAL[i%len(PAL)] for i in range(len(srt))], line=dict(width=0)),
        text=[f"{s[1]} ({s[2]}%)" for s in srt],
        textposition="outside",
        textfont=dict(family=TNR, size=10, color=C_DARK),
        hovertemplate="%{y} : %{x}<extra></extra>",
        name=lbl,
    ))
    fig_hbar.update_layout(
        **_layout(margin=dict(l=20,r=80,t=20,b=45)),
        xaxis=_ax("Effectif", range=[0, max(values)*1.2]),
        yaxis=_ax(),
    )

    # 4. Fréquences relatives (barres empilées normalisées)
    fig_freq = go.Figure()
    fig_freq.add_trace(go.Bar(
        x=cats, y=pcts,
        marker=dict(color=clrs, line=dict(width=0)),
        text=[f"{p}%" for p in pcts],
        textposition="inside",
        textfont=dict(family=TNR, size=11, color="#fff", weight="bold"),
        hovertemplate="%{x} : %{y}%<extra></extra>",
        name="Fréquence (%)",
    ))
    fig_freq.add_hline(y=100/len(cats) if cats else 50,
                       line_dash="dot", line_color=C_DARK, line_width=1,
                       annotation_text="Fréquence équirépartie",
                       annotation_font=dict(family=TNR, size=9, color=C_DARK),
                       annotation_position="top right")
    fig_freq.update_layout(
        **_layout(margin=dict(l=45,r=20,t=20,b=55)),
        xaxis=_ax(lbl),
        yaxis=_ax("Fréquence relative (%)", range=[0,max(pcts)*1.25]),
    )

    return html.Div([
        _grid(
            _graph_box("Diagramme en barres", f"Effectif par modalité de « {lbl} »", fig_bar, 280),
            _graph_box("Diagramme en secteurs (Donut)", f"Répartition de « {lbl} »", fig_pie, 280),
        ),
        _grid(
            _graph_box("Classement des modalités", f"Modalités de « {lbl} » triées par effectif décroissant", fig_hbar, 260),
            _graph_box("Fréquences relatives (%)", f"Proportion de chaque modalité de « {lbl} »", fig_freq, 260),
        ),
    ])


# ══════════════════════════════════════════════════════════════════════════════
#  Graphiques — Bivariés
# ══════════════════════════════════════════════════════════════════════════════
def _bi(pairs, vx, vy, vcol, tx, ty, lx, ly, ux, uy):
    graphs = []

    if tx=="num" and ty=="num":
        xs=[p[0] for p in pairs]; ys=[p[1] for p in pairs]

        # Couleurs par variable catégorielle
        if vcol and VARS[vcol]["type"]=="cat":
            cats_u = list(set(p[2] for p in pairs if p[2] is not None))
            cc = {c:PAL[i%len(PAL)] for i,c in enumerate(cats_u)}
            clrs = [cc.get(p[2], C_BLU) for p in pairs]
            lcol = VARS[vcol]["label"]
        else:
            clrs = C_BLU; lcol = None

        # 1. Nuage de points + droite de régression
        fig_sc = go.Figure()
        fig_sc.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers",
            marker=dict(color=clrs, size=8, opacity=0.8,
                        line=dict(width=1.5, color="#fff")),
            customdata=[[p[3],p[4]] for p in pairs],
            hovertemplate=f"<b>%{{customdata[0]}}</b> · %{{customdata[1]}}<br>{lx}: %{{x:.1f}}{ux}<br>{ly}: %{{y:.1f}}{uy}<extra></extra>",
            name="Observations",
        ))
        n_ = len(xs); mx_=sum(xs)/n_; my_=sum(ys)/n_
        num_=sum((xs[i]-mx_)*(ys[i]-my_) for i in range(n_))
        den_=sum((x-mx_)**2 for x in xs)
        if den_>0:
            slope=num_/den_; intc=my_-slope*mx_
            x_r=[min(xs),max(xs)]; y_r=[slope*x+intc for x in x_r]
            fig_sc.add_trace(go.Scatter(
                x=x_r, y=y_r, mode="lines",
                line=dict(color=C_RED, width=2, dash="dash"),
                name="Régression", showlegend=False,
            ))
            r_val = _corr(xs,ys)
            fig_sc.add_annotation(
                xref="paper", yref="paper", x=0.02, y=0.97,
                text=f"r = {r_val}", showarrow=False,
                font=dict(family=TNR, size=11, color=C_DARK),
                bgcolor="white", borderpad=3, xanchor="left", yanchor="top",
            )
        fig_sc.update_layout(
            **_layout(margin=dict(l=50,r=20,t=20,b=50)),
            xaxis=_ax(f"{lx}{' ('+ux+')' if ux else ''}"),
            yaxis=_ax(f"{ly}{' ('+uy+')' if uy else ''}"),
        )
        graphs.append(_graph_box(
            f"Nuage de points : {lx} vs {ly}",
            "Chaque point = 1 observation · droite de régression en rouge", fig_sc, 320))

        # 2. Histogramme 2D (densité)
        fig_h2 = go.Figure()
        fig_h2.add_trace(go.Histogram2d(
            x=xs, y=ys, nbinsx=8, nbinsy=8,
            colorscale=[[0,"#F0F9FF"],[0.5,C_BLU],[1,C_DARK]],
            hovertemplate=f"{lx}: %{{x:.1f}}<br>{ly}: %{{y:.1f}}<br>Densité: %{{z}}<extra></extra>",
            colorbar=dict(title=dict(text="N",font=dict(family=TNR,size=11)),
                         thickness=12, tickfont=dict(family=TNR,size=9)),
        ))
        fig_h2.update_layout(
            **_layout(margin=dict(l=50,r=70,t=20,b=50)),
            xaxis=_ax(f"{lx}{' ('+ux+')' if ux else ''}"),
            yaxis=_ax(f"{ly}{' ('+uy+')' if uy else ''}"),
        )
        graphs.append(_graph_box(
            f"Densité jointe : {lx} × {ly}",
            "Histogramme 2D — zones foncées = forte concentration", fig_h2, 300))

        # 3. Comparaison des distributions (deux KDE)
        fig_dens = go.Figure()
        for vals_, nm, clr in [(xs, lx, C_BLU),(ys, ly, C_GRN)]:
            mn_=min(vals_); mx_=max(vals_); mv_=sum(vals_)/len(vals_)
            bw_=max(0.01,1.06*(sum((v-mv_)**2 for v in vals_)/len(vals_))**0.5*len(vals_)**(-0.2))
            xk=[mn_+i*(mx_-mn_)/100 for i in range(101)] if mx_!=mn_ else [mn_]*2
            yk=[sum(math.exp(-0.5*((x-v)/bw_)**2)/(bw_*math.sqrt(2*math.pi)) for v in vals_)/len(vals_) for x in xk]
            fig_dens.add_trace(go.Scatter(
                x=xk, y=yk, mode="lines", name=nm,
                line=dict(color=clr, width=2),
                fill="tozeroy", fillcolor=_rgba(clr, 0.1),
            ))
        fig_dens.update_layout(
            **_layout(margin=dict(l=50,r=20,t=20,b=45), showlegend=True,
                      legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center",
                                  font=dict(family=TNR,size=10))),
            xaxis=_ax("Valeur"), yaxis=_ax("Densité estimée"),
        )
        graphs.append(_graph_box(
            "Comparaison des densités",
            f"Densité de {lx} (bleu) vs {ly} (vert) — superposées pour comparaison", fig_dens, 280))

    elif tx=="cat" and ty=="num":
        cats_u = sorted(set(p[0] for p in pairs if p[0] is not None))

        # 1. Boxplot groupé
        fig_box = go.Figure()
        for i,cat in enumerate(cats_u):
            vs = [p[1] for p in pairs if p[0]==cat]
            if vs:
                clr = PAL[i%len(PAL)]
                fig_box.add_trace(go.Box(
                    y=vs, name=str(cat),
                    marker=dict(color=clr, size=4, line=dict(width=1,color="#fff")),
                    line=dict(color=clr, width=2),
                    fillcolor=_rgba(clr, 0.12),
                    boxmean=True, boxpoints="outliers",
                    hovertemplate=f"{cat}<br>%{{y:.1f}}{uy}<extra></extra>",
                ))
        fig_box.update_layout(
            **_layout(margin=dict(l=50,r=20,t=20,b=45), showlegend=False),
            xaxis=_ax(lx), yaxis=_ax(f"{ly}{' ('+uy+')' if uy else ''}"),
        )
        graphs.append(_graph_box(
            f"Distribution de « {ly} » selon « {lx} »",
            "Boxplot groupé — médiane, quartiles, valeurs aberrantes", fig_box, 320))

        # 2. Barres de moyennes
        means = {cat: [p[1] for p in pairs if p[0]==cat and p[1] is not None] for cat in cats_u}
        srt   = sorted(means.items(), key=lambda x: sum(x[1])/len(x[1]) if x[1] else 0, reverse=True)
        avgs  = [round(sum(v)/len(v),2) if v else 0 for _,v in srt]
        errs  = [round((_stats(v) or {}).get("std",0),2) for _,v in srt]
        fig_bar= go.Figure()
        fig_bar.add_trace(go.Bar(
            x=[s[0] for s in srt], y=avgs,
            error_y=dict(type="data", array=errs, visible=True, color=C_LGRAY, thickness=1.5),
            marker=dict(color=[PAL[i%len(PAL)] for i in range(len(srt))], line=dict(width=0)),
            text=[f"{a}{uy}" for a in avgs], textposition="outside",
            textfont=dict(family=TNR, size=10, color=C_DARK),
            hovertemplate="%{x} : %{y:.2f}±%{error_y.array:.2f}<extra></extra>",
        ))
        fig_bar.update_layout(
            **_layout(margin=dict(l=50,r=20,t=20,b=55)),
            xaxis=_ax(lx),
            yaxis=_ax(f"Moyenne de {ly}{' ('+uy+')' if uy else ''}",
                      range=[0, max(avgs)*1.25] if avgs else [0,1]),
        )
        graphs.append(_graph_box(
            f"Moyenne de « {ly} » par « {lx} »",
            "Barres de moyennes avec barres d'erreur (±1 écart-type)", fig_bar, 280))

        # 3. Violon
        fig_vio = go.Figure()
        for i,cat in enumerate(cats_u):
            vs = [p[1] for p in pairs if p[0]==cat and p[1] is not None]
            if len(vs) > 2:
                clr = PAL[i%len(PAL)]
                fig_vio.add_trace(go.Violin(
                    y=vs, name=str(cat),
                    line_color=clr, fillcolor=_rgba(clr, 0.2),
                    box_visible=True, meanline_visible=True,
                    points="outliers",
                    hovertemplate=f"{cat}<br>%{{y:.1f}}{uy}<extra></extra>",
                ))
        fig_vio.update_layout(
            **_layout(margin=dict(l=50,r=20,t=20,b=45), showlegend=False),
            xaxis=_ax(lx), yaxis=_ax(f"{ly}{' ('+uy+')' if uy else ''}"),
        )
        graphs.append(_graph_box(
            f"Violon : forme de la distribution de « {ly} » par « {lx} »",
            "Visualisation de la densité et du boxplot superposés", fig_vio, 300))

    elif tx=="cat" and ty=="cat":
        cats_x = sorted(set(p[0] for p in pairs if p[0] is not None))
        cats_y = sorted(set(p[1] for p in pairs if p[1] is not None))
        matrix = [[sum(1 for p in pairs if p[0]==cx and p[1]==cy)
                   for cx in cats_x] for cy in cats_y]
        text_m = [[str(v) for v in row] for row in matrix]

        # 1. Heatmap contingence
        fig_heat = go.Figure(go.Heatmap(
            z=matrix, x=cats_x, y=cats_y,
            colorscale=[[0,"#F0F9FF"],[0.5,C_BLU],[1,C_DARK]],
            text=text_m, texttemplate="%{text}",
            textfont=dict(family=TNR, size=11),
            colorbar=dict(thickness=12, tickfont=dict(family=TNR,size=9)),
            hovertemplate=f"{lx}: %{{x}}<br>{ly}: %{{y}}<br>Effectif: %{{z}}<extra></extra>",
        ))
        fig_heat.update_layout(
            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
            font=dict(family=TNR, color=C_DARK, size=11),
            margin=dict(l=20,r=70,t=20,b=60),
            xaxis=dict(tickfont=dict(family=TNR,size=10), side="bottom",
                       title=dict(text=lx,font=dict(family=TNR,size=11))),
            yaxis=dict(tickfont=dict(family=TNR,size=10),
                       title=dict(text=ly,font=dict(family=TNR,size=11))),
        )
        graphs.append(_graph_box(
            f"Table de contingence : « {lx} » × « {ly} »",
            "Effectif de chaque croisement de modalités", fig_heat, 300))

        # 2. Barres groupées
        fig_grp = go.Figure()
        for i,cy in enumerate(cats_y):
            fig_grp.add_trace(go.Bar(
                name=str(cy),
                x=cats_x,
                y=[sum(1 for p in pairs if p[0]==cx and p[1]==cy) for cx in cats_x],
                marker=dict(color=PAL[i%len(PAL)]),
                hovertemplate=f"{ly}={cy} · {lx}=%{{x}} : %{{y}}<extra></extra>",
            ))
        fig_grp.update_layout(
            **_layout(margin=dict(l=50,r=20,t=20,b=60), showlegend=True,
                      barmode="group",
                      legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center",
                                  font=dict(family=TNR,size=10))),
            xaxis=_ax(lx), yaxis=_ax("Effectif"),
        )
        graphs.append(_graph_box(
            f"Barres groupées : « {lx} » par « {ly} »",
            "Comparaison des effectifs croisés", fig_grp, 300))

    if not graphs:
        graphs = [html.Div(_warn("Cette combinaison de variables n'est pas encore prise en charge."))]

    return html.Div(style={"display":"flex","flexDirection":"column","gap":"16px"}, children=graphs)


# ══════════════════════════════════════════════════════════════════════════════
#  Graphiques — Multivariés
# ══════════════════════════════════════════════════════════════════════════════
def _multi(rows, num_v, cat_v, all_v, grp):
    graphs = []

    # 1. Matrice de corrélation
    if len(num_v) >= 2:
        lbls  = [VARS[v]["label"] for v in num_v]
        corr_m = []
        for vy in num_v:
            row_c = []
            for vx in num_v:
                ps = [(r[vx],r[vy]) for r in rows if r.get(vx) is not None and r.get(vy) is not None]
                if len(ps) > 1:
                    xs=[p[0] for p in ps]; ys=[p[1] for p in ps]
                    row_c.append(_corr(xs,ys))
                else:
                    row_c.append(1 if vx==vy else 0)
            corr_m.append(row_c)

        text_c = [[f"{v:.2f}" for v in row] for row in corr_m]
        text_color = [["#fff" if abs(v)>0.6 else C_DARK for v in row] for row in corr_m]
        fig_corr = go.Figure(go.Heatmap(
            z=corr_m, x=lbls, y=lbls,
            colorscale=[[0,C_RED],[0.5,"#FFFFFF"],[1,C_GRN]],
            zmin=-1, zmax=1,
            text=text_c, texttemplate="%{text}",
            textfont=dict(family=TNR, size=11),
            colorbar=dict(title=dict(text="r",font=dict(family=TNR,size=11)),
                         thickness=12, tickfont=dict(family=TNR,size=9),
                         tickvals=[-1,-0.5,0,0.5,1]),
            hovertemplate="%{y} × %{x}<br>r = %{z:.3f}<extra></extra>",
        ))
        fig_corr.update_layout(
            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
            font=dict(family=TNR, color=C_DARK, size=11),
            margin=dict(l=20,r=80,t=20,b=20),
            xaxis=dict(tickfont=dict(family=TNR,size=10), side="bottom"),
            yaxis=dict(tickfont=dict(family=TNR,size=10), autorange="reversed"),
        )
        h_corr = 200 + len(num_v)*40
        graphs.append(_graph_box(
            "Matrice de corrélation",
            "Corrélations de Pearson entre toutes les variables numériques (rouge=négative, vert=positive)",
            fig_corr, h_corr))

    # 2. SPLOM (scatter matrix)
    if len(num_v) >= 2:
        vars_sp = num_v[:4]
        dims = []
        for v in vars_sp:
            vals = [r[v] for r in rows if r.get(v) is not None]
            dims.append(dict(label=VARS[v]["label"][:12], values=vals))

        if grp and VARS[grp]["type"]=="cat":
            grp_vals = [r.get(grp,"") for r in rows]
            grp_u    = list(set(g for g in grp_vals if g))
            color_idx= [grp_u.index(g) if g in grp_u else 0 for g in grp_vals]
            n_grp    = max(2, len(grp_u))
            cscale   = [[i/(n_grp-1), PAL[i%len(PAL)]] for i in range(n_grp)]
        else:
            color_idx= [0]*len(rows)
            cscale   = [[0,C_BLU],[1,C_BLU]]

        fig_sp = go.Figure(go.Splom(
            dimensions=dims,
            marker=dict(color=color_idx, colorscale=cscale,
                        size=4, opacity=0.65,
                        line=dict(width=0.5, color="#fff")),
            diagonal_visible=True, showupperhalf=False,
        ))
        fig_sp.update_layout(
            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
            font=dict(family=TNR, color=C_DARK, size=10),
            margin=dict(l=20,r=20,t=20,b=20),
            showlegend=False,
        )
        graphs.append(_graph_box(
            "Matrice de nuages de points (SPLOM)",
            "Toutes les paires de variables numériques — chaque cellule = un nuage de points",
            fig_sp, 420))

    # 3. Barres groupées par variable de groupe
    if num_v and grp:
        grp_u = sorted(set(r[grp] for r in rows if r.get(grp) is not None))
        fig_mb = go.Figure()
        for i,g in enumerate(grp_u):
            avgs_g = []
            for nv in num_v:
                vs_g = [r[nv] for r in rows if r.get(grp)==g and r.get(nv) is not None]
                avgs_g.append(round(sum(vs_g)/len(vs_g),2) if vs_g else 0)
            fig_mb.add_trace(go.Bar(
                name=str(g), x=[VARS[v]["label"] for v in num_v], y=avgs_g,
                marker=dict(color=PAL[i%len(PAL)]),
                text=[str(a) for a in avgs_g], textposition="outside",
                textfont=dict(family=TNR, size=9, color=C_DARK),
                hovertemplate=f"{VARS[grp]['label']}={g}<br>%{{x}} : %{{y:.2f}}<extra></extra>",
            ))
        lbl_grp = VARS[grp]["label"]
        fig_mb.update_layout(
            **_layout(margin=dict(l=50,r=20,t=20,b=80), showlegend=True, barmode="group",
                      legend=dict(orientation="h", y=-0.28, x=0.5, xanchor="center",
                                  font=dict(family=TNR,size=10))),
            xaxis=_ax("Variables"), yaxis=_ax("Valeur moyenne"),
        )
        graphs.append(_graph_box(
            f"Profil moyen des variables par « {lbl_grp} »",
            f"Comparaison des moyennes de chaque variable selon {lbl_grp}",
            fig_mb, 340))

    # 4. Heatmap des moyennes par cours
    if len(num_v) >= 2:
        cours_u = sorted(set(r["cours"] for r in rows))
        z_data, txt_data = [], []
        for v in num_v:
            row_z, row_t = [], []
            for c in cours_u:
                vs = [r[v] for r in rows if r["cours"]==c and r.get(v) is not None]
                avg= round(sum(vs)/len(vs),1) if vs else 0
                row_z.append(avg); row_t.append(str(avg))
            z_data.append(row_z); txt_data.append(row_t)

        fig_hm = go.Figure(go.Heatmap(
            z=z_data, x=cours_u, y=[VARS[v]["label"] for v in num_v],
            colorscale=[[0,C_RED],[0.4,C_ORG],[0.7,C_BLU],[1,C_GRN]],
            text=txt_data, texttemplate="%{text}",
            textfont=dict(family=TNR, size=10),
            colorbar=dict(thickness=12, tickfont=dict(family=TNR,size=9)),
            hovertemplate="Cours: %{x}<br>Variable: %{y}<br>Moyenne: %{z}<extra></extra>",
        ))
        fig_hm.update_layout(
            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
            font=dict(family=TNR, color=C_DARK, size=11),
            margin=dict(l=20,r=80,t=20,b=50),
            xaxis=dict(tickfont=dict(family=TNR,size=10),
                       title=dict(text="Cours",font=dict(family=TNR,size=11))),
            yaxis=dict(tickfont=dict(family=TNR,size=10)),
        )
        h_hm = 160 + len(num_v)*45
        graphs.append(_graph_box(
            "Heatmap des moyennes par cours et variable",
            "Chaque cellule = moyenne de la variable pour le cours — permet de repérer les disparités",
            fig_hm, h_hm))

    # 5. Profils radar par cours (si >= 2 num_v)
    if len(num_v) >= 3:
        cours_u = sorted(set(r["cours"] for r in rows))[:6]
        lbls_r  = [VARS[v]["label"] for v in num_v]
        fig_rad = go.Figure()
        for i,c in enumerate(cours_u):
            vals_r = []
            for v in num_v:
                vs = [r[v] for r in rows if r["cours"]==c and r.get(v) is not None]
                vals_r.append(round(sum(vs)/len(vs),1) if vs else 0)
            vals_r_closed = vals_r + [vals_r[0]]
            lbls_closed   = lbls_r + [lbls_r[0]]
            clr = PAL[i%len(PAL)]
            fig_rad.add_trace(go.Scatterpolar(
                r=vals_r_closed, theta=lbls_closed,
                fill="toself", name=c,
                line=dict(color=clr, width=2),
                fillcolor=_rgba(clr, 0.1),
                hovertemplate=f"Cours : {c}<br>%{{theta}} : %{{r:.1f}}<extra></extra>",
            ))
        fig_rad.update_layout(
            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
            font=dict(family=TNR, color=C_DARK, size=11),
            polar=dict(bgcolor="#FAFAFA",
                       radialaxis=dict(visible=True, tickfont=dict(family=TNR,size=9)),
                       angularaxis=dict(tickfont=dict(family=TNR,size=9))),
            showlegend=True,
            margin=dict(l=50,r=50,t=30,b=60),
            legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center",
                        font=dict(family=TNR,size=10)),
        )
        graphs.append(_graph_box(
            "Graphique radar des profils par cours",
            "Comparaison multidimensionnelle des cours sur toutes les variables sélectionnées",
            fig_rad, 380))

    if not graphs:
        return html.Div(_warn("Sélectionnez au moins 2 variables numériques pour l'analyse multivariée."))

    return html.Div(style={"display":"flex","flexDirection":"column","gap":"16px"}, children=graphs)