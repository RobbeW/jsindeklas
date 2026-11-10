"""Conservative parser for the pinned timed jsPDF export revision."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

TIMED_CONFIG = json.loads(Path(__file__).with_name('timed-prompts.json').read_text(encoding='utf-8'))
TIMED_BINDING = {'assessment_id': 'toets_3', 'variant': 'regular',
                 'revision': 'toets-3-2026-01-09-v1', 'adapter_version': 'timed-jspdf-v1'}


def _normal(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text)).strip()


def _prompt(text):
    return _normal(re.sub(r'(?m)^\s*//\s?', '', text))


def _native(line, size):
    chars = line.get('chars', [])
    return bool(chars) and all(c.get('fontname') == 'Helvetica-Bold' and
                               abs(c.get('size', 0) - size) < .2 for c in chars)


def has_timed_footer(pages):
    """Recognize only the exporter's native timed-footer heading."""
    return any(line.get('text') == 'Door de browser geregistreerd:' and _native(line, 13)
               for lines, _ in pages for line in lines)


def inspect_timed(pages):
    """Inspect positioned native text; never return evidence for an uncertain route."""
    def result(disposition, reason, sections=None):
        return {'disposition': disposition, 'reasons': [reason], 'sections': sections or []}

    if not pages:
        return result('unsupported', 'cover_or_contents')
    flat = [(number, line) for number, (lines, _) in enumerate(pages, 1) for line in lines]
    cover = pages[0][0]
    if not any(l['text'] == 'JavaScript in de Klas - Gebundelde export' and _native(l, 18) for l in cover):
        return result('unsupported', 'cover_or_contents')
    footers = [i for i, (_, l) in enumerate(flat) if l['text'] == 'Door de browser geregistreerd:' and _native(l, 13)]
    if not footers:
        return result('unsupported', 'timed_footer_missing')
    if len(footers) != 1:
        return result('triage', 'timed_footer_multiple')
    footer_i = footers[0]
    footer_lines = flat[footer_i + 1:]
    versions = [l['text'][len('Versie:'):].strip() for _, l in footer_lines if l['text'].startswith('Versie:')]
    if len(versions) != 1:
        return result('triage', 'revision_missing_or_multiple')
    if versions[0] != TIMED_BINDING['revision']:
        return result('unsupported', 'timed_revision')
    url_starts = [i for i, (_, line) in enumerate(footer_lines) if line['text'].startswith('Pagina-URL:')]
    browser_starts = [i for i, (_, line) in enumerate(footer_lines) if line['text'].startswith('Browser:')]
    if len(url_starts) != 1 or len(browser_starts) != 1 or url_starts[0] >= browser_starts[0]:
        return result('triage', 'footer_route')
    url_text = ''.join(line['text'].strip() for _, line in footer_lines[url_starts[0]:browser_starts[0]])
    try:
        url = urlsplit(url_text.removeprefix('Pagina-URL:').strip())
        if (url.scheme not in ('http', 'https') or not url.netloc or url.query or url.fragment
                or not url.path.endswith('/platform.html')):
            return result('triage', 'footer_route')
    except ValueError:
        return result('triage', 'footer_route')
    if not all(any(l['text'].startswith(label) for _, l in footer_lines) for label in
               ('Poging:', 'Afgerond:', 'Start (UTC):', 'Einde (UTC):', 'Browser:')):
        return result('triage', 'footer_incomplete')
    heads = [(i, int(m.group(1)), int(m.group(2))) for i, (_, line) in enumerate(flat)
             if _native(line, 18) and (m := re.fullmatch(r'Oefening (\d+) / (\d+)', line['text']))]
    if [(n, total) for _, n, total in heads] != [(i, 9) for i in range(1, 10)]:
        return result('triage', 'section_order_or_missing')
    toc_labels = [i for i, l in enumerate(cover) if l['text'] == 'Inhoud:' and _native(l, 13)]
    if len(toc_labels) != 1 or not any(l['text'] == TIMED_CONFIG['title'] for l in cover[:toc_labels[0]]):
        return result('triage', 'cover_title_or_contents')
    toc = _normal(' '.join(l['text'] for l in cover[toc_labels[0] + 1:]))
    if toc != _normal(' '.join(q['title'] for q in TIMED_CONFIG['questions'])):
        return result('triage', 'contents_titles_or_order')
    if heads[0][0] <= 0 or flat[heads[0][0]][0] == 1 or footer_i <= heads[-1][0]:
        return result('triage', 'section_or_footer_position')
    sections, exercises = [], []
    labels = {'Opdracht:': 'prompt', 'Code:': 'code', 'Code van de laatste uitvoering:': 'earlier_code',
              'Console-uitvoer:': 'console', 'Console-uitvoer van eerdere code:': 'console',
              'Canvas:': 'canvas', 'Canvas van eerdere code:': 'canvas',
              'Beoordeling & feedback leerkracht:': 'review'}
    for i, (start, _, _) in enumerate(heads):
        end = heads[i+1][0] if i < 8 else footer_i
        lines = flat[start:end]
        q = TIMED_CONFIG['questions'][i]
        sections.append({'question_id': q['id'], 'start_page': lines[0][0],
                         'end_page': flat[end - 1][0]})
        if len(lines) < 2 or lines[1][1]['text'] != q['title']:
            return result('triage', 'section_title', sections)
        headings = {}
        for j, (_, line) in enumerate(lines):
            key = labels.get(line['text']) if _native(line, 13) else None
            if key:
                if key in headings:
                    return result('triage', 'duplicate_heading', sections)
                headings[key] = j
        if not all(k in headings for k in ('code', 'console', 'review')):
            return result('triage', 'required_heading_missing', sections)
        order = [headings[k] for k in ('prompt', 'code', 'earlier_code', 'console', 'canvas', 'review') if k in headings]
        if order != sorted(order):
            return result('triage', 'heading_order', sections)
        stale = lines[headings['console']][1]['text'] == 'Console-uitvoer van eerdere code:'
        if stale != ('earlier_code' in headings) or ('canvas' in headings and
           (lines[headings['canvas']][1]['text'] == 'Canvas van eerdere code:') != stale):
            return result('triage', 'earlier_output_conflict', sections)
        code_start = headings['code'] + 1
        code_end = headings.get('earlier_code', headings['console'])
        expected = _prompt(q['prompt'])
        starter_end = None
        for j in range(code_start, code_end):
            candidate = _prompt('\n'.join(line['text'] for _, line in lines[code_start:j+1]))
            if candidate == expected:
                starter_end = j + 1
                break
            if not expected.startswith(candidate):
                break
        if 'prompt' in headings:
            actual = _normal(' '.join(line['text'] for _, line in lines[headings['prompt']+1:headings['code']]))
            if actual != expected:
                return result('triage', 'prompt_mismatch', sections)
        elif starter_end is None:
            return result('triage', 'starter_missing_or_mismatch', sections)
        exercises.append({'lines': lines, 'headings': headings,
                          'answer_start': starter_end if starter_end is not None else code_start,
                          'stale_output': stale})
    return {'disposition': 'accepted', 'reasons': ['matched_timed_revision'], 'sections': sections,
            'footer': flat[footer_i], 'exercises': exercises}
