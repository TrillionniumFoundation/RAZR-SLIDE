"""Complete only 44 missing original L1 pcurves; no repeated Common or repair."""
from pathlib import Path
import argparse,copy,hashlib,json,sys,time,resource,traceback,importlib.metadata
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'source-original'));import owned_process

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def canonical(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def require(x,m):
 if not x:raise ValueError(m)
def main():
 p=argparse.ArgumentParser();p.add_argument('--contract',required=True);p.add_argument('--output',required=True);p.add_argument('--reader-of');a=p.parse_args()
 owned_process.announce_worker_from_environment(Path(__file__).resolve());out=Path(a.output);require(not out.exists(),'fresh supplementary output required');out.mkdir(parents=True)
 c=json.loads(Path(a.contract).read_text());index=json.loads((HERE/'R3E_BSPLINE_INDEX.json').read_text());require(sha(HERE/'R3E_BSPLINE_INDEX.json')==c['index_sha256'],'index differs')
 for n,h in c['source_sha256'].items():require(sha(HERE/n)==h,'frozen supplementary source differs')
 begin=time.monotonic();report={'schema':'R3E-complete-original-BSpline-pcurve-supplement-v1','contract_sha256':sha(a.contract),'index_sha256':sha(HERE/'R3E_BSPLINE_INDEX.json'),'source_sha256':c['source_sha256'],'execution_completed':False,'records':[],'new_Boolean_calls':0,'native_geometry_or_tolerances_modified':False}
 def save():
  report['elapsed_seconds']=time.monotonic()-begin;report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024;(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 try:
  import cadquery as cq,OCP
  import boundary_inventory_l8 as inv
  import extend_boundary_inventory_r3 as extension
  report['runtime']={'python':sys.version,'OCP':OCP.__version__,'packages':{n:importlib.metadata.version(n) for n in ['cadquery','cadquery-ocp','numpy','scipy']}}
  require(sys.flags.optimize==0,'optimized Python refused')
  for entry in index['inputs']:
   item=entry['input'];path=HERE/item['relative_path'];require(sha(path)==item['sha256'] and path.stat().st_size==item['bytes'],'original BREP identity differs')
   shape=cq.Shape.importBrep(str(path));baseline=inv.inspect(shape);got=canonical(baseline);require(got==entry['expected_complete_original_boundary_canonical_sha256'],'fresh complete baseline inventory differs')
   target_keys={(r['face_index'],r['wire_index'],r['occurrence_index']):r for r in entry['pcurve_targets']};curves=[]
   for fi,face in enumerate(shape.Faces()):
    for wi,wire in enumerate(face.Wires()):
     it=inv.TopoDS_Iterator(wire.wrapped,True,True);oi=0
     while it.More():
      if (fi,wi,oi) in target_keys:
       target=target_keys[(fi,wi,oi)];edge=inv.TopoDS.Edge_s(it.Value());ad=inv.BRepAdaptor_Curve2d(edge,face.wrapped);old=inv.curve_record(ad,2);require(old==target['old_pcurve_record'],'exact original pcurve metadata differs')
       complete=copy.deepcopy(old);extension.complete_curve(complete,ad,2);curve=ad.BSpline();complete['bspline']['defined_first_parameter']=inv.scalar(curve.FirstParameter());complete['bspline']['defined_last_parameter']=inv.scalar(curve.LastParameter());complete['bspline']['native_is_closed']=bool(curve.IsClosed())
       curves.append({**target,'complete_pcurve_record':complete})
      oi+=1;it.Next()
   require(len(curves)==len(entry['pcurve_targets']),'supplement target missing');report['records'].append({'input':item,'original_complete_boundary_canonical_sha256':got,'fresh_complete_original_inventory_bitwise_equal':True,'original_counts':baseline['counts'],'complete_pcurves':curves});save()
   require(report['elapsed_seconds']<c['wall_seconds'] and report['peak_RSS_bytes']<=c['RSS_limit_bytes'],'original resource guard')
   print(json.dumps({'case':item['case_id'],'material_id':item['material_id'],'pcurves':len(curves),'baseline_matches':True}),flush=True)
  if a.reader_of:
   previous=json.loads(Path(a.reader_of).read_text());require(previous['execution_completed'],'producer incomplete');report['independent_reader']={'producer_report_sha256':sha(a.reader_of),'all_complete_curve_records_bitwise_equal':previous['records']==report['records']}
  report['actual_original_shape_count']=len(report['records']);report['actual_original_BSpline_pcurve_count']=sum(len(r['complete_pcurves']) for r in report['records'])
  report['all_sources_unchanged']=all(sha(HERE/n)==h for n,h in c['source_sha256'].items());require(report['all_sources_unchanged'],'supplementary source changed')
  report['execution_completed']=report['actual_original_shape_count']==8 and report['actual_original_BSpline_pcurve_count']==44
 except Exception as exc:report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
 save();print(json.dumps({k:report.get(k) for k in ['execution_completed','failure','elapsed_seconds','peak_RSS_bytes']}),flush=True);return 0 if report['execution_completed'] else 2
if __name__=='__main__':raise SystemExit(main())
