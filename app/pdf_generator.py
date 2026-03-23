# app/pdf_generator.py
# ═══════════════════════════════════════════════════════════════
#  Smart Interview System — Professional PDF Report Generator
#  Engine  : ReportLab
#  Sections: Header → Summary → Performance → AI Feedback
#            → Suggestions → Final Recommendation
# ═══════════════════════════════════════════════════════════════

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String
from io import BytesIO
from datetime import datetime
import json

# ─────────────────────────────────────────────────────────────
#  COLOR PALETTE
# ─────────────────────────────────────────────────────────────
C_PRIMARY   = colors.HexColor('#4F46E5')
C_PRIMARY_D = colors.HexColor('#3730A3')
C_PRIMARY_L = colors.HexColor('#EEF2FF')
C_PURPLE    = colors.HexColor('#7C3AED')
C_GREEN     = colors.HexColor('#10B981')
C_GREEN_L   = colors.HexColor('#F0FDF4')
C_GREEN_D   = colors.HexColor('#065F46')
C_AMBER     = colors.HexColor('#F59E0B')
C_AMBER_L   = colors.HexColor('#FFFBEB')
C_AMBER_D   = colors.HexColor('#92400E')
C_RED       = colors.HexColor('#EF4444')
C_RED_L     = colors.HexColor('#FEF2F2')
C_RED_D     = colors.HexColor('#B91C1C')
C_TEXT      = colors.HexColor('#0F172A')
C_MUTED     = colors.HexColor('#64748B')
C_FAINT     = colors.HexColor('#94A3B8')
C_BORDER    = colors.HexColor('#E2E8F0')
C_BG        = colors.HexColor('#F8FAFC')
C_BG2       = colors.HexColor('#F1F5F9')
C_WHITE     = colors.white
C_DARK      = colors.HexColor('#0F172A')

W = 170 * mm   # usable page width


# ─────────────────────────────────────────────────────────────
#  SCORE HELPERS
# ─────────────────────────────────────────────────────────────
def _clr(s):
    s = float(s)
    return C_GREEN if s >= 70 else (C_AMBER if s >= 40 else C_RED)

def _bg(s):
    s = float(s)
    return C_GREEN_L if s >= 70 else (C_AMBER_L if s >= 40 else C_RED_L)

def _dark(s):
    s = float(s)
    return C_GREEN_D if s >= 70 else (C_AMBER_D if s >= 40 else C_RED_D)

def _grade(s):
    s = float(s)
    if s >= 85: return "A"
    if s >= 70: return "B"
    if s >= 55: return "C"
    if s >= 40: return "D"
    return "F"

def _level(s):
    s = float(s)
    if s >= 80: return "Advanced"
    if s >= 60: return "Intermediate"
    if s >= 40: return "Beginner"
    return "Needs Practice"

def _label(s):
    s = float(s)
    if s >= 80: return "Excellent"
    if s >= 70: return "Good"
    if s >= 55: return "Average"
    if s >= 40: return "Below Average"
    return "Needs Improvement"


