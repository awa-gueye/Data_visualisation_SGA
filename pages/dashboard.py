"""
pages/dashboard.py — v10
4 onglets : Indicateurs / Visualisation / Classements / Situation
Filtres cours + période fonctionnels sur tous les onglets
Animations sur tous les onglets
"""
from dash import html, dcc, Input, Output, State, ctx
import plotly.graph_objects as go
from datetime import date, timedelta
from sqlalchemy import func
import time as _time

from pages.components import sidebar, topbar
from utils.db import get_db
from models import Student, Course, Session, Attendance, Grade
from utils.format import fr, fr_pct, fr_note

FONT  = "Nunito, sans-serif"
POPS  = "Poppins, sans-serif"
DARK  = "#0A1628"
GRAY  = "#6B7280"
LGRAY = "#9CA3AF"
GRID  = "rgba(0,0,0,0.05)"
BG    = "rgba(0,0,0,0)"
PAL   = ["#0EA5E9","#8B5CF6","#10B981","#F59E0B","#EF4444","#06B6D4"]
W, H  = 310, 220

TABS = [
    ("indicateurs",   "Indicateurs clés", "10 KPIs"),
    ("visualisation", "Visualisation",    "9 graphiques"),
    ("classements",   "Classements",      "Top & Rankings"),
    ("situation",     "Situation",        "Séances & Cours"),
]


# ── Helpers filtres ───────────────────────────────────────────────────────────
def _parse_filters(course_id, period):
    cid  = None if (not course_id or course_id == "all") else int(course_id)
    days = int(period) if period and period != "0" else 0
    cut  = date.today() - timedelta(days=days) if days > 0 else None
    return cid, cut


# ── Données (avec filtres) ────────────────────────────────────────────────────
def _opts():
    db = get_db()
    try:
        opts = [{"label":"Tous les cours","value":"all"}]
        for c in db.query(Course).filter_by(is_active=True).all():
            opts.append({"label":f"{c.code} – {c.label}","value":str(c.id)})
        return opts
    finally: db.close()

def _stats(cid=None, cut=None):
    db = get_db()
    try:
        n_st = db.query(Student).filter_by(is_active=True).count()
        n_co = db.query(Course).filter_by(is_active=True).count()

        se_q = db.query(Session)
        if cid: se_q = se_q.filter_by(course_id=cid)
        if cut: se_q = se_q.filter(Session.date >= cut)
        n_se = se_q.count()

        # IDs séances filtrées pour les attendances
        all_sess_ids = [s.id for s in se_q.all()]

        att_q = db.query(Attendance)
        if all_sess_ids:
            att_q = att_q.filter(Attendance.session_id.in_(all_sess_ids))
        elif cid or cut:
            att_q = att_q.filter(False)

        t_att = att_q.count()
        a_att = att_q.filter_by(is_absent=True).count()
        j_att = att_q.filter_by(is_absent=True, justified=True).count()
        ar    = round(a_att/t_att*100,1) if t_att else 0
        jr    = round(j_att/a_att*100,1) if a_att else 0

        gr_q = db.query(Grade)
        if cid: gr_q = gr_q.filter_by(course_id=cid)
        grades = gr_q.all()
        avg   = round(sum(g.score for g in grades)/len(grades),1) if grades else 0
        t_g   = len(grades)
        p_g   = sum(1 for g in grades if g.score >= 10)
        e_g   = sum(1 for g in grades if g.score >= 14)
        f_g   = sum(1 for g in grades if g.score < 10)
        pr    = round(p_g/t_g*100,1) if t_g else 0
        er    = round(e_g/t_g*100,1) if t_g else 0

        w  = date.today()-timedelta(days=7)
        m  = date.today()-timedelta(days=30)
        nw = db.query(Session).filter(Session.date>=w).count()
        nm = db.query(Session).filter(Session.date>=m).count()

        return dict(n_st=n_st,n_co=n_co,n_se=n_se,ar=ar,jr=jr,
                    avg=avg,pr=pr,er=er,f_g=f_g,nw=nw,nm=nm,t_g=t_g)
    finally: db.close()

def _absence_rows(cid=None, cut=None):
    db = get_db()
    try:
        rows=[]
        q = db.query(Course).filter_by(is_active=True)
        if cid: q = q.filter_by(id=cid)
        for c in q.all():
            sess = [s for s in c.sessions if (not cut or s.date >= cut)]
            t=sum(len(s.attendances) for s in sess)
            a=sum(1 for s in sess for x in s.attendances if x.is_absent)
            if t>0: rows.append({"label":c.label,"code":c.code,"pct":round(a/t*100,1),"color":c.color})
        return rows
    finally: db.close()

def _grade_rows(cid=None, cut=None):
    db = get_db()
    try:
        rows=[]
        q = db.query(Course).filter_by(is_active=True)
        if cid: q = q.filter_by(id=cid)
        for c in q.all():
            gs = db.query(Grade).filter_by(course_id=c.id).all()
            if gs:
                rows.append({"label":c.label,"code":c.code,
                             "avg":round(sum(g.score for g in gs)/len(gs),1),"color":c.color})
        return rows
    finally: db.close()

def _scores(cid=None, cut=None):
    db = get_db()
    try:
        q = db.query(Grade)
        if cid: q = q.filter_by(course_id=cid)
        return [g.score for g in q.all()]
    finally: db.close()

def _timeline(cid=None, cut=None, days=42):
    db = get_db()
    try:
        cutoff = cut or (date.today()-timedelta(days=days))
        q = db.query(Session).filter(Session.date>=cutoff)
        if cid: q = q.filter_by(course_id=cid)
        sess = q.order_by(Session.date).all()
        by={}
        for s in sess:
            d=s.date.strftime("%d/%m"); by[d]=by.get(d,0)+1
        return list(by.keys()),list(by.values())
    finally: db.close()

def _progress(cid=None, cut=None):
    db = get_db()
    try:
        q = db.query(Course).filter_by(is_active=True)
        if cid: q = q.filter_by(id=cid)
        return [{"code":c.code,"label":c.label,"done":c.hours_done,
                 "total":c.total_hours,"pct":c.progress_pct,"color":c.color}
                for c in q.all()]
    finally: db.close()

def _tops(cid=None, cut=None, n=8):
    db = get_db()
    try:
        ranked=[]
        for st in db.query(Student).filter_by(is_active=True).all():
            q = db.query(Grade).filter_by(student_id=st.id)
            if cid: q = q.filter_by(course_id=cid)
            gs = q.all()
            if gs:
                avg=round(sum(g.score for g in gs)/len(gs),1)
                ab=db.query(Attendance).filter_by(student_id=st.id,is_absent=True).count()
                tot=db.query(Attendance).filter_by(student_id=st.id).count()
                ranked.append({"name":f"{st.first_name} {st.last_name}","avg":avg,
                               "ab":ab,"tot":tot,"pct":round(ab/tot*100,1) if tot else 0})
        ranked.sort(key=lambda x:x["avg"],reverse=True)
        return ranked[:n]
    finally: db.close()

