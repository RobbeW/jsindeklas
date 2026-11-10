"""Private, revision-bound promotion of learner reports."""
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path

from grading.common import read_json, sha256_file, write_json
from grading.intake import _resolve
from grading.reports import REPORT_FILES, REPORT_LAYOUT, render_reports
from grading.review_store import current_approval


def _key(value):
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _identity(snapshot):
    binding = snapshot['binding']
    if not isinstance(binding.get('submission_id'), str) or not binding['submission_id'] or not isinstance(binding.get('identity_fingerprint'), str) or not binding['identity_fingerprint']:
        raise ValueError('submission and identity binding required')
    return {'format': 'jsik-release-v1', 'binding': binding, 'report_layout': REPORT_LAYOUT,
            'revision': snapshot['revision'], 'snapshot_sha256': _fingerprint(snapshot)}


def _version(identity):
    return f"r{identity['revision']}-{identity['report_layout']}-{identity['snapshot_sha256']}"


def _safe(root, path):
    root = Path(root)
    if root.is_symlink():
        raise ValueError("symlink in output path")
    _resolve(root.resolve(), path.relative_to(root).as_posix())
    return path


def _paths(root, submission):
    key = _key(submission)
    return _safe(root, root / 'learner' / key), _safe(root, root / 'teacher' / 'releases' / (key + '.json'))


def _verified(folder, manifest):
    try:
        files = manifest['files']
        return (folder.is_dir() and not folder.is_symlink()
                and set(p.name for p in folder.iterdir()) == set(REPORT_FILES)
                and set(files) == set(REPORT_FILES)
                and all((folder / n).is_file() and not (folder / n).is_symlink()
                        and sha256_file(folder / n) == files[n] for n in REPORT_FILES))
    except (OSError, KeyError, TypeError):
        return False


def promote(root, source_pdf, learner, baseline, snapshot, validate_current):
    """Return the directory containing exactly the three approved learner PDFs.

    The caller holds inventory and review locks throughout this operation.
    """
    root = Path(root)
    identity = _identity(snapshot)
    if not current_approval(snapshot) or snapshot['binding'] != baseline.get('binding'):
        raise ValueError('current approval and matching binding required')
    source_hash = snapshot['binding']['source_sha256']
    if sha256_file(source_pdf) != source_hash:
        raise ValueError('source changed')
    parent, pointer = _paths(root, snapshot['binding']['submission_id'])
    if pointer.exists():
        try:
            existing = read_json(pointer)
            if (not isinstance(existing, dict) or existing.get('format') != 'jsik-release-v1'
                    or existing['binding']['submission_id'] != snapshot['binding']['submission_id']):
                raise ValueError('unowned current pointer')
        except (OSError, KeyError, TypeError):
            raise ValueError('unowned current pointer') from None
    if validate_current() is False:
        raise ValueError('review changed')
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    pointer.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    version = _version(identity)
    target = parent / version
    manifest_path = _safe(root, pointer.parent / (pointer.stem + '-' + version + '.json'))
    _safe(root, target)
    # A manifest written before the atomic directory move identifies our interrupted work.
    if not target.exists() and not target.is_symlink() and manifest_path.is_file() and not manifest_path.is_symlink():
        try:
            interrupted = read_json(manifest_path)
        except (OSError, ValueError):
            raise ValueError('unowned or incomplete release') from None
        if (not isinstance(interrupted, dict) or any(interrupted.get(k) != v for k, v in identity.items())
                or set(interrupted.get('files', {})) != set(REPORT_FILES)):
            raise ValueError('unowned or incomplete release')
        manifest_path.unlink()
    if target.exists() or target.is_symlink() or manifest_path.exists() or manifest_path.is_symlink():
        try:
            manifest = read_json(manifest_path)
        except (OSError, ValueError):
            raise ValueError('unowned or incomplete release') from None
        if not isinstance(manifest, dict) or any(manifest.get(k) != v for k, v in identity.items()) or not _verified(target, manifest):
            raise ValueError('unowned or damaged release')
    else:
        # A private temporary directory is automatically removed after failed rendering.
        with tempfile.TemporaryDirectory(prefix='.release-', dir=parent) as temporary:
            stage = Path(temporary) / 'render'
            stage.mkdir(mode=0o700)
            render_reports(stage, source_pdf, learner, baseline, snapshot, final=True)
            if sha256_file(source_pdf) != source_hash:
                raise ValueError('source changed during rendering')
            if set(p.name for p in stage.iterdir()) != set(REPORT_FILES):
                raise ValueError('incomplete report set')
            if validate_current() is False:
                raise ValueError('review changed during rendering')
            manifest = {**identity, 'files': {name: sha256_file(stage / name) for name in REPORT_FILES}}
            # Record ownership before moving the set; an interrupted move can be retried.
            write_json(manifest_path, manifest)
            stage.rename(target)
    if sha256_file(source_pdf) != source_hash:
        raise ValueError('source changed')
    if validate_current() is False or not current_approval(snapshot):
        raise ValueError('review changed')
    write_json(pointer, {**manifest, 'version': version})
    return target