# ─────────────────────────────────────────────────────────────
#  PARAGRAPH STYLES
# ─────────────────────────────────────────────────────────────
def _S():
    return {
        "title":    ParagraphStyle("title",  fontName="Helvetica-Bold", fontSize=20,
                                   textColor=C_WHITE,  leading=26, alignment=TA_CENTER),
        "subtitle": ParagraphStyle("sub",    fontName="Helvetica",      fontSize=10,
                                   textColor=colors.HexColor('#C7D2FE'), leading=14, alignment=TA_CENTER),
        "sec_hdr":  ParagraphStyle("sh",     fontName="Helvetica-Bold", fontSize=11,
                                   textColor=C_WHITE,  leading=16),
        "h2":       ParagraphStyle("h2",     fontName="Helvetica-Bold", fontSize=10,
                                   textColor=C_TEXT,   leading=14, spaceBefore=4, spaceAfter=3),
        "h3":       ParagraphStyle("h3",     fontName="Helvetica-Bold", fontSize=9,
                                   textColor=C_TEXT,   leading=13, spaceAfter=2),
        "body":     ParagraphStyle("body",   fontName="Helvetica",      fontSize=9,
                                   textColor=C_MUTED,  leading=14, spaceAfter=2),
        "dark":     ParagraphStyle("dark",   fontName="Helvetica",      fontSize=9,
                                   textColor=C_TEXT,   leading=14, spaceAfter=2),
        "small":    ParagraphStyle("sm",     fontName="Helvetica",      fontSize=7.5,
                                   textColor=C_FAINT,  leading=11),
        "fb":       ParagraphStyle("fb",     fontName="Helvetica",      fontSize=9,
                                   textColor=colors.HexColor('#1E3A8A'), leading=14, leftIndent=6, spaceAfter=3),
        "ok":       ParagraphStyle("ok",     fontName="Helvetica",      fontSize=9,
                                   textColor=C_GREEN_D, leading=14, leftIndent=6, spaceAfter=2),
        "bad":      ParagraphStyle("bad",    fontName="Helvetica",      fontSize=9,
                                   textColor=C_RED_D,  leading=14, leftIndent=6, spaceAfter=2),
        "italic":   ParagraphStyle("ita",    fontName="Helvetica-Oblique", fontSize=9,
                                   textColor=C_PURPLE, leading=13, leftIndent=8, spaceAfter=2),
        "footer":   ParagraphStyle("ft",     fontName="Helvetica",      fontSize=7,
                                   textColor=C_FAINT,  leading=10, alignment=TA_CENTER),
        "q_white":  ParagraphStyle("qw",     fontName="Helvetica-Bold", fontSize=9,
                                   textColor=C_WHITE,  leading=13),
        "q_score":  ParagraphStyle("qs",     fontName="Helvetica-Bold", fontSize=10,
                                   textColor=C_WHITE,  leading=14, alignment=TA_RIGHT),
    }


# ─────────────────────────────────────────────────────────────
#  HELPER — progress bar
# ─────────────────────────────────────────────────────────────
def _bar(label, value, color, bar_w=115*mm):
    """Label + visual progress bar + % text."""
    value   = min(float(value), 100)
    fill_w  = (value / 100) * bar_w

    d = Drawing(bar_w + 28*mm, 13)
    d.add(Rect(0, 2, bar_w, 9,
               fillColor=C_BG2, strokeColor=C_BORDER, strokeWidth=0.4, rx=4, ry=4))
    if fill_w > 1:
        d.add(Rect(0, 2, fill_w, 9,
                   fillColor=color, strokeColor=None, rx=4, ry=4))
    d.add(String(bar_w + 5*mm, 3.5,
                 f"{round(value)}%",
                 fontName="Helvetica-Bold", fontSize=8, fillColor=color))

    t = Table([[
        Paragraph(label, ParagraphStyle("bl", fontName="Helvetica", fontSize=8,
                                        textColor=C_TEXT, leading=12)),
        d,
    ]], colWidths=[38*mm, bar_w + 30*mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
    ]))
    return t


# ─────────────────────────────────────────────────────────────
#  HELPER — section divider
# ─────────────────────────────────────────────────────────────
def _sec(title, color=None):
    if color is None: color = C_PRIMARY
    S = _S()
    t = Table([[Paragraph(f'<b>{title}</b>', S["sec_hdr"])]], colWidths=[W])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),color),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),10),('ROUNDEDCORNERS',[5]),
    ]))
    return [Spacer(1,4*mm), t, Spacer(1,3*mm)]


# ═══════════════════════════════════════════════════════════════
#  1. HEADER
# ═══════════════════════════════════════════════════════════════
def build_header(name, email, session_id, started_at):
    S  = _S()
    dt = started_at.strftime('%d %B %Y, %I:%M %p') if started_at else datetime.now().strftime('%d %B %Y')

    banner = Table([
        [Paragraph('🎯  Smart Interview System', S["title"])],
        [Paragraph('AI-Powered Interview Performance Report', S["subtitle"])],
    ], colWidths=[W])
    banner.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),C_PRIMARY),
        ('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),10),
        ('LEFTPADDING',(0,0),(-1,-1),14),('ROUNDEDCORNERS',[8]),
    ]))

    lbl_s = ParagraphStyle("il", fontName="Helvetica-Bold", fontSize=8,
                           textColor=C_PRIMARY, leading=11)
    val_s = ParagraphStyle("iv", fontName="Helvetica", fontSize=9,
                           textColor=C_TEXT, leading=13)
    info = Table([
        [Paragraph('Candidate', lbl_s), Paragraph('Email', lbl_s),
         Paragraph('Date', lbl_s),      Paragraph('Session', lbl_s)],
        [Paragraph(name, val_s),        Paragraph(email, val_s),
         Paragraph(dt, val_s),          Paragraph(f'#{session_id}', val_s)],
    ], colWidths=[44*mm, 58*mm, 46*mm, 22*mm])
    info.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),C_PRIMARY_L),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('BOX',(0,0),(-1,-1),0.5,C_BORDER),
        ('LINEBELOW',(0,0),(-1,0),0.5,C_BORDER),
        ('ROUNDEDCORNERS',[4]),
    ]))
    return [banner, Spacer(1,4*mm), info, Spacer(1,5*mm)]


