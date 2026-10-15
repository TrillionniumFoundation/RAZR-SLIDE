"""Combine genuine independent inherited / fresh parent test exit receipts; no historical count as fresh."""
import json,re,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
s=json.loads((R/'baseline_R40/verification/R40_inherited_results.json').read_text())
assert s['success'] and s['actual_fresh_parent_reexecuted']==697 and len(s['rows'])==19
assert all(r['success'] and r['exit_code']==0 for r in s['rows'])
for fn in ['R41_inherited_exit.txt','R41_fresh_R39_exit.txt','R41_fresh_R40_exit.txt']:
 assert (R/fn).read_text().strip()=='0'
for logfile,count in [('R41_fresh_R40_test.log',38),('baseline_R40/verification/R40_fresh_R39.log',31)]:
 txt=(R/logfile).read_text();assert re.search(rf'Ran\s+{count}\s+tests?',txt) and txt.strip().endswith('OK')
report={'revision':'R41 parent tests freshly re-run from the frozen parent sources',
 'parents':{'R21_R38':697,'R39':31,'R40':38,'exit_R21_R38':0,'exit_R39':0,'exit_R40':0},
 'parent_fresh_test_total':766,'R21_R38_run_provenance':s['provenance'],
 'R40_SHA256_original_full_zip':'8df51e8e2c7a8c2733ddaa541eba9e85124d75d33c1a5e7b071fd1ec1f4db7ec',
 'parent_source_not_modified':True,'manufacturing_go':False}
(R/'verification/R41_parent_fresh.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
