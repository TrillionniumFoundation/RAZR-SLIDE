"""Independent accounting of deliberately changed cover interfaces and STEP assemblies."""
from pathlib import Path
import argparse,json,hashlib,tempfile,tarfile,sys
ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--stage',type=Path,required=True);ap.add_argument('--assembly',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
sys.path.insert(0,str(a.repo/'integration'))
import cam_contact_native as n
from translation_regions import regions,subtract_regions
from verify_contact_motion import PARTS

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
 vals=n.cq.importers.importStep(str(p)).vals()
 if len(vals)!=1:raise ValueError('extra STEP roots')
 return n.single(vals[0])
def same(x,y):
 if n.whole_material(x.cut(y),empty=True)[1]>1e-7 or n.whole_material(y.cut(x),empty=True)[1]>1e-7:raise ValueError('material changed')
report=json.loads(a.stage.read_text());assembly=json.loads(a.assembly.read_text());inputs={str(a.stage):sha(a.stage),str(a.assembly):sha(a.assembly)};new={};rows=[]
for role,item in report['exports'].items():
 p=a.stage.parent/item['path']
 if p.parent!=a.stage.parent or sha(p)!=item['sha256']:raise ValueError('stage member identity mismatch')
 new[role]=read(p);inputs[str(p)]=sha(p)
with tempfile.TemporaryDirectory(prefix='native-cover-material-') as td:
 def old(phase,arcname,member):
  root=a.repo/'engineering'/phase;man=json.loads((root/'geometry-manifest.json').read_text());arc=root/arcname
  if sha(arc)!=man['archive_sha256']:raise ValueError('archive identity mismatch')
  inputs[str(arc)]=sha(arc);e=next(x for x in man['files'] if x['path']==member)
  with tarfile.open(arc,'r:gz') as t:b=t.extractfile(member).read()
  if hashlib.sha256(b).hexdigest()!=e['sha256']:raise ValueError('native member mismatch')
  p=Path(td)/hashlib.sha256(b).hexdigest();p.write_bytes(b)
  return read(p)
 for side in 'LR':
  cover=new[side+'_OLD_COVER'];root=new[side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS'];inner=new[side+'_ROOT_INNER'];ex=-1 if side=='L' else 1
  previous=old('keycover-geometry-20261014','project-owned-geometry.tar.gz','motion/'+side+'_OLD_COVER.step')
  source=old('contact-motion-20261014','project-owned-native-geometry.tar.gz','contact/'+side+'_OLD_COVER.step')
  key=old('keycover-geometry-20261014','project-owned-geometry.tar.gz','motion/'+side+'_KEY_COMPLETE_Q.step')
  ir,_=regions(inner,(-ex*10.,0,0));er,_=regions(root,(ex*10.,0,0));tongue=n.box(side,1.21,4.26,1.74,1.86,-7.25,-6.43)
  outside=subtract_regions(source.cut(cover).cut(key).cut(tongue),ir+er)
  if n.whole_material(outside,empty=True)[1]>1e-7:raise ValueError('removal outside declared new interfaces')
  removed=n.whole_material(source.cut(cover),empty=True)[1];added=n.whole_material(cover.cut(source),empty=True)[1]
  if abs(source.Volume()+added-removed-cover.Volume())>1e-7:raise ValueError('source cover material balance mismatch')
  if abs(removed-3.66365132894153)>1e-7 or abs(added-2.328)>1e-7:raise ValueError('declared admission-interface material differs')
  old_bounds=n.bounds(side,previous);new_bounds=n.bounds(side,cover)
  if abs(new_bounds[1][1]-12.5)>1e-7 or abs(new_bounds[1][1]-old_bounds[1][1]-3.5)>1e-7:raise ValueError('growth differs from declared value')
  negative=[]
  for name,moving,v in [('ROOT_INNER',inner,(-ex*.05,0,0)),('ROOT_OUTER',root,(ex*.05,0,0))]:
   before=n.common(moving.translate(v),previous);after=n.common(moving.translate(v),cover)
   if before<=1e-7 or after>1e-7:raise ValueError('old admission rejection or new clearance not reproduced')
   negative.append({'moving':name,'old_positive_mm3':before,'new_mm3':after,'translation_mm':v})
  rows.append({'side':side,'new_volume_mm3':cover.Volume(),'source_original_removed_mm3':removed,'new_added_mm3':added,'previous_candidate_removed_mm3':n.whole_material(previous.cut(cover),empty=True)[1],'previous_candidate_added_mm3':n.whole_material(cover.cut(previous),empty=True)[1],'old_bounds_eqr':old_bounds,'new_bounds_eqr':new_bounds,'late_cover_entry_not_relabelled':True,'new_locator_interface_not_equivalent_to_old_closed_hole':True,'actual_pose_negative_controls':negative})
 assembled=[]
 for item in assembly['STEP_exports']:
  p=a.assembly.parent/item['path']
  if not p.resolve().is_relative_to(a.assembly.parent.resolve()) or sha(p)!=item['sha256']:raise ValueError('assembly identity mismatch')
  inputs[str(p)]=sha(p);vals=n.cq.importers.importStep(str(p)).vals()
  if len(vals)!=1:raise ValueError('extra assembly root')
  leaves,_=n.whole_material(vals[0])
  if len(leaves)!=46:raise ValueError('lost assembly material')
  if p.name.startswith('STOW'):
   used=set()
   for side in 'LR':
    for name in PARTS:
     target=new[side+'_'+name];bb=target.BoundingBox();match=[i for i,s in enumerate(leaves) if abs(s.Volume()-target.Volume())<1e-7 and all(abs(getattr(s.BoundingBox(),k)-getattr(bb,k))<1e-7 for k in ('xmin','xmax','ymin','ymax','zmin','zmax'))]
     if len(match)!=1 or match[0] in used:raise ValueError('missing/ambiguous STOW assembly role')
     used.add(match[0]);same(leaves[match[0]],target)
   if len(used)!=46:raise ValueError('unverified STOW assembly leaf')
  assembled.append({'path':p.name,'valid_positive_leaves':46,'STOW_bijective_match':p.name.startswith('STOW')})
if len(assembled)!=2:raise ValueError('missing whole assembly')
if inputs!={p:sha(p) for p in inputs}:raise ValueError('input changed')
if any(x.startswith(('cover_admission','keycover_bypass','stow_contact_slots','split_root_cartridges')) for x in sys.modules):raise ValueError('candidate builder imported')
result={'verifier_sha256':sha(__file__),'input_SHA256':inputs,'input_bytes_unchanged':True,'cover_material':rows,'assembly_reimports':assembled,'valid_assembly_solids':92,'STOW_assembly_matched_leaves':46,'candidate_builder_imported':False,'same_CAD_kernel_not_cross_engine':True,'locator_retention_clamp_actuation_and_phone_fit_unqualified':True,'candidate_go':False,'manufacturing_go':False}
with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print('NATIVE_MATERIAL_AND_92_SOLIDS_REIMPORTED',flush=True)
