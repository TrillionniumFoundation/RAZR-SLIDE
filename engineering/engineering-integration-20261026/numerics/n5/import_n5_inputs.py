"""Copy only SHA-bound original N1 inputs and selected safe N4b math evidence."""
from pathlib import Path
import argparse,hashlib,json,os,resource,shutil,time

FROZEN = {
 'K.npz': (285135469,'80f6f50243d421a3b0ab9eeff1324db029677b63febeaad1f023bf9609e9f1cb'),
 'loads.npz': (48176390,'811ba687959bb34dec5ada401b35f07123c917bfc4e68ad982d661fd62fac9a6'),
 'mesh.npz': (744696,'310152fc64af21451cc5ea4be683a73075109ed7e6ec588a6e8bcacf4979ac34'),
 'report.json': (2807,'a392e019d4cbe0a34c7b163e307dc04a8a1ec4152cd11573dd3c2ff0bdab0a66'),
}


def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()


def copied(root,name,target,size,digest):
 src=root/name
 if not src.is_file() or src.is_symlink() or not src.resolve().is_relative_to(root):
  raise ValueError('source member missing or escaped')
 if src.stat().st_size!=size or sha(src)!=digest:raise ValueError('frozen member bytes differ')
 target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():raise ValueError('fresh import destination required')
 try:os.link(src,target)
 except OSError:shutil.copyfile(src,target)
 if sha(target)!=digest:raise ValueError('copied member bytes differ')
 return {'bytes':size,'sha256':digest,'original_bytes_unchanged':True}


def main(args):
 if __debug__ is not True:raise RuntimeError('assertions must remain enabled')
 start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(int(3.5*1024**3),int(3.5*1024**3)))
 original=args.original.resolve(strict=True);n4b=args.n4b.resolve(strict=True)
 root=args.case.resolve(strict=True);volume=root/'volume/panel/level-2';seed=root/'seed-N4b'
 if volume.exists() or seed.exists():raise ValueError('fresh import destinations required')
 selected=json.loads(args.manifest.read_text())
 result={'schema':'razr-N5-frozen-original-and-N4b-starting-inputs-v1','completed':False,
  'original_N1_origin':{'run_id':40206010654,'artifact_id':12603523689},
  'N4b_origin':{'run_id':40274319237,'artifact_id':12629751343,
   'engineering_ZIP_sha256':'da01643858154ed4f796f9cde3dbd9ca4c3617c081d5112ac9a4da7f8d4b9a24',
   'engineering_ZIP_actual_stream_verified_before_preregistration':True,
   'ZIP_reverified_in_this_import':False},
  'selection_manifest_sha256':sha(args.manifest),'copied_original_volume_members':{},
  'copied_N4b_scientific_members':{},'raw_N1_runtime_copied_or_exported':False,
  'N4b_full_8_step_history_remains_in_original_artifact':True,
  'all_original_N4b_102_field_math_hashes_retained_in_imported_manifest':True,
  'original_K_b_C_constraints_and_acceptance_unchanged':True,
  'new_sparse_factorization_executed':False,'new_probe_results_created_by_import':False,
  'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
 try:
  if os.statvfs(root).f_bavail*os.statvfs(root).f_frsize<500*1024**2:raise RuntimeError('500MiB reserve unavailable')
  for name,(size,digest) in FROZEN.items():
   result['copied_original_volume_members'][name]=copied(original,'volume/panel/level-2/'+name,volume/name,size,digest)
  for name,info in selected.items():
   if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('invalid selected relative member')
   result['copied_N4b_scientific_members'][name]=copied(n4b,name,seed/name,info['bytes'],info['sha256'])
  report=json.loads((seed/'probe-N4/report.engineering.json').read_text())
  readback=json.loads((seed/'N4-independent-field-readback.engineering.json').read_text())
  assert report['is_original_record'] is False and readback['is_original_record'] is False
  r=report['selected_engineering_fields'];b=readback['selected_engineering_fields']
  assert r['diagnostic_completed'] and b['completed'] and not r['refined_all_five_passed'] and not b['five_original_gates_passed']
  assert len(r['refined_probes'])==5 and [x['passes_original_threshold'] for x in r['refined_probes']]==[False,True,True,True,True]
  assert b['outer_fields_checked']==b['correction_fields_checked']==8 and b['files_hash_checked']==102
  exports=json.loads((seed/'EXPORT_MANIFEST.json').read_text())['exported_files']
  assert len(r['files_sha256'])==102
  for name,digest in r['files_sha256'].items():assert exports['probe-N4/'+name]['sha256']==digest
  result['completed']=True
 except BaseException as exc:
  result['error_type']=type(exc).__name__
  raise
 finally:
  result['seconds']=time.monotonic()-start;result['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
  args.receipt.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 print(json.dumps({'completed':result['completed'],'seconds':result['seconds'],
  'copied_original_members':len(result['copied_original_volume_members']),
  'copied_N4b_scientific_members':len(result['copied_N4b_scientific_members'])},indent=2))


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--n4b',type=Path,required=True)
 p.add_argument('--case',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True)
 main(p.parse_args())
