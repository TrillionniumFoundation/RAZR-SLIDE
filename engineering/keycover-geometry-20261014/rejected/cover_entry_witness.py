"""Concrete cover insertion negative control, old and new covers, both sides.
Not a proof that no multi-stage/rotating assembly route exists.
"""
from pathlib import Path
import argparse,json,hashlib,tarfile,tempfile,sys

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--motion',type=Path,required=True);ap.add_argument('--motion-sha',required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
if sha(a.motion)!=a.motion_sha:raise ValueError('motion receipt changed')
sys.path.insert(0,str(a.repo/'integration'));import cam_contact_native as n
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
r=json.loads(a.motion.read_text());base=a.repo/'engineering/contact-motion-20261014';g=json.loads((base/'geometry-manifest.json').read_text());arc=base/'project-owned-native-geometry.tar.gz'
if sha(arc)!=g['archive_sha256']:raise ValueError('old geometry archive changed')
entries={x['path']:x for x in g['files']};inputs={str(a.motion):sha(a.motion),str(arc):sha(arc)};rows=[]
def read_current(name):
 item=r['exports'][name];p=a.motion.parent/item['path']
 if p.parent!=a.motion.parent or sha(p)!=item['sha256']:raise ValueError('native STEP changed')
 inputs[str(p)]=sha(p);raw=n.cq.importers.importStep(str(p)).vals()
 if len(raw)!=1:raise ValueError('extra native roots')
 return n.single(raw[0])
with tempfile.TemporaryDirectory() as tmp:
 with tarfile.open(arc,'r:gz') as t:
  for side in 'LR':
   name='contact/'+side+'_OLD_COVER.step';b=t.extractfile(name).read()
   if hashlib.sha256(b).hexdigest()!=entries[name]['sha256']:raise ValueError('old cover bytes changed')
   p=Path(tmp)/(side+'.step');p.write_bytes(b);old=n.single(n.cq.importers.importStep(str(p)).val());new=read_current(side+'_OLD_COVER');root=read_current(side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS')
   values=[]
   for label,cover in [('old',old),('new',new)]:
    moved=cover.translate((0,0,.05));actual=n.common(moved,root)
    if actual<=1e-7:raise ValueError('expected blocked cover entry not reproduced')
    pair=n.cq.Compound.makeCompound([moved,root]);f=out/(side+'_'+label+'_COVER_ENTRY_COLLISION.step');n.cq.exporters.export(pair,str(f))
    raw=n.cq.importers.importStep(str(f)).vals()
    if len(raw)!=1:raise ValueError('extra exported roots')
    leaves,_=n.whole_material(raw[0])
    if len(leaves)!=2:raise ValueError('missing collision participant')
    recomputed=n.common(leaves[0],leaves[1])
    if abs(recomputed-actual)>1e-7:raise ValueError('native reimport changed collision')
    rows.append({'side':side,'variant':label,'translation_world_mm':[0,0,.05],'actual_common_mm3':actual,'reimported_common_mm3':recomputed,'whole_positive_solid_leaves':2,'counterexample_STEP':{'path':f.name,'sha256':sha(f)}});values.append(actual)
   if abs(values[0]-values[1])>1e-7:raise ValueError('old/new obstruction differs')
if inputs!={p:sha(p) for p in inputs}:raise ValueError('source changed')
if any(x.startswith(('keycover_bypass','stow_contact_slots','stow_continuous_slots')) for x in sys.modules):raise ValueError('scene generator imported')
result={'source_sha256':sha(__file__),'inputs_SHA256':inputs,'input_bytes_unchanged':True,'rows':rows,'builder_imported':False,'same_CAD_kernel':True,'current_cover_entry_stage_qualified':False,'no_global_assembly_impossibility_claim':True,'obstruction_preexists_new_U_bridge':True,'manufacturing_go':False}
(out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
print('REPRODUCED_BLOCKED_ENTRY: 4 actual pairs, old/new equal; stage rejected',flush=True)
raise SystemExit(1)
