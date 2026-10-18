"""Compare the predeclared four cells only after all independent passes exist.
The two original-target fields are explicitly prior verified baselines.
"""
from pathlib import Path
import json,hashlib,gzip
import numpy as np
from scipy.sparse import load_npz
ROOT=Path('/home/qian-qi/RAZR-SLIDE-rank-delivery-20261018')
BASE=Path('/home/qian-qi/.local/share/razr-slide-evidence/rank-replay-20261018')
OUT=Path('/home/qian-qi/.local/share/razr-slide-evidence/rank-followup-20261018')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
oldmanifest=json.loads((BASE/'pr32-before-fix/manifest.json').read_text())
oldident={r['path']:r for r in oldmanifest['files']}
readback=json.loads((OUT/'test_identity_readback.json').read_text())
assert readback['tested_commit']=='4b180d500be53ad7ab07905d6adc35dfd8945be0'
paths=[]
for sides in (256,512):
 paths.append((sides,1e-7,BASE/f'pr32-before-fix/p{sides}-t100',BASE/f'pr32-before-fix/audit-p{sides}-t100',True))
 paths.append((sides,2e-8,BASE/f'strict{sides}-v2',BASE/f'audit{sides}-v2',False))
missing=[str(ad/'report.json') for _,_,_,ad,_ in paths if not (ad/'report.json').exists()]
if missing:raise SystemExit('Independent strict result not yet available: '+', '.join(missing))
common=dict(np.load(BASE/'strict512-v2/panel/effective-loads.npz',allow_pickle=False))
meta=json.loads(gzip.decompress((ROOT/'engineering/contact-field-20261015/coupled-field-audit.json.gz').read_bytes()))['contact_patches']
raw=json.loads(gzip.decompress((ROOT/'engineering/contact-field-20261015/common-cell-results.json.gz').read_bytes()))
byname={p['patch']:p for p in meta};flat=[(byname[g['patch']],c) for g in raw for c in g['cells']]
assert len(flat)==5255
rows=[];reference=None;bound={}
for sides,target,src,audit,prior in paths:
 r=json.loads((src/'report.json').read_text());v=json.loads((audit/'report.json').read_text())
 assert r['passed'] and v['passed'] and r['case']==v['full_discrete_case']==6
 assert r['gap_tolerance_mm']==v['gap_tolerance_mm']==target
 assert v['total_regions']==5255 and v['minimum_covered_bound_mm']>=-target
 assert r['frozen_selection_sha256']==v['frozen_selection_sha256']==sha(ROOT/'engineering/joint-sensitivity-20261017/frozen-selection.json')
 if prior:
  for path in [src/'report.json',src/'full-fields.npz',audit/'report.json']:
   rec=oldident[str(path.relative_to(BASE/'pr32-before-fix'))];assert sha(path)==rec['sha256'] and path.stat().st_size==rec['bytes']
 else:
  assert (BASE/f'audit{sides}-v2.exit').read_text().strip()=='0'
  assert r['rank_fallback']=='qr_pivot'
 arrays={}
 for body in ['panel','frame']:
  arrays[body]=(load_npz(src/body/'coupling.npz'),dict(np.load(src/body/'local-blocks.npz',allow_pickle=False)),json.loads((src/body/'selection.json').read_text()))
 if reference is None:reference=arrays
 for body in arrays:
  aa,bb,ss=arrays[body];ar,br,sr=reference[body]
  assert ss==sr and (aa!=ar).nnz==0
  assert set(bb)==set(br) and all(np.array_equal(bb[k],br[k]) for k in bb)
  assert v['full_checks'][body]['internal_recovery']['private_DOFs_recovered']==(4321500 if body=='panel' else 5972100)
 x=dict(np.load(src/'full-fields.npz',allow_pickle=False))
 response=float(common['F'][:,2]@x['up']+common['Fb'][:,2]@x['bp'])
 energy=sum(float(v['full_checks'][b]['twice_strain_energy']) for b in ['panel','frame'])/2
 patches={k:{'force':np.zeros(3),'moment':np.zeros(3),'active_points':0} for k in byname}
 for point,f in zip(r['contact_points'][4:],x['forces'][4:]):
  m,c=flat[point['cell']];assert point['patch']==m['patch'];axis=m['normal_axis'];sign=m['normal_sign'];tan=[j for j in range(3) if j!=axis]
  xyz=np.zeros(3);xyz[tan]=point['xy'];xyz[axis]=1.2 if axis==2 else sign*36.325
  force=np.zeros(3);force[axis]=-sign*f
  acc=patches[m['patch']];acc['force']+=force;acc['moment']+=np.cross(xyz,force);acc['active_points']+=int(f>0)
 for acc in patches.values():
  acc['force']=acc['force'].tolist();acc['moment']=acc['moment'].tolist()
 row={'circle_sides':sides,'gap_target_mm':target,'source':str(src),'audit':str(audit),'prior_verified_baseline_not_rerun':prior,
      'case':6,'selected_faces':sum(len(z[2]) for z in arrays.values()),'new_trace_coefficients':len(x['bp'])+len(x['bf']),
      'contact_constraints':len(r['contact_points'])-4,'new_exchange_solves':len(r['history']),
      'independent_gap_bound_mm':v['minimum_covered_bound_mm'],'all_regions_audited':5255,
      'common_512_external_observation':response,'elastic_energy':energy,'bolt_forces':x['forces'][:4].tolist(),'patch_reactions':patches,
      'full_checks':v['full_checks'],'equilibrium_force_moment':v['balance'],'complementarity':v['contact_complementarity'],
      'solver_report_sha256':sha(src/'report.json'),'fields_sha256':sha(src/'full-fields.npz'),'independent_report_sha256':sha(audit/'report.json')}
 rows.append(row)
 for path in [src/'report.json',src/'full-fields.npz',audit/'report.json']:bound[str(path)]=sha(path)
