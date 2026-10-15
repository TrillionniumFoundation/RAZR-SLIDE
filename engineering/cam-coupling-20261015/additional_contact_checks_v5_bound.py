from pathlib import Path
import sys,json,gzip,hashlib
ROOT=Path('/home/qian-qi/RAZR-SLIDE-coupling-20261015');OUT=Path('/tmp/razr-coupling-20261015')
sys.path.insert(0,str(ROOT/'integration'))
import verify_cam_coupling as v
r,p,h=v.load(OUT/'native-v5/manifest.json');assert r['source_sha256']==v.sha(ROOT/'integration/cam_coupling.py'), 'manifest/builder identity mismatch';old=v.source_parts(h)
rows=[]
for s,d in ((0.,0.),(40.,0.),(79.75,0.),(79.75,8.2)):
 proto=v.prototype(p,s,d)
 for side in 'LR':
  pin=proto[side+'_TELESCOPE_3'];cam=proto[side+'_B_CAM']
  for delta in (-.02,.02):
   value=v.common(pin.translate((0,0,delta)),cam)
   assert value>v.TOL,(side,s,d,delta,value)
   rows.append({'side':side,'slide_mm':s,'descent_mm':d,'head_axial_displacement_mm':delta,'cam_common_mm3':value})
print('AXIAL_CAPTURE',len(rows),'positive native stops',flush=True)
profiles={};fp=ROOT/'engineering/thin-mechanism-20261015/native-verification.json.gz';data=json.loads(gzip.decompress(fp.read_bytes()));h[str(fp)]=v.sha(fp)
fields=('pin_radius','floor_height','floor_corner_q','ramp_slope','pin_q','lower_stop_height','q_max')
for side in 'LR':profiles[side]=[v.ContactProfile(**{k:c['profile'][k] for k in fields}) for c in data['sides'][side]['contacts']]
# A permitted inward-return pair of groove flanks, not clamped to q=0.
dx=(v.G-v.R)*(1+v.K*v.K)**.5;half=dx+(v.G-v.R)*2**.5
flank=v.prototype(p,0.,0.,dx=dx,dq=half);results=[]
for parked in (1.1,.55,0.):
 parts=v.scene(p,old,profiles,0.,0.)
 for side in 'LR':
  sign=-1 if side=='L' else 1
  parts[side+'_KEY']=flank[side+'_KEY_YOKE'];parts[side+'_PAWL']=old[side+'_PAWL'].translate((0,0,parked))
  parts[side+'_CROSSHEAD']=flank[side+'_CROSSHEAD']
  for i in range(1,4):parts[f'{side}_TELESCOPE_{i}']=flank[f'{side}_TELESCOPE_{i}']
  for i in (0,1):
   delta=profiles[side][i].evaluate(half)[0]-profiles[side][i].evaluate(0)[0]
   parts[f'{side}_STOP_{i}']=old[f'{side}_STOP_{i}'].translate((sign*delta,0,0))
   role=f'{side}_SPRING_{i}_OD_TOL_ENVELOPE';b=old[role].BoundingBox();lo=b.xmin+min(0,sign*delta);hi=b.xmax+max(0,sign*delta)
   parts[role]=v.n.single(v.cq.Solid.makeCylinder(.43,hi-lo,v.cq.Vector(lo,(b.ymin+b.ymax)/2,(b.zmin+b.zmax)/2),v.cq.Vector(1,0,0)))
 bad=[]
 for side in 'LR':
  names=[side+'_KEY',side+'_PAWL',side+'_STOP_0',side+'_STOP_1']
  pairs={tuple(sorted((a,b))) for a in names for b in parts if a!=b}
  for a,b in sorted(pairs):
   value=v.common(parts[a],parts[b])
   if value>v.TOL:bad.append({'a':a,'b':b,'common_mm3':value})
 results.append({'PAWL_outward_mm':parked,'KEY_positive_return_offset_mm':half,'positive_pairs':bad})
 print('RETURN_FLANK',parked,'bad',bad,flush=True)
assert all(v.sha(f)==value for f,value in h.items())
result={'tested_builder_sha256':v.sha(ROOT/'integration/cam_coupling.py'),'input_sha256':h,'verifier_sha256':v.sha(ROOT/'integration/verify_cam_coupling.py'),'axial_head_capture_trials':rows,'return_flank_latch_probes':results,'slot_allowance_halfwidth_mm':half,'scope':'additional local native checks; not included in current unit count; no forces, full timing or actuator qualification','candidate_go':False,'manufacturing_go':False}
(OUT/'additional-contact-checks-v5-bound.json').write_text(json.dumps(result,indent=2)+'\n')
