"""Local file primitives for the private grading workflow."""

import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


def sha256_file(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def read_json(path):
    with Path(path).open(encoding="utf-8") as source:
        return json.load(source)


def write_json(path, value):
    """Replace a complete private JSON file, preserving it on write failure."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary:
            temp_path = Path(temporary.name)
            json.dump(value, temporary, ensure_ascii=False, allow_nan=False, indent=2)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        temp_path.replace(path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@contextmanager
def file_lock(path):
    """Serialize local mutations using a separate, stable lock file."""
    import fcntl

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with os.fdopen(os.open(path, os.O_CREAT | os.O_WRONLY, 0o600), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield
