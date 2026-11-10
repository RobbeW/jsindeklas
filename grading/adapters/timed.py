"""Evidence extraction from the timed PDF's native exercise blocks."""
from io import BytesIO
import re

import pdfplumber

from grading.intake.timed import inspect_timed
from grading.pdf_text import positioned_pages


def _area_between(lines, first, last, pages):
    first_page, first_line = lines[first]
    last_page, last_line = lines[last]
    regions = []
    for number in range(first_page, last_page + 1):
        page = pages[number - 1][1]
        top = first_line['region']['box'][3] if number == first_page else 0
        bottom = last_line['region']['box'][1] if number == last_page else page.height
        if bottom > top:
            regions.append({'page': number, 'box': [0, top, page.width, bottom]})
    return regions


def _images(regions, pages):
    images = []
    for region in regions:
        number = region['page']
        _, top, _, bottom = region['box']
        for image in pages[number - 1][1].images:
            if image['top'] < bottom and image['bottom'] > top:
                images.append({'page': number, 'box': [image['x0'], image['top'], image['x1'], image['bottom']]})
    return images


def _quality(lines):
    if any(re.search(r'\ufffd|\x00|\(cid:\d+\)', line['text']) for _, line in lines):
        return 'unreadable'
    for _, line in lines:
        chars = line['chars']
        if any(abs(a['x0'] - b['x0']) < .1 and abs(a['top'] - b['top']) < .1 and
               a['text'] == b['text'] for a, b in zip(chars, chars[1:])):
            return 'ambiguous'
    return None


def _normalized(regions, pages):
    result = []
    for region in regions:
        number = region['page']
        page = pages[number - 1][1]
        x0, top, x1, bottom = region['box']
        result.append({'page': number, 'box': [x0 / page.width, top / page.height,
                                               x1 / page.width, bottom / page.height]})
    return result


def _exercise_evidence(qid, exercise, pages, geometry_safe):
    lines, heads = exercise['lines'], exercise['headings']
    stale_output = exercise['stale_output']
    end_code = heads.get('earlier_code', heads['console'])
    answer_start = exercise['answer_start']
    code = [(number, line) for number, line in lines[answer_start:end_code] if line['text'].strip()]
    answer_area = _area_between(lines, answer_start - 1, end_code, pages)
    code_state = _quality(code)
    if not geometry_safe or _images(answer_area, pages):
        code_state = 'ambiguous'
    code_state = code_state or ('present' if code else 'proven_blank')

    console_end = heads.get('canvas', heads['review'])
    console = [(number, line) for number, line in lines[heads['console'] + 1:console_end]
               if line['text'].strip() and line['text'].strip() != '(geen uitvoer)']
    if stale_output:
        console_state = 'unavailable'
        console_reason = 'console belongs to earlier code; consult the original'
    else:
        console_area = _area_between(lines, heads['console'], console_end, pages)
        console_state = _quality(console)
        if not geometry_safe or _images(console_area, pages):
            console_state = 'ambiguous'
        console_state = console_state or ('present' if console else 'unavailable')
        console_reason = 'supporting output; empty output proves nothing'
        if console and code_state == 'proven_blank':
            code_state = 'ambiguous'

    def item(kind, state, reason, text=(), regions=()):
        return {'evidence_id': f'{qid}:{kind}', 'question_id': qid, 'kind': kind,
                'state': state, 'method': 'pdfplumber-positioned-text',
                'quote': '\n'.join(line['text'] for _, line in text) if state == 'present' else '',
                'regions': _normalized(regions, pages), 'reason': reason}

    code_reason = {
        'present': 'final learner code', 'proven_blank': 'no answer text; teacher attestation required',
        'ambiguous': 'possible conflicting output, image, text layer or page geometry',
        'unreadable': 'damaged glyphs',
    }[code_state]
    canvas_images = []
    if not stale_output and geometry_safe and 'canvas' in heads:
        canvas_images = _images(_area_between(lines, heads['canvas'], heads['review'], pages), pages)
    canvas = item('canvas', 'present' if canvas_images else 'unavailable',
                  'canvas belongs to earlier code; consult the original' if stale_output else
                  ('embedded image requires original inspection' if canvas_images else 'canvas image not located'),
                  regions=canvas_images)
    canvas['method'] = 'pdfplumber-image-region'
    return [
        item('code', code_state, code_reason, code, [line['region'] for _, line in code] or answer_area),
        item('console', console_state, console_reason, console,
             [line['region'] for _, line in console] if not stale_output else []),
        canvas,
    ]


def extract_timed(data, registration):
    with pdfplumber.open(BytesIO(data)) as pdf:
        pages = positioned_pages(pdf)
        layout = inspect_timed(pages)
        if layout['disposition'] != 'accepted' or layout['sections'] != registration.get('sections'):
            raise ValueError('registration route mismatch')
        geometry_safe = all(not page.rotation and page.cropbox == page.mediabox for _, page in pages)
        evidence = []
        for section, exercise in zip(layout['sections'], layout['exercises']):
            evidence.extend(_exercise_evidence(section['question_id'], exercise, pages, geometry_safe))
        footer_page, heading = layout['footer']
        verification = []
        for number in range(footer_page, len(pages) + 1):
            page = pages[number - 1][1]
            top = max(0, heading['region']['box'][1] - 2) if number == footer_page else 0
            verification.append({'page': number, 'box': [0, top, page.width, page.height]})
        return {'submission_id': registration['submission_id'], 'source_sha256': registration['sha256'],
                'evidence': evidence, 'verification_regions': _normalized(verification, pages),
                'verification_safe': geometry_safe}
