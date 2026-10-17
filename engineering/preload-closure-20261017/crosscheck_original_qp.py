"""Re-solve each final finite contact system with the frozen pre-optimization solver."""
from pathlib import Path
import argparse,importlib.util,json,time,hashlib
import numpy as np
O=Path('/tmp/razr-preload-closure-20261017');RUN=O/'original-optimized-v1';SRC=Path('/home/qian-qi/RAZR-SLIDE-preload-closure-20261017/integration/contact_dual_active.py')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('frozen_original_force_solver',SRC);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('--cases',type=int,nargs='+',required=True);a=p.parse_args()
for case in a.cases:
 d=RUN/f'case-{case}';r=json.loads((d/'report.json').read_text());assert r['passed']
 target=d/'original-qp-crosscheck.json';assert not target.exists()
 snapshots=sorted(d.glob('checkpoint-*'));cp=snapshots[-1];meta=json.loads((cp/'manifest.json').read_text())
 assert sha(cp/'response.npz')==meta['response_sha256'] and sha(cp/'points.json')==meta['points_sha256']
 data=np.load(cp/'response.npz',allow_pickle=False);warm=np.array(r['forces']);S=data['H'].copy();assert len(warm)==len(S)
 S[np.arange(4),np.arange(4)]+=5.;q=data['qfree'][:,case%4]*1e-5-data['initialgap'];q[:4]+=.001
 start=time.monotonic();res=m.solve_force_qp(S,q,data['G'],data['loadG'][:,case%4]*1e-5,initial=warm);elapsed=time.monotonic()-start
 assert res['passed'],res['status'];lam=np.array(res['forces']);diff=lam-warm
 e0=float(.5*warm@S@warm-q@warm);e1=float(.5*lam@S@lam-q@lam)
 error=abs(e1-e0)/max(abs(e0),abs(e1),1e-20);assert error<1e-7
 result={'case':case,'frozen_original_solver_sha256':sha(SRC),'final_field_report_sha256':sha(d/'report.json'),'finite_checkpoint_sha256':sha(cp/'response.npz'),
 'passed':True,'original_qp_passed':True,'original_qp_iterations':res['iterations'],'maximum_force_difference':float(np.max(abs(diff))),
 'relative_objective_difference':error,'complementary_energy_of_difference':float(diff@S@diff),'seconds_single_run':elapsed,'finite_QP_only_not_a_second_full_field_audit':True,'original_solver_result':res}
 target.write_text(json.dumps(result,indent=2)+'\n');print('FROZEN_ORIGINAL_QP',case,res['iterations'],error,result['maximum_force_difference'],flush=True)
