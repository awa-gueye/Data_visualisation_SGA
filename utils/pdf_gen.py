"""
utils/pdf_gen.py – Génération de bulletins PDF avec ReportLab (design premium)
"""
import io
import os
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from config import PDF_OUTPUT_DIR, COLORS

os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

# ── Palette de couleurs professionnelle ─────────────────────────────────────
C_NAVY       = colors.HexColor("#1B2A4A")   # Bleu marine profond (headers)
C_BLUE       = colors.HexColor("#2563EB")   # Bleu vif (accents principaux)
C_BLUE_LIGHT = colors.HexColor("#DBEAFE")   # Bleu très clair (fond lignes)
C_TEAL       = colors.HexColor("#0D9488")   # Teal (succès / positif)
C_TEAL_LIGHT = colors.HexColor("#CCFBF1")   # Teal clair
C_RED        = colors.HexColor("#DC2626")   # Rouge (échec / alerte)
C_RED_LIGHT  = colors.HexColor("#FEE2E2")   # Rouge très clair
C_AMBER      = colors.HexColor("#D97706")   # Ambre (avertissement)
C_AMBER_LIGHT= colors.HexColor("#FEF3C7")   # Ambre clair
C_GRAY_100   = colors.HexColor("#F1F5F9")   # Gris très clair (fond alterné)
C_GRAY_200   = colors.HexColor("#E2E8F0")   # Gris clair (bordures)
C_GRAY_600   = colors.HexColor("#475569")   # Gris moyen (texte secondaire)
C_GRAY_800   = colors.HexColor("#1E293B")   # Gris foncé (texte principal)
C_WHITE      = colors.HexColor("#FFFFFF")   # Blanc pur
C_GOLD       = colors.HexColor("#F59E0B")   # Or (mention honorifique)


# ── Styles de texte ──────────────────────────────────────────────────────────
def _make_styles():
    s = {}
    s["title"] = ParagraphStyle(
        "title", fontSize=20, fontName="Helvetica-Bold",
        textColor=C_WHITE, alignment=TA_CENTER, leading=26,
    )
    s["subtitle"] = ParagraphStyle(
        "subtitle", fontSize=9, fontName="Helvetica",
        textColor=colors.HexColor("#93C5FD"), alignment=TA_CENTER, leading=14,
    )
    s["section"] = ParagraphStyle(
        "section", fontSize=11, fontName="Helvetica-Bold",
        textColor=C_NAVY, spaceAfter=4, leading=16,
    )
    s["bold"] = ParagraphStyle(
        "bold", fontSize=9.5, fontName="Helvetica-Bold", textColor=C_GRAY_800, leading=14,
    )
    s["body"] = ParagraphStyle(
        "body", fontSize=9.5, fontName="Helvetica", textColor=C_GRAY_800, leading=14,
    )
    s["muted"] = ParagraphStyle(
        "muted", fontSize=8, fontName="Helvetica", textColor=C_GRAY_600, leading=12,
    )
    s["footer"] = ParagraphStyle(
        "footer", fontSize=7.5, fontName="Helvetica",
        textColor=C_GRAY_600, alignment=TA_CENTER, leading=11,
    )
    s["label"] = ParagraphStyle(
        "label", fontSize=8, fontName="Helvetica-Bold",
        textColor=C_GRAY_600, leading=12, spaceAfter=1,
    )
    return s


