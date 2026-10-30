"""Fresh native whole-region readback with original signed-volume safeguards.

The two format runs share this builder and OCCT. They are independent process
and serialization readbacks, not independent kernels or exact-set proofs.
"""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import io
import json
import math
import os
import resource
import signal
import time
import traceback

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--format',choices=['brep','step'],required=True)
a=parser.parse_args(); OUT=HERE/('native-'+a.format+'-attempt1');OUT.mkdir(exist_ok=False)
resource.setrlimit(resource.RLIMIT_AS,(3<<29,3<<29));resource.setrlimit(resource.RLIMIT_CPU,(120,120))
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
signal.alarm(120);started=time.monotonic()

from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common,BRepAlgoAPI_Cut,BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.TopAbs import TopAbs_SOLID,TopAbs_COMPOUND,TopAbs_COMPSOLID,TopAbs_FACE,TopAbs_VERTEX
from OCP.TopoDS import TopoDS,TopoDS_Shape,TopoDS_Iterator
from OCP.TopExp import TopExp_Explorer
from OCP.TopTools import TopTools_ListOfShape
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.gp import gp_Pnt
from OCP.BRep import BRep_Tool

TOL=1e-7
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fprint(s):
    b=io.BytesIO();BRepTools.Write_s(s,b);raw=b.getvalue()
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def mass(s):
    g=GProp_GProps();BRepGProp.VolumeProperties_s(s,g)
    return float(g.Mass())
def signature(s,empty=False):
    leaves=[]
    def visit(n):
        assert BRepCheck_Analyzer(n).IsValid(),'invalid topology'
        k=n.ShapeType()
        if k==TopAbs_SOLID:
            v=mass(n);assert math.isfinite(v) and v>0,'nonpositive signed solid';leaves.append(v)
        elif k in (TopAbs_COMPOUND,TopAbs_COMPSOLID):
            it=TopoDS_Iterator(n);kids=0
            while it.More():visit(it.Value());kids+=1;it.Next()
            assert kids or empty,'empty topology'
        else:raise ValueError('free non-solid topology: '+str(k))
    visit(s);v=mass(s)
    assert math.isfinite(v) and v>=0 and abs(sum(leaves)-v)<=TOL and (leaves or empty),'whole signed volume mismatch'
    bb=None
    if leaves:
        b=Bnd_Box();BRepBndLib.AddOptimal_s(s,b,False,False);x0,y0,z0,x1,y1,z1=b.Get();bb=[x0,x1,y0,y1,z0,z1]
    return {'valid':True,'signed_volume_mm3':v,'solid_count':len(leaves),'solid_signed_volumes_mm3':leaves,'bounds_mm':bb}
def copy(s):
    c=BRepBuilderAPI_Copy(s,True,False);assert c.IsDone();return c.Shape()
def op(x,y,kind):
    lhs=TopTools_ListOfShape();rhs=TopTools_ListOfShape();lhs.Append(copy(x));rhs.Append(copy(y))
    b={'common':BRepAlgoAPI_Common,'cut':BRepAlgoAPI_Cut,'fuse':BRepAlgoAPI_Fuse}[kind]()
    b.SetArguments(lhs);b.SetTools(rhs);b.SetNonDestructive(True);b.SetRunParallel(False);b.Build();assert b.IsDone()
    return b.Shape()
def box(v):return BRepPrimAPI_MakeBox(gp_Pnt(*v[0]),gp_Pnt(*v[1])).Shape()
def save(s,path,empty=False):
    path.parent.mkdir(parents=True,exist_ok=True);assert not path.exists()
    BRepTools.Write_s(s,str(path));return {'file':str(path.relative_to(HERE)),'bytes':path.stat().st_size,'sha256':sha(path),**signature(s,empty)}
