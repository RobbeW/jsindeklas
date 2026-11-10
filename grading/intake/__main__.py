import argparse
import json
import os
from pathlib import Path
from . import scan

parser = argparse.ArgumentParser(description='Offline private assessment intake')
parser.add_argument('root')
parser.add_argument('manifest')
parser.add_argument('--output', required=True, help='private JSON destination outside the source root')
args = parser.parse_args()
root = Path(args.root).resolve(strict=True)
out = Path(args.output).resolve()
if out.is_relative_to(root):
    parser.error('output must be outside the source root')
result = scan(root, args.manifest)
fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    f.write('\n')