# ═══════════════════════════════════════════════════════════════
#  2. SCORE SUMMARY
# ═══════════════════════════════════════════════════════════════
def build_score_summary(total_score, overall_grade, answers):
    S  = _S()
    sc = float(total_score)
    c  = _clr(sc); b = _bg(sc)

    passed  = sum(1 for a in answers if float(a.get("score") or 0) >= 70)
    skipped = sum(1 for a in answers
                  if not (a.get("answer") or "").strip()
                  or (a.get("answer") or "").lower().strip() == "skipped")

    # Big score box
    score_box = Table([
        [Paragraph(f'<font color="{c.hexval()}"><b>{round(sc)}%</b></font>',
                   ParagraphStyle("SB", fontName="Helvetica-Bold", fontSize=44,
                                  textColor=c, leading=52, alignment=TA_CENTER))],
        [Paragraph(f'Grade  {overall_grade}',
                   ParagraphStyle("GB", fontName="Helvetica-Bold", fontSize=17,
                                  textColor=c, leading=22, alignment=TA_CENTER))],
        [Paragraph(_label(sc),
                   ParagraphStyle("LB", fontName="Helvetica", fontSize=9,
                                  textColor=C_MUTED, leading=13, alignment=TA_CENTER))],
    ], colWidths=[60*mm])
    score_box.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),b),
        ('TOPPADDING',(0,0),(-1,-1),14),('BOTTOMPADDING',(0,0),(-1,-1),14),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('BOX',(0,0),(-1,-1),1.5,c),('ROUNDEDCORNERS',[8]),
    ]))

    # Stats table
    def sr(lbl, val, vc=C_TEXT):
        return [Paragraph(f'<b>{lbl}</b>',
                          ParagraphStyle("sl", fontName="Helvetica-Bold", fontSize=9,
                                         textColor=C_MUTED, leading=13)),
                Paragraph(str(val),
                          ParagraphStyle("sv", fontName="Helvetica-Bold", fontSize=9,
                                         textColor=vc, leading=13))]
    stats = Table([
        sr("Performance Level",  _level(sc), c),
        sr("Total Questions",    len(answers)),
        sr("Answered",           len(answers) - skipped),
        sr("Passed  (≥ 70%)",    passed,  C_GREEN),
        sr("Needs Work",         len(answers) - passed, C_RED),
        sr("Skipped",            skipped, C_FAINT),
    ], colWidths=[54*mm, 54*mm])
    stats.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(0,-1),C_BG),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('LEFTPADDING',(0,0),(-1,-1),10),
        ('LINEBELOW',(0,0),(-1,-2),0.3,C_BORDER),
        ('BOX',(0,0),(-1,-1),0.5,C_BORDER),('ROUNDEDCORNERS',[4]),
    ]))

    combined = Table([[score_box, stats]], colWidths=[65*mm, 105*mm])
    combined.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    return [combined, Spacer(1,5*mm), _bar("Overall Score", sc, c), Spacer(1,2*mm)]


