"""Fresh original-BREP ordered topology, full affine curves, and tolerance census."""
import argparse,hashlib,json,os,resource,signal,sys,time,traceback
from fractions import Fraction as F
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FACES=[104,109,110,115,118,121]
def identity(path):
    path=Path(path);return {'path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def line_record(ad):
    assert str(ad.GetType()).endswith('GeomAbs_Line'),'only actual complete LINE curves admitted'
    line=ad.Line();origin=list(line.Location().Coord());direction=list(line.Direction().Coord())
    first,last=F(ad.FirstParameter()),F(ad.LastParameter());assert first<=last
    return {'type':'LINE','origin':origin,'direction':direction,'origin_exact':list(map(lambda x:str(F(x)),origin)),
            'direction_exact':list(map(lambda x:str(F(x)),direction)),'complete_parameter_interval':[str(first),str(last)]}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(805306368,805306368));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('60-second native wire census limit')));signal.alarm(60)
    r={'schema':'razr-r13-complete-ordered-wire-native-census-v1','completed':False,'faces':[],
       'source':identity(__file__),'capacity_basis':identity(ROOT/'ALGORITHM_AND_CAPACITY.md'),
       'limits':{'seconds':60,'address_space_bytes':805306368,'cpus':1,'faces':6,'wires':12,'edges':48},
       'native_filled_domain_equals_completion_model_proved':False,'uniform_compiled_error_proved':False,'continuous_G2':False}
    try:
        import faulthandler;faulthandler.dump_traceback_later(20,repeat=True)
        sys.path.insert(0,str(ROOT/'inputs'))
        import native_axis_inventory_r11 as native
        import OCP
        from OCP.BRep import BRep_Builder,BRep_Tool
        from OCP.BRepTools import BRepTools,BRepTools_WireExplorer
        from OCP.BRepAdaptor import BRepAdaptor_Surface,BRepAdaptor_Curve2d,BRepAdaptor_Curve
        from OCP.TopExp import TopExp_Explorer,TopExp
        from OCP.TopAbs import TopAbs_FACE,TopAbs_WIRE,TopAbs_EDGE
        from OCP.TopoDS import TopoDS,TopoDS_Shape
        manifest=json.loads((ROOT/'inputs/INPUT_MANIFEST.json').read_text())
        for row in manifest['files']:
            actual=identity(ROOT/'inputs'/row['path']);assert all(actual[k]==row[k] for k in ('bytes','sha256'))
        r['input_manifest']=identity(ROOT/'inputs/INPUT_MANIFEST.json');r['OCP_version']=OCP.__version__
        r['native_helper']=identity(native.__file__)
        source=ROOT/'inputs/A_BACK_PANEL.brep';shape=TopoDS_Shape();assert BRepTools.Read_s(shape,str(source),BRep_Builder())
        r['input']=identity(source);r['whole_native_metrics']=native.metrics(shape)
        assert r['whole_native_metrics']['native_valid'] and r['whole_native_metrics']['signed_volume_float']>0
        assert r['whole_native_metrics']['counts']['solids']==1
        fmap=native.unique(shape,TopAbs_FACE);assert fmap.Extent()==298
        prior=json.loads((ROOT/'inputs/R12_trim_frontier.json').read_text());prior_map={f['face_index']:f for f in prior['faces']}
        full=json.loads((ROOT/'inputs/R12_native_boundaries.json').read_text())['bodies']['A_BACK_PANEL']['faces']
        edge_count=wire_count=0
        for fi in FACES:
            face=TopoDS.Face_s(fmap.FindKey(fi+1));ad=BRepAdaptor_Surface(face);assert str(ad.GetType()).endswith('GeomAbs_Plane')
            plane=ad.Plane();recipe={'origin':list(plane.Location().Coord()),'x_direction':list(plane.XAxis().Direction().Coord()),'y_direction':list(plane.YAxis().Direction().Coord())}
            assert all(recipe[k]==full[fi]['recipe'][k] for k in recipe)
            outer=BRepTools.OuterWire_s(face);wexp=TopExp_Explorer(face,TopAbs_WIRE);wires=[]
            while wexp.More():wires.append(TopoDS.Wire_s(wexp.Current()));wexp.Next()
            assert len(wires)==2
            frow={'face_index':fi,'native_face_orientation':str(face.Orientation()),'face_tolerance_exact':str(F(BRep_Tool.Tolerance_s(face))),
                  'plane_recipe':recipe,'wire_count':len(wires),'wires':[]}
            eexp=TopExp_Explorer(face,TopAbs_EDGE);occurrences=[]
            while eexp.More():occurrences.append(TopoDS.Edge_s(eexp.Current()));eexp.Next()
            assert len(occurrences)==8;used=[False]*8
            for wi,wire in enumerate(wires):
                wrow={'wire_index':wi,'native_is_outer_wire':wire.IsSame(outer),'native_closed_flag':wire.Closed(),
                      'orientation':str(wire.Orientation()),'edges':[],'joins':[]}
                walker=BRepTools_WireExplorer(wire,face);ordered=[];ends=[]
                while walker.More():
                    edge=TopoDS.Edge_s(walker.Current());idx=next(i for i,e in enumerate(occurrences) if not used[i] and edge.IsEqual(e));used[idx]=True
                    pc=line_record(BRepAdaptor_Curve2d(edge,face));c3=line_record(BRepAdaptor_Curve(edge))
                    first=TopExp.FirstVertex_s(edge,True);last=TopExp.LastVertex_s(edge,True)
                    assert not first.IsNull() and not last.IsNull()
                    vertices=[]
                    for vertex in (first,last):
                        vertices.append({'point':list(BRep_Tool.Pnt_s(vertex).Coord()),'tolerance_exact':str(F(BRep_Tool.Tolerance_s(vertex)))})
                    erow={'face_occurrence_index':idx,'orientation':str(edge.Orientation()),'pcurve':pc,'curve3d':c3,
                          'edge_tolerance_exact':str(F(BRep_Tool.Tolerance_s(edge))),
                          'same_parameter_flag':BRep_Tool.SameParameter_s(edge),'same_range_flag':BRep_Tool.SameRange_s(edge),
                          'degenerated_flag':BRep_Tool.Degenerated_s(edge),'oriented_vertices':vertices}
                    previous=prior_map[fi]['wires'][wi]['edges'][len(ordered)]
                    assert previous['face_occurrence_index']==idx and previous['orientation']==erow['orientation']
                    assert previous['origin_exact']==pc['origin_exact'] and previous['direction_exact']==pc['direction_exact']
                    assert previous['complete_trim_interval']==pc['complete_parameter_interval']
                    old=full[fi]['edges'][idx]
                    for fresh,field in ((pc,'pcurve'),(c3,'curve3d')):
                        assert fresh['origin']==old[field]['origin'] and fresh['direction']==old[field]['direction']
                        assert fresh['complete_parameter_interval']==old[field]['complete_trim_parameter_interval']
                    wrow['edges'].append(erow);ordered.append(edge);ends.append((first,last));walker.Next()
                assert len(ordered)==4
                for i,(_,last) in enumerate(ends):
                    next_first=ends[(i+1)%len(ends)][0]
                    wrow['joins'].append({'after_edge':i,'to_edge':(i+1)%len(ends),'same_native_vertex_identity':last.IsSame(next_first)})
                assert all(x['same_native_vertex_identity'] for x in wrow['joins'])
                assert wrow['native_is_outer_wire']==prior_map[fi]['wires'][wi]['native_is_outer_wire']
                assert wrow['orientation']==prior_map[fi]['wires'][wi]['orientation']
                frow['wires'].append(wrow);wire_count+=1;edge_count+=len(ordered)
            assert all(used);frow['all_face_occurrences_accounted_exactly_once']=True;r['faces'].append(frow)
        assert len(r['faces'])==6 and wire_count==12 and edge_count==48
        r.update(completed=True,wire_count=wire_count,complete_ordered_edge_count=edge_count,
                 original_r12_correspondence_exact=True,all_consecutive_edges_share_actual_native_vertex=True)
        assert r['input']==identity(source)
    except Exception as e:r['failure']={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0);r['seconds']=time.monotonic()-start;r['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r.get(k) for k in ('completed','wire_count','complete_ordered_edge_count','seconds','peak_RSS_bytes','failure')}))
    if not r['completed']:raise SystemExit(1)

if __name__=='__main__':main()