def generate_student_report(student, grades, attendances, courses) -> bytes:
    """Génère un bulletin de notes complet en PDF – design premium."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.8*cm, leftMargin=1.8*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )
    S = _make_styles()
    story = []

    # ── En-tête avec fond dégradé simulé ────────────────────────────────────
    header_data = [[
        Paragraph("🎓  Bulletin de Notes", S["title"]),
        Paragraph(f"Année {date.today().year}", S["subtitle"]),
    ]]
    header_table = Table(header_data, colWidths=[18*cm])
    # Flatten to single cell
    header_data = [[
        Table([
            [Paragraph("🎓  Bulletin de Notes", S["title"])],
            [Paragraph("Système de Gestion Académique – Établissement de Formation", S["subtitle"])],
        ], colWidths=[18*cm])
    ]]
    header_table = Table(header_data, colWidths=[18*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 18),
        ("BOTTOMPADDING", (0,0), (-1,-1), 18),
        ("LEFTPADDING",   (0,0), (-1,-1), 20),
        ("RIGHTPADDING",  (0,0), (-1,-1), 20),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5*cm))

    # Bandeau bleu accent
    story.append(HRFlowable(width="100%", thickness=3, color=C_BLUE, spaceAfter=12))

    # ── Carte infos étudiant ─────────────────────────────────────────────────
    story.append(Paragraph("Informations de l'étudiant", S["section"]))

    student_rows = [
        [
            Paragraph("Nom complet",     S["label"]), Paragraph(student.full_name,    S["bold"]),
            Paragraph("Code étudiant",   S["label"]), Paragraph(student.student_code, S["bold"]),
        ],
        [
            Paragraph("Email",           S["label"]), Paragraph(student.email,         S["body"]),
            Paragraph("Date naissance",  S["label"]), Paragraph(str(student.birth_date) if student.birth_date else "–", S["body"]),
        ],
        [
            Paragraph("Date du bulletin",S["label"]), Paragraph(date.today().strftime("%d/%m/%Y"), S["bold"]),
            Paragraph("Statut",          S["label"]), Paragraph(
                "✅  Actif" if student.is_active else "❌  Inactif", S["body"]
            ),
        ],
    ]

    info_table = Table(student_rows, colWidths=[3.2*cm, 5.8*cm, 3.2*cm, 5.8*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_GRAY_100),
        ("BACKGROUND",    (0,0), (0,-1), C_BLUE_LIGHT),
        ("BACKGROUND",    (2,0), (2,-1), C_BLUE_LIGHT),
        ("GRID",          (0,0), (-1,-1), 0.5, C_GRAY_200),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ROUNDEDCORNERS",[4]),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.6*cm))

    # ── Tableau des notes ─────────────────────────────────────────────────────
    story.append(Paragraph("Résultats académiques", S["section"]))

    grade_header = [
        Paragraph("Code",          S["bold"]),
        Paragraph("Matière",       S["bold"]),
        Paragraph("Enseignant",    S["bold"]),
        Paragraph("Note /20",      S["bold"]),
        Paragraph("Coeff.",        S["bold"]),
        Paragraph("Pondérée",      S["bold"]),
    ]
    grade_rows = [grade_header]

    course_map = {c.id: c for c in courses}
    course_grades = {}
    for g in grades:
        course_grades.setdefault(g.course_id, []).append(g)

    total_weight = 0
    total_score  = 0
    row_colors   = []  # pour style alterné

    for i, (cid, g_list) in enumerate(course_grades.items()):
        course = course_map.get(cid)
        if not course:
            continue
        w_sum = sum(g.score * g.coefficient for g in g_list)
        c_sum = sum(g.coefficient          for g in g_list)
        avg   = round(w_sum / c_sum, 2)    if c_sum else 0
        total_weight += c_sum
        total_score  += w_sum

        # Couleur note
        if avg >= 14:
            note_style = ParagraphStyle("ns", fontSize=10, fontName="Helvetica-Bold", textColor=C_TEAL)
            bg = C_TEAL_LIGHT if avg >= 14 else C_WHITE
        elif avg >= 10:
            note_style = ParagraphStyle("ns", fontSize=10, fontName="Helvetica-Bold", textColor=C_BLUE)
            bg = C_WHITE
        else:
            note_style = ParagraphStyle("ns", fontSize=10, fontName="Helvetica-Bold", textColor=C_RED)
            bg = C_RED_LIGHT

        row_colors.append((i + 1, bg))

        row = [
            Paragraph(course.code,                S["body"]),
            Paragraph(course.label,               S["body"]),
            Paragraph(course.teacher or "–",      S["body"]),
            Paragraph(f"{avg}/20",                note_style),
            Paragraph(str(round(c_sum, 1)),        S["body"]),
            Paragraph(str(round(w_sum, 2)),        S["body"]),
        ]
        grade_rows.append(row)

    # Ligne récapitulatif
    overall = round(total_score / total_weight, 2) if total_weight else 0
    mention = _get_mention(overall)
    mention_color = C_GOLD if overall >= 14 else (C_TEAL if overall >= 10 else C_RED)
    grade_rows.append([
        Paragraph("", S["body"]),
        Paragraph("", S["body"]),
        Paragraph("MOYENNE GÉNÉRALE", ParagraphStyle("mg", fontSize=10, fontName="Helvetica-Bold", textColor=C_WHITE)),
        Paragraph(f"{overall}/20",    ParagraphStyle("mo", fontSize=11, fontName="Helvetica-Bold", textColor=C_WHITE)),
        Paragraph(str(round(total_weight, 1)), ParagraphStyle("mw", fontSize=9.5, fontName="Helvetica-Bold", textColor=C_WHITE)),
        Paragraph(mention,            ParagraphStyle("mn", fontSize=10, fontName="Helvetica-Bold", textColor=C_GOLD)),
    ])

    grade_table = Table(grade_rows, colWidths=[2.2*cm, 5.0*cm, 3.5*cm, 2.5*cm, 2.2*cm, 2.6*cm])

    ts = TableStyle([
        # Header
        ("BACKGROUND",    (0,0),  (-1,0),  C_NAVY),
        ("TEXTCOLOR",     (0,0),  (-1,0),  C_WHITE),
        # Footer total
        ("BACKGROUND",    (0,-1), (-1,-1), C_BLUE),
        # Grille
        ("GRID",          (0,0),  (-1,-1), 0.4, C_GRAY_200),
        ("LINEABOVE",     (0,-1), (-1,-1), 1.5, C_NAVY),
        # Padding
        ("TOPPADDING",    (0,0),  (-1,-1), 8),
        ("BOTTOMPADDING", (0,0),  (-1,-1), 8),
        ("LEFTPADDING",   (0,0),  (-1,-1), 9),
        ("RIGHTPADDING",  (0,0),  (-1,-1), 9),
        ("ALIGN",         (3,0),  (5,-1),  "CENTER"),
        ("VALIGN",        (0,0),  (-1,-1), "MIDDLE"),
    ])
    # Lignes alternées
    for idx, (row_i, bg) in enumerate(row_colors):
        if bg != C_WHITE:
            ts.add("BACKGROUND", (0, row_i), (-1, row_i), bg)
        elif row_i % 2 == 0:
            ts.add("BACKGROUND", (0, row_i), (-1, row_i), C_GRAY_100)

    grade_table.setStyle(ts)
    story.append(grade_table)
    story.append(Spacer(1, 0.6*cm))

    # ── Résumé visuel de la mention ──────────────────────────────────────────
    mention_bg = C_TEAL_LIGHT if overall >= 10 else C_RED_LIGHT
    mention_border = C_TEAL if overall >= 10 else C_RED
    score_label = f"Note globale : {overall}/20"
    mention_row = [[
        Table([
            [Paragraph("📊  " + score_label, ParagraphStyle("sl", fontSize=11, fontName="Helvetica-Bold", textColor=C_GRAY_800))],
            [Paragraph(f"Mention : {mention}", ParagraphStyle("ml", fontSize=12, fontName="Helvetica-Bold", textColor=mention_border))],
        ], colWidths=[16*cm]),
    ]]
    mention_table = Table(mention_row, colWidths=[18*cm])
    mention_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), mention_bg),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
        ("LINERIGHT",     (0,0), (0,-1),  3, mention_border),
    ]))
    story.append(mention_table)
    story.append(Spacer(1, 0.6*cm))

    # ── Présences ─────────────────────────────────────────────────────────────
    story.append(Paragraph("Suivi des présences", S["section"]))

    total_sessions = len(attendances)
    total_absences = sum(1 for a in attendances if a.is_absent)
    justified      = sum(1 for a in attendances if a.is_absent and a.justified)
    present        = total_sessions - total_absences
    abs_rate       = round(total_absences / total_sessions * 100, 1) if total_sessions else 0
    pres_rate      = round(100 - abs_rate, 1)

    abs_color = C_TEAL if abs_rate < 15 else (C_AMBER if abs_rate < 30 else C_RED)

    abs_data = [
        # Header
        [
            Paragraph("Séances totales", S["label"]),
            Paragraph("Présences",       S["label"]),
            Paragraph("Absences",        S["label"]),
            Paragraph("Justifiées",      S["label"]),
            Paragraph("Taux présence",   S["label"]),
        ],
        [
            Paragraph(str(total_sessions), S["bold"]),
            Paragraph(str(present),         ParagraphStyle("prs", fontSize=11, fontName="Helvetica-Bold", textColor=C_TEAL)),
            Paragraph(str(total_absences),  ParagraphStyle("abs", fontSize=11, fontName="Helvetica-Bold", textColor=abs_color)),
            Paragraph(str(justified),       S["bold"]),
            Paragraph(f"{pres_rate}%",      ParagraphStyle("pr", fontSize=11, fontName="Helvetica-Bold", textColor=abs_color)),
        ],
    ]
    abs_table = Table(abs_data, colWidths=[3.6*cm]*5)
    abs_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_GRAY_100),
        ("BACKGROUND",    (0,1), (-1,1),  C_WHITE),
        ("GRID",          (0,0), (-1,-1), 0.4, C_GRAY_200),
        ("LINEBELOW",     (0,0), (-1,0),  1, C_GRAY_200),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(abs_table)
    story.append(Spacer(1, 0.8*cm))

    # ── Pied de page ──────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.8, color=C_GRAY_200))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Document généré le {date.today().strftime('%d/%m/%Y')} "
        f"par le Système de Gestion Académique  ·  Confidentiel  ·  Ne pas diffuser",
        S["footer"]
    ))

    doc.build(story)
    return buffer.getvalue()


def _get_mention(avg: float) -> str:
    if avg >= 16: return "Très Bien"
    if avg >= 14: return "Bien"
    if avg >= 12: return "Assez Bien"
    if avg >= 10: return "Passable"
    return "Insuffisant"


def generate_attendance_report(course, sessions_data) -> bytes:
    """Génère un rapport de présence pour un cours – design premium."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.8*cm, leftMargin=1.8*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )
    S = _make_styles()
    story = []

    # ── En-tête ──────────────────────────────────────────────────────────────
    header_inner = Table([
        [Paragraph(f"📋  Rapport de Présences", S["title"])],
        [Paragraph(f"{course.code}  ·  {course.label}", S["subtitle"])],
    ], colWidths=[18*cm])
    header_table = Table([[header_inner]], colWidths=[18*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 16),
        ("BOTTOMPADDING", (0,0), (-1,-1), 16),
        ("LEFTPADDING",   (0,0), (-1,-1), 20),
        ("RIGHTPADDING",  (0,0), (-1,-1), 20),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=3, color=C_BLUE, spaceAfter=10))

    for sess_info in sessions_data:
        sess = sess_info["session"]
        atts = sess_info["attendances"]

        # Titre séance
        pres_count = sum(1 for a in atts if not a.is_absent)
        abs_count  = len(atts) - pres_count
        session_title = Table([[
            Paragraph(
                f"📅  Séance du {sess.date.strftime('%d/%m/%Y')}  –  {sess.theme or 'Sans thème'}",
                ParagraphStyle("st", fontSize=10, fontName="Helvetica-Bold", textColor=C_NAVY)
            ),
            Paragraph(
                f"✅ {pres_count} présents  ·  ❌ {abs_count} absents",
                ParagraphStyle("sc", fontSize=9, fontName="Helvetica", textColor=C_GRAY_600, alignment=TA_RIGHT)
            ),
        ]], colWidths=[10*cm, 8*cm])
        session_title.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), C_BLUE_LIGHT),
            ("TOPPADDING",    (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("RIGHTPADDING",  (0,0), (-1,-1), 10),
            ("LINEBELOW",     (0,0), (-1,-1), 1.5, C_BLUE),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(session_title)

        rows = [[
            Paragraph("Étudiant",  S["bold"]),
            Paragraph("Statut",    S["bold"]),
            Paragraph("Justifié",  S["bold"]),
        ]]
        for i, att in enumerate(atts):
            absent = att.is_absent
            status_style = ParagraphStyle(
                "ss", fontSize=9.5, fontName="Helvetica-Bold",
                textColor=C_RED if absent else C_TEAL
            )
            row_bg = C_RED_LIGHT if absent else C_WHITE
            rows.append([
                Paragraph(att.student.full_name if att.student else "–", S["body"]),
                Paragraph("Absent" if absent else "Présent", status_style),
                Paragraph("✓ Oui" if att.justified else "–", S["body"]),
            ])

        t = Table(rows, colWidths=[9*cm, 5*cm, 4*cm])
        ts2 = TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), C_NAVY),
            ("TEXTCOLOR",     (0,0), (-1,0), C_WHITE),
            ("GRID",          (0,0), (-1,-1), 0.4, C_GRAY_200),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("RIGHTPADDING",  (0,0), (-1,-1), 8),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ])
        for i, att in enumerate(atts):
            if att.is_absent:
                ts2.add("BACKGROUND", (0, i+1), (-1, i+1), C_RED_LIGHT)
            elif (i+1) % 2 == 0:
                ts2.add("BACKGROUND", (0, i+1), (-1, i+1), C_GRAY_100)
        t.setStyle(ts2)
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    # Pied de page
    story.append(HRFlowable(width="100%", thickness=0.8, color=C_GRAY_200))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Document généré le {date.today().strftime('%d/%m/%Y')} "
        f"par le Système de Gestion Académique  ·  Confidentiel",
        S["footer"]
    ))

    doc.build(story)
    return buffer.getvalue()