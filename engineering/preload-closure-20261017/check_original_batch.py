"""Compare current batch kernel with unchanged scalar auditor on actual frozen cells."""
from pathlib import Path
import json,gzip,sys,time,hashlib
import numpy as np
R=Path('/home/qian-qi/RAZR-SLIDE-preload-closure-20261017');O=Path('/tmp/razr-preload-closure-20261017');sys.path.insert(0,str(R/'integration'))
from contact_exchange import QuadraticGapBatch
from contact_patch_audit import extrema
cf=R/'engineering/contact-field-20261015/common-cell-results.json.gz';mf=R/'engineering/contact-field-20261015/coupled-field-audit.json.gz'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hashes={str(p):sha(p) for p in (cf,mf,R/'integration/contact_exchange.py',R/'integration/contact_patch_audit.py')}
groups=json.loads(gzip.decompress(cf.read_bytes()));metas={x['patch']:x for x in json.loads(gzip.decompress(mf.read_bytes()))['contact_patches']}
flat=[(metas[g['patch']],c) for g in groups for c in g['cells']];assert len(flat)==5255
polys=[c['polygon'] for _,c in flat];origins=[m['origin_tangent_mm'] for m,_ in flat];coeff=np.stack([c['quadratic_gap_coefficients'] for _,c in flat]);batch=QuadraticGapBatch(polys,origins);rows=[]
for case in range(8):
 start=time.monotonic();actual=batch.extrema(coeff[:,:,case]);batch_seconds=time.monotonic()-start
 start=time.monotonic();scalar=[extrema(coeff[i,:,case],polys[i],origins[i]) for i in range(len(flat))];scalar_seconds=time.monotonic()-start
 wantmin=np.array([x['minimum'] for x in scalar]);wantmax=np.array([x['maximum'] for x in scalar]);counts=np.array([x['candidate_count'] for x in scalar])
 minimum_error=float(np.max(abs(actual['minimum']-wantmin)));maximum_error=float(np.max(abs(actual['maximum']-wantmax)))
 assert max(minimum_error,maximum_error)<1e-10
 assert np.array_equal(actual['candidate_count'],counts)
 assert np.array_equal(actual['minimum'] < -1e-7,wantmin < -1e-7)
 rows.append({'case':case,'cells':5255,'minimum_error_mm':minimum_error,'maximum_error_mm':maximum_error,'candidate_counts_equal':True,'original_threshold_classification_equal':True,'negative_cells':int(np.sum(wantmin < -1e-7)),'batch_seconds_single_observation':batch_seconds,'scalar_seconds_single_observation':scalar_seconds})
 print('ORIGINAL_BATCH_MATCH',case,minimum_error,maximum_error,flush=True)
assert all(sha(Path(p))==h for p,h in hashes.items())
report={'input_sha256':hashes,'real_original_common_cells':True,'old_rejected_average_fields_not_new_contact_solutions':True,'total_polynomial_case_checks':42040,'all_passed':True,'rows':rows,'not_total_solver_speed_or_FE_convergence':True,'candidate_go':False,'manufacturing_go':False}
(O/'original-batch-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
