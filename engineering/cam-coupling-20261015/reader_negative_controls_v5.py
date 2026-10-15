from pathlib import Path
import json,sys,tempfile,shutil
ROOT=Path('/home/qian-qi/RAZR-SLIDE-coupling-20261015');OUT=Path('/tmp/razr-coupling-20261015');SOURCE=OUT/'native-v5'
sys.path.insert(0,str(ROOT/'integration'));import verify_cam_coupling as v
rows=[]
for case in ('missing_part','nonfinite_certificate','changed_STEP','symlink_to_original'):
 with tempfile.TemporaryDirectory(prefix='coupling-negative-',dir=OUT) as td:
  td=Path(td);meta=json.loads((SOURCE/'manifest.json').read_text())
  for f in SOURCE.glob('*.step'):shutil.copyfile(f,td/f.name)
  if case=='missing_part':meta['exports'].pop('L_B_CAM')
  if case=='nonfinite_certificate':meta['exports']['L_B_CAM']['volume_mm3']=float('nan')
  if case=='changed_STEP':
   f=td/'L_B_CAM.step';f.write_bytes(f.read_bytes()+b'\nchanged controlled STEP\n')
  if case=='symlink_to_original':
   f=td/'L_B_CAM.step';f.unlink();f.symlink_to(SOURCE/'L_B_CAM.step')
  p=td/'manifest.json';p.write_text(json.dumps(meta))
  try:v.load(p)
  except ValueError as exc:row={'case':case,'rejected':True,'error':str(exc)}
  else:raise AssertionError('invalid native input accepted: '+case)
  rows.append(row);print(json.dumps(row),flush=True)
(OUT/'reader-negative-controls-v5.json').write_text(json.dumps({'tests':rows,'all_rejected':True,'reader_sha256':v.sha(ROOT/'integration/verify_cam_coupling.py'),'not_in_unit_suite_count':True},indent=2)+'\n')
