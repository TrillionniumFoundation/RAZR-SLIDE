"""Read complete original STOP/SPRING geometry, retaining exact input identity."""
from pathlib import Path
import datetime as dt,hashlib,json,math,os,resource,signal,time,traceback
HERE=Path(__file__).resolve().parent;OUT=HERE/'stop-spring-readback-attempt1';OUT.mkdir(exist_ok=False)
assert (HERE/'STOP_SPRING_READBACK_PLAN.json').is_file()
resource.setrlimit(resource.RLIMIT_AS,(805306368,805306368));resource.setrlimit(resource.RLIMIT_CPU,(60,60));signal.alarm(60)
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});start=time.monotonic()
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.TopoDS import TopoDS,TopoDS_Shape,TopoDS_Iterator
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID,TopAbs_COMPOUND,TopAbs_COMPSOLID,TopAbs_FACE
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.GeomAbs import GeomAbs_Cylinder
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def xyz(p):return [p.X(),p.Y(),p.Z()]
def mass(s):
    g=GProp_GProps();BRepGProp.VolumeProperties_s(s,g);return g.Mass()
def sig(s):
    leaves=[]
    def walk(n):
        assert BRepCheck_Analyzer(n).IsValid()
        if n.ShapeType()==TopAbs_SOLID:
            v=mass(n);assert math.isfinite(v) and v>0;leaves.append(v)
        elif n.ShapeType() in (TopAbs_COMPOUND,TopAbs_COMPSOLID):
            it=TopoDS_Iterator(n);count=0
            while it.More():walk(it.Value());count+=1;it.Next()
            assert count
        else:raise ValueError('non-solid topology')
    walk(s);v=mass(s);assert len(leaves)==1 and math.isfinite(v) and v>0 and abs(sum(leaves)-v)<=1e-7
    b=Bnd_Box();BRepBndLib.AddOptimal_s(s,b,False,False);x0,y0,z0,x1,y1,z1=b.Get()
    return {'valid':True,'solid_count':len(leaves),'signed_volume_mm3':v,'bounds_mm':[x0,x1,y0,y1,z0,z1]}
report={'schema':'razr-r13-complete-current-stop-spring-native-readback-v1','completed':False,'source_sha256':sha(__file__),
        'plan_sha256':sha(HERE/'STOP_SPRING_READBACK_PLAN.json'),'input_manifest_sha256':sha(HERE/'INPUT_MANIFEST.json'),
        'motion_report_sha256':sha(HERE/'COMPLETE_SOURCE_MOTION_DOMAIN.json'),'bodies':[],'failures':[],
        'native_bounds_are_only_diagnostic':True,'source_real_interval_to_native_error_bridge_proved':False,
        'physical_spring_force_or_preload_proved':False,'full_15D_G2':False}
try:
    manifest=json.loads((HERE/'INPUT_MANIFEST.json').read_text());factory=json.loads((HERE/'inputs/report.json').read_text())
    names=[s+role for s in 'LR' for i in (0,1) for role in (f'_STOP_{i}',f'_SPRING_{i}_OD_TOL_ENVELOPE')]
    for name in names:
        row={'name':name,'representations':{}}
        expected=factory['body_exports'][name]['signature']
        for fmt in ('brep','step'):
            p=HERE/'inputs'/(name+'.'+fmt);before=sha(p);assert before==manifest['files'][p.name]['sha256']
            if fmt=='brep':s=TopoDS_Shape();assert BRepTools.Read_s(s,str(p),BRep_Builder())
            else:
                rd=STEPControl_Reader();assert rd.ReadFile(str(p))==IFSelect_RetDone and rd.TransferRoots()==1;s=rd.OneShape()
            sg=sig(s);assert abs(sg['signed_volume_mm3']-expected['signed_volume_mm3'])<=1e-7
            assert max(abs(x-y) for x,y in zip(sg['bounds_mm'],expected['bounds_mm']))<=1e-7
            faces=[];ex=TopExp_Explorer(s,TopAbs_FACE)
            while ex.More():
                f=TopoDS.Face_s(ex.Current());ad=BRepAdaptor_Surface(f,True)
                fr={'index':len(faces),'type':str(ad.GetType()),'orientation':str(f.Orientation()),
                    'UV':[ad.FirstUParameter(),ad.LastUParameter(),ad.FirstVParameter(),ad.LastVParameter()]}
                if ad.GetType()==GeomAbs_Cylinder:
                    c=ad.Cylinder();fr['cylinder']={'origin':xyz(c.Location()),'axis':xyz(c.Axis().Direction()),'radius_mm':c.Radius()}
                faces.append(fr);ex.Next()
            assert sha(p)==before;row['representations'][fmt]={'file_sha256':before,'signature':sg,'complete_face_catalog':faces}
        row['maximum_BREP_STEP_signature_difference']=max(abs(x-y) for x,y in zip([row['representations']['brep']['signature']['signed_volume_mm3'],*row['representations']['brep']['signature']['bounds_mm']],
                                                                              [row['representations']['step']['signature']['signed_volume_mm3'],*row['representations']['step']['signature']['bounds_mm']]))
        report['bodies'].append(row)
    report['completed']=True
except BaseException as e:report['failures'].append({'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()})
finally:
    report['seconds']=time.monotonic()-start;report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    (OUT/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({'completed':report['completed'],'bodies':len(report['bodies']),'seconds':report['seconds'],'RSS':report['peak_RSS_bytes'],'failures':len(report['failures'])}))
raise SystemExit(0 if report['completed'] else 1)
