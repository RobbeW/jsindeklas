"""Positioned text shared by the offline PDF intake and evidence adapters."""


def positioned_lines(page, number):
    # Preserve spaces and indentation from characters, not normalized words.
    chars = sorted(page.chars, key=lambda char: (round(char['top'], 1), char['x0']))
    rows = []
    for char in chars:
        if not rows or abs(rows[-1][0]['top'] - char['top']) > 2:
            rows.append([char])
        else:
            rows[-1].append(char)
    lines = []
    for row in rows:
        row.sort(key=lambda char: char['x0'])
        box = [min(c['x0'] for c in row), min(c['top'] for c in row),
               max(c['x1'] for c in row), max(c['bottom'] for c in row)]
        lines.append({'text': ''.join(c['text'] for c in row),
                      'region': {'page': number, 'box': box}, 'chars': row})
    return lines


def positioned_pages(pdf):
    return [(positioned_lines(page, number), page) for number, page in enumerate(pdf.pages, 1)]