# ═══════════════════════════════════════════════════════════════
#  3. PERFORMANCE ANALYSIS
# ═══════════════════════════════════════════════════════════════
def build_performance_analysis(answers):
    S = _S()
    all_str, all_wk = [], []
    for a in answers:
        try: all_str += json.loads(a.get("strengths")  or "[]")
        except: pass
        try: all_wk  += json.loads(a.get("weaknesses") or "[]")
        except: pass
    all_str = list(dict.fromkeys(all_str))[:7]
    all_wk  = list(dict.fromkeys(all_wk)) [:7]

    def list_box(title, items, bg, txt, border):
        rows = [[Paragraph(f'<b>{title}</b>',
                           ParagraphStyle("lbt", fontName="Helvetica-Bold", fontSize=9,
                                          textColor=txt, leading=13))]]
        for item in (items or ['No data yet']):
            rows.append([Paragraph(f'•  {item}',
                                   ParagraphStyle("lbi", fontName="Helvetica", fontSize=8.5,
                                                  textColor=txt, leading=13, leftIndent=4, spaceAfter=1))])
        t = Table(rows, colWidths=[80*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),bg),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ('LEFTPADDING',(0,0),(-1,-1),9),
            ('BOX',(0,0),(-1,-1),0.8,border),('ROUNDEDCORNERS',[5]),
        ]))
        return t

    sw = Table([[
        list_box("💪  Strength Areas",  all_str, C_GREEN_L, C_GREEN_D, C_GREEN),
        list_box("⚠️  Areas to Improve", all_wk,  C_RED_L,   C_RED_D,   C_RED),
    ]], colWidths=[84*mm, 86*mm])
    sw.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),2),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))

    rows = [sw, Spacer(1,5*mm), Paragraph('<b>Score Per Question</b>', S["h2"])]
    for i, a in enumerate(answers):
        sc  = float(a.get("score") or 0)
        lbl = f'Q{i+1}: {a["question"][:62]}{"…" if len(a["question"])>62 else ""}'
        rows.append(_bar(lbl, sc, _clr(sc)))
    rows.append(Spacer(1,3*mm))
    return rows


# ═══════════════════════════════════════════════════════════════
#  4. AI FEEDBACK PER QUESTION
# ═══════════════════════════════════════════════════════════════
def build_ai_feedback(answers):
    S = _S()
    elements = []

    for i, a in enumerate(answers):
        sc       = float(a.get("score") or 0)
        grade    = a.get("grade") or _grade(sc)
        c        = _clr(sc)
        q        = a.get("question", "")
        ans      = (a.get("answer") or "").strip()
        fb       = (a.get("feedback") or "").strip()
        sug      = (a.get("suggested_answer") or "").strip()
        skipped  = not ans or ans.lower() == "skipped"

        try: strs = json.loads(a.get("strengths")  or "[]")
        except: strs = []
        try: wks  = json.loads(a.get("weaknesses") or "[]")
        except: wks  = []

        # Card header
        hdr = Table([[
            Paragraph(f'<font color="white"><b>Q{i+1}</b></font>',
                      ParagraphStyle("QN", fontName="Helvetica-Bold", fontSize=10,
                                     textColor=C_WHITE, leading=14, alignment=TA_CENTER)),
            Paragraph(q[:95]+('…' if len(q)>95 else ''), S["q_white"]),
            Paragraph(f'<font color="white"><b>{round(sc)}/100 · {grade}</b></font>', S["q_score"]),
        ]], colWidths=[13*mm, 133*mm, 24*mm])
        hdr.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),c),
            ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ROUNDEDCORNERS',[5]),
        ]))

        # Card body
        body = []
        body.append([_bar("Score", sc, c, bar_w=100*mm)])
        if skipped:
            body.append([Paragraph(
                '📭  This question was skipped — no answer provided.',
                ParagraphStyle("sk", fontName="Helvetica-Oblique", fontSize=9,
                               textColor=C_FAINT, leading=13))])
        else:
            body.append([Paragraph('<b>📝 Your Answer</b>', S["h3"])])
            body.append([Paragraph(ans[:380]+('…' if len(ans)>380 else ''), S["body"])])

        body.append([Paragraph('<b>🤖 AI Feedback</b>', S["h3"])])
        body.append([Paragraph(fb or _auto_feedback(q, ans, sc, strs, wks), S["fb"])])

        if strs:
            body.append([Paragraph('<b>✅ What You Did Well</b>', S["h3"])])
            for s in strs[:3]:
                body.append([Paragraph(f'  •  {s}', S["ok"])])
        if wks:
            body.append([Paragraph('<b>⚠️ What to Improve</b>', S["h3"])])
            for w in wks[:3]:
                body.append([Paragraph(f'  •  {w}', S["bad"])])
        if sug:
            body.append([Paragraph('<b>💡 Ideal Answer Approach</b>', S["h3"])])
            body.append([Paragraph(sug[:380]+('…' if len(sug)>380 else ''), S["italic"])])

        body_t = Table(body, colWidths=[166*mm])
        body_t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),C_BG),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),3),
            ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
            ('BOX',(0,0),(-1,-1),0.5,C_BORDER),
        ]))
        elements.append(KeepTogether([hdr, body_t]))
        elements.append(Spacer(1,4*mm))
    return elements


