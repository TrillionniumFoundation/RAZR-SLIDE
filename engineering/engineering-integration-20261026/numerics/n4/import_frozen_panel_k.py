"""N4b: recover the already-frozen original K and diagnose rejected reassembly.

No numerical values, sparse representation, constraints, C or original acceptance
rule are changed. The C2/N1 reconstructed matrix remains a historical input to
an S4-bound new solver study; it is not the earlier volume-v3 historical K/H.
"""
from pathlib import Path
import argparse,hashlib,json,os,resource,shutil,time
import numpy as np

FROZEN = {
 'K.npz': (285135469,'80f6f50243d421a3b0ab9eeff1324db029677b63febeaad1f023bf9609e9f1cb'),
 'loads.npz': (48176390,'811ba687959bb34dec5ada401b35f07123c917bfc4e68ad982d661fd62fac9a6'),
 'mesh.npz': (744696,'310152fc64af21451cc5ea4be683a73075109ed7e6ec588a6e8bcacf4979ac34'),
 'report.json': (2807,'a392e019d4cbe0a34c7b163e307dc04a8a1ec4152cd11573dd3c2ff0bdab0a66'),
}
REJECTED_K = 'fc21f4348328b99e13d0ce1f066172e017565e14606d3c821f2216fef7dc8997'


def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()


def compare_arrays(left,right):
 result={'shape_equal':left.shape==right.shape,'dtype_equal':left.dtype==right.dtype,
  'frozen_shape':list(left.shape),'rebuilt_shape':list(right.shape),'frozen_dtype':str(left.dtype),'rebuilt_dtype':str(right.dtype),
  'frozen_array_sha256':hashlib.sha256(left.tobytes()).hexdigest(),'rebuilt_array_sha256':hashlib.sha256(right.tobytes()).hexdigest()}
 result['bytes_equal']=result['shape_equal'] and result['dtype_equal'] and result['frozen_array_sha256']==result['rebuilt_array_sha256']
 if result['shape_equal'] and result['dtype_equal'] and left.dtype.kind in ('f','i','u'):
  count=0;maximum=0.;scale=0.;squares=np.longdouble(0.)
  a=left.ravel();b=right.ravel()
  for i in range(0,len(a),262144):
   x=a[i:i+262144];y=b[i:i+262144]
   count+=int(np.count_nonzero(x!=y));d=x.astype(np.longdouble)-y.astype(np.longdouble)
   maximum=max(maximum,float(np.max(np.abs(d),initial=0)))
   scale=max(scale,float(np.max(np.abs(x),initial=0)))
   squares+=np.sum(d*d,dtype=np.longdouble)
  result.update(changed_entries=count,max_absolute_difference=maximum,frozen_max_absolute=scale,
   max_difference_over_max_frozen_or_one=maximum/max(scale,1.),difference_l2=float(np.sqrt(squares)))
 return result


def main(args):
 if __debug__ is not True:raise RuntimeError('assertions must remain enabled')
 start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(int(3.5*1024**3),int(3.5*1024**3)))
 frozen=args.frozen.resolve(strict=True);rebuilt=args.rebuilt.resolve(strict=True)
 target=args.volume.resolve()/'panel'/'level-2';target.mkdir(parents=True,exist_ok=False)
 result={'schema':'razr-N4b-frozen-input-recovery-and-reassembly-comparison-v1','completed':False,
  'frozen_input_origin':{'diagnostic_source_C2':'bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb','run_id':40206010654,'artifact_id':12603523689,
   'artifact_name':'c2-panel-pivot-N1-40206010654-1','prior_independently_verified_ZIP_sha256':'a69e6dc15e81cc750552a062224c0e92e352ec7f29a691d92f148885d7cf8c2c',
   'downloaded_ZIP_reverified_this_invocation':False,'all_selected_original_member_bytes_checked_this_invocation':False},
  'rejected_reassembly_origin':{'functional_source_S4':'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560','run_id':40273524820,'artifact_id':12629167410,
   'artifact_name':'s4-panel-GMRES-N4-engineering-40273524820-1','required_K_sha256':REJECTED_K},
  'same_original_K_b_C_required':True,'original_five_probe_float64_limit':1e-7,'new_displacement_or_residual_computed_by_this_import':False,
  'earliest_historical_K_or_H_restored':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,
  'capacity_basis':{'wall_seconds':180,'AS_bytes':int(3.5*1024**3),'comparison_largest_arrays_bytes':2*189171864,'block_entries':262144,'no_sparse_factorization':True},
  'copied_original_members':{},'array_comparisons':{}}
 try:
  if os.statvfs(target).f_bavail*os.statvfs(target).f_frsize<500*1024**2:raise RuntimeError('original 500MiB reserve unavailable')
  for name,(size,digest) in FROZEN.items():
   src=frozen/'volume/panel/level-2'/name
   if not src.is_file() or src.is_symlink() or src.stat().st_size!=size or sha(src)!=digest:raise ValueError('frozen original member differs: '+name)
   if not src.resolve().is_relative_to(frozen):raise ValueError('frozen source path escaped')
   dst=target/name
   try:os.link(src,dst)
   except OSError:shutil.copyfile(src,dst)
   if sha(dst)!=digest:raise ValueError('frozen byte copy differs: '+name)
   result['copied_original_members'][name]={'bytes':size,'sha256':digest,'original_bytes_unchanged':True}
  result['frozen_input_origin']['all_selected_original_member_bytes_checked_this_invocation']=True
  report=json.loads((target/'report.json').read_text())
  assert report['body']=='panel' and report['level']==2 and report['dofs']==344103 and report['E_normalization']==1.0 and report['nu']==0.3
  assert report['original_faces_and_surface_P2_traces_unchanged'] and not report['body_loads_on_added_internal_DOFs']
  rejected=rebuilt/'volume/panel/level-2/K.npz'
  assert rejected.is_file() and not rejected.is_symlink() and rejected.resolve().is_relative_to(rebuilt)
  assert sha(rejected)==REJECTED_K
  with np.load(target/'K.npz',allow_pickle=False) as left,np.load(rejected,allow_pickle=False) as right:
   assert set(left.files)==set(right.files)=={'indices','indptr','format','shape','data'}
   for name in ('indices','indptr','format','shape','data'):
    result['array_comparisons'][name]=compare_arrays(left[name],right[name])
  c=result['array_comparisons'];result['sparse_pattern_and_format_identical']=all(c[k]['bytes_equal'] for k in ('indices','indptr','format','shape'))
  result['numerical_data_identical']=c['data']['bytes_equal']
  result['only_container_serialization_difference']=all(v['bytes_equal'] for v in c.values())
  result['difference_cause_not_established']=True
  result['copied_K_sha256']=sha(target/'K.npz');assert result['copied_K_sha256']==FROZEN['K.npz'][1]
  result['completed']=True
 except BaseException as exc:
  result['error_type']=type(exc).__name__
  raise
 finally:
  result['seconds']=time.monotonic()-start;result['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
  args.receipt.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 print(json.dumps({k:result[k] for k in ('completed','copied_K_sha256','sparse_pattern_and_format_identical','numerical_data_identical','only_container_serialization_difference','seconds','peak_rss_kib')},indent=2))


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--frozen',type=Path,required=True);p.add_argument('--rebuilt',type=Path,required=True);p.add_argument('--volume',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True)
 main(p.parse_args())