def faces(s):
    out=[];ex=TopExp_Explorer(s,TopAbs_FACE)
    while ex.More():
        face=TopoDS.Face_s(ex.Current());surf=BRepAdaptor_Surface(face,True)
        row={'index':len(out),'type':str(surf.GetType()),'orientation':str(face.Orientation()),
             'UV':[surf.FirstUParameter(),surf.LastUParameter(),surf.FirstVParameter(),surf.LastVParameter()], 'vertices':[]}
        vx=TopExp_Explorer(face,TopAbs_VERTEX)
        while vx.More():
            p=BRep_Tool.Pnt_s(TopoDS.Vertex_s(vx.Current()));row['vertices'].append([p.X(),p.Y(),p.Z()]);vx.Next()
        if str(surf.GetType()).endswith('Plane'):
            p=surf.Plane();loc=p.Location();n=p.Axis().Direction();row['plane_origin']=[loc.X(),loc.Y(),loc.Z()];row['axis']=[n.X(),n.Y(),n.Z()]
        out.append(row);ex.Next()
    return out
def load(name):
    p=HERE/'inputs'/(name+'.'+a.format)
    if a.format=='brep':
        s=TopoDS_Shape();assert BRepTools.Read_s(s,str(p),BRep_Builder())
    else:
        reader=STEPControl_Reader();assert reader.ReadFile(str(p))==IFSelect_RetDone
        assert reader.TransferRoots()==1;s=reader.OneShape()
    sg=signature(s);assert sg['solid_count']==1
    return s,sg

report={'schema':'razr-r13-native-complete-modified-region-readback-v1','completed':False,'format':a.format,
        'source_sha256':sha(__file__),'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'declarations_sha256':sha(HERE/'MODIFIED_REGION_DECLARATIONS.json'),'regions':{},'input_bodies':{},'failures':[],
        'native_zero_difference_is_not_exact_set_identity':True,'independent_kernel':False,
        'original_volume_gate_mm3':TOL,'full_15D_G2':False,'global_minimum_wall':False}
try:
    manifest=json.loads((HERE/'INPUT_MANIFEST.json').read_text())
    for name,row in manifest['files'].items():assert sha(HERE/row['copy_path'])==row['sha256']
    decl=json.loads((HERE/'MODIFIED_REGION_DECLARATIONS.json').read_text())
    factory=json.loads((HERE/'inputs/report.json').read_text());bodies={};fingerprints={}
    for name in sorted({r['body'] for r in decl['regions'].values()}):
        s,sg=load(name);bodies[name]=s;fingerprints[name]=fprint(s)
        expected=factory['body_exports'][name]['signature'] if 'signature' in factory['body_exports'][name] else factory['body_exports'][name]['signature_before']
        assert sg['solid_count']==expected['solid_count'] and abs(sg['signed_volume_mm3']-expected['signed_volume_mm3'])<=TOL
        report['input_bodies'][name]={'signature':sg,'fingerprint_before':fingerprints[name]}
    for name,row in decl['regions'].items():
        print(json.dumps({'stage':'start_region','name':name,'format':a.format}),flush=True)
        native=OUT/name;win=box(row['window']);crop=op(bodies[row['body']],win,'common')
        expected=None
        items=list(row['boxes'].items())
        if a.format=='step':items.reverse()
        for label,bd in items:
            part=box(bd);expected=part if expected is None else op(expected,part,'fuse')
        expected=op(expected,win,'common')
        rec={'body':row['body'],'full_declared_window':row['window'],'actual_crop':save(crop,native/'actual-crop.brep'),
             'expected_union':save(expected,native/'expected-union.brep'),'actual_complete_face_catalog':faces(crop)}
        for tag,x,y in [('actual_minus_expected',crop,expected),('expected_minus_actual',expected,crop)]:
            rec[tag]=save(op(x,y,'cut'),native/(tag+'.brep'),True)
        rec['original_material_gate_passes']=all(rec[tag]['signed_volume_mm3']<=TOL for tag in ('actual_minus_expected','expected_minus_actual'))
        report['regions'][name]=rec
        if not rec['original_material_gate_passes']:report['failures'].append({'region':name,'reason':'whole declared region differs; raw materials retained'})
    for name,s in bodies.items():
        after=fprint(s);report['input_bodies'][name]['fingerprint_after']=after;assert after==fingerprints[name]
    report['completed']=True
    report['all_declared_regions_match_under_original_native_gate']=not report['failures']
except BaseException as e:
    report['failures'].append({'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()})
finally:
    report['seconds']=time.monotonic()-started;report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    (OUT/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({'completed':report['completed'],'failures':len(report['failures']),'seconds':report['seconds'],'RSS':report['peak_RSS_bytes']}))
raise SystemExit(0 if report['completed'] and not report['failures'] else 1)
