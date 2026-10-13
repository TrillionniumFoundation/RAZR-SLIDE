"""For offline re-verification only: embedded R35 frozen-member hashes.
No original ZIP signature is re-verified unless original ZIP is separately supplied.
"""
import json,hashlib
from r25_capture import ROOT

def run():
 d=json.loads((ROOT/'audit/R36_R35_immutable.json').read_text())
 assert d['original_file_count']==853
 for a in d['members']:
  p=ROOT/a['path']
  assert p.is_file() and p.stat().st_size==a['size'] and hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'],a['path']
 print('R36 OFFLINE embedded ancestor manifest matched',len(d['members']),
       'not equivalent to external-original ZIP provenance proof',flush=True)
if __name__=='__main__':run()