def _top_absents(cid=None, cut=None, n=8):
    db = get_db()
    try:
        rows=[]
        for st in db.query(Student).filter_by(is_active=True).all():
            q = db.query(Attendance).filter_by(student_id=st.id)
            if cid:
                sids = [s.id for s in db.query(Session).filter_by(course_id=cid).all()]
                q = q.filter(Attendance.session_id.in_(sids)) if sids else q.filter(False)
            ab  = q.filter_by(is_absent=True).count()
            tot = q.count()
            if tot>0:
                rows.append({"name":f"{st.first_name} {st.last_name}",
                             "ab":ab,"tot":tot,"pct":round(ab/tot*100,1)})
        rows.sort(key=lambda x:x["ab"],reverse=True)
        return rows[:n]
    finally: db.close()

def _sessions(cid=None, cut=None, n=8):
    db = get_db()
    try:
        q = db.query(Session).order_by(Session.date.desc())
        if cid: q = q.filter_by(course_id=cid)
        if cut: q = q.filter(Session.date >= cut)
        rows=[]
        for s in q.limit(n).all():
            na=sum(1 for a in s.attendances if a.is_absent)
            nt=len(s.attendances)
            rows.append({"course":s.course.code if s.course else "–",
                         "label":s.course.label if s.course else "–",
                         "date":s.date.strftime("%d/%m/%Y"),
                         "theme":s.theme or "–","absent":na,"total":nt,
                         "color":s.course.color if s.course else "#0EA5E9",
                         "duration":s.duration})
        return rows
    finally: db.close()

def _notes_par_cours(cid=None, cut=None):
    db = get_db()
    try:
        result=[]
        q = db.query(Course).filter_by(is_active=True)
        if cid: q = q.filter_by(id=cid)
        for c in q.all():
            scores=[g.score for g in db.query(Grade).filter_by(course_id=c.id).all()]
            if scores: result.append({"label":c.label,"code":c.code,"scores":scores,"color":c.color})
        return result
    finally: db.close()

def _presence_par_jour(cid=None, cut=None):
    db = get_db()
    try:
        jours=["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"]
        data={j:{"p":0,"t":0} for j in jours}
        q = db.query(Session)
        if cid: q = q.filter_by(course_id=cid)
        if cut: q = q.filter(Session.date >= cut)
        for s in q.all():
            j=jours[s.date.weekday()] if s.date.weekday()<6 else None
            if j:
                for a in s.attendances:
                    data[j]["t"]+=1
                    if not a.is_absent: data[j]["p"]+=1
        rows=[]
        for j in jours:
            t=data[j]["t"]
            if t>0: rows.append({"jour":j,"pct":round(data[j]["p"]/t*100,1),"total":t})
        return rows
    finally: db.close()

