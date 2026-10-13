#!/usr/bin/env python3
"""Verify every actual transferred STEP root, including non-solid leaves."""
import hashlib,json,platform,sys
from pathlib import Path
import cadquery as cq
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent
REPO=PROJECT.parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(REPO/'engineering/cad-review-20261013'))
sys.path.insert(0,str(REPO/'engineering/strict-motion-audit-20261013'))
from verify_step_payload import full_solid_payload
from occ_signed_volume import validated_solid_volume

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    rows=[]
    for path in sorted((PROJECT/'cad').glob('*.step')):
        before=sha(path);roots=cq.importers.importStep(str(path)).vals()
        solids,counts=full_solid_payload(roots)
        if sha(path)!=before:raise ValueError('STEP bytes changed during payload read')
        rows.append({'path':str(path.relative_to(PROJECT)),'sha256':before,
            'transferred_roots':len(roots),'visited_shape_types':counts,
            'valid_positive_solid_leaf_count':len(solids),'free_non_solid_leaf_count':0,
            'positive_signed_solid_volumes_mm3':[validated_solid_volume(s) for s in solids]})
    count=sum(r['valid_positive_solid_leaf_count'] for r in rows)
    if len(rows)!=16 or count!=180:raise ValueError('Actual payload topology differs from fixed research export contract')
    report={'host':platform.node(),'cadquery':cq.__version__,'script_sha256':sha(__file__),
        'readonly_guard_sha256':sha(REPO/'engineering/strict-motion-audit-20261013/verify_step_payload.py'),
        'actual_STEP_payload_rows':rows,'total_actual_valid_positive_solid_leaves':count,
        'free_non_solid_payload_leaves':0,'manufacturing_go':False}
    (HERE/'full-step-payload-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'STEP_files':len(rows),'positive_solid_leaves':count,'free_non_solid_leaves':0,'manufacturing_go':False},indent=2))
if __name__=='__main__':main()
