"""Bounded raw native wire census; exact gaps prevent invented hole closure."""
import argparse,gzip,hashlib,json,os,resource,signal,sys,time,traceback
from fractions import Fraction as F
from pathlib import Path

def ident(path):
    path=Path(path);return {'path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parent;a.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(805306368,805306368));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('60 second trim frontier limit')));signal.alarm(60)
    report={'schema':'razr-r12-targeted-native-trim-frontier-v1','completed':False,'source':ident(__file__),
            'capacity_basis':ident(root/'TRIM_FRONTIER_BASIS.md'),'limits':{'seconds':60,'bytes':805306368,'cpus':1,'faces':64,'edge_occurrences':512},
            'new_spatial_splits':0,'new_split_depth':0,'original_split_limit':4096,'original_depth_limit':24,
            'original_threshold_exact':str(F(1e-7)),'native_set_identity_proved':False,'uniform_compiled_error_proved':False,
            'full_continuous_G2':False,'diagnostic_does_not_subtract_any_positive_residual':True}
    try:
        import faulthandler;faulthandler.dump_traceback_later(20,repeat=True)
        import projected_boundary_r12 as projection
        projections_path=root/'exterior-refinement-attempt1/complete_face_projections.json.gz'
        projections=json.load(gzip.open(projections_path,'rt'))['bodies']['A_BACK_PANEL']
        maximum=max(F(face[1][1]) for face in projections)
        blocked=set();targets=[]
        for key in ('L_KEY','R_KEY'):
            ledger_path=root/f'exterior-refinement-attempt1/{key}-exterior-ledger.json.gz'
            ledger=json.load(gzip.open(ledger_path,'rt'))
            for box in ledger['original_positive_boxes']:
                if F(box['upper_exact'])<=F(1e-7):continue
                B=[[F(v) for v in pair] for pair in box['box_exact']]
                tube=(B[0],(B[1][0],maximum+1),B[2]);failed=[]
                for index,face in enumerate(projections):
                    separated=False
                    for k,n in enumerate(projection.NORMALS):
                        lo,hi=projection.box_projection(tube,n)
                        if F(face[k][1])<=lo or F(face[k][0])>=hi:separated=True;break
                    if not separated:failed.append(index);blocked.add(index)
                targets.append({'key':key,'locator':box['locator'],'positive_volume_exact':box['positive_full_box_volume_exact'],
                                'open_tube_exact':[[str(x) for x in pair] for pair in tube],'blocking_faces':failed})
        assert len(blocked)<=64
        report.update(projections=ident(projections_path),targets=targets,blocking_face_indices=sorted(blocked))
        sys.path.insert(0,str(root/'inputs'))
        import native_axis_inventory_r11 as native
        from OCP.BRep import BRep_Builder,BRep_Tool
        from OCP.BRepTools import BRepTools,BRepTools_WireExplorer
        from OCP.BRepAdaptor import BRepAdaptor_Curve2d,BRepAdaptor_Curve
        from OCP.TopExp import TopExp_Explorer,TopExp
        from OCP.TopAbs import TopAbs_FACE,TopAbs_WIRE,TopAbs_EDGE,TopAbs_REVERSED
        from OCP.TopoDS import TopoDS,TopoDS_Shape
        path=root/'inputs/A_BACK_PANEL.brep';shape=TopoDS_Shape();assert BRepTools.Read_s(shape,str(path),BRep_Builder())
        faces=native.unique(shape,TopAbs_FACE);report['input']=ident(path);report['whole_face_count']=faces.Extent();assert faces.Extent()==298
        rows=[];total_edges=0;all_closed=True
        for index in sorted(blocked):
            face=TopoDS.Face_s(faces.FindKey(index+1));outer=BRepTools.OuterWire_s(face)
            explorer=TopExp_Explorer(face,TopAbs_WIRE);wires=[]
            while explorer.More():wires.append(TopoDS.Wire_s(explorer.Current()));explorer.Next()
            frow={'face_index':index,'native_face_orientation':str(face.Orientation()),'wire_count':len(wires),'wires':[]}
            face_edge_explorer=TopExp_Explorer(face,TopAbs_EDGE);face_occurrences=[]
            while face_edge_explorer.More():face_occurrences.append(TopoDS.Edge_s(face_edge_explorer.Current()));face_edge_explorer.Next()
            used=[False]*len(face_occurrences)
            for wi,wire in enumerate(wires):
                wrow={'wire_index':wi,'native_is_outer_wire':wire.IsSame(outer),'native_closed_flag':wire.Closed(),'orientation':str(wire.Orientation()),'edges':[]}
                walker=BRepTools_WireExplorer(wire,face)
                while walker.More():
                    edge=TopoDS.Edge_s(walker.Current());match=next(i for i,e in enumerate(face_occurrences) if not used[i] and edge.IsEqual(e));used[match]=True
                    pc=BRepAdaptor_Curve2d(edge,face);assert str(pc.GetType()).endswith('GeomAbs_Line')
                    line=pc.Line();origin=[F(v) for v in line.Location().Coord()];direction=[F(v) for v in line.Direction().Coord()]
                    first,last=F(pc.FirstParameter()),F(pc.LastParameter());start_uv=[x+v*first for x,v in zip(origin,direction)];end_uv=[x+v*last for x,v in zip(origin,direction)]
                    if edge.Orientation()==TopAbs_REVERSED:start_uv,end_uv=end_uv,start_uv
                    first_vertex=TopExp.FirstVertex_s(edge,True);last_vertex=TopExp.LastVertex_s(edge,True)
                    wrow['edges'].append({'face_occurrence_index':match,'orientation':str(edge.Orientation()),'type':'LINE',
                        'origin_exact':list(map(str,origin)),'direction_exact':list(map(str,direction)),
                        'complete_trim_interval':[str(first),str(last)],'oriented_start_UV':list(map(str,start_uv)),'oriented_end_UV':list(map(str,end_uv)),
                        'native_first_vertex':list(BRep_Tool.Pnt_s(first_vertex).Coord()),'native_last_vertex':list(BRep_Tool.Pnt_s(last_vertex).Coord()),
                        'native_first_vertex_tolerance':BRep_Tool.Tolerance_s(first_vertex),'native_last_vertex_tolerance':BRep_Tool.Tolerance_s(last_vertex)})
                    total_edges+=1;assert total_edges<=512;walker.Next()
                edges=wrow['edges'];assert edges
                gaps=[]
                for ei,edge in enumerate(edges):
                    after=edges[(ei+1)%len(edges)]
                    delta=[F(b)-F(a) for a,b in zip(edge['oriented_end_UV'],after['oriented_start_UV'])]
                    gaps.append({'after_edge':ei,'to_edge':(ei+1)%len(edges),'delta_UV_exact':list(map(str,delta)),'exactly_zero':all(v==0 for v in delta)})
                wrow['exact_endpoint_gaps']=gaps;wrow['exactly_closed']=all(g['exactly_zero'] for g in gaps)
                all_closed &= wrow['exactly_closed'];frow['wires'].append(wrow)
            assert all(used),'ordered wires must enumerate every original face edge occurrence exactly once'
            frow['all_face_occurrences_accounted']=True;frow['face_edge_occurrences']=len(face_occurrences);rows.append(frow)
        report.update(faces=rows,complete_ordered_edge_occurrences=total_edges,all_ordered_wires_exactly_closed=all_closed,
                      exact_trim_hole_refinement_admitted=False,
                      frontier='Ordered native wire identity is available, but exact serialized pcurve endpoints do not all close. No endpoint snapping or undocumented native tolerance/trim filling is admitted. Prior positive residual retained.' if not all_closed else 'Exact endpoint closure observed, but filled-trim domain equivalence still unproved; no refinement admitted.')
        report['completed']=True
    except Exception as e:report['failure']={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0);report['seconds']=time.monotonic()-start;report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report.get(k) for k in ('completed','blocking_face_indices','complete_ordered_edge_occurrences','all_ordered_wires_exactly_closed','exact_trim_hole_refinement_admitted','seconds','peak_RSS_bytes','failure')}))
    if not report['completed']:raise SystemExit(1)

if __name__=='__main__':main()