# ═══════════════════════════════════════════════════════════════
#  5. IMPROVEMENT SUGGESTIONS
# ═══════════════════════════════════════════════════════════════
def build_improvement_suggestions(answers, total_score):
    S = _S(); sc = float(total_score)
    all_wk = []
    for a in answers:
        try: all_wk += json.loads(a.get("weaknesses") or "[]")
        except: pass
    all_wk  = list(dict.fromkeys(all_wk))
    low_qs  = [i+1 for i,a in enumerate(answers) if float(a.get("score") or 0) < 55]

    tips = []
    if sc < 70:
        tips.append("Use the <b>STAR method</b> (Situation → Task → Action → Result) to give complete, structured answers.")
    if any('communication' in w.lower() or 'clarity' in w.lower() for w in all_wk):
        tips.append("Improve <b>communication clarity</b> — record mock answers and review tone, pace, and structure.")
    if any('technical' in w.lower() or 'example' in w.lower() for w in all_wk):
        tips.append("Link <b>technical explanations</b> to real projects — show what you built, not just what you know.")
    if low_qs:
        qs = ', '.join([f'Q{i}' for i in low_qs])
        tips.append(f"Rework answers to <b>{qs}</b> — these scored below 55% and need more depth and specificity.")
    tips += [
        "Record <b>mock interviews</b> and review for filler words, confidence, and completeness.",
        "Prepare 2–3 strong examples for the <b>top 30 interview questions</b> in your target role.",
        "Always include <b>context, actions, and measurable results</b> — avoid vague or generic statements.",
        "Build a <b>project portfolio</b> that demonstrates real-world problem-solving and technical skills.",
    ]
    elements = []
    for tip in tips[:7]:
        row = Table([[
            Paragraph('➤', ParagraphStyle("ar", fontName="Helvetica-Bold", fontSize=10,
                                           textColor=C_PRIMARY, leading=14, alignment=TA_CENTER)),
            Paragraph(tip, S["dark"]),
        ]], colWidths=[8*mm, 158*mm])
        row.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
            ('LEFTPADDING',(0,0),(-1,-1),0),
        ]))
        elements.append(row)
    elements.append(Spacer(1,3*mm))
    return elements


# ═══════════════════════════════════════════════════════════════
#  6. FINAL RECOMMENDATION
# ═══════════════════════════════════════════════════════════════
def build_recommendation(total_score, overall_grade):
    sc = float(total_score)
    if sc >= 75:
        icon, verdict = "✅", "Candidate is Interview-Ready"
        msg = (f"Based on this AI assessment, <b>{verdict}</b>. Score: <b>{round(sc)}%</b> "
               f"(Grade <b>{overall_grade}</b>). Solid communication, structured thinking, and "
               f"good technical knowledge demonstrated. Continue refining edge-case answers "
               f"for senior-level interviews.")
        c, b = C_GREEN, C_GREEN_L
    elif sc >= 50:
        icon, verdict = "🔧", "Candidate Needs Some Improvement"
        msg = (f"<b>{verdict}</b> before attending real interviews. "
               f"Score: <b>{round(sc)}%</b> (Grade <b>{overall_grade}</b>). "
               f"Potential is visible — structure answers better, deepen technical knowledge, "
               f"and build confidence through regular mock practice. Target: 70%+ in 4–6 weeks.")
        c, b = C_AMBER, C_AMBER_L
    else:
        icon, verdict = "⚠️", "Significant Improvement Required"
        msg = (f"<b>{verdict}</b>. Score: <b>{round(sc)}%</b> (Grade <b>{overall_grade}</b>). "
               f"Complete a structured interview preparation course, practice daily mock interviews, "
               f"review all flagged topics, and build real-world project experience. Aim for 60%+ before applying.")
        c, b = C_RED, C_RED_L

    t = Table([[
        Paragraph(f'{icon}  <b>Final Recommendation: {verdict}</b>',
                  ParagraphStyle("rv", fontName="Helvetica-Bold", fontSize=11,
                                 textColor=c, leading=16)),
        Paragraph(msg, ParagraphStyle("rm", fontName="Helvetica", fontSize=9,
                                      textColor=C_TEXT, leading=14)),
    ]], colWidths=[W])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),b),
        ('BOX',(0,0),(-1,-1),2,c),
        ('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12),
        ('LEFTPADDING',(0,0),(-1,-1),14),('RIGHTPADDING',(0,0),(-1,-1),14),
        ('ROUNDEDCORNERS',[7]),
    ]))
    return [t]


