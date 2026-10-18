from pathlib import Path
import numpy as np,json,hashlib
R=Path('/home/qian-qi/RAZR-SLIDE-bearing-orderfix-20261018');O=Path('/home/qian-qi/.local/share/razr-slide-evidence/bearing-followup-20261018');V=Path('/home/qian-qi/.local/share/razr-slide-evidence/volume-convergence-20261017/volume-v3/frame/level-2')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
L=dict(np.load(V/'loads.npz',allow_pickle=False));axes=[L[f'axis{i}'] for i in range(3)];xyz=L['xyz'][:,axes[0]].T
rows=[];inputs={str(V/'loads.npz'):sha(V/'loads.npz')}
for stage in ['install-force','service-locked']:
 src=R/'engineering/installation-control-20261018'/stage
 r=json.loads((src/'report.json').read_text());v=json.loads((src/'independent-report.json').read_text());assert r['passed'] and v['passed']
 for fn in ['report.json','full-fields.npz','independent-report.json']:inputs[str(src/fn)]=sha(src/fn)
 z=dict(np.load(src/'full-fields.npz',allow_pickle=False));offset=len(z['up'])+len(z['bp']);f=z['load'][offset:offset+len(z['uf'])];nodal=np.stack([f[a] for a in axes],axis=1)
 wrench=np.r_[nodal.sum(axis=0),np.cross(xyz,nodal).sum(axis=0)];force_scale=max(np.max(abs(z['forces'])),1e-20)
 unsupported=np.max(abs(wrench[:3]))>1e-7*force_scale
 rows.append({'stage':stage,'source_field_sha256':sha(src/'full-fields.npz'),'member_force_over_Epanel_mm2':wrench[:3].tolist(),'member_moment_over_Epanel_mm3_about_original_origin':wrench[3:].tolist(),'required_external_counter_force_over_Epanel_mm2':(-wrench[:3]).tolist(),'required_external_counter_moment_over_Epanel_mm3':(-wrench[3:]).tolist(),'force_scale_for_roundoff_check':float(force_scale),'unsupported_as_free_static_frame':bool(unsupported),'bubble_generalized_loads_have_zero_rigid_work':True})
assert not rows[0]['unsupported_as_free_static_frame'] and rows[1]['unsupported_as_free_static_frame']
result={'passed_equilibrium_diagnostic':True,'records':rows,'no_new_FE_solve_or_contact_equilibrium':True,'conclusion':'Unloaded frozen frame tractions are self-equilibrated; loaded frame requires a real support or opposing applied load. Numerical coordinate gauges cannot supply this force. Existing fixture distributes that required reaction but does not identify a real restraint.', 'input_sha256':inputs,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
for p,h in inputs.items():assert sha(p)==h
(O/'service-support-resultant.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
