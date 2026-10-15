"""Restore exact original NPZ from bounded transport parts; never overwrite."""
from pathlib import Path
import argparse,hashlib,json
p=Path(__file__).resolve().parent
m=json.loads((p/'parts_manifest.json').read_text())
ap=argparse.ArgumentParser();ap.add_argument('--destination',type=Path);a=ap.parse_args()
target=a.destination or p.parents[1]/m['original_repository_path']
chunks=[]
for r in m['parts']:
 b=(p/r['path']).read_bytes()
 if len(b)!=r['size'] or hashlib.sha256(b).hexdigest()!=r['sha256']:raise ValueError('part mismatch')
 chunks.append(b)
b=b''.join(chunks)
if len(b)!=m['original_size'] or hashlib.sha256(b).hexdigest()!=m['original_sha256']:raise ValueError('original mismatch')
if target.exists():
 if target.read_bytes()!=b:raise ValueError('existing destination differs; no overwrite')
 status='existing_identical'
else:
 target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(b)
 status='restored'
print(json.dumps({'status':status,'bytes':len(b),'sha256':m['original_sha256'],'manufacturing_go':False}))