# ─────────────────────────────────────────────────────────────
#  AUTO FEEDBACK — when DB feedback is missing
# ─────────────────────────────────────────────────────────────
def _auto_feedback(question, answer, score, strengths, weaknesses):
    sc  = float(score)
    ans = (answer or "").strip()
    if not ans or ans.lower() == "skipped":
        return ("This question was not attempted. Prepare a 2–3 minute structured response "
                "using the STAR method. Even a partial answer earns partial credit.")
    if len(ans) < 40:
        return (f"Your answer was very brief ({len(ans)} chars). Expand with specific examples, "
                "use the STAR method, and explain both actions taken and outcomes achieved.")
    if sc >= 78:
        extra = f" Particularly strong: {strengths[0]}." if strengths else ""
        return (f"Excellent answer.{extra} To reach 90+, add quantifiable outcomes "
                "and a brief self-reflection on lessons learned.")
    if sc >= 55:
        improve = f" Key gap: {weaknesses[0]}." if weaknesses else ""
        return (f"Decent response but lacking depth.{improve} Include a concrete real-world "
                "example, quantify achievements, and ensure clear beginning–middle–end structure.")
    weak_note = f" Main issue: {weaknesses[0]}." if weaknesses else ""
    return (f"Needs significant improvement in structure and specificity.{weak_note} "
            "Research model answers, practice structured responses aloud, and link "
            "your answer to real scenarios from your work or projects.")


# ═══════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════
def generate_interview_pdf(session_data, answers):
    """
    Generate professional PDF.

    Args:
        session_data (dict): session_id, name, email, started_at, total_score
        answers (list): answer dicts from DB

    Returns:
        bytes: PDF content
    """
    # Ensure JSON fields are parsed
    for a in answers:
        if not isinstance(a.get("strengths_list"), list):
            try: a["strengths_list"]  = json.loads(a.get("strengths")  or "[]")
            except: a["strengths_list"]  = []
        if not isinstance(a.get("weaknesses_list"), list):
            try: a["weaknesses_list"] = json.loads(a.get("weaknesses") or "[]")
            except: a["weaknesses_list"] = []
        a["strengths"]  = json.dumps(a.get("strengths_list",  []))
        a["weaknesses"] = json.dumps(a.get("weaknesses_list", []))

    total_score = float(session_data.get("total_score") or 0)
    grade       = _grade(total_score)
    session_id  = session_data.get("session_id", "")
    started_at  = session_data.get("started_at")
    buffer      = BytesIO()

    # Page event — decorative footer bar on every page
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(C_PRIMARY)
        canvas.rect(0, 0, A4[0], 10, fill=1, stroke=0)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(C_WHITE)
        canvas.drawCentredString(
            A4[0] / 2, 3,
            f"Smart Interview System  ·  Session #{session_id}  ·  "
            f"Page {doc.page}  ·  {datetime.now().strftime('%d %b %Y')}"
        )
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=16*mm,  bottomMargin=18*mm,
        title=f"Interview Report — {session_data.get('name','Candidate')}",
        author="Smart Interview System",
    )

    S = _S()
    story = []

    story += build_header(
        session_data.get("name", "Candidate"),
        session_data.get("email", ""),
        session_id, started_at
    )
    story += _sec("📊  Overall Summary")
    story += build_score_summary(total_score, grade, answers)

    story += _sec("📈  Performance Analysis")
    story += build_performance_analysis(answers)

    story += _sec("🤖  AI Feedback — Question by Question")
    story += build_ai_feedback(answers)

    story += _sec("💡  Improvement Suggestions", color=C_PURPLE)
    story += build_improvement_suggestions(answers, total_score)

    story += _sec("🏁  Final Recommendation", color=C_DARK)
    story += build_recommendation(total_score, grade)

    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f"Generated by Smart Interview System  ·  AI-Powered Assessment  ·  "
        f"Session #{session_id}  ·  {datetime.now().strftime('%d %B %Y, %H:%M')}",
        S["footer"]
    ))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buffer.getvalue()