"""Package members, archived test receipts and new STEP files: OFFLINE CHECK.
This verifies file consistency, not manufacturer provenance or real hardware.
"""
from pathlib import Path
import re,hashlib,json,unittest
from r25_capture import ROOT

def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def run():
    f=json.loads((ROOT/'audit/R38_R37_frozen_manifest.json').read_text())
    assert len(f['entries'])==1043
    for i in f['entries']:
        p=ROOT/i['path'];assert p.is_file() and p.stat().st_size==i['size'] and sha(p)==i['sha256'],i['path']
    inherited=json.loads((ROOT/'verification/R38_inherited_results.json').read_text())
    assert inherited['success'] and inherited['fresh_total']==661
    assert len(inherited['cases'])==18 and all(c['success'] and c['exit_code']==0 for c in inherited['cases'])
    for c in inherited['cases']:
        p=ROOT/c['log'];t=p.read_text()
        assert sha(p)==c['sha256'] and int(re.search(r'Ran\s+(\d+)\s+tests?',t).group(1))==c['actual_count'] and t.rstrip().endswith('OK')
    local=(ROOT/'verification/R38_new_tests.log').read_text()
    assert re.search(r'Ran 36 tests?',local) and local.rstrip().endswith('OK')
    manifest=json.loads((ROOT/'verification/R38_STEP_manifest.json').read_text())
    assert manifest['step_count']==5 and manifest['intentional_ghost_count']==1
    for z in manifest['scenes']:assert sha(ROOT/'cad'/z['file'])==z['sha256']
    res=json.loads((ROOT/'verification/R38_results.json').read_text())
    assert res['total_research_tests_reexecuted']==697 and res['manufacturing_go'] is False
    print('R38 OFFLINE OK: 1043 source members, 661+36 software tests, five STEP file hashes; hardware NO-GO')
if __name__=='__main__':run()
