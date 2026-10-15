"""Conditional frictionless support at the real cover/post load patches.

Unit magnitudes are normalization. Contact-node LP gives feasibility and a
minimum within that finite normal-ray model, not actual screw loads or a load
rating. All four screws and the frame are still treated as fixed reactions.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np
from scipy.optimize import linprog
R=Path('/home/qian-qi/RAZR-SLIDE-panel-shear-v2-20261015');O=Path('/tmp/razr-panel-shear-20261015')
sys.path.insert(0,str(R/'integration'))
import verify_panel_shear_key as v
_,new,h=v.w.w.w.load_new(O/'native-v2/manifest.json')
sp=O/'native-v2/full-verification.json';subset=json.loads(sp.read_text());h[str(sp)]=v.v.sha(sp)
assert subset['passed'] and subset['source_sha256']==v.v.sha(R/'integration/panel_shear_key.py')
rows=[]
for record in subset['native_panel_support_contacts']:
 dx=record['dx_mm'];sign=-1 if dx<0 else 1;side='L' if dx<0 else 'R'
 panel=new['A_BACK_PANEL'].translate((dx,0,0));cover=new[side+'_OLD_COVER'].translate((dx+sign*.02,0,0))
 source=v.w.planar_contacts(cover,{'A_BACK_PANEL':panel})
 if len(source)!=4 or any(p['normal_into_cover'][0]*sign>-.999999 for p in source):raise ValueError('actual cover reaction patch missing')
 support=record['patches'];origin=np.asarray(panel.Center().toTuple());columns=[];weights=[];owners=[]
 for patch in support:
  normal=np.array(patch['normal_into_cover'])
  for point in patch['points_mm']:
   columns.append(np.r_[normal,np.cross(np.array(point)-origin,normal)])
   weights.append(abs(normal[2]) if patch['neighbor'].startswith('FRAME_') else 0.)
   owners.append(patch['neighbor'])
 W=np.asarray(columns).T;c=np.asarray(weights)
 points=sorted({tuple(float(x) for x in pt) for patch in source for pt in patch['points_mm']})
 cases=[]
 for point in points:
  force=np.array([sign,0.,0.]);external=np.r_[force,np.cross(np.array(point)-origin,force)]
  fit=linprog(c,A_eq=W,b_eq=-external,bounds=(0,None),method='highs')
  if fit.status not in (0,2):raise ValueError('unit patch feasibility unresolved')
  entry={'source_point_mm':point,'feasible':bool(fit.success),'solver_status':int(fit.status)}
  if fit.success:
   residual=float(np.max(np.abs(W@fit.x+external)))
   if residual>1e-8 or np.min(fit.x)<-1e-8:raise ValueError('invalid normal reaction certificate')
   entry.update({'minimum_total_screw_axial_N_per_unit_outward_N':float(c@fit.x),'residual':residual,
                 'coefficients_N':fit.x.tolist()})
  cases.append(entry)
 if not all(x['feasible'] for x in cases):raise ValueError('a real load-patch point lacks support')
 records={'side':side,'panel_dx_mm':dx,'cover_outward_relative_panel_mm':.02,'actual_cover_load_patches':source,
          'support_matrix':W.tolist(),'screw_axial_objective':c.tolist(),'reaction_owners':owners,'cases':cases,
          'minimum_over_checked_points_N_per_N':min(x['minimum_total_screw_axial_N_per_unit_outward_N'] for x in cases),
          'maximum_over_checked_points_N_per_N':max(x['minimum_total_screw_axial_N_per_unit_outward_N'] for x in cases)}
 rows.append(records)
 print('LOAD_PATCH',side,'points',len(cases),'screw_axial_LP_min_range',[records['minimum_over_checked_points_N_per_N'],records['maximum_over_checked_points_N_per_N']],flush=True)
assert all(v.v.sha(path)==sha for path,sha in h.items())
result={'source_sha256':v.v.sha(__file__),'input_sha256':h,'rows':rows,
        'all_real_patch_vertices_and_centers_feasible':True,
        'convex_combination_only_extends_this_fixed_normal_ray_model':True,
        'not_actual_load_or_uniform_screw_sharing':True,
        'finite_reaction_ray_model_minimum_not_certified_continuous_contact_optimum':True,
        'actual_thread_preload_material_stiffness_capacity_qualified':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
(O/'frame-anchor-patch-budget-v2.json').write_text(json.dumps(result,indent=2)+'\n')
