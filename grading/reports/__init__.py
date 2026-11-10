"""Offline learner reports generated from a reviewed, source-bound snapshot."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
import math

import pypdfium2 as pdfium
from PIL import ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Circle, Drawing, String
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab
from reportlab.lib.utils import ImageReader

from grading.review_store import current_approval, _fingerprint, _validate_feedback
from grading.practice import PRACTICE
from grading.intake import CONFIG

REPORT_FILES = ('puntenoverzicht.pdf', 'feedbackkaart.pdf', 'toets-met-feedback.pdf')
REPORT_LAYOUT = 'feedback-v3'
PURPLE = colors.HexColor('#5200FF')
INK = colors.HexColor('#160033')
MUTED = colors.HexColor('#625B70')
PANEL = colors.HexColor('#F5F1FF')
RULE = colors.HexColor('#E2DDEA')
QUESTION_TITLES = {question['id']: question['title'] for question in CONFIG['questions']}
CRITERION_LABELS = {
    'functioneel': 'Functioneel', 'leesbaar': 'Leesbaar',
    'programmeerconcept': 'Programmeerconcept', 'wiskundeconcept': 'Wiskundeconcept',
}
ROOT = Path(__file__).resolve().parents[2]
_FONT_DIR = Path(reportlab.__file__).parent / 'fonts'
pdfmetrics.registerFont(TTFont('ReportVera', str(_FONT_DIR / 'Vera.ttf')))
pdfmetrics.registerFont(TTFont('ReportVeraBold', str(_FONT_DIR / 'VeraBd.ttf')))
pdfmetrics.registerFontFamily('ReportVera', normal='ReportVera', bold='ReportVeraBold', italic='ReportVera', boldItalic='ReportVeraBold')


def _p(text, style):
    return Paragraph(escape(str(text)).replace('\n', '<br/>'), style)


def _styles():
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = 'ReportVera'
    styles.add(ParagraphStyle(name='BrandTitle', parent=styles['Title'], fontName='ReportVeraBold', textColor=INK, fontSize=19, leading=23, spaceAfter=12))
    styles.add(ParagraphStyle(name='BrandHeading', parent=styles['Heading2'], fontName='ReportVeraBold', textColor=PURPLE, spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name='BrandBody', parent=styles['BodyText'], textColor=INK, fontSize=10, leading=14, spaceAfter=6, splitLongWords=True))
    styles.add(ParagraphStyle(name='BrandSmall', parent=styles['BodyText'], textColor=INK, fontSize=8, leading=11, splitLongWords=True))
    return styles


def _header(c, doc, card_status=None):
    is_card = card_status is not None
    margin = (15 if is_card else 18)*mm
    c.setFillColor(PURPLE)
    band = (4.5 if is_card else 8)*mm
    c.rect(0, A4[1]-band, A4[0], band, fill=1, stroke=0)
    icon = ROOT / 'favicon.png'
    if icon.exists():
        c.drawImage(str(icon), margin, A4[1]-28*mm if is_card else A4[1]-24*mm,
                    (12 if is_card else 9)*mm, (12 if is_card else 9)*mm, mask='auto')
    c.setFont('ReportVeraBold', 10)
    c.setFillColor(INK)
    c.drawString(margin+(16 if is_card else 12)*mm, A4[1]-21*mm, 'JavaScript in de Klas')
    c.setFont('ReportVera', 8)
    if is_card:
        c.setFillColor(MUTED)
        c.drawString(margin+16*mm, A4[1]-26.5*mm, 'TOETS HOOFDSTUK 3 · DE SELECTIE')
        c.setStrokeColor(RULE)
        c.line(margin, 15*mm, A4[0]-margin, 15*mm)
        c.setFont('ReportVera', 7)
        c.drawString(margin, 10.5*mm, '© 2026 Robbe Wulgaert · AI in de Klas · robbewulgaert.be')
        if card_status:
            c.drawRightString(A4[0]-margin-9*mm, 10.5*mm, card_status)
    c.drawRightString(A4[0]-margin, (10.5 if is_card else 12)*mm, str(doc.page))


def _document(path, story, card_status=None):
    is_card = card_status is not None
    margin = (15 if is_card else 18)*mm
    template = SimpleDocTemplate(str(path) if isinstance(path, Path) else path, pagesize=A4,
                                 leftMargin=margin, rightMargin=margin, topMargin=34*mm if is_card else 31*mm,
                                 bottomMargin=19*mm, title='Feedback op je toets' if is_card else 'JavaScript in de Klas')
    def page_header(canvas, doc):
        _header(canvas, doc, card_status)
    template.build(story, onFirstPage=page_header, onLaterPages=page_header)


def _num(n):
    return f'{n:g}'.replace('.', ',')


def _table(rows, widths):
    t = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F0EBFF')),
                           ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LINEBELOW', (0,0), (-1,-1), .3, colors.HexColor('#E2DDEA')),
                           ('LEFTPADDING', (0,0), (-1,-1), 5), ('RIGHTPADDING', (0,0), (-1,-1), 5),
                           ('TOPPADDING', (0,0), (-1,-1), 5), ('BOTTOMPADDING', (0,0), (-1,-1), 5)]))
    return t


def _criterion_label(criterion):
    suffix = criterion['criterion_id'].split('.', 1)[-1]
    return CRITERION_LABELS.get(suffix, suffix)


def _range(earned, pending, maximum):
    value = _num(earned)
    if pending:
        value += f'–{_num(earned+pending)}'
    return f'{value} / {_num(maximum)}'


def _criterion_summary(criteria, width, style):
    rows = [[], []]
    for suffix, label in CRITERION_LABELS.items():
        group = [c for c in criteria if c['criterion_id'].endswith('.' + suffix)]
        earned = sum(c['effective_points'] for c in group if c['effective_points'] is not None)
        pending = sum(c['effective_max'] for c in group if c['effective_points'] is None)
        maximum = sum(c['effective_max'] for c in group)
        rows[0].append(_p(label, style))
        rows[1].append(_p(_range(earned, pending, maximum), style))
    return _table(rows, [width/len(CRITERION_LABELS)]*len(CRITERION_LABELS))


def _panel(rows, widths, commands=()):
    return Table(rows, colWidths=widths, cornerRadii=[11]*4, splitByRow=0, hAlign='LEFT',
                 style=TableStyle([
                     ('BACKGROUND', (0, 0), (-1, -1), PANEL),
                     ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                     ('LEFTPADDING', (0, 0), (-1, -1), 12),
                     ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                     ('TOPPADDING', (0, 0), (-1, -1), 7),
                     ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                     *commands,
                 ]))


def _badge(number):
    badge = Drawing(22, 22)
    badge.add(Circle(11, 11, 10, strokeColor=None, fillColor=PURPLE))
    badge.add(String(11, 8, str(number), fontName='ReportVeraBold', fontSize=9,
                     fillColor=colors.white, textAnchor='middle'))
    return badge


def _card_table(values, widths, styles, total_row=False):
    rows = [[_p(cell, styles['CardTableHead'] if i == 0 or (total_row and i == len(values)-1)
               else styles['CardTableBody']) for cell in row] for i, row in enumerate(values)]
    table = _table(rows, widths)
    if total_row:
        table.setStyle(TableStyle([('BACKGROUND', (0, -1), (-1, -1), PANEL)]))
    return table


def _feedback_card(path, learner, feedback, criteria, total, status):
    styles = _styles()
    body, small = styles['BrandBody'], styles['BrandSmall']
    styles.add(ParagraphStyle(name='CardTitle', parent=styles['BrandTitle'], alignment=0,
                              fontSize=24, leading=28, textColor=PURPLE, spaceAfter=10))
    styles.add(ParagraphStyle(name='CardScore', parent=styles['CardTitle'], fontSize=22,
                              leading=28, spaceAfter=0))
    styles.add(ParagraphStyle(name='CardHeading', parent=styles['BrandHeading'], textColor=INK))
    styles.add(ParagraphStyle(name='CardPanelText', parent=body, spaceAfter=0))
    styles.add(ParagraphStyle(name='CardPractice', parent=small, textColor=PURPLE))
    styles.add(ParagraphStyle(name='CardMuted', parent=small, textColor=MUTED))
    styles.add(ParagraphStyle(name='CardTableBody', parent=small, fontSize=8.5, leading=10.5))
    styles.add(ParagraphStyle(name='CardTableHead', parent=styles['CardTableBody'],
                              fontName='ReportVeraBold', textColor=PURPLE))
    title, heading, panel_text = styles['CardTitle'], styles['CardHeading'], styles['CardPanelText']
    identity = _p(f"{learner['name']} · {learner['class_name']}", styles['CardMuted'])
    width = 175*mm
    by_id = {c['criterion_id']: c for c in criteria}
    earned, loss, pending, maximum = (total[k] for k in ('earned', 'loss', 'pending', 'maximum'))
    result = _range(earned, pending, maximum)
    score_note = status
    if pending:
        score_note = '\n'.join(filter(None, (status, f"{_num(pending)} punten nog na te kijken")))
    story = [_p('Feedback op je toets', title), identity, Spacer(1, 14),
             _panel([[_p(result, styles['CardScore']), _p(score_note, panel_text)]],
                    [width*.54, width*.46]), Spacer(1, 3),
             _p('Je score per criterium', heading), _criterion_summary(criteria, width, styles['CardTableBody'])]
    strength = feedback['strength']
    if strength:
        story.extend([_p('Dit gaat al goed', heading), _p(strength['text'], body)])
    story.append(_p('Dit zijn jouw werkpunten', heading))
    if not feedback['priorities']:
        message = 'Er zijn nog geen werkpunten toegevoegd.' if loss or pending else 'Je behaalde alle punten.'
        story.append(_p(message, body))
    for number, item in enumerate(feedback['priorities'], 1):
        qid = by_id[item['criterion_id']]['question_id']
        exercise = _p(f"Oefening {QUESTION_TITLES[qid]}", styles['CardMuted'])
        content = [_p(item['observation'], panel_text),
                   _p(f"Probeer dit: {item['correction']}", styles['CardPractice'])]
        if item.get('practice_id'):
            content.append(_p('Oefen verder: ' + PRACTICE[item['practice_id']]['label'], styles['CardPractice']))
        rows = [[_badge(number), [_p(item['title'], heading), exercise]]]
        rows.extend([paragraph, ''] for paragraph in content)
        spans = [('SPAN', (0, index), (1, index)) for index in range(1, len(rows))]
        panel = _panel(rows, [32, width-32], spans + [
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (0, 0), 0),
            ('LEFTPADDING', (1, 0), (1, 0), 3),
        ])
        # A single work point longer than a page needs normal paragraph flow.
        if panel.wrap(width, 0)[1] > A4[1] - 53*mm - 12:
            story.extend([_p(f"{number}. {item['title']}", heading), exercise, *content])
        else:
            story.append(panel)
        story.append(Spacer(1, 11))
    if loss or pending:
        story.extend([_p('Verderop zie je je punten per oefening.', styles['CardMuted']), PageBreak(),
                      _p('Je punten per vraag', title), identity, Spacer(1, 15)])
        summary = [['Oefening', 'Behaald / max.', 'Verlies', 'Nog open']]
        deductions = [['Onderdeel', 'Behaald / maximum', 'Verlies']]
        unresolved = [['Oefening', 'Nog na te kijken', 'Punten open']]
        for qid in dict.fromkeys(c['question_id'] for c in criteria):
            question = [c for c in criteria if c['question_id'] == qid]
            q_earned = sum(c['effective_points'] for c in question if c['effective_points'] is not None)
            q_open = [c for c in question if c['effective_points'] is None]
            q_pending = sum(c['effective_max'] for c in q_open)
            q_max = sum(c['effective_max'] for c in question)
            summary.append([QUESTION_TITLES[qid], _range(q_earned, q_pending, q_max),
                            _num(q_max-q_earned-q_pending), _num(q_pending)])
            for c in question:
                points, limit = c['effective_points'], c['effective_max']
                if points is not None and points < limit:
                    deductions.append([f"{QUESTION_TITLES[qid]} · {_criterion_label(c)}",
                                       _range(points, 0, limit), f"-{_num(limit-points)}"])
            if q_open:
                unresolved.append([QUESTION_TITLES[qid], ', '.join(map(_criterion_label, q_open)), _num(q_pending)])
        summary.append(['Totaal', result, _num(loss), _num(pending)])
        story.append(_card_table(summary, [82*mm, 39*mm, 26*mm, 28*mm], styles, total_row=True))
        if loss:
            story.extend([_p('Waar verloor je punten?', heading),
                          _p('Bekijk deze onderdelen en probeer de oefeningen opnieuw.', body),
                          _card_table(deductions, [104*mm, 46*mm, 25*mm], styles)])
        if pending:
            story.extend([_p('Nog na te kijken', heading),
                          _p('Deze punten tellen voorlopig mee in de bovengrens van je score.', body),
                          _card_table(unresolved, [65*mm, 81*mm, 29*mm], styles)])
        equation = f"{_num(maximum)} - {_num(loss)} puntenverlies = {_num(maximum-loss)}"
        if pending:
            equation += f" maximaal. Met {_num(pending)} punten nog open is je voorlopige score {result}."
        else:
            equation += f" / {_num(maximum)}."
        story.extend([Spacer(1, 14), _p(equation, styles['BrandHeading'])])
    _document(path, story, card_status=status)


def _region(region, pages):
    try:
        page, box = region['page'], region['box']
        if type(page) is not int or not 1 <= page <= pages or len(box) != 4:
            raise ValueError
        x0, y0, x1, y1 = box
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in box) or not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise ValueError
        return page, box
    except (KeyError, TypeError, ValueError):
        raise ValueError('invalid normalized region') from None


def render_reports(folder, source_pdf, learner, baseline, snapshot, final=False):
    """Write three PDFs to an existing empty private folder; return their paths."""
    folder = Path(folder)
    if not folder.is_dir() or any(folder.iterdir()):
        raise ValueError('an empty output folder is required')
    data = Path(source_pdf).read_bytes()
    if (not baseline.get('verification_safe') or snapshot.get('binding') != baseline.get('binding')
            or snapshot.get('baseline_sha256') != _fingerprint(baseline)
            or sha256(data).hexdigest() != baseline['binding']['source_sha256']):
        raise ValueError('unsafe or mismatched source and review')
    if final and not current_approval(snapshot):
        raise ValueError('current approval required')
    _validate_feedback(snapshot['feedback'], snapshot, baseline)
    source = pdfium.PdfDocument(data)
    regions = [_region(r, len(source)) for r in baseline['verification_regions']]
    if not regions:
        raise ValueError('verification regions required')
    score = snapshot['score']
    criteria = score['criteria']
    total = score['totals']
    earned = sum(c['effective_points'] for c in criteria if c['effective_points'] is not None)
    pending = sum(c['effective_max'] for c in criteria if c['effective_points'] is None)
    maximum = sum(c['effective_max'] for c in criteria)
    if total != {'earned': earned, 'loss': maximum-earned-pending, 'pending': pending, 'maximum': maximum, 'range': [earned, earned+pending]}:
        raise ValueError('score does not reconcile')
    s = _styles(); body = s['BrandBody']; small = s['BrandSmall']
    status = 'Nagekeken door je leerkracht' if final else ''
    intro = [_p(status, s['BrandHeading'])] if status else []
    intro.append(_p(f"{learner['name']} · {learner['class_name']}", body))
    number = lambda n: _num(n)
    result = _range(earned, pending, maximum)
    story = [_p('Puntenoverzicht', s['BrandTitle']), *intro, _p(f'Totaal: {result}', s['BrandHeading']),
             _p(f"Bevestigd puntenverlies: {number(total['loss'])} · Nog open: {number(pending)} punten", body),
             _p('Je score per criterium', s['BrandHeading']), _criterion_summary(criteria, 170*mm, small),
             _p('Je punten per oefening', s['BrandHeading'])]
    rows = [[_p(x, small) for x in ('Oefening / criterium', 'Behaald / max.', 'Verlies', 'Open')]]
    for qid in dict.fromkeys(c['question_id'] for c in criteria):
        group = [c for c in criteria if c['question_id'] == qid]
        qe = sum(c['effective_points'] for c in group if c['effective_points'] is not None)
        qp = sum(c['effective_max'] for c in group if c['effective_points'] is None)
        qm = sum(c['effective_max'] for c in group)
        rows.append([_p(x, small) for x in ('Oefening ' + str(int(qid.rsplit('ex', 1)[-1])), f'{number(qe)} / {number(qm)}', number(qm-qe-qp), number(qp))])
        for c in group:
            value = c['effective_points']; mx = c['effective_max']
            rows.append([_p(x, small) for x in (_criterion_label(c), f'{number(value) if value is not None else "–"} / {number(mx)}', number(mx-value) if value is not None else '–', number(mx) if value is None else '–')])
    story.append(_table(rows, [76*mm, 35*mm, 30*mm, 29*mm]))
    _document(folder / REPORT_FILES[0], story)
    feedback = snapshot['feedback']
    _feedback_card(folder / REPORT_FILES[1], learner, feedback, criteria, total, status)
    evidence = {e['evidence_id']: e for e in baseline['evidence']}
    by_id = {c['criterion_id']: c for c in criteria}
    markers, appendix = [], []
    for i, item in enumerate(feedback['priorities'], 1):
        found = False
        for eid in by_id[item['criterion_id']]['evidence_ids']:
            e = evidence.get(eid, {})
            if e.get('state') != 'present': continue
            for region in e.get('regions', []):
                try: page, box = _region(region, len(source))
                except ValueError: continue
                if any(page == rp and box[0] < rb[2] and box[2] > rb[0] and box[1] < rb[3] and box[3] > rb[1] for rp, rb in regions): continue
                markers.append((page, box, i)); found = True
        if not found: appendix.append((i, item))
    out = canvas.Canvas(str(folder / REPORT_FILES[2]), pagesize=A4, pageCompression=1)
    out.setTitle('Toets met feedback')
    for index in range(len(source)):
        page = source[index]
        image = page.render(scale=2).to_pil().convert('RGB')
        draw = ImageDraw.Draw(image)
        for pn, box in regions:
            if pn == index+1:
                x0, y0, x1, y1 = box
                draw.rectangle((math.floor(x0*image.width), math.floor(y0*image.height), math.ceil(x1*image.width), math.ceil(y1*image.height)), fill='white')
        width, height = page.get_size(); out.setPageSize((width, height))
        out.drawImage(ImageReader(image), 0, 0, width, height)
        numbered = set()
        outlines = set()
        badges = {}
        for pn, box, i in markers:
            if pn == index+1:
                x0, y0, x1, y1 = box
                outline = tuple(box)
                if outline not in outlines:
                    out.setStrokeColor(PURPLE); out.setLineWidth(1.5)
                    out.rect(x0*width, (1-y1)*height, (x1-x0)*width, (y1-y0)*height, fill=0, stroke=1)
                    outlines.add(outline)
                if i not in numbered:
                    badges.setdefault((x0, y0), []).append(str(i))
                    numbered.add(i)
        for (x0, y0), labels in badges.items():
            badge_width = 8 + 6*len(labels)
            left = max(1, x0*width - badge_width - 2)
            y = min(height-8, (1-y0)*height)
            out.setFillColor(PURPLE)
            out.roundRect(left, y-7, badge_width, 14, 7, fill=1, stroke=0)
            out.setFillColor(colors.white); out.setFont('Helvetica-Bold', 8)
            out.drawCentredString(left+badge_width/2, y-3, ' '.join(labels))
        out.showPage()
        page.close()
    out.save(); source.close()
    # Append a paginated legend, including findings whose geometry was uncertain.
    from pypdf import PdfReader, PdfWriter
    legend = BytesIO()
    legend_story = [_p('Feedback bij je toets', s['BrandTitle']), *intro, _p(f'Totaal: {result}', s['BrandHeading'])]
    for i, item in enumerate(feedback['priorities'], 1):
        legend_story.extend([_p(f"{i}. {item['title']}", s['BrandHeading']), _p(item['observation'], body), _p(f"Probeer dit: {item['correction']}", body)])
        if item.get('practice_id'):
            legend_story.append(_p('Oefen verder: ' + PRACTICE[item['practice_id']]['label'], body))
        if any(n == i for n, _ in appendix): legend_story.append(_p('De plaats op de toets is niet zeker aangeduid.', body))
    if pending: legend_story.append(_p(f'Nog na te kijken: {number(pending)} punten.', body))
    _document(legend, legend_story)
    writer = PdfWriter(); writer.append(str(folder / REPORT_FILES[2])); legend.seek(0); writer.append(PdfReader(legend))
    with (folder / REPORT_FILES[2]).open('wb') as output: writer.write(output)
    return tuple(folder / name for name in REPORT_FILES)
