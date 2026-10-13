#!/usr/bin/env python3
"""Atomically publish a small R79 incremental ZIP, never bundling original parents."""
import argparse,hashlib,json,os,tempfile
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

def package(src,dest):
 src=Path(src);dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
 files=[p for p in src.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc',) and p.name!='R79_SHA256_MANIFEST.json']
 # Only include controlled R79 files, not source temp archives or incidental logs.
 good={'src','tests','docs','results','verification'}
 files=[p for p in files if len(p.relative_to(src).parts)==1 or p.relative_to(src).parts[0] in good]
 files.sort(key=lambda p:str(p.relative_to(src)))
 sha=lambda b:hashlib.sha256(b).hexdigest()
 entries={str(p.relative_to(src)):sha(p.read_bytes()) for p in files}
 manifest={'revision':'R79-standstill-acceleration-gate','members_sha256':entries,
  'parent_CAD_archives_embedded':False,'candidate_go':False,'CAD_modify_go':False,'manufacturing_go':False}
 with tempfile.NamedTemporaryFile(prefix='.r79-build-',suffix='.zip',dir=dest.parent,delete=False) as f:
  temp=Path(f.name)
 try:
  with ZipFile(temp,'w',compression=ZIP_DEFLATED,compresslevel=8) as z:
   for p in files:z.write(p,arcname=str(p.relative_to(src)))
   z.writestr('R79_SHA256_MANIFEST.json',json.dumps(manifest,sort_keys=True,indent=2)+'\n')
  from R79_VERIFY_PACKAGE import verify
  first=verify(temp)
  if first['sha_manifest_member_count']!=len(files):raise RuntimeError('count mismatch')
  os.replace(temp,dest)
  final=verify(dest)
  if final['zip_sha256']!=first['zip_sha256']:raise RuntimeError('publish SHA changed')
  (dest.parent/(dest.name+'.sha256')).write_text(final['zip_sha256']+'  '+dest.name+'\n')
  return final
 finally:
  if temp.exists():temp.unlink()

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('src');ap.add_argument('dest');args=ap.parse_args()
 print(json.dumps(package(args.src,args.dest),sort_keys=True))
