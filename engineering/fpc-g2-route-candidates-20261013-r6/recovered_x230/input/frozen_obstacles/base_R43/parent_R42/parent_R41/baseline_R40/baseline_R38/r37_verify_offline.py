"""Offline self-consistency check; NOT proof of independently provided R36 source ZIP."""
import json,hashlib,re
from r25_capture import ROOT

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
  frozen=json.loads((ROOT/'audit/R37_R36_immutable.json').read_text())
  assert len(frozen['entries'])==977
  for r in frozen['entries']:
    p=ROOT/r['path'];assert p.is_file() and p.stat().st_size==r['size'] and sha(p)==r['sha256'],r['path']
  step=json.loads((ROOT/'verification/R37_STEP_manifest.json').read_text())
  assert step['count']==7 and step['ghost_count']==4
  for r in step['scenes']:
    assert sha(ROOT/'cad'/r['file'])==r['sha256'],r['file']
  original=json.loads((ROOT/'verification/R37_inherited_receipts.json').read_text())
  assert original['success'] and original['R36_fresh_inherited_count']==613
  for r in original['cases']:
    s=(ROOT/r['log']).read_text()
    assert sha(ROOT/r['log'])==r['sha256']
    assert re.search(r'Ran\s+(\d+)\s+tests?',s) and s.rstrip().endswith('OK')
  new=(ROOT/'verification/R37_new_48.log').read_text()
  assert re.search(r'Ran 48 tests?',new) and new.rstrip().endswith('OK')
  ret=json.loads((ROOT/'verification/R37_results.json').read_text())
  assert ret['total_fresh_test_count']==661 and ret['manufacturing_go'] is False
  print('OFFLINE R37 package self-consistency OK: 977 ancestor files, 661 research tests, 7 STEP scenes; NOT source identity or hardware qualification.')
if __name__=='__main__':run()
