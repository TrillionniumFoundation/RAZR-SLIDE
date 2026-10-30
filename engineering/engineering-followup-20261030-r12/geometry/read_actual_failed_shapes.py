"""Read the exact failed R12 native shapes without changing prior records."""
import os,resource,signal,json,time,datetime
resource.setrlimit(resource.RLIMIT_AS,(3<<29,3<<29));resource.setrlimit(resource.RLIMIT_CPU,(30,30))
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});signal.alarm(40)
from current_key_common import HERE,cq,sha
paths=['producer-v1/L/regions/planar_face_13.brep',
       'producer-v3/L/regions/planar_face_1.brep',
       'producer-v3/L/commons/planar_face_1.brep',
       'producer-v4/R/regions/planar_face_15.unoriented.brep',
       'producer-v4/R/regions/planar_face_15.brep']
rows=[]
for rel in paths:
    p=HERE/rel;s=cq.Shape.importBrep(str(p))
    rows.append({'file':rel,'sha256':sha(p),'bytes':p.stat().st_size,
                 'native_isValid':s.isValid(),'shape_type':s.ShapeType(),
                 'signed_volume_mm3':s.Volume(),'positive_solid_gate_passes':all(t.Volume()>0 for t in s.Solids()),
                 'all_solid_signed_volumes_mm3':[t.Volume() for t in s.Solids()]})
result={'schema':'razr-r12-exact-failed-shapes-native-readback-v1',
    'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(__file__),
    'original_reports_rewritten':False,'failures_reclassified_as_pass':False,'shapes':rows,
    'impossible_Common_original_operand_bound_mm3':rows[1]['signed_volume_mm3']+1e-7,
    'observed_impossible_Common_mm3':rows[2]['signed_volume_mm3'],
    'impossible_Common_violation_preserved':rows[2]['signed_volume_mm3']>rows[1]['signed_volume_mm3']+1e-7}
(HERE/'REAL_FAILURE_NATIVE_READBACK.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
