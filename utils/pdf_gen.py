"""
utils/pdf_gen.py – Génération de bulletins PDF avec ReportLab
"""
import io
import os
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from config import PDF_OUTPUT_DIR, COLORS

os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

# Couleurs ReportLab
PRIMARY  = colors.HexColor("#6C63FF")
DARK     = colors.HexColor("#0F0E17")
SURFACE  = colors.HexColor("#1A1A2E")
ACCENT   = colors.HexColor("#43E97B")
DANGER   = colors.HexColor("#FF4757")
WARNING  = colors.HexColor("#F7B731")
LIGHT    = colors.HexColor("#FFFFFE")
MUTED    = colors.HexColor("#A7A9BE")


def generate_student_report(student, grades, attendances, courses) -> bytes:
    """
    Génère un bulletin de notes complet en PDF.
    Retourne les bytes du fichier PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
    )

    styles = getSampleStyleSheet()
    story  = []

    # ── En-tête ──────────────────────────────────────────────────────────────
    header_style = ParagraphStyle(
        "Header",
        fontSize=22,
        fontName="Helvetica-Bold",
        textColor=LIGHT,
        backColor=DARK,
        alignment=TA_CENTER,
        spaceAfter=0,
        spaceBefore=0,
        leading=28,
        borderPad=12,
    )
    sub_style = ParagraphStyle(
        "Sub",
        fontSize=10,
        fontName="Helvetica",
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceAfter=0,
    )

    # Header table
    header_data = [[Paragraph("🎓 Bulletin de Notes", header_style)]]
    header_table = Table(header_data, colWidths=[18*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3*cm))

    # Sous-titre établissement
    story.append(Paragraph("Système de Gestion Académique – Établissement de Formation", sub_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY))
    story.append(Spacer(1, 0.4*cm))

    # ── Infos étudiant ────────────────────────────────────────────────────────
    info_style = ParagraphStyle("Info", fontSize=10, fontName="Helvetica", textColor=DARK)
    bold_style = ParagraphStyle("Bold", fontSize=10, fontName="Helvetica-Bold", textColor=DARK)

    student_info = [
        [Paragraph("<b>Nom complet :</b>",    bold_style), Paragraph(student.full_name,          info_style),
         Paragraph("<b>Code étudiant :</b>",  bold_style), Paragraph(student.student_code,        info_style)],
        [Paragraph("<b>Email :</b>",          bold_style), Paragraph(student.email,               info_style),
         Paragraph("<b>Date de naissance :</b>", bold_style), Paragraph(str(student.birth_date) if student.birth_date else "–", info_style)],
        [Paragraph("<b>Date du bulletin :</b>", bold_style), Paragraph(date.today().strftime("%d/%m/%Y"), info_style),
         Paragraph("<b>Statut :</b>",         bold_style), Paragraph("Actif" if student.is_active else "Inactif", info_style)],
    ]
    info_table = Table(student_info, colWidths=[4*cm, 5*cm, 4*cm, 5*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F5F5FF")),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#E0E0FF")),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.6*cm))

    # ── Tableau des notes ─────────────────────────────────────────────────────
    story.append(Paragraph(
        "<b>Résultats académiques</b>",
        ParagraphStyle("Section", fontSize=13, fontName="Helvetica-Bold",
                       textColor=PRIMARY, spaceAfter=6)
    ))
    story.append(Spacer(1, 0.2*cm))

    # Agréger par cours
    course_map = {c.id: c for c in courses}
    course_grades = {}
    for g in grades:
        cid = g.course_id
        if cid not in course_grades:
            course_grades[cid] = []
        course_grades[cid].append(g)

    grade_header = [
        Paragraph("<b>Code</b>",      bold_style),
        Paragraph("<b>Matière</b>",   bold_style),
        Paragraph("<b>Enseignant</b>",bold_style),
        Paragraph("<b>Note /20</b>",  bold_style),
        Paragraph("<b>Coefficient</b>",bold_style),
        Paragraph("<b>Note pondérée</b>", bold_style),
    ]
    grade_rows = [grade_header]

    total_weight = 0
    total_score  = 0

    for cid, g_list in course_grades.items():
        course = course_map.get(cid)
        if not course:
            continue
        # Moyenne du cours (pondérée par coefficient)
        w_sum = sum(g.score * g.coefficient for g in g_list)
        c_sum = sum(g.coefficient for g in g_list)
        avg   = round(w_sum / c_sum, 2) if c_sum else 0

        total_weight += c_sum
        total_score  += w_sum

        color_score = ACCENT if avg >= 10 else DANGER
        row = [
            Paragraph(course.code,    info_style),
            Paragraph(course.label,   info_style),
            Paragraph(course.teacher or "–", info_style),
            Paragraph(f"<b>{avg}/20</b>", ParagraphStyle("S", fontSize=10, fontName="Helvetica-Bold", textColor=color_score)),
            Paragraph(str(round(c_sum,1)), info_style),
            Paragraph(f"{round(w_sum,2)}", info_style),
        ]
        grade_rows.append(row)

    # Ligne moyenne générale
    overall = round(total_score / total_weight, 2) if total_weight else 0
    mention = _get_mention(overall)
    grade_rows.append([
        Paragraph("", info_style),
        Paragraph("", info_style),
        Paragraph("<b>MOYENNE GÉNÉRALE</b>", bold_style),
        Paragraph(f"<b>{overall}/20</b>",
                  ParagraphStyle("Avg", fontSize=11, fontName="Helvetica-Bold",
                                 textColor=ACCENT if overall >= 10 else DANGER)),
        Paragraph(f"<b>{round(total_weight,1)}</b>", bold_style),
        Paragraph(f"<b>{mention}</b>",
                  ParagraphStyle("Men", fontSize=10, fontName="Helvetica-Bold",
                                 textColor=PRIMARY)),
    ])

    grade_table = Table(grade_rows, colWidths=[2.5*cm, 4.5*cm, 3.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
    grade_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0),  PRIMARY),
        ("TEXTCOLOR",   (0,0), (-1,0),  LIGHT),
        ("BACKGROUND",  (0,-1),(-1,-1), colors.HexColor("#1A1A2E")),
        ("TEXTCOLOR",   (0,-1),(-1,-1), LIGHT),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#F8F8FF")]),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#E0E0FF")),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("ALIGN",       (3,0), (5,-1), "CENTER"),
    ]))
    story.append(grade_table)
    story.append(Spacer(1, 0.6*cm))

    # ── Absences ─────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "<b>Suivi des présences</b>",
        ParagraphStyle("Section2", fontSize=13, fontName="Helvetica-Bold",
                       textColor=PRIMARY, spaceAfter=6)
    ))
    story.append(Spacer(1, 0.2*cm))

    total_sessions = len(attendances)
    total_absences = sum(1 for a in attendances if a.is_absent)
    justified      = sum(1 for a in attendances if a.is_absent and a.justified)
    abs_rate       = round(total_absences / total_sessions * 100, 1) if total_sessions else 0

    abs_data = [
        [Paragraph("<b>Total séances</b>", bold_style),   Paragraph(str(total_sessions), info_style),
         Paragraph("<b>Absences</b>",      bold_style),   Paragraph(str(total_absences), info_style)],
        [Paragraph("<b>Justifiées</b>",    bold_style),   Paragraph(str(justified),      info_style),
         Paragraph("<b>Taux d\'absence</b>", bold_style), Paragraph(f"{abs_rate}%",      info_style)],
    ]
    abs_table = Table(abs_data, colWidths=[4*cm, 5*cm, 4*cm, 5*cm])
    abs_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F5F5FF")),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#E0E0FF")),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(abs_table)
    story.append(Spacer(1, 0.8*cm))

    # ── Pied de page ──────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=MUTED))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Document généré le {date.today().strftime('%d/%m/%Y')} par le Système de Gestion Académique · Confidentiel",
        ParagraphStyle("Footer", fontSize=8, textColor=MUTED, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buffer.getvalue()


def _get_mention(avg: float) -> str:
    if avg >= 16:  return "Très Bien"
    if avg >= 14:  return "Bien"
    if avg >= 12:  return "Assez Bien"
    if avg >= 10:  return "Passable"
    return "Insuffisant"


def generate_attendance_report(course, sessions_data) -> bytes:
    """Génère un rapport de présence pour un cours."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story  = []

    bold_style = ParagraphStyle("Bold", fontSize=10, fontName="Helvetica-Bold", textColor=DARK)
    info_style = ParagraphStyle("Info", fontSize=10, fontName="Helvetica",      textColor=DARK)

    story.append(Paragraph(
        f"Rapport de Présences – {course.code} · {course.label}",
        ParagraphStyle("Title", fontSize=16, fontName="Helvetica-Bold",
                       textColor=PRIMARY, spaceAfter=6)
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY))
    story.append(Spacer(1, 0.4*cm))

    for sess_info in sessions_data:
        sess   = sess_info["session"]
        atts   = sess_info["attendances"]
        story.append(Paragraph(
            f"<b>Séance du {sess.date.strftime('%d/%m/%Y')}</b> – {sess.theme or 'Sans thème'}",
            bold_style
        ))
        rows = [[
            Paragraph("<b>Étudiant</b>", bold_style),
            Paragraph("<b>Statut</b>",   bold_style),
            Paragraph("<b>Justifié</b>", bold_style),
        ]]
        for att in atts:
            status = "Absent" if att.is_absent else "Présent"
            color  = DANGER if att.is_absent else ACCENT
            rows.append([
                Paragraph(att.student.full_name if att.student else "–", info_style),
                Paragraph(f"<font color='#{color.hexval()[1:]}'><b>{status}</b></font>", info_style),
                Paragraph("Oui" if att.justified else "–", info_style),
            ])
        t = Table(rows, colWidths=[8*cm, 5*cm, 5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0,0), (-1,0), PRIMARY),
            ("TEXTCOLOR",      (0,0), (-1,0), LIGHT),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8F8FF")]),
            ("GRID",           (0,0), (-1,-1), 0.5, colors.HexColor("#E0E0FF")),
            ("TOPPADDING",     (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",  (0,0), (-1,-1), 5),
            ("LEFTPADDING",    (0,0), (-1,-1), 6),
            ("RIGHTPADDING",   (0,0), (-1,-1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    doc.build(story)
    return buffer.getvalue()