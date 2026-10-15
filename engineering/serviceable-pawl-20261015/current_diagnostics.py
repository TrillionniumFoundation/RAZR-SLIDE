"""Current V2 native negative inputs and endpoint contact limits, not qualification."""
from pathlib import Path
import json,sys,tempfile,shutil,math
R=Path('/home/qian-qi/RAZR-SLIDE-serviceable-control-20261015');O=Path('/tmp/razr-serviceable-control-20261015');sys.path.insert(0,str(R/'integration'))
import verify_serviceable_pawl as v
source=O/'native-v2';meta,new,h=v.load(source/'manifest.json')
assert meta['source_sha256']==v.sha(R/'integration/serviceable_pawl.py')
parent,prior,old,profiles=v.parent_native(h)
neg=[]
for case in ('missing_part','changed_STEP','nonfinite_certificate','symlink'):
 with tempfile.TemporaryDirectory(prefix='serviceable-negative-',dir=O) as td:
  d=Path(td);m=json.loads((source/'manifest.json').read_text())
  for f in source.glob('*.step'):shutil.copyfile(f,d/f.name)
  if case=='missing_part':m['exports'].pop('R_ROOF')
  if case=='changed_STEP':
   f=d/'R_ROOF.step';f.write_bytes(f.read_bytes()+b'\nMODIFIED\n')
  if case=='nonfinite_certificate':m['exports']['R_ROOF']['volume_mm3']=float('nan')
  if case=='symlink':
   f=d/'R_ROOF.step';f.unlink();f.symlink_to(source/'R_ROOF.step')
  p=d/'manifest.json';p.write_text(json.dumps(m))
  try:v.load(p)
  except ValueError as error:neg.append({'case':case,'rejected':True,'error':str(error)})
  else:raise ValueError('invalid native input was accepted')
  print('NEGATIVE',neg[-1],flush=True)
kh=(v.w.v.G-v.w.v.R)*(math.hypot(1,v.w.v.K)+math.sqrt(2));ph=.025*math.hypot(1,1.1/3);rows=[]
selected={'A_BACK_PANEL'}|{side+'_'+role for side in 'LR' for role in ('PAWL','SHOULDER_PIN_NOMINAL','TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS','ROOF')}
for u in (0.,1.5,3.):
 for sign in (-1,1):
  p=v.scene(new,parent,prior,old,profiles,0.,0.,(u,u))
  reference=v.w.scene(parent,prior,old,profiles,0.,0.,(u,u),key_offset=kh,actuator_flank=sign*ph)
  for side in 'LR':
   for role in ('KEY','CROSSHEAD','STOP_0','STOP_1','SPRING_0_OD_TOL_ENVELOPE','SPRING_1_OD_TOL_ENVELOPE','TELESCOPE_1','TELESCOPE_2','TELESCOPE_3'):
    p[side+'_'+role]=reference[side+'_'+role]
   z=u*1.1/3+sign*ph
   p[side+'_PAWL']=new[side+'_PAWL'].translate((0,0,z))
   p[side+'_SHOULDER_PIN_NOMINAL']=new[side+'_SHOULDER_PIN_NOMINAL'].translate((0,0,z))
  pairs=v.w.pairs(p,selected);bad=[r for r in pairs if r['common_mm3']>v.TOL]
  rows.append({'tab_mm':u,'KEY_positive_return_offset_mm':kh,'PAWL_flank_offset_mm':sign*ph,'pairs':len(pairs),'positive_pairs':bad})
  print('ENDPOINT',u,sign,bad,flush=True)
assert all(v.sha(f)==value for f,value in h.items())
(O/'current-diagnostics.json').write_text(json.dumps({'source_sha256':meta['source_sha256'],'reader_sha256':v.sha(R/'integration/verify_serviceable_pawl.py'),'input_sha256':h,'reader_negative_controls':neg,'combined_slot_clearance_cases':rows,'all_checked_clearance_cases_clear':not any(r['positive_pairs'] for r in rows),'scope':__doc__,'not_in_unit_count':True,'thread_preload_holding_force_qualified':False,'candidate_go':False,'manufacturing_go':False},indent=2)+'\n')
