"""Offline, read-only intake.

scan(root, manifest) accepts a directory and a dict (or path to JSON) with
``entries``: [{roster_id, class_id, name, class_name, assessment_id,
attempt_slot, source}], and optional ``managed_outputs`` relative paths.
It returns private JSON-compatible results. Paths are relative to root; symlinks
and traversal are refused. The manifest and output must remain teacher-private.
No registry or source is written; submission IDs are stable for identical bytes.
CLI: python -m grading.intake ROOT MANIFEST --output PRIVATE_JSON
Section page bounds are inclusive and 1-based, for W02; raw page text is not
emitted. A path under a managed output is excluded, including on rescans.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from pypdf import PdfReader

CONFIG = json.loads(Path(__file__).with_name('prompts.json').read_text(encoding='utf-8'))
BINDING = {'assessment_id': 'toets_3', 'variant': 'regular', 'revision': 'legacy-toets-4-741bede', 'adapter_version': 'bundled-jspdf-v1'}
FINGERPRINT = hashlib.sha256(json.dumps({'binding': BINDING, 'config': CONFIG}, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', s)).strip()


def _prompt(s):
    # Exporter wraps long comments; collapse whitespace and line comment markers.
    return _norm(re.sub(r'(?m)^\s*//\s?', '', unicodedata.normalize('NFC', s)))


def _resolve(root, relative):
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ValueError('invalid relative path')
    p = PurePosixPath(relative)
    if p.is_absolute() or any(part in ('.', '..') for part in p.parts):
        raise ValueError('invalid relative path')
    path = root
    for part in p.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('symlink refused')
    if not path.resolve().is_relative_to(root):
        raise ValueError('path outside root')
    return path


def _route(pages):
    text = '\n'.join(pages)
    if 'JavaScript in de Klas' not in pages[0] or 'Gebundelde export' not in pages[0] or 'Inhoud:' not in pages[0]:
        return 'unsupported', ['cover_or_contents'], []
    positions = list(re.finditer(r'^Oefening[ \t]+(\d+)[ \t]*/[ \t]*9[ \t]*$', text, re.M))
    if [int(m.group(1)) for m in positions] != list(range(1, 10)):
        return 'triage', ['section_order_or_missing'], []
    toc = _norm(text[:positions[0].start()])
    cursor = 0
    for q in CONFIG['questions']:
        location = toc.find(_norm(q['title']), cursor)
        if location < 0:
            return 'triage', ['contents_titles_or_order'], []
        cursor = location + len(_norm(q['title']))
    bounds = []
    starts = []
    pos = 0
    for page in pages:
        starts.append(pos)
        pos += len(page) + 1
    for i, m in enumerate(positions):
        end = positions[i+1].start() if i < 8 else len(text)
        section = text[m.end():end]
        q = CONFIG['questions'][i]
        start_page = sum(x <= m.start() for x in starts)
        end_page = sum(x < end for x in starts)
        bounds.append({'question_id': q['id'], 'start_page': start_page, 'end_page': end_page})
        if not _norm(section).startswith(_norm(q['title'])):
            return 'triage', ['section_title'], bounds
        code = re.search(r'^Code:[ \t]*\n(.*?)^Console-uitvoer:', section, re.S | re.M)
        if not code:
            return 'triage', ['code_block_missing'], bounds
        marker = re.search(r'Schrijf\s+hieronder\s+je\s+code\s*\.', code.group(1))
        given = re.search(r'//\s*Gegeven\s*:', code.group(1))
        if not given or not marker or given.start() > marker.start():
            return 'triage', ['starter_missing'], bounds
        actual = _prompt(code.group(1)[given.start():marker.end()])
        expected = _prompt(q['prompt'])
        if actual != expected:
            # A complete but different prompt is a different revision, not an answer.
            return 'unsupported', ['prompt_revision'], bounds
        urls = re.findall(r'^Pagina-URL:[ \t]*(\S+)', section, re.M)
        if len(urls) != 1:
            return 'triage', ['verification_url_missing_or_multiple'], bounds
        try:
            url = urlsplit(urls[0])
        except ValueError:
            return 'triage', ['verification_url_invalid'], bounds
        if url.scheme not in ('http', 'https') or not url.netloc or not url.path.endswith('/evaluaties/toets_4.html'):
            return 'triage', ['verification_route_conflict'], bounds
    return 'accepted', ['matched_legacy_prompt_and_route'], bounds


def scan(root, manifest):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('root must be a directory')
    if not isinstance(manifest, dict):
        manifest = json.loads(Path(manifest).read_text(encoding='utf-8'))
    if not isinstance(manifest, dict):
        raise ValueError('manifest must be a JSON object')
    entries = manifest.get('entries')
    if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
        raise ValueError('entries must be a list of objects')
    output_paths = manifest.get('managed_outputs', [])
    if not isinstance(output_paths, list):
        raise ValueError('managed_outputs must be a list')
    managed = [_resolve(root, p) for p in output_paths]
    identities = {}
    for entry in entries:
        fields = ('name', 'class_name', 'roster_id', 'class_id')
        if all(isinstance(entry.get(k), str) and entry[k].strip() for k in fields):
            name_and_class = (_norm(entry['name']), _norm(entry['class_name']))
            identities.setdefault(name_and_class, set()).add((entry['roster_id'], entry['class_id']))
    results = []
    for entry in entries:
        r = {'source': entry.get('source'), 'roster_id': entry.get('roster_id'), 'class_id': entry.get('class_id'), 'attempt_slot': entry.get('attempt_slot'), 'binding': dict(BINDING), 'route_fingerprint': FINGERPRINT}
        results.append(r)
        required = ('source', 'roster_id', 'class_id', 'name', 'class_name', 'assessment_id', 'attempt_slot')
        if any(not isinstance(entry.get(k), str) or not entry[k].strip() for k in required):
            r.update(disposition='triage', reasons=['manifest_fields_missing']); continue
        if entry['assessment_id'] != BINDING['assessment_id']:
            r.update(disposition='unsupported', reasons=['assessment_mismatch']); continue
        try:
            path = _resolve(root, entry['source'])
            if any(path == p or path.is_relative_to(p) for p in managed):
                r.update(disposition='excluded', reasons=['managed_output']); continue
            if not path.is_file():
                if not path.exists():
                    raise FileNotFoundError(path)
                raise ValueError('source is not a regular file')
            data = path.read_bytes()
        except FileNotFoundError:
            r.update(disposition='missing', reasons=['source_missing']); continue
        except (OSError, ValueError):
            r.update(disposition='triage', reasons=['source_path_refused']); continue
        digest = hashlib.sha256(data).hexdigest()
        r.update(sha256=digest, submission_id='sub_' + hashlib.sha256(('jsik-intake-v1:' + digest).encode()).hexdigest())
        try:
            from io import BytesIO
            reader = PdfReader(BytesIO(data), strict=True)
            pages = [p.extract_text() or '' for p in reader.pages]
            if not pages:
                raise ValueError('empty PDF')
        except Exception:
            r.update(disposition='corrupt', reasons=['pdf_unreadable']); continue
        disposition, reasons, sections = _route(pages)
        r.update(disposition=disposition, reasons=reasons, sections=sections)
        if disposition == 'accepted':
            name = re.search(r'^Naam:\s*(.*?)\s*$', pages[0], re.M)
            klass = re.search(r'^Klas:\s*(.*?)\s*$', pages[0], re.M)
            if not name or not klass or _norm(name.group(1)) != _norm(entry['name']) or _norm(klass.group(1)) != _norm(entry['class_name']):
                r.update(disposition='mismatch', reasons=['visible_identity_mismatch'])
            elif len(identities[(_norm(entry['name']), _norm(entry['class_name']))]) > 1:
                r.update(disposition='triage', reasons=['visible_identity_ambiguous'])
    # Conflicts include all readable files, regardless of their individual routing status.
    for i, a in enumerate(results):
        if 'sha256' not in a: continue
        for b in results[i+1:]:
            if 'sha256' not in b: continue
            same_person = (a['roster_id'], a['class_id']) == (b['roster_id'], b['class_id'])
            same_slot = same_person and a['attempt_slot'] == b['attempt_slot']
            if a['sha256'] == b['sha256']:
                reason = 'duplicate_bytes' if same_person else 'bytes_claimed_by_different_learners'
            elif same_person:
                reason = 'competing_hand_ins' if same_slot else 'multiple_attempts'
            else:
                continue
            for r in (a, b):
                r['disposition'] = 'conflict'
                if reason not in r['reasons']: r['reasons'].append(reason)
    return {'version': 1, 'results': results}
