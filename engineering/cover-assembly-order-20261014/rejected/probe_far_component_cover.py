from pathlib import Path
import sys,json,traceback,hashlib,tarfile
R=Path('/home/qian-qi/RAZR-SLIDE-coverorder-20261014');E=Path('/home/qian-qi/RAZR-SLIDE-coverorder-evidence-20261014');D=E/'native-inputs';sys.path.insert(0,str(R/'integration'));import cam_contact_native as n
from straight_envelope import envelope
from translation_regions import regions,subtract_regions,checks
out=E/'far-component-preflight';out.mkdir();rows=[]
for side in 'LR':
 p={name:n.single(n.cq.importers.importStep(str(D/(side+'_'+name+'.step'))).val()) for name in ['ROOT_INNER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS','OLD_COVER','PARKED_PAWL','STOP_0','STOP_1']}
 inside=1 if side=='L' else -1
 try:
  inner,mi=regions(p['ROOT_INNER'],(inside*10.,0,0));outer,mo=regions(p['ROOT_OUTER_CONNECTED_ALL_FRAGMENTS'],(-inside*10.,0,0))
  # Recover exactly the pre-U source cover; current key/root geometry unchanged.
  base=R/'engineering/contact-motion-20261014';gm=json.loads((base/'geometry-manifest.json').read_text());arc=base/'project-owned-native-geometry.tar.gz';assert hashlib.sha256(arc.read_bytes()).hexdigest()==gm['archive_sha256'];nm='contact/'+side+'_OLD_COVER.step';entry=next(x for x in gm['files'] if x['path']==nm)
  with tarfile.open(arc,'r:gz') as t:data=t.extractfile(nm).read()
  assert hashlib.sha256(data).hexdigest()==entry['sha256'];f=out/(side+'_ORIGINAL_COVER.step');f.write_bytes(data);source=n.single(n.cq.importers.importStep(str(f)).val())
  # Rails move inside the actual swept locator posts, not arbitrary cutting
  # of disconnected fragments. This is a new explicit cover-interface design.
  bridge=n.fuse([n.box(side,-2.7,-2.4,4.9,12.5,-2.9,-2.5),n.box(side,2.4,2.7,4.9,12.5,-2.9,-2.5),n.box(side,-2.7,2.7,12.2,12.5,-2.9,-2.5)])
  # Existing key full sweep is reused byte-exact from latest evidence.
  latest=R/'engineering/keycover-geometry-20261014';gg=json.loads((latest/'geometry-manifest.json').read_text());arc2=latest/'project-owned-geometry.tar.gz';nm2='motion/'+side+'_KEY_COMPLETE_Q.step';entry2=next(x for x in gg['files'] if x['path']==nm2)
  with tarfile.open(arc2,'r:gz') as t:kb=t.extractfile(nm2).read()
  assert hashlib.sha256(kb).hexdigest()==entry2['sha256'];kf=out/(side+'_KEY_SWEEP.step');kf.write_bytes(kb);key=n.single(n.cq.importers.importStep(str(kf)).val())
  cover=subtract_regions(source.fuse(bridge).cut(key).clean(),inner+outer);leaves,volume=n.whole_material(cover)
  extra=n.whole_material(source.cut(cover),empty=True)[1];added=n.whole_material(cover.cut(source),empty=True)[1]
  n.cq.exporters.export(cover,str(out/(side+'_ADMISSION_COVER.brep')))
  row={'side':side,'cover_components':len(leaves),'source_volume_mm3':source.Volume(),'new_volume_mm3':volume,'removed_original_mm3':extra,'added_mm3':added,'whole_components':[{'volume':sh.Volume(),'bounds':n.bounds(side,sh),'original_material':n.common(sh,source)} for sh in leaves]}
  if len(leaves)==1:
   row['checks']={name:n.common(cover,shape) for name,shape in {**p,'KEY_FULL':key}.items() if name!='OLD_COVER'}
   row['inner_regions']=checks(inner,cover);row['outer_regions']=checks(outer,cover);row['region_counts']=[len(inner),len(outer)]
   row['bounds_eqr']=n.bounds(side,cover);row['COM_eqr']=n.local(side,cover.Center())
  rows.append(row);print(row,flush=True)
  for name,bodies in [('INNER_ENTRY',inner),('OUTER_ENTRY',outer)]:
   for i,body in enumerate(bodies):n.cq.exporters.export(body,str(out/(side+'_'+name+'_'+str(i)+'.step')))
 except Exception as exc:rows.append({'side':side,'error':str(exc),'traceback':traceback.format_exc()});print('REJECT',side,str(exc),flush=True)
 (out/'report.json').write_text(json.dumps({'rows':rows,'new_interfaces_not_qualified':True,'manufacturing_go':False},indent=2))
