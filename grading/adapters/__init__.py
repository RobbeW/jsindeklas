"""Conservative offline evidence extraction for the W01 bundled export.

Coordinates are normalized to the visible page (0–1), top-left origin, one-based pages;
pdfplumber applies the page rotation and crop box. Blank is only a candidate:
a teacher must attest to the original before a zero may be assigned. Verification
regions are deliberately generous and must be redacted, not merely overlaid.
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re

import pdfplumber
from pypdf import PdfReader

from grading.intake import BINDING, FINGERPRINT, _route


def _box(chars, page):
    return {'page': page, 'box': [min(c['x0'] for c in chars), min(c['top'] for c in chars),
                                  max(c['x1'] for c in chars), max(c['bottom'] for c in chars)]}


def _lines(page, number):
    # Preserve spaces and indentation from positioned characters, not normalised words.
    chars = sorted(page.chars, key=lambda c: (round(c['top'], 1), c['x0']))
    rows = []
    for c in chars:
        if not rows or abs(rows[-1][0]['top'] - c['top']) > 2:
            rows.append([c])
        else:
            rows[-1].append(c)
    result = []
    for row in rows:
        row.sort(key=lambda c: c['x0'])
        text = ''.join(c['text'] for c in row)
        result.append({'text': text, 'region': _box(row, number), 'chars': row})
    return result


def extract(pdf_path, registration):
    """Extract JSON-compatible evidence from the same bytes checked against W01.

    Raises ValueError on stale/unaccepted registration or unsafe footer location.
    """
    if (registration.get('disposition') != 'accepted' or
        registration.get('binding') != BINDING or registration.get('route_fingerprint') != FINGERPRINT or
        not registration.get('submission_id')):
        raise ValueError('accepted W01 registration required')
    data = Path(pdf_path).read_bytes()
    digest = sha256(data).hexdigest()
    if digest != registration.get('sha256'):
        raise ValueError('source hash mismatch')
    reader = PdfReader(BytesIO(data), strict=True)
    disposition, _, sections = _route([p.extract_text() or '' for p in reader.pages])
    if disposition != 'accepted' or sections != registration.get('sections'):
        raise ValueError('registration route mismatch')
    evidence, verification, verification_safe = [], [], True
    with pdfplumber.open(BytesIO(data)) as pdf:
        pages = [(_lines(p, i + 1), p) for i, p in enumerate(pdf.pages)]
        for section in sections:
            qid = section['question_id']
            lines = []
            for number in range(section['start_page'], section['end_page'] + 1):
                rows, page = pages[number - 1]
                lines.extend((number, line) for line in rows)
            # Section bounds may share a page; use explicit heading boundaries.
            n = int(qid[-2:])
            headings = [i for i, (_, l) in enumerate(lines) if re.fullmatch(r'Oefening\s+\d+\s*/\s*9', l['text'].strip())]
            own = [i for i in headings if re.fullmatch(rf'Oefening\s+{n}\s*/\s*9', lines[i][1]['text'].strip())]
            if len(own) != 1:
                verification_safe = False
                for kind in ('code', 'console', 'canvas'):
                    evidence.append({'evidence_id': f'{qid}:{kind}', 'question_id': qid, 'kind': kind,
                                     'state': 'ambiguous', 'method': 'pdfplumber-positioned-text',
                                     'quote': '', 'regions': [], 'reason': 'section geometry cannot be located'})
                continue
            start = own[0]
            end = next((i for i in headings if i > start), len(lines))
            lines = lines[start:end]
            footers = [i for i, (_, l) in enumerate(lines) if l['text'].startswith('Pagina-URL:')]
            if len(footers) != 1:
                raise ValueError('verification metadata cannot be located')
            footer = footers[0]
            # Include the entire verification page and every following page in this
            # section, up to the next section heading. This also covers continuation.
            footer_starts = [i for i, (_, l) in enumerate(lines[:footer + 1]) if re.search(r'Verificatiegegevens:', l['text'], re.I)]
            if not footer_starts:
                raise ValueError('verification start cannot be located')
            footer = footer_starts[-1]
            fpage = lines[footer][0]
            for number in range(fpage, section['end_page'] + 1):
                p = pages[number - 1][1]
                # If another section shares the page, redact only above its heading.
                allrows = pages[number - 1][0]
                nxt = next((l for l in allrows if re.search(rf'Oefening\s+{n+1}\s*/\s*9', l['text'])), None)
                bottom = nxt['region']['box'][1] if nxt else p.height
                top = max(0, lines[footer][1]['region']['box'][1] - 2) if number == fpage else 0
                verification.append({'page': number, 'box': [0, top / p.height, 1, bottom / p.height]})
            def indexes(pattern):
                return [i for i, (_, l) in enumerate(lines[:footer]) if re.search(pattern, l['text'])]
            code = indexes(r'^\s*Code:\s*$')
            marker = indexes(r'Schrijf\s+hieronder\s+je\s+code\s*\.')
            console = indexes(r'^\s*Console-uitvoer:\s*$')
            canvas = indexes(r'^\s*Canvas:\s*$')
            damaged = any(re.search(r'\ufffd|\x00|\(cid:\d+\)', l['text']) for _, l in lines[:footer])
            duplicated = any(any(abs(a['x0']-b['x0']) < .1 and abs(a['top']-b['top']) < .1 and a['text'] == b['text'] for a, b in zip(l['chars'], l['chars'][1:])) for _, l in lines)
            affected_pages = {pn for pn, _ in lines[:footer]}
            def area_between(first, last):
                first_page, first_line = lines[first]
                last_page, last_line = lines[last]
                result = []
                for pn in range(first_page, last_page + 1):
                    p = pages[pn - 1][1]
                    top = first_line['region']['box'][3] if pn == first_page else 0
                    bottom = last_line['region']['box'][1] if pn == last_page else p.height
                    if bottom > top:
                        result.append({'page': pn, 'box': [0, top, p.width, bottom]})
                return result

            def images_in(regions):
                result = []
                for region in regions:
                    pn = region['page']
                    x0, top, x1, bottom = region['box']
                    for image in pages[pn - 1][1].images:
                        if image['x0'] < x1 and image['x1'] > x0 and image['top'] < bottom and image['bottom'] > top:
                            result.append({'page': pn, 'box': [image['x0'], image['top'], image['x1'], image['bottom']]})
                return result
            rotated = any((reader.pages[pn-1].rotation or 0) % 360 for pn in affected_pages)
            def item(kind, selected, state, reason):
                evidence.append({'evidence_id': f'{qid}:{kind}', 'question_id': qid, 'kind': kind,
                                 'state': state, 'method': 'pdfplumber-positioned-text',
                                 'quote': '\n'.join(l['text'] for _, l in selected) if state == 'present' else '',
                                 'regions': [l['region'] for _, l in selected], 'reason': reason})
            if len(code) != 1 or len(marker) != 1 or len(console) != 1 or not code[0] < marker[0] < console[0]:
                item('code', [], 'ambiguous', 'starter or answer boundaries unclear')
            else:
                selected = [(pn, l) for pn, l in lines[marker[0]+1:console[0]] if l['text'].strip()]
                starter = [l['text'].strip() for _, l in lines[code[0]+1:marker[0]] if l['text'].strip()]
                before = not starter or not re.match(r'^//\s*Gegeven:', starter[0])
                answer_area = area_between(marker[0], console[0])
                if damaged: state, reason = 'unreadable', 'damaged glyphs'
                elif duplicated or images_in(answer_area) or rotated or before: state, reason = 'ambiguous', 'possible layer, rotation or starter conflict'
                elif selected: state, reason = 'present', 'learner text after starter'
                else: state, reason = 'proven_blank', 'scaffold only; teacher attestation required'
                item('code', selected, state, reason)
                if not selected:
                    evidence[-1]['regions'] = answer_area
            code_evidence = evidence[-1]
            if len(console) == 1:
                stops = [i for i in canvas + indexes(r'^\s*Beoordeling\s*&\s*feedback') if console[0] < i < footer]
                stop = min(stops, default=footer)
                selected = [(pn, l) for pn, l in lines[console[0]+1:stop] if l['text'].strip() and l['text'].strip() != '(geen uitvoer)']
                # Empty console is never proof of a blank answer.
                state = 'ambiguous' if duplicated or images_in(area_between(console[0], stop)) or rotated else ('unreadable' if damaged else ('present' if selected else 'unavailable'))
                if selected and code_evidence['state'] == 'proven_blank':
                    code_evidence.update(state='ambiguous', reason='saved console output conflicts with scaffold-only code')
                item('console', selected, state, 'supporting output; empty output proves nothing')
            else: item('console', [], 'unavailable', 'console boundary missing')
            table = indexes(r'^\s*Beoordeling\s*&\s*feedback')
            stop = next((i for i in table if canvas and i > canvas[0]), footer)
            images = images_in(area_between(canvas[0], stop)) if len(canvas) == 1 else []
            item('canvas', [], 'present' if images else 'unavailable', 'embedded image requires original inspection' if images else 'canvas image not located')
            evidence[-1]['method'] = 'pdfplumber-image-region'
            evidence[-1]['regions'] = images
    for entry in evidence:
        for region in entry['regions']:
            page = pages[region['page'] - 1][1]
            x0, top, x1, bottom = region['box']
            region['box'] = [x0 / page.width, top / page.height, x1 / page.width, bottom / page.height]
    return {'submission_id': registration['submission_id'], 'source_sha256': digest, 'evidence': evidence,
            'verification_regions': verification, 'verification_safe': verification_safe}
