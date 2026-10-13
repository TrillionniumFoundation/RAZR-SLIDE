#!/usr/bin/env python3
"""Check atomic R79 incremental archive CRC, member uniqueness and SHA256 manifest."""
import argparse,hashlib,json
from zipfile import ZipFile
from pathlib import Path

def verify(path):
 p=Path(path);h=hashlib.sha256(p.read_bytes()).hexdigest()
 with ZipFile(p) as z:
  names=z.namelist()
  if len(names)!=len(set(names)):raise RuntimeError('Duplicate member!')
  bad=z.testzip()
  if bad:raise RuntimeError(f'Bad CRC: {bad}')
  manifest=json.loads(z.read('R79_SHA256_MANIFEST.json'))
  actual={n:hashlib.sha256(z.read(n)).hexdigest() for n in names if n!='R79_SHA256_MANIFEST.json'}
  if actual!=manifest['members_sha256']:raise RuntimeError('ZIP member SHA mismatch')
  if manifest['candidate_go'] or manifest['CAD_modify_go'] or manifest['manufacturing_go']:raise RuntimeError('False qualification!')
 return {'zip_sha256':h,'zip_member_count':len(names),'sha_manifest_member_count':len(actual),'all_CRC_SHA256_pass':True,'manufacturing_go':False}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('zip_path');args=ap.parse_args()
 print(json.dumps(verify(args.zip_path),sort_keys=True))
