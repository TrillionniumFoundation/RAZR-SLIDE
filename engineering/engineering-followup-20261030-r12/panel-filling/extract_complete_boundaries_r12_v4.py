"""New actual native census plus complete analytical boundary-support records."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib,json,os,resource,signal,sys,time,traceback
from pathlib import Path


def identity(p):
    p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}


def raw_only(value):
    derived={'method','exact_range','exact_support_radius_upper','full_circle_support_radius_upper','complete_pcurve_UV','complete_analytic_face_world_support','complete_swept_support','exact_carrier_volume_upper_mm3'}
    if isinstance(value,dict):return {k:raw_only(v) for k,v in value.items() if k not in derived}
    if isinstance(value,list):return [raw_only(v) for v in value]
    return value


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=int,default=180);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent;start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(805306368,805306368));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('180-second native extraction')));signal.alarm(args.seconds)
    report={'schema':'razr-r12-complete-current-panel-key-boundaries-v1','completed':False,'bodies':{},
            'native_set_identity_or_uniform_compiled_error_proved':False,'full_continuous_G2':False,
            'limits':{'seconds':args.seconds,'address_space_bytes':805306368,'cpus':1},'source':identity(__file__)}
    def progress(stage,**extra):
        row={'stage':stage,'elapsed_seconds':time.monotonic()-start,**extra}
        (args.output/'progress.json').write_text(json.dumps(row)+'\n');print(json.dumps(row),flush=True)
    try:
        import faulthandler
        faulthandler.dump_traceback_later(30,repeat=True)
        progress('before_import')
        sys.path.insert(0,str(root/'inputs'))
        import native_axis_inventory_r11 as native
        from OCP.BRep import BRep_Builder,BRep_Tool
        from OCP.BRepTools import BRepTools
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.TopAbs import TopAbs_FACE,TopAbs_VERTEX
        from OCP.TopoDS import TopoDS,TopoDS_Shape
        import complete_surface_support_v3 as support
        class NativeVertex:
            def __init__(self,value):self.value=value
            def toTuple(self):return BRep_Tool.Pnt_s(self.value).Coord()
        class NativeFace:
            def __init__(self,value):self.wrapped=value
            def geomType(self):
                kind=str(BRepAdaptor_Surface(self.wrapped).GetType()).rsplit('.',1)[-1]
                return {'GeomAbs_Plane':'PLANE','GeomAbs_Cylinder':'CYLINDER'}[kind]
            def Vertices(self):
                values=native.unique(self.wrapped,TopAbs_VERTEX)
                return [NativeVertex(TopoDS.Vertex_s(values.FindKey(i))) for i in range(1,values.Extent()+1)]
        progress('after_import')
        manifest=json.loads((root/'inputs/manifest.json').read_text())
        for name,row in manifest['files'].items():
            actual=identity(root/'inputs'/name);assert all(actual[k]==row[k] for k in ('bytes','sha256'))
        report['input_manifest']=identity(root/'inputs/manifest.json');report['support_source']=identity(support.__file__);report['native_raw_extractor_source']=identity(native.__file__)
        prior=json.loads((root/'inputs/geometry-v6-prior-report.json').read_text())
        for name in ('A_BACK_PANEL','L_KEY','R_KEY'):
            path=root/'inputs'/(name+'.brep');progress('before_shape_import',body=name);shape=TopoDS_Shape();assert BRepTools.Read_s(shape,str(path),BRep_Builder());progress('after_shape_import',body=name)
            progress('before_native_validity',body=name)
            metrics=native.metrics(shape);assert metrics['native_valid'] and metrics['counts']['solids']==1
            progress('before_native_volume',body=name)
            assert metrics['signed_volume_float']>0
            progress('after_native_volume',body=name)
            motion=(0,0,0) if name=='A_BACK_PANEL' else (0,12,0)
            rows=[];kinds=Counter();curves=Counter()
            face_map=native.unique(shape,TopAbs_FACE)
            faces=[NativeFace(TopoDS.Face_s(face_map.FindKey(i))) for i in range(1,face_map.Extent()+1)]
            for index,face in enumerate(faces):
                progress('before_face_support',body=name,index=index,kind=face.geomType())
                B,record=support.full_face_support(face,motion);record['face_index']=index
                progress('after_face_support',body=name,index=index)
                rows.append(record);kinds[record['kind']]+=1
                curves.update(e['pcurve']['type'] for e in record['edges'])
            assert len(rows)==metrics['counts']['faces']
            if name!='A_BACK_PANEL':
                saved=prior['sides'][name[0]]['complete_face_inventory']
                assert len(saved)==len(rows)
                for fresh,old in zip(rows,saved):
                    assert raw_only({k:v for k,v in fresh.items() if k!='face_index'})==raw_only(old['complete_face_support_certificate'])
            report['bodies'][name]={'input':identity(path),'whole_native_valid':True,'positive_native_signed_volume':metrics['signed_volume_float'],
                'native_face_count':len(rows),'native_unique_edge_count':metrics['counts']['edges'],'surface_types':dict(kinds),
                'complete_pcurve_occurrence_types':dict(curves),'motion':list(motion),'faces':rows,
                'box_count':len(rows),'native_compiled_set_identity_proved':False}
        report['completed']=True
    except Exception as exc:report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0);report['seconds']=time.monotonic()-start;report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'completed':report['completed'],'seconds':report['seconds'],'peak_RSS_bytes':report['peak_RSS_bytes'],
                      'body_census':{k:{x:v[x] for x in ('native_face_count','surface_types','complete_pcurve_occurrence_types')} for k,v in report['bodies'].items()},'failure':report.get('failure')}))
    if not report['completed']:raise SystemExit(1)

if __name__=='__main__':main()