def release_status(root, submission_id, snapshot_or_none):
    try:
        parent, pointer = _paths(Path(root), submission_id)
    except ValueError:
        return 'stale'
    if not pointer.exists() and not pointer.is_symlink():
        return 'unreleased'
    try:
        manifest = read_json(pointer)
        snapshot = snapshot_or_none
        identity = _identity(snapshot)
        version = _version(identity)
        if (not current_approval(snapshot) or snapshot['binding']['submission_id'] != submission_id
                or any(manifest.get(k) != v for k, v in identity.items())
                or manifest.get('version') != version or not _verified(parent / version, manifest)):
            return 'stale'
        stored_path = _safe(Path(root), pointer.parent / (pointer.stem + '-' + version + '.json'))
        stored = read_json(stored_path)
        if stored != {k: v for k, v in manifest.items() if k != 'version'}:
            return 'stale'
        return 'current'
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return 'stale'


def _cell(value):
    if value is None:
        return ''
    if isinstance(value, (list, tuple)):
        value = '–'.join(str(x).replace('.', ',') for x in dict.fromkeys(value))
    text = str(value)
    if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        return "'" + text
    return text


def write_overview(root, rows):
    """Write a private immutable teacher CSV and atomically update its pointer."""
    root = Path(root)
    folder = _safe(root, root / 'teacher')
    pointer = _safe(root, folder / 'leerkrachtoverzicht-current.json')
    if pointer.exists():
        try:
            previous = read_json(pointer)
            if not isinstance(previous, dict) or previous.get('format') != 'jsik-overview-v1':
                raise ValueError('unowned overview pointer')
        except (OSError, TypeError):
            raise ValueError('unowned overview pointer') from None
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    fields = ('name', 'class_name', 'roster_id', 'class_id', 'source', 'assessment_id',
              'revision', 'status', 'range', 'maximum', 'release_status')
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8-sig', newline='', dir=folder, delete=False) as out:
            temp = Path(out.name)
            writer = csv.writer(out)
            writer.writerow(fields)
            for row in rows:
                writer.writerow([_cell(row.get(field)) for field in fields])
            out.flush()
            os.fsync(out.fileno())
        digest = sha256_file(temp)
        version = _safe(root, folder / ('overview-' + digest))
        path = _safe(root, version / 'leerkrachtoverzicht.csv')
        if version.exists():
            if not version.is_dir() or set(p.name for p in version.iterdir()) != {path.name} or not path.is_file() or sha256_file(path) != digest:
                raise ValueError('unowned overview version')
        else:
            with tempfile.TemporaryDirectory(prefix='.overview-', dir=folder) as staging:
                staged = Path(staging) / 'version'
                staged.mkdir(mode=0o700)
                temp.replace(staged / path.name)
                staged.rename(version)
        write_json(pointer, {'format': 'jsik-overview-v1', 'file': str(path.relative_to(folder)), 'sha256': digest})
        return path
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