def _evolution_moyennes(cid=None, cut=None):
    db = get_db()
    try:
        result=[]
        q = db.query(Course).filter_by(is_active=True)
        if cid: q = q.filter_by(id=cid)
        for c in q.all():
            all_g=db.query(Grade).filter_by(course_id=c.id).all()
            if len(all_g)>=2:
                chunk=max(1,len(all_g)//6)
                avgs=[round(sum(g.score for g in all_g[i:i+chunk])/len(all_g[i:i+chunk]),1)
                      for i in range(0,len(all_g),chunk)]
                result.append({"label":c.code,"x":[f"S{k+1}" for k in range(len(avgs))],"y":avgs,"color":c.color})
        return result
    finally: db.close()

def _grades_by_type(cid=None, cut=None):
    db = get_db()
    try:
        types={}
        q = db.query(Grade)
        if cid: q = q.filter_by(course_id=cid)
        for g in q.all():
            lbl=g.label or "Autre"
            if lbl not in types: types[lbl]=[]
            types[lbl].append(g.score)
        return [{"label":k,"avg":round(sum(v)/len(v),1),"count":len(v)} for k,v in types.items()]
    finally: db.close()


# ── Figures ───────────────────────────────────────────────────────────────────
def _empty(w=W,h=H):
    fig=go.Figure()
    fig.add_annotation(text="Aucune donnée",xref="paper",yref="paper",x=0.5,y=0.5,
                       showarrow=False,font=dict(color=LGRAY,size=12,family=FONT))
    fig.update_layout(paper_bgcolor=BG,plot_bgcolor=BG,width=w,height=h,autosize=False,
                      margin=dict(l=8,r=8,t=8,b=8))
    return fig

def _bl(w=W,h=H,ml=10,mr=10,mt=12,mb=28):
    return dict(paper_bgcolor=BG,plot_bgcolor=BG,width=w,height=h,autosize=False,
                showlegend=False,margin=dict(l=ml,r=mr,t=mt,b=mb),
                font=dict(family=FONT,color=GRAY,size=10),
                xaxis=dict(gridcolor=GRID,tickfont=dict(size=9,color=LGRAY)),
                yaxis=dict(gridcolor=GRID,tickfont=dict(size=9,color=LGRAY)))

def _fig_gauge(avg,w=W,h=H):
    color="#10B981" if avg>=14 else "#0EA5E9" if avg>=10 else "#EF4444"
    fig=go.Figure(go.Indicator(mode="gauge+number",value=avg,
        number=dict(suffix=" / 20",font=dict(size=24,family=POPS,color=DARK)),
        gauge=dict(axis=dict(range=[0,20],tickvals=[0,5,10,15,20],tickfont=dict(size=9,color=LGRAY)),
                   bar=dict(color=color,thickness=0.6),bgcolor="white",borderwidth=0,
                   steps=[dict(range=[0,10],color="rgba(239,68,68,0.07)"),
                          dict(range=[10,14],color="rgba(14,165,233,0.07)"),
                          dict(range=[14,20],color="rgba(16,185,129,0.07)")],
                   threshold=dict(line=dict(color=DARK,width=2),thickness=0.8,value=10))))
    fig.update_layout(paper_bgcolor=BG,width=w,height=h,autosize=False,
                      margin=dict(l=14,r=14,t=10,b=0),font=dict(family=FONT))
    return fig

def _fig_donut(rows, w=460, h=H):
    if not rows: return _empty(w, h)
    fig = go.Figure(go.Pie(
        labels=[r["label"] for r in rows],
        values=[r["pct"] for r in rows],
        hole=0.58,
        marker=dict(colors=PAL[:len(rows)], line=dict(color="#fff", width=2)),
        textinfo="label+percent",
        textfont=dict(size=9, family=FONT),
        hovertemplate="<b>%{label}</b><br>Taux d'absence : %{value:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=BG, width=w, height=h, autosize=False,
        showlegend=True,
        legend=dict(
            font=dict(size=9, family=FONT, color=DARK),
            orientation="v",
            x=0.5, y=0.5,
            xanchor="center", yanchor="middle",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#E5E7EB", borderwidth=1,
            itemsizing="constant",
        ),
        margin=dict(l=8, r=130, t=8, b=8),
        font=dict(family=FONT),
    )
    return fig

def _fig_histo(scores,w=W,h=H):
    if not scores: return _empty(w,h)
    bins=[0,4,6,8,10,12,14,16,18,20]; lbls=["0-4","4-6","6-8","8-10","10-12","12-14","14-16","16-18","18-20"]
    cnts=[0]*(len(bins)-1)
    for s in scores:
        for i in range(len(bins)-1):
            if bins[i]<=s<=bins[i+1]: cnts[i]+=1; break
    colors=["#EF4444" if bins[i+1]<=10 else "#0EA5E9" if bins[i+1]<=14 else "#10B981" for i in range(len(bins)-1)]
    fig=go.Figure(go.Bar(x=lbls,y=cnts,marker=dict(color=colors,line=dict(width=0)),
        text=cnts,textposition="outside",textfont=dict(size=9,family=FONT,color=DARK),width=0.7,
        hovertemplate="<b>Tranche %{x}</b><br>%{y} étudiant(s)<extra></extra>"))
    fig.add_annotation(x=0.98,y=0.95,xref="paper",yref="paper",
        text=f"Moy. {round(sum(scores)/len(scores),1)}/20",showarrow=False,
        font=dict(size=10,color="#0EA5E9",family=POPS),bgcolor="rgba(14,165,233,0.1)",
        bordercolor="#0EA5E9",borderwidth=1,borderpad=4,xanchor="right")
    layout=_bl(w,h,mb=28); layout["xaxis"]["title"]=dict(text="Notes",font=dict(size=9,color=LGRAY))
    fig.update_layout(**layout); return fig

def _fig_bars(rows,w=W,h=H):
    if not rows: return _empty(w,h)
    lbls=[r["label"] for r in rows]; avgs=[r["avg"] for r in rows]
    colors=["#10B981" if a>=14 else "#0EA5E9" if a>=10 else "#EF4444" for a in avgs]
    fig=go.Figure(go.Bar(x=avgs,y=lbls,orientation="h",marker=dict(color=colors,line=dict(width=0)),
        text=[f"{a}/20" for a in avgs],textposition="outside",textfont=dict(size=10,family=POPS,color=DARK),
        width=0.5,hovertemplate="<b>%{y}</b><br>Moyenne : %{x}/20<extra></extra>"))
    fig.add_vline(x=10,line_dash="dot",line_color="rgba(239,68,68,0.4)",line_width=1.5)
    fig.update_layout(paper_bgcolor=BG,plot_bgcolor=BG,width=w,height=h,autosize=False,showlegend=False,
        margin=dict(l=8,r=60,t=10,b=20),font=dict(family=FONT,color=GRAY,size=10),
        xaxis=dict(range=[0,22],gridcolor=GRID,tickfont=dict(size=9,color=LGRAY)),
        yaxis=dict(gridcolor=GRID,tickfont=dict(size=10,color=DARK)))
    return fig

def _fig_line(dates,counts,w=W,h=H):
    if not dates: return _empty(w,h)
    fig=go.Figure(go.Scatter(x=dates,y=counts,mode="lines+markers",
        line=dict(color="#0EA5E9",width=2.5,shape="spline",smoothing=0.8),
        marker=dict(color="#0EA5E9",size=6,line=dict(color="#fff",width=2)),
        fill="tozeroy",fillcolor="rgba(14,165,233,0.08)",
        hovertemplate="<b>%{x}</b><br>%{y} séance(s)<extra></extra>"))
    layout=_bl(w,h,mb=28); layout["yaxis"]["dtick"]=1
    fig.update_layout(**layout); return fig

def _fig_radar(courses,w=W,h=H):
    if not courses: return _empty(w,h)
    lbls=[c["code"] for c in courses]+[courses[0]["code"]]
    vals=[c["pct"] for c in courses]+[courses[0]["pct"]]
    fig=go.Figure(go.Scatterpolar(r=vals,theta=lbls,fill="toself",fillcolor="rgba(14,165,233,0.1)",
        line=dict(color="#0EA5E9",width=2),marker=dict(size=4,color="#0EA5E9"),
        hovertemplate="<b>%{theta}</b><br>Avancement : %{r:.0f}%<extra></extra>"))
    fig.update_layout(paper_bgcolor=BG,width=w,height=h,autosize=False,showlegend=False,
        margin=dict(l=28,r=28,t=28,b=28),
        polar=dict(bgcolor=BG,radialaxis=dict(visible=True,range=[0,100],
                   tickfont=dict(size=7,color=LGRAY),gridcolor="rgba(0,0,0,0.06)"),
                   angularaxis=dict(tickfont=dict(size=9,color=DARK,family=POPS),
                                    gridcolor="rgba(0,0,0,0.06)")),
        font=dict(family=FONT))
    return fig

def _fig_absents(rows,w=W,h=H):
    if not rows: return _empty(w,h)
    names=[r["name"].split()[0][0]+". "+(r["name"].split()[1] if len(r["name"].split())>1 else "") for r in rows]
    vals=[r["ab"] for r in rows]; pcts=[r["pct"] for r in rows]
    colors=["#EF4444" if p>20 else "#F59E0B" if p>10 else "#0EA5E9" for p in pcts]
    fig=go.Figure(go.Bar(x=vals,y=names,orientation="h",marker=dict(color=colors,line=dict(width=0)),
        text=[f"{v} ({p}%)" for v,p in zip(vals,pcts)],textposition="outside",
        textfont=dict(size=9,family=FONT,color=DARK),width=0.55,
        hovertemplate="<b>%{y}</b><br>%{x} absence(s)<extra></extra>"))
    fig.update_layout(paper_bgcolor=BG,plot_bgcolor=BG,width=w,height=h,autosize=False,showlegend=False,
        margin=dict(l=8,r=72,t=10,b=20),font=dict(family=FONT,color=GRAY,size=10),
        xaxis=dict(gridcolor=GRID,tickfont=dict(size=9,color=LGRAY)),
        yaxis=dict(tickfont=dict(size=9,color=DARK)))
    return fig

def _fig_scatter(pts,w=W,h=H):
    if not pts: return _empty(w,h)
    x=[p["ab"] for p in pts]; y=[p["avg"] for p in pts]
    colors=["#10B981" if a>=14 else "#0EA5E9" if a>=10 else "#EF4444" for a in y]
    fig=go.Figure(go.Scatter(x=x,y=y,mode="markers+text",
        marker=dict(size=11,color=colors,line=dict(color="#fff",width=2),opacity=0.85),
        text=[p["name"].split()[0] for p in pts],textposition="top center",
        textfont=dict(size=8,family=FONT,color=DARK),
        hovertemplate="<b>%{text}</b><br>Absences : %{x}<br>Moyenne : %{y}/20<extra></extra>"))
    fig.add_hline(y=10,line_dash="dot",line_color="rgba(239,68,68,0.4)",line_width=1.5)
    layout=_bl(w,h,mb=28)
    layout["xaxis"]["title"]=dict(text="Absences",font=dict(size=9,color=LGRAY))
    layout["yaxis"].update({"range":[0,22],"title":dict(text="Moyenne /20",font=dict(size=9,color=LGRAY))})
    fig.update_layout(**layout); return fig

def _fig_by_type(rows,w=W,h=H):
    if not rows: return _empty(w,h)
    lbls=[r["label"] for r in rows]; avgs=[r["avg"] for r in rows]; cnts=[r["count"] for r in rows]
    colors=["#10B981" if a>=14 else "#0EA5E9" if a>=10 else "#EF4444" for a in avgs]
    fig=go.Figure()
    fig.add_trace(go.Bar(name="Moyenne",x=lbls,y=avgs,marker=dict(color=colors,line=dict(width=0)),
        text=[f"{a}/20" for a in avgs],textposition="outside",textfont=dict(size=10,family=POPS,color=DARK),
        width=0.5,yaxis="y"))
    fig.add_trace(go.Scatter(name="Nb notes",x=lbls,y=cnts,mode="markers",
        marker=dict(size=9,color="#8B5CF6",symbol="diamond",line=dict(color="#fff",width=2)),yaxis="y2"))
    fig.add_hline(y=10,line_dash="dot",line_color="rgba(239,68,68,0.4)",line_width=1.5)
    fig.update_layout(paper_bgcolor=BG,plot_bgcolor=BG,width=w,height=h,autosize=False,showlegend=True,
        legend=dict(orientation="h",y=1.12,x=0.5,xanchor="center",font=dict(size=9,family=FONT)),
        margin=dict(l=10,r=36,t=26,b=28),font=dict(family=FONT,color=GRAY,size=10),
        xaxis=dict(gridcolor=GRID,tickfont=dict(size=9,color=DARK)),
        yaxis=dict(gridcolor=GRID,range=[0,22],tickfont=dict(size=9,color=LGRAY)),
        yaxis2=dict(overlaying="y",side="right",tickfont=dict(size=9,color="#8B5CF6"),showgrid=False))
    return fig

def _fig_boxplot(rows,w=W,h=H):
    if not rows: return _empty(w,h)
    fills=["rgba(14,165,233,0.15)","rgba(139,92,246,0.15)","rgba(16,185,129,0.15)",
           "rgba(245,158,11,0.15)","rgba(239,68,68,0.15)","rgba(6,182,212,0.15)"]
    fig=go.Figure()
    for i,r in enumerate(rows):
        fig.add_trace(go.Box(y=r["scores"],name=r["code"],boxmean=True,
            marker=dict(color=PAL[i%len(PAL)],line=dict(color="#fff",width=1)),
            line=dict(color=PAL[i%len(PAL)]),fillcolor=fills[i%len(fills)],
            hovertemplate=f"<b>{r['label']}</b><br>Note : %{{y}}/20<extra></extra>"))
    fig.add_hline(y=10,line_dash="dot",line_color="rgba(239,68,68,0.4)",line_width=1.5)
    fig.update_layout(paper_bgcolor=BG,plot_bgcolor=BG,width=w,height=h,autosize=False,showlegend=False,
        margin=dict(l=10,r=10,t=10,b=24),font=dict(family=FONT,color=GRAY,size=10),
        xaxis=dict(gridcolor=GRID,tickfont=dict(size=9,color=DARK)),
        yaxis=dict(gridcolor=GRID,range=[0,22],tickfont=dict(size=9,color=LGRAY)))
    return fig

def _fig_presence_jour(rows,w=W,h=H):
    if not rows: return _empty(w,h)
    colors=["#10B981" if r["pct"]>=85 else "#0EA5E9" if r["pct"]>=70 else "#F59E0B" for r in rows]
    fig=go.Figure(go.Bar(x=[r["jour"] for r in rows],y=[r["pct"] for r in rows],
        marker=dict(color=colors,line=dict(width=0)),
        text=[f"{r['pct']}%" for r in rows],textposition="outside",
        textfont=dict(size=10,family=POPS,color=DARK),width=0.6,
        hovertemplate="<b>%{x}</b><br>Taux de présence : %{y}%<extra></extra>"))
    fig.add_hline(y=80,line_dash="dot",line_color="rgba(14,165,233,0.4)",line_width=1.5)
    layout=_bl(w,h,mt=16,mb=24); layout["yaxis"]["range"]=[0,110]
    fig.update_layout(**layout); return fig

def _fig_evolution(series,w=W,h=H):
    if not series: return _empty(w,h)
    fig=go.Figure()
    for i,s in enumerate(series):
        fig.add_trace(go.Scatter(x=s["x"],y=s["y"],name=s["label"],mode="lines+markers",
            line=dict(color=PAL[i%len(PAL)],width=2,shape="spline"),
            marker=dict(size=5,color=PAL[i%len(PAL)],line=dict(color="#fff",width=1.5)),
            hovertemplate=f"<b>{s['label']}</b><br>Semaine : %{{x}}<br>Moyenne : %{{y}}/20<extra></extra>"))
    fig.add_hline(y=10,line_dash="dot",line_color="rgba(239,68,68,0.35)",line_width=1.5)
    layout=_bl(w,h,mr=12,mt=26,mb=28); layout["showlegend"]=True
    layout["legend"]=dict(orientation="h",y=1.12,x=0.5,xanchor="center",font=dict(size=8,family=FONT))
    layout["yaxis"]["range"]=[0,22]
    fig.update_layout(**layout); return fig


# ── Composants UI ─────────────────────────────────────────────────────────────
def _kpi(num,value,label,sub,border,bg):
    return html.Div(className="kpi-anim",style={
        "background":"#fff","borderRadius":"14px","padding":"18px 20px",
        "boxShadow":"0 2px 10px rgba(10,22,40,0.07)","borderLeft":f"4px solid {border}",
        "position":"relative","overflow":"hidden","animationDelay":f"{(num-1)*0.06}s",
    },children=[
        html.Div(f"KPI {num:02d}",style={"position":"absolute","top":"10px","right":"12px",
            "fontSize":"9px","fontWeight":"700","letterSpacing":"1px","color":border,
            "background":bg,"padding":"2px 7px","borderRadius":"99px"}),
        html.Div(value,style={"fontFamily":POPS,"fontSize":"26px","fontWeight":"800","color":DARK,
            "letterSpacing":"-0.5px","lineHeight":"1","marginBottom":"5px","marginTop":"4px"}),
        html.Div(label,style={"fontSize":"10.5px","fontWeight":"700","textTransform":"uppercase",
            "letterSpacing":"0.7px","color":GRAY,"marginBottom":"3px"}),
        html.Div(sub,style={"fontSize":"10.5px","color":border,"fontWeight":"600"}) if sub else None,
    ])

def _gchart(num, title, sub, fig, delay=0):
    w = fig.layout.width if fig.layout.width else W
    h = fig.layout.height if fig.layout.height else H
    return html.Div(className="chart-anim", style={
        "background": "#fff", "borderRadius": "14px", "padding": "14px 14px 8px",
        "boxShadow": "0 2px 10px rgba(10,22,40,0.07)",
        "animationDelay": f"{delay}s",
    }, children=[
        html.Div(style={
            "display": "flex", "justifyContent": "space-between",
            "alignItems": "flex-start", "marginBottom": "2px"
        }, children=[
            html.Div([
                html.Div(title, style={"fontFamily": POPS, "fontWeight": "700", "fontSize": "12px", "color": DARK}),
                html.Div(sub,   style={"fontSize": "10px", "color": LGRAY, "marginTop": "1px"}),
            ]),
            html.Div(f"G{num:02d}", style={
                "fontSize": "9px", "fontWeight": "700", "letterSpacing": "1px",
                "color": "#0EA5E9", "background": "#E0F2FE",
                "padding": "2px 7px", "borderRadius": "99px",
            }),
        ]),
        html.Hr(style={"border": "none", "borderTop": "1px solid #F3F4F6", "margin": "7px 0 3px"}),
        html.Div(style={"lineHeight": "0"}, children=[   # ← overflow:hidden supprimé
            dcc.Graph(
                figure=fig,
                config={"displayModeBar": False, "responsive": False},
                style={"width": f"{w}px", "height": f"{h}px", "display": "block"},  # ← width dynamique
            ),
        ]),
    ])

def _panel_card(title,badge_txt,badge_bg,badge_fg,children):
    return html.Div(style={"background":"#fff","borderRadius":"14px","padding":"18px",
        "boxShadow":"0 2px 10px rgba(10,22,40,0.07)"},children=[
        html.Div(style={"display":"flex","justifyContent":"space-between","alignItems":"center",
            "paddingBottom":"12px","marginBottom":"12px","borderBottom":"1px solid #F3F4F6"},children=[
            html.Div(title,style={"fontFamily":POPS,"fontWeight":"700","fontSize":"13.5px","color":DARK}),
            html.Div(badge_txt,style={"fontSize":"10.5px","fontWeight":"700","background":badge_bg,
                "color":badge_fg,"padding":"3px 10px","borderRadius":"99px"}) if badge_txt else html.Div(),
        ]),html.Div(children),
    ])

def _trow(rank,s,delay=0):
    lbls=["1er","2e","3e","4e","5e","6e","7e","8e"]
    lc=["#F59E0B","#9CA3AF","#CD7F32"]+["#6B7280"]*5
    gc="#10B981" if s["avg"]>=14 else "#0EA5E9" if s["avg"]>=10 else "#EF4444"
    return html.Div(className="stat-anim",style={
        "display":"flex","alignItems":"center","gap":"10px","padding":"8px 10px",
        "borderRadius":"8px","background":"#F8FAFC" if rank%2==0 else "#fff",
        "marginBottom":"3px","animationDelay":f"{delay}s"},children=[
        html.Div(lbls[rank] if rank<8 else f"{rank+1}e",style={"fontFamily":POPS,"fontWeight":"800",
            "fontSize":"10px","color":lc[min(rank,7)],"width":"24px","textAlign":"center"}),
        html.Div(s["name"],style={"flex":"1","fontWeight":"600","fontSize":"12.5px","color":DARK}),
        html.Div(style={"textAlign":"right"},children=[
            html.Div(f"{s['avg']}/20",style={"fontFamily":POPS,"fontWeight":"800","fontSize":"12.5px","color":gc}),
            html.Div(f"{s['ab']} abs.",style={"fontSize":"10px","color":LGRAY}),
        ]),
    ])

def _abs_row(rank,s,delay=0):
    clr="#EF4444" if s["pct"]>20 else "#F59E0B" if s["pct"]>10 else "#10B981"
    bg="#FFF7F7" if s["pct"]>20 else "#FFFBEB" if s["pct"]>10 else "#F0FDF4"
    return html.Div(className="stat-anim",style={
        "display":"flex","alignItems":"center","gap":"10px","padding":"8px 10px",
        "borderRadius":"8px","background":bg,"marginBottom":"4px",
        "animationDelay":f"{delay}s"},children=[
        html.Div(f"#{rank+1}",style={"fontFamily":POPS,"fontWeight":"800","fontSize":"10px",
            "color":clr,"width":"24px","textAlign":"center"}),
        html.Div(s["name"],style={"flex":"1","fontWeight":"600","fontSize":"12px","color":DARK}),
        html.Div(style={"textAlign":"right"},children=[
            html.Div(f"{s['ab']} abs.",style={"fontFamily":POPS,"fontWeight":"800","fontSize":"12px","color":clr}),
            html.Div(f"{s['pct']}% du temps",style={"fontSize":"10px","color":LGRAY}),
        ]),
    ])

def _cbar(c,delay=0):
    pct=c["pct"]
    clr="#10B981" if pct>=80 else "#0EA5E9" if pct>=50 else "#EF4444"
    return html.Div(className="stat-anim",style={"marginBottom":"12px","animationDelay":f"{delay}s"},children=[
        html.Div(style={"display":"flex","justifyContent":"space-between","alignItems":"center","marginBottom":"4px"},children=[
            html.Div(style={"display":"flex","alignItems":"center","gap":"6px"},children=[
                html.Div(style={"width":"7px","height":"7px","borderRadius":"50%","background":c["color"]}),
                html.Span(c["code"],style={"fontFamily":POPS,"fontWeight":"700","fontSize":"11.5px","color":DARK}),
                html.Span(c["label"],style={"color":LGRAY,"fontSize":"11px"}),
            ]),
            html.Span(f"{c['done']}h/{c['total']}h",style={"fontSize":"10.5px","color":LGRAY}),
        ]),
        html.Div(style={"background":"#F3F4F6","borderRadius":"99px","height":"5px","overflow":"hidden"},children=[
            html.Div(style={"width":f"{pct}%","height":"100%","borderRadius":"99px","background":clr}),
        ]),
        html.Div(f"{pct}%",style={"fontSize":"10px","color":clr,"fontWeight":"600","marginTop":"2px"}),
    ])


# ── Rendu des onglets ─────────────────────────────────────────────────────────
def _render_indicateurs(st, prog):
    _ts = str(_time.time())
    return html.Div(id=f"tab-ind-{_ts}", className="tab-content", children=[
        html.Div(style={"display":"grid","gridTemplateColumns":"repeat(5,1fr)","gap":"12px","marginBottom":"12px"},children=[
            _kpi(1,str(st["n_st"]),"Étudiants actifs",f"{st['nw']} séances/sem.","#0EA5E9","#E0F2FE"),
            _kpi(2,str(st["n_co"]),"Cours actifs","Matières en cours","#8B5CF6","#EDE9FE"),
            _kpi(3,str(st["n_se"]),"Séances totales",f"{st['nm']} ce mois","#F59E0B","#FEF3C7"),
            _kpi(4,f"{st['ar']}%","Taux d'absence","Toutes séances",
                 "#EF4444" if st["ar"]>20 else "#10B981","#FEF2F2" if st["ar"]>20 else "#ECFDF5"),
            _kpi(5,f"{st['avg']}/20","Moyenne générale",f"Réussite : {st['pr']}%",
                 "#10B981" if st["avg"]>=10 else "#EF4444","#ECFDF5" if st["avg"]>=10 else "#FEF2F2"),
        ]),
        html.Div(style={"display":"grid","gridTemplateColumns":"repeat(5,1fr)","gap":"12px","marginBottom":"20px"},children=[
            _kpi(6,f"{st['pr']}%","Taux de réussite","Notes >= 10/20","#10B981","#ECFDF5"),
            _kpi(7,f"{st['er']}%","Taux d'excellence","Notes >= 14/20","#06B6D4","#CFFAFE"),
            _kpi(8,str(st["f_g"]),"Notes insuffisantes","Notes < 10/20","#EF4444","#FEF2F2"),
            _kpi(9,f"{st['jr']}%","Absences justifiées","Sur les absences","#F59E0B","#FEF3C7"),
            _kpi(10,str(st["nw"]),"Séances cette sem.",f"{st['nm']} ce mois","#8B5CF6","#EDE9FE"),
        ]),
        html.Div(className="chart-anim",style={
            "background":"#fff","borderRadius":"14px","padding":"20px",
            "boxShadow":"0 2px 10px rgba(10,22,40,0.07)","animationDelay":"0.6s"},children=[
            html.Div("Récapitulatif général",style={"fontFamily":POPS,"fontWeight":"700","fontSize":"14px",
                "color":DARK,"marginBottom":"14px","paddingBottom":"12px","borderBottom":"1px solid #F3F4F6"}),
            html.Div(style={"display":"grid","gridTemplateColumns":"repeat(4,1fr)","gap":"12px"},children=[
                html.Div(className="kpi-anim",style={
                    "background":bg,"borderRadius":"10px","padding":"14px 16px",
                    "borderLeft":f"3px solid {clr}","animationDelay":f"{0.7+j*0.07}s"},children=[
                    html.Div(val,style={"fontFamily":POPS,"fontWeight":"800","fontSize":"20px","color":DARK}),
                    html.Div(lbl,style={"fontSize":"11px","color":GRAY,"marginTop":"3px"}),
                ]) for j,(lbl,val,clr,bg) in enumerate([
                    ("Total étudiants",str(st["n_st"]),"#0EA5E9","#F0F9FF"),
                    ("Total séances",str(st["n_se"]),"#F59E0B","#FFFBEB"),
                    ("Total notes",str(st["t_g"]),"#8B5CF6","#F5F3FF"),
                    ("Taux de réussite",f"{st['pr']}%","#10B981","#F0FDF4"),
                ])
            ]),
        ]),
    ])


def _render_visualisation(st, cid=None, cut=None):
    _ts = str(_time.time())
    ab=_absence_rows(cid,cut); av=_grade_rows(cid,cut)
    tl_d,tl_c=_timeline(cid,cut); prog=_progress(cid,cut)
    by_type=_grades_by_type(cid,cut); boxplot=_notes_par_cours(cid,cut)
    evol=_evolution_moyennes(cid,cut)
    absents=_top_absents(cid,cut); tops=_tops(cid,cut)
    scatter=[{"name":t["name"],"ab":t["ab"],"avg":t["avg"]} for t in tops]
    chart_rows=[
        [(2,"Absences par cours","Répartition du taux d'absence",_fig_donut(ab)),
         (4,"Moyenne par cours","Comparaison — seuil 10 en pointillé",_fig_bars(av)),
         (5,"Activité des séances","Séances par date (6 semaines)",_fig_line(tl_d,tl_c))],
        [(6,"Avancement des cours","% des heures réalisées",_fig_radar(prog)),
         (7,"Top des absences","Étudiants les plus absents",_fig_absents(absents)),
         (8,"Absences vs Moyenne","Corrélation présence/résultats",_fig_scatter(scatter))],
        [(9,"Notes par évaluation","Moyenne et volume par catégorie",_fig_by_type(by_type)),
         (10,"Boxplot par cours","Distribution min/max/médiane",_fig_boxplot(boxplot)),
         (12,"Évolution des moyennes","Progression au fil des semaines",_fig_evolution(evol))],
    ]
    delay=0.0; children=[]
    for row in chart_rows:
        cells=[]
        for num,title,sub,fig in row:
            cells.append(_gchart(num,title,sub,fig,delay)); delay+=0.08
        children.append(html.Div(style={"display":"grid","gridTemplateColumns":"1fr 1fr 1fr",
            "gap":"13px","marginBottom":"13px"},children=cells))
    return html.Div(id=f"tab-vis-{_ts}", className="tab-content", children=children)


def _render_classements(cid=None, cut=None):
    _ts = str(_time.time())
    tops=_tops(cid,cut); absents=_top_absents(cid,cut)
    return html.Div(id=f"tab-cls-{_ts}", className="tab-content", children=[
        html.Div(style={"display":"grid","gridTemplateColumns":"1fr 1fr","gap":"16px","marginBottom":"16px"},children=[
            _panel_card("Classement par mérite","Meilleure moyenne","#FEF9C3","#D97706",
                        [_trow(i,s,delay=i*0.06) for i,s in enumerate(tops)]),
            _panel_card("Classement par absences","Plus d'absences","#FEF2F2","#EF4444",
                        [_abs_row(i,s,delay=i*0.06) for i,s in enumerate(absents)]),
        ]),
        html.Div(className="chart-anim",style={
            "background":"#fff","borderRadius":"14px","padding":"24px",
            "boxShadow":"0 2px 10px rgba(10,22,40,0.07)","border":"1px solid #E5E7EB",
            "animationDelay":"0.5s"},children=[
            html.Div("Vue comparative",style={"fontFamily":POPS,"fontWeight":"800","fontSize":"15px",
                "color":DARK,"marginBottom":"18px"}),
            html.Div(style={"display":"grid","gridTemplateColumns":"repeat(4,1fr)","gap":"16px"},children=[
                html.Div(className="kpi-anim",style={
                    "textAlign":"center","background":"#F8FAFC","borderRadius":"12px",
                    "padding":"18px 12px","border":"1px solid #E5E7EB",
                    "animationDelay":f"{0.55+j*0.08}s"},children=[
                    html.Div(v,style={"fontFamily":POPS,"fontSize":"28px","fontWeight":"800","color":c}),
                    html.Div(l,style={"fontSize":"11px","color":GRAY,"marginTop":"4px"}),
                    html.Div(n,style={"fontSize":"11px","color":DARK,"fontWeight":"700","marginTop":"3px"}),
                ]) for j,(v,l,c,n) in enumerate([
                    (f"{tops[0]['avg']}/20" if tops else "—","Meilleure moyenne","#F59E0B",tops[0]["name"] if tops else "—"),
                    (f"{tops[-1]['avg']}/20" if tops else "—","Moyenne plancher","#0EA5E9",tops[-1]["name"] if tops else "—"),
                    (str(absents[0]["ab"]) if absents else "0","Max absences","#EF4444",absents[0]["name"] if absents else "—"),
                    (f"{round(sum(s['avg'] for s in tops)/len(tops),1)}/20" if tops else "—",
                     "Moyenne du groupe","#10B981",f"Top {len(tops)} étudiants"),
                ])
            ]),
        ]),
    ])


def _render_situation(cid=None, cut=None):
    _ts = str(_time.time())
    sess=_sessions(cid,cut); prog=_progress(cid,cut); st=_stats(cid,cut)
    return html.Div(id=f"tab-sit-{_ts}", className="tab-content", children=[
        html.Div(className="chart-anim",style={"marginBottom":"16px","animationDelay":"0s"},children=[
            _panel_card("Séances récentes",f"{st['n_se']} total","#E0F2FE","#0EA5E9",
            html.Div([
                html.Div(style={"display":"grid","gridTemplateColumns":"80px 1fr 110px 70px 80px 70px",
                    "gap":"8px","padding":"8px 10px","marginBottom":"4px",
                    "background":"#0A1628","borderRadius":"8px"},children=[
                    html.Span(h,style={"fontSize":"10px","fontWeight":"700","textTransform":"uppercase",
                        "letterSpacing":"0.8px","color":"rgba(255,255,255,0.6)"})
                    for h in ["Cours","Thème","Date","Durée","Présents","Absents"]
                ]),
                *[html.Div(className="stat-anim",style={
                    "display":"grid","gridTemplateColumns":"80px 1fr 110px 70px 80px 70px",
                    "gap":"8px","padding":"9px 10px","borderRadius":"8px","alignItems":"center",
                    "background":"#F8FAFC" if i%2==0 else "#fff",
                    "animationDelay":f"{i*0.05}s"},children=[
                    html.Div(style={"display":"flex","alignItems":"center","gap":"5px"},children=[
                        html.Div(style={"width":"8px","height":"8px","borderRadius":"50%",
                            "background":s["color"],"flexShrink":"0"}),
                        html.Span(s["course"],style={"fontFamily":POPS,"fontWeight":"700",
                            "fontSize":"11.5px","color":DARK}),
                    ]),
                    html.Span(s["theme"],style={"fontSize":"11.5px","color":GRAY,
                        "overflow":"hidden","textOverflow":"ellipsis","whiteSpace":"nowrap"}),
                    html.Span(s["date"],style={"fontSize":"11px","color":LGRAY}),
                    html.Span(f"{s.get('duration',2)}h",style={"fontSize":"11.5px","color":GRAY}),
                    html.Div(style={"display":"flex","alignItems":"center","gap":"6px"},children=[
                        html.Div(style={"flex":"1","background":"#F3F4F6","borderRadius":"99px","height":"4px"},children=[
                            html.Div(style={"width":f"{round((s['total']-s['absent'])/s['total']*100) if s['total'] else 100}%",
                                "height":"100%","borderRadius":"99px","background":"#10B981"}),
                        ]),
                        html.Span(str(s["total"]-s["absent"]),style={"fontSize":"11px",
                            "fontWeight":"700","color":"#10B981","flexShrink":"0"}),
                    ]),
                    html.Span(str(s["absent"]) if s["absent"]>0 else "—",
                              style={"fontSize":"11px","fontWeight":"700",
                                     "color":"#EF4444" if s["absent"]>0 else LGRAY}),
                ]) for i,s in enumerate(sess)],
            ])),
        ]),
        html.Div(style={"display":"grid","gridTemplateColumns":"1.2fr 1fr","gap":"16px"},children=[
            html.Div(className="chart-anim",style={"animationDelay":"0.1s"},children=[
                _panel_card("Avancement des cours",f"{len(prog)} cours","#EDE9FE","#8B5CF6",
                            html.Div([_cbar(c,delay=i*0.06) for i,c in enumerate(prog)])),
            ]),
            html.Div(style={"display":"flex","flexDirection":"column","gap":"10px"},children=[
                html.Div(className="stat-anim",style={
                    "background":"#fff","borderRadius":"12px","padding":"14px 18px",
                    "boxShadow":"0 2px 10px rgba(10,22,40,0.07)","display":"flex",
                    "alignItems":"center","gap":"14px","borderLeft":f"4px solid {clr}",
                    "animationDelay":f"{0.15+i*0.1}s"},children=[
                    html.Div([
                        html.Div(val,style={"fontFamily":POPS,"fontWeight":"800","fontSize":"20px",
                            "color":DARK,"lineHeight":"1"}),
                        html.Div(lbl,style={"fontSize":"11px","color":GRAY,"marginTop":"2px"}),
                    ]),
                    html.Div(sub,style={"marginLeft":"auto","fontSize":"11px","fontWeight":"700",
                        "color":clr,"background":sbg,"padding":"3px 10px","borderRadius":"99px"}),
                ]) for i,(val,lbl,sub,clr,sbg) in enumerate([
                    (str(st["nw"]),      "Séances cette semaine", f"{st['nm']} ce mois",    "#0EA5E9","#E0F2FE"),
                    (f"{st['pr']}%",     "Taux de réussite",      "Notes >= 10",             "#10B981","#ECFDF5"),
                    (f"{st['ar']}%",     "Taux d'absence",        "Toutes séances",          "#F59E0B","#FEF3C7"),
                    (f"{st['avg']}/20",  "Moyenne générale",      f"{st['er']}% excellent",  "#8B5CF6","#EDE9FE"),
                    (f"{st['jr']}%",     "Absences justifiées",   f"{st['f_g']} notes < 10", "#EF4444","#FEF2F2"),
                ])
            ]),
        ]),
    ])


# ── Boutons onglets ───────────────────────────────────────────────────────────
def _btn_styles(active_tab):
    styles = []
    for key,_,__ in TABS:
        is_active = active_tab == key
        styles.append({
            "padding":"9px 22px","borderRadius":"9px","border":"none",
            "cursor":"pointer","fontFamily":POPS,"fontWeight":"700",
            "fontSize":"12.5px","lineHeight":"1.3","whiteSpace":"nowrap",
            "transition":"all 0.2s ease",
            "background":"#0EA5E9" if is_active else "transparent",
            "color":"#fff" if is_active else GRAY,
            "boxShadow":"0 4px 12px rgba(14,165,233,0.3)" if is_active else "none",
        })
    return styles


# ── Layout ────────────────────────────────────────────────────────────────────
def layout(user=None):
    st   = _stats()
    prog = _progress()
    return html.Div(id="app-shell", children=[
        sidebar("/", user),
        html.Div(id="main-content", children=[
            topbar("Tableau de Bord",""),
            html.Div(id="page-content", children=[

                html.Div(style={
                    "display":"flex","alignItems":"center","justifyContent":"space-between",
                    "marginBottom":"18px","paddingBottom":"16px",
                    "borderBottom":"2px solid #F3F4F6","gap":"12px",
                },children=[
                    html.Div([
                        html.Div("Tableau de bord",style={"fontFamily":POPS,"fontSize":"21px",
                            "fontWeight":"800","color":DARK,"letterSpacing":"-0.3px","marginBottom":"2px"}),
                        html.Div(f"Mise à jour : {date.today().strftime('%d %B %Y')}",
                                 style={"fontSize":"11px","color":LGRAY}),
                    ],style={"flexShrink":"0"}),

                    html.Div(style={
                        "display":"flex","gap":"5px",
                        "background":"#F3F4F6","borderRadius":"12px","padding":"5px",
                    },children=[
                        html.Button(id=f"btn-{key}",n_clicks=0,
                            children=[
                                html.Div(lbl,style={"fontWeight":"700","fontSize":"12.5px"}),
                                html.Div(hint,style={"fontSize":"9px","opacity":"0.75","marginTop":"1px"}),
                            ],
                            style={
                                "padding":"9px 22px","borderRadius":"9px","border":"none",
                                "cursor":"pointer","fontFamily":POPS,"fontWeight":"700",
                                "fontSize":"12.5px","lineHeight":"1.3","whiteSpace":"nowrap",
                                "background":"#0EA5E9" if key=="indicateurs" else "transparent",
                                "color":"#fff" if key=="indicateurs" else GRAY,
                                "boxShadow":"0 4px 12px rgba(14,165,233,0.3)" if key=="indicateurs" else "none",
                                "transition":"all 0.2s ease",
                            }
                        ) for key,lbl,hint in TABS
                    ]),

                    html.Div("10 KPIs · 9 Graphiques",style={
                        "background":"#F0F9FF","borderRadius":"8px","padding":"7px 14px",
                        "fontSize":"11px","color":"#0EA5E9","fontWeight":"700",
                        "fontFamily":POPS,"border":"1px solid rgba(14,165,233,0.2)",
                        "whiteSpace":"nowrap","flexShrink":"0",
                    }),
                ]),

                html.Div(style={
                    "background":"#fff","borderRadius":"12px","padding":"12px 20px",
                    "boxShadow":"0 2px 10px rgba(10,22,40,0.07)","marginBottom":"16px",
                    "display":"flex","alignItems":"center","gap":"16px","flexWrap":"wrap",
                },children=[
                    html.Div("Filtres",style={"fontFamily":POPS,"fontWeight":"700","fontSize":"12.5px","color":DARK}),
                    html.Div(style={"width":"1px","height":"22px","background":"#E5E7EB"}),
                    html.Div(style={"display":"flex","alignItems":"center","gap":"7px"},children=[
                        html.Label("Cours",style={"fontSize":"10px","fontWeight":"700","color":GRAY,
                            "textTransform":"uppercase","letterSpacing":"0.8px","whiteSpace":"nowrap"}),
                        dcc.Dropdown(id="f-course",options=_opts(),value="all",clearable=False,
                                     style={"width":"190px","fontSize":"12px"}),
                    ]),
                    html.Div(style={"display":"flex","alignItems":"center","gap":"7px"},children=[
                        html.Label("Période",style={"fontSize":"10px","fontWeight":"700","color":GRAY,
                            "textTransform":"uppercase","letterSpacing":"0.8px","whiteSpace":"nowrap"}),
                        dcc.Dropdown(id="f-period",
                                     options=[{"label":"Toute la période","value":"0"},
                                              {"label":"7 derniers jours","value":"7"},
                                              {"label":"30 derniers jours","value":"30"},
                                              {"label":"90 derniers jours","value":"90"}],
                                     value="0",clearable=False,
                                     style={"width":"170px","fontSize":"12px"}),
                    ]),
                    html.Button("Réinitialiser",id="f-reset",n_clicks=0,style={
                        "marginLeft":"auto","background":"transparent","border":"1px solid #D1D5DB",
                        "borderRadius":"8px","padding":"6px 14px","fontSize":"11.5px","fontWeight":"700",
                        "color":GRAY,"cursor":"pointer","fontFamily":POPS,
                    }),
                ]),

                dcc.Store(id="active-tab-store", data="indicateurs"),
                html.Div(id="dash-tab-content", children=[_render_indicateurs(st, prog)]),
            ]),
        ]),
    ])


# ── Callbacks ─────────────────────────────────────────────────────────────────
def register_callbacks(app):

    @app.callback(
        Output("btn-indicateurs",   "style"),
        Output("btn-visualisation", "style"),
        Output("btn-classements",   "style"),
        Output("btn-situation",     "style"),
        Output("dash-tab-content",  "children"),
        Output("active-tab-store",  "data"),
        Input("btn-indicateurs",   "n_clicks"),
        Input("btn-visualisation", "n_clicks"),
        Input("btn-classements",   "n_clicks"),
        Input("btn-situation",     "n_clicks"),
        Input("f-course",          "value"),
        Input("f-period",          "value"),
        State("active-tab-store",  "data"),
        prevent_initial_call=True,
    )
    def handle_tab(n1, n2, n3, n4, course_id, period, current_tab):
        triggered = ctx.triggered_id or "btn-indicateurs"

        # Filtres → garder l'onglet actif courant
        if triggered in ("f-course", "f-period"):
            tab = current_tab or "indicateurs"
        else:
            tab = triggered.replace("btn-", "")

        cid, cut = _parse_filters(course_id, period)
        styles   = _btn_styles(tab)
        st       = _stats(cid, cut)
        prog     = _progress(cid, cut)

        if tab == "indicateurs":
            content = _render_indicateurs(st, prog)
        elif tab == "visualisation":
            content = _render_visualisation(st, cid, cut)
        elif tab == "classements":
            content = _render_classements(cid, cut)
        else:
            content = _render_situation(cid, cut)

        return styles[0], styles[1], styles[2], styles[3], content, tab

    @app.callback(
        Output("f-course","value"),
        Output("f-period","value"),
        Input("f-reset","n_clicks"),
        prevent_initial_call=True,
    )
    def reset(n):
        return "all","0"