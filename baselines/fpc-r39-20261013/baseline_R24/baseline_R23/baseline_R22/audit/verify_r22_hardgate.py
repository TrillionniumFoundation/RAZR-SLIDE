"""Verify archived R22 engineering package bytes after extracting the archive."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
j=json.loads((root/'audit/R22_content_manifest.json').read_text(encoding='utf-8'))
for row in j['files']:
    p=(root/row['path']).resolve()
    if not p.is_relative_to(root.resolve()):raise SystemExit('BAD PATH')
    if not p.is_file():raise SystemExit('MISSING '+row['path'])
    if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise SystemExit('SHA FAILURE '+row['path'])
assert j['manufacturing_go'] is False
assert json.loads((root/'verification/R22_adversarial_results.json').read_text())['manufacturing_go'] is False
print('PASS',len(j['files']),'files SHA256; MANUFACTURING NO-GO remains enforced')
