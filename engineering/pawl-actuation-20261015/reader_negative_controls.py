from pathlib import Path
import sys,json,shutil,tempfile
R=Path('/home/qian-qi/RAZR-SLIDE-pawl-actuation-20261015');O=Path('/tmp/razr-pawl-actuation-20261015');sys.path.insert(0,str(R/'integration'))
import verify_pawl_actuator as w
source=O/'native-v2';rows=[]
for case in ('missing_part','nonfinite_certificate','changed_STEP','symlink_to_original'):
 with tempfile.TemporaryDirectory(prefix='pawl-reader-negative-',dir=O) as td:
  folder=Path(td);meta=json.loads((source/'manifest.json').read_text())
  for f in source.glob('*.step'):shutil.copyfile(f,folder/f.name)
  if case=='missing_part':meta['exports'].pop('R_TAB')
  if case=='nonfinite_certificate':meta['exports']['R_TAB']['volume_mm3']=float('nan')
  if case=='changed_STEP':
   f=folder/'R_TAB.step';f.write_bytes(f.read_bytes()+b'\nCHANGED\n')
  if case=='symlink_to_original':
   f=folder/'R_TAB.step';f.unlink();f.symlink_to(source/'R_TAB.step')
  p=folder/'manifest.json';p.write_text(json.dumps(meta))
  try:w.load_new(p)
  except (ValueError,OSError) as e:rows.append({'case':case,'rejected':True,'error':str(e)})
  else:raise RuntimeError('bad native input was accepted: '+case)
  print(rows[-1],flush=True)
(O/'reader-negative-controls.json').write_text(json.dumps({'all_rejected':True,'rows':rows,'reader_sha256':w.sha(R/'integration/verify_pawl_actuator.py')},indent=2)+'\n')
