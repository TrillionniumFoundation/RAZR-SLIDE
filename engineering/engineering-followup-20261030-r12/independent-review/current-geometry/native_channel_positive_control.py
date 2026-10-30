"""Positive actual KEY material inside the deliberately enlarged wrong channel."""
import os,resource,signal,time,json,hashlib,io,datetime
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(3<<29,3<<29));resource.setrlimit(resource.RLIMIT_CPU,(60,60))
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});signal.alarm(75)
started=time.monotonic()
import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common,BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
from OCP.TopTools import TopTools_ListOfShape
ROOT=Path(__file__).resolve().parent
INPUT=ROOT.parent/'geometry_work/inputs'
OUT=ROOT/'positive-native-control';OUT.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clone(s):
    c=BRepBuilderAPI_Copy(s.wrapped,True,False);assert c.IsDone();return cq.Shape.cast(c.Shape())
def fingerprint(s):
    b=io.BytesIO();assert s.exportBrep(b);return hashlib.sha256(b.getvalue()).hexdigest()
def operation(a,b,kind):
    aa=TopTools_ListOfShape();bb=TopTools_ListOfShape();aa.Append(clone(a).wrapped);bb.Append(clone(b).wrapped)
    op=(BRepAlgoAPI_Common if kind=='common' else BRepAlgoAPI_Cut)();op.SetArguments(aa);op.SetTools(bb)
    op.SetNonDestructive(True);op.SetRunParallel(False);op.Build();assert op.IsDone();return cq.Shape.cast(op.Shape())
def save(s,name):
    p=OUT/(name+'.brep');assert clone(s).exportBrep(str(p))
    assert s.isValid();volumes=[v.Volume() for v in s.Solids()]
    assert all(v>0 for v in volumes) and abs(sum(volumes)-s.Volume())<=1e-7
    return {'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size,
            'valid_native_topology':True,'signed_volume_mm3':s.Volume(),'solid_volumes':volumes}
rows=[]
for side in 'LR':
    x0,x1=(11.32,11.38) if side=='R' else (-11.38,-11.32)
    cube=cq.Solid.makeBox(x1-x0,.1,.1,cq.Vector(x0,59.95,1.35))
    cube_rec=save(cube,side+'-positive-arm-cuboid')
    for role in ('BREP','STEP'):
        path=INPUT/(side+'_KEY.'+role.lower())
        if role=='BREP':body=cq.Shape.importBrep(str(path))
        else:
            roots=cq.importers.importStep(str(path)).vals();assert len(roots)==1;body=roots[0]
        before=fingerprint(body)
        common=operation(cube,body,'common');missing=operation(cube,body,'cut')
        cr=save(common,side+'-'+role+'-Common');mr=save(missing,side+'-'+role+'-cuboid-minus-KEY')
        assert cr['signed_volume_mm3']>1e-7 and mr['signed_volume_mm3']<=1e-7
        assert abs(cr['signed_volume_mm3']-cube_rec['signed_volume_mm3'])<=1e-7
        assert fingerprint(body)==before
        rows.append({'side':side,'role':role,'input_sha256':sha(path),'cuboid':cube_rec,
                     'Common':cr,'cuboid_minus_KEY':mr,'complete_key_fingerprint_unchanged':True,
                     'incorrect_enlarged_channel_contains_positive_native_KEY_material':True})
report={'schema':'razr-r12-channel-negative-control-actual-native-positive-material-v1',
    'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(__file__),
    'completed':True,'rows':rows,'seconds':time.monotonic()-started,
    'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
    'original_Common_gate_mm3':1e-7,'this_is_a_positive_control_not_a_full_domain_proof':True,
    'two_formats_share_native_kernel':True,'native_filling_or_compiled_error_formally_proved':False}
(ROOT/'NATIVE_KEY_CHANNEL_POSITIVE_CONTROL.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'completed':True,'Common_volumes':[r['Common']['signed_volume_mm3'] for r in rows],'seconds':report['seconds']}))
