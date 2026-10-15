"""Independent raw STEP closure: every assembly leaf, original material and roots.
Only the generic whole-payload reader is loaded, never any geometry generator.
"""
from pathlib import Path
import json,hashlib,importlib.util,sys,platform,time
R=Path('/home/qian-qi/RAZR-SLIDE-stow-closure-20261014');E=Path('/home/qian-qi/RAZR-SLIDE-stow-closure-evidence-20261014')
A=E/'v2-replay-184';G=E/'continuous-installation-gate';OLD=Path('/home/qian-qi/RAZR-SLIDE-stow-repair-evidence-20261014/sweep-fixed-slots')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('independent_whole_material',R/'integration/verify_stow_sweep.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
receipt=json.loads((A/'split-receipt.json').read_text());gate=json.loads((G/'report.json').read_text());oldr=json.loads((OLD/'report.json').read_text());assert sha(OLD/'report.json')=='da1b2e40d80cecaf1da38fe35b0754981d01fcbe75603f1e86d9fdc852178ffe'
inputs={str(p):sha(p) for p in [A/'split-receipt.json',G/'report.json',OLD/'report.json',R/'integration/verify_stow_sweep.py']};rows=[];stow=[];start=time.monotonic()
for exp in receipt['STEP_exports']:
 p=A/exp['path'];assert p.is_relative_to(A) and sha(p)==exp['sha256'];inputs[str(p)]=sha(p)
 roots=v.cq.importers.importStep(str(p)).vals();assert len(roots)==1;leaves,volume=v.material(roots[0]);assert len(leaves)==exp['expected_part_count']==46
 rows.append({'file':p.name,'positive_valid_complete_leaves':len(leaves),'signed_volume_sum_mm3':volume})
 if p.name.startswith('STOW'):stow=leaves
assert len(stow)==46 and len(rows)==2
used=[];paired=[]
for side in 'LR':
 for name,exp in gate['exports'].items():
  if not name.startswith(side+'_') or name[len(side)+1:] not in [r for r in ['ROOT_INNER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS','STOP_0','STOP_1','PAWL','KEY','OLD_COVER']]+[f'{n}_{i}' for n in ['CAP','SPRING_GUIDE','SPRING_CAP'] for i in range(2)]+[f'SCREW_{i}_{j}' for i in range(2) for j in range(2)]+[f'SPRING_{i}_OD_TOL_ENVELOPE' for i in range(2)]+[f'SPRING_SCREW_{i}_M1x3_NOMINAL' for i in range(2)]+[f'ROOT_JOIN_SCREW_{i}_M1x3_NOMINAL' for i in range(2)]:continue
  p=G/exp['path'];assert sha(p)==exp['sha256'];inputs[str(p)]=sha(p);single=v.single(v.cq.importers.importStep(str(p)).val());cert=exp['certificate']
  matches=[i for i,x in enumerate(stow) if abs(x.Volume()-cert['signed_volume_mm3'])<1e-7 and all(abs(getattr(x.BoundingBox(),k)-z)<1e-7 for k,z in cert['bounds_mm'].items())]
  assert len(matches)==1 and matches[0] not in used,(name,matches);i=matches[0];used.append(i)
  assert v.material(stow[i].cut(single),allow_empty=True)[1]<=1e-7 and v.material(single.cut(stow[i]),allow_empty=True)[1]<=1e-7
  paired.append(name)
assert len(used)==46, len(used)
material=[]
for row in oldr['rows']:
 side=row['side'];oldexp=row['exports']['original_root'];p=OLD/oldexp['path'];assert sha(p)==oldexp['sha256'];inputs[str(p)]=sha(p);old=v.single(v.cq.importers.importStep(str(p)).val())
 newexp=gate['exports'][side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS'];p=G/newexp['path'];inputs[str(p)]=sha(p);new=v.single(v.cq.importers.importStep(str(p)).val())
 p=G/gate['exports'][side+'_PAWL_RETURN']['path'];inputs[str(p)]=sha(p);returned=v.single(v.cq.importers.importStep(str(p)).val())
 p=G/gate['exports'][side+'_PAWL_INSERTION']['path'];inputs[str(p)]=sha(p);inserted=v.single(v.cq.importers.importStep(str(p)).val())
 removed=v.material(old.cut(new),allow_empty=True)[1];added=v.material(new.cut(old),allow_empty=True)[1];outside=v.material(old.cut(new).cut(returned).cut(inserted),allow_empty=True)[1]
 assert abs(removed-.0256)<1e-7 and outside<=1e-7 and abs(old.Volume()+added-removed-new.Volume())<1e-7
 bounds={k:getattr(new.BoundingBox(),k)-getattr(old.BoundingBox(),k) for k in ('xmin','xmax','ymin','ymax','zmin','zmax')};assert all(abs(x)<=1e-7 for x in bounds.values())
 material.append({'side':side,'old_root_mm3':old.Volume(),'new_root_mm3':new.Volume(),'added_mm3':added,'removed_mm3':removed,'original_removed_outside_two_declared_motion_envelopes_mm3':outside,'bounds_delta_mm':bounds,'new_root_complete_positive_single_solid':True})
assert inputs=={p:sha(p) for p in inputs};assert not any(n.startswith(('stow_continuous','stow_motion','stow_web','split_root','build_spring')) for n in sys.modules)
result={'host':platform.node(),'script_sha256':sha(__file__),'inputs_SHA256':inputs,'input_bytes_unchanged':True,'assemblies':rows,'complete_assembly_positive_leaves':92,'every_STOW_assembly_leaf_bijectively_matched_to_gate':46,'matched_names':paired,'material_reimport_check':material,'builder_imported':False,'same_CAD_kernel_not_cross_engine':True,'material_connectivity_not_strength_or_tolerance_qualification':True,'candidate_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
(E/'independent-v2-assembly-material.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'assembly_leaves':92,'matched_STOW_leaves':46,'roots':material,'manufacturing_go':False}))