lookup={(row['circle_sides'],row['gap_target_mm']):row for row in rows}
effects=[]
for sides in (256,512):
 a=lookup[sides,1e-7];b=lookup[sides,2e-8]
 effects.append({'type':'stricter_contact_target','circle_sides':sides,'relative_observation':b['common_512_external_observation']/a['common_512_external_observation']-1,'relative_energy':b['elastic_energy']/a['elastic_energy']-1})
for target in (1e-7,2e-8):
 a=lookup[256,target];b=lookup[512,target]
 effects.append({'type':'circle_refinement','target':target,'relative_observation':b['common_512_external_observation']/a['common_512_external_observation']-1,'relative_energy':b['elastic_energy']/a['elastic_energy']-1})
interaction={}
for key in ['common_512_external_observation','elastic_energy']:
 delta=(lookup[512,2e-8][key]-lookup[512,1e-7][key])-(lookup[256,2e-8][key]-lookup[256,1e-7][key])
 interaction[key]={'difference_of_differences':delta,'relative_to_256_original_target':delta/lookup[256,1e-7][key]}
result={'all_four_cells_independently_passed':True,'same_energy_and_selected_trace_space':True,'cases':rows,'effects':effects,'interaction':interaction,
 'unit_source_readback':readback,'input_sha256':bound,'script_sha256':sha(__file__),
 'old_target_baselines_prior_465cefa_new_strict_4b180d5':True,'one_normalized_physical_case_only':True,
 'gap_targets_numerical_not_manufacturing_precision':True,'sensitivity_not_continuum_error_or_capacity':True,
 'ideal_remote_fixture_neutral_Y_prescribed_pressure_and_initial_spring_force_retained':True,
 'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
for path,h in bound.items():assert sha(path)==h
out=OUT/'four-cell-summary.json';assert not out.exists();out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print('FOUR_CELL_COMPARISON_COMPLETE',json.dumps(effects),flush=True)
