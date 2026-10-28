"""Read preserved native operands and record their complete boundary inventory.

No Boolean, geometry repair, or tolerance change is executed. Local support
parameters and stored TopLoc matrices are both retained for exact analysis.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,sys,time,resource,math,importlib.metadata
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/"source-s4"))
import cadquery as cq,OCP
import product_assembly as p
from OCP.BinTools import BinTools
from OCP.TopoDS import TopoDS_Shape,TopoDS,TopoDS_Iterator
from OCP.TopLoc import TopLoc_Location
from OCP.BRepAdaptor import BRepAdaptor_Surface,BRepAdaptor_Curve,BRepAdaptor_Curve2d
from OCP.BRep import BRep_Tool
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.GeomAbs import GeomAbs_Plane,GeomAbs_Cylinder,GeomAbs_Line,GeomAbs_Circle


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def exact(values):return [str(F(float(v))) for v in values]
def scalar(v):return {"float":float(v),"hex":float(v).hex(),"exact":str(F(float(v)))}
def transform(shape):
    t=shape.Location().Transformation()
    return {"identity":shape.Location().IsIdentity(),"matrix_3x4_exact":[exact(t.Value(i,j) for j in range(1,5)) for i in range(1,4)],"form":str(t.Form())}
def index(shape,items):
    matches=[i for i,x in enumerate(items) if shape.IsSame(x.wrapped)]
    return matches[0] if len(matches)==1 else None


def curve_record(c,dimensions):
    result={"type":str(c.GetType()),"first_parameter":scalar(c.FirstParameter()),"last_parameter":scalar(c.LastParameter())}
    if c.GetType()==GeomAbs_Line:
        line=c.Line();result.update(origin_exact=exact(line.Location().Coord()),direction_exact=exact(line.Direction().Coord()))
    elif c.GetType()==GeomAbs_Circle:
        circle=c.Circle();result.update(center_exact=exact(circle.Location().Coord()),radius=scalar(circle.Radius()))
        if dimensions==3:
            result.update(axis_exact=exact(circle.Axis().Direction().Coord()),X_exact=exact(circle.XAxis().Direction().Coord()),Y_exact=exact(circle.YAxis().Direction().Coord()))
        else:result.update(X_exact=exact(circle.XAxis().Direction().Coord()),Y_exact=exact(circle.YAxis().Direction().Coord()))
    for name in ("IsClosed","IsPeriodic","Period"):
        try:result[name]=getattr(c,name)()
        except Exception as exc:result[name]={"unavailable":type(exc).__name__}
    return result


def surface_record(ad):
    record={"type":str(ad.GetType()),"U_interval":[scalar(ad.FirstUParameter()),scalar(ad.LastUParameter())],"V_interval":[scalar(ad.FirstVParameter()),scalar(ad.LastVParameter())]}
    if ad.GetType()==GeomAbs_Plane:
        g=ad.Plane();record.update(origin_exact=exact(g.Location().Coord()),axis_exact=exact(g.Axis().Direction().Coord()),X_exact=exact(g.XAxis().Direction().Coord()),Y_exact=exact(g.YAxis().Direction().Coord()))
    elif ad.GetType()==GeomAbs_Cylinder:
        g=ad.Cylinder();record.update(origin_exact=exact(g.Location().Coord()),axis_exact=exact(g.Axis().Direction().Coord()),X_exact=exact(g.XAxis().Direction().Coord()),Y_exact=exact(g.YAxis().Direction().Coord()),radius=scalar(g.Radius()))
    for name in ("IsUClosed","IsVClosed","IsUPeriodic","IsVPeriodic","UPeriod","VPeriod"):
        try:record[name]=getattr(ad,name)()
        except Exception as exc:record[name]={"unavailable":type(exc).__name__}
    return record


def inspect(shape):
    solids=shape.Solids();shells=shape.Shells();faces=shape.Faces();edges=shape.Edges();vertices=shape.Vertices()
    result={"shape_type":shape.ShapeType(),"orientation":str(shape.wrapped.Orientation()),"location":transform(shape.wrapped),
      "native_valid":shape.isValid(),"native_signed_volume":scalar(shape.Volume()),
      "counts":{"solids":len(solids),"shells":len(shells),"faces":len(faces),"edges":len(edges),"vertices":len(vertices)},
      "solids":[],"shells":[],"faces":[],"edges":[],"vertices":[],"incomplete_inventory":[]}
    try:result["original_whole_material_guard"]={"passed":True,"volume":p.volume(shape)}
    except Exception as exc:result["original_whole_material_guard"]={"passed":False,"failure":{"type":type(exc).__name__,"message":str(exc)}}
    for i,solid in enumerate(solids):
        c=BRepClass3d_SolidClassifier(solid.wrapped);c.PerformInfinitePoint(1e-7)
        result["solids"].append({"index":i,"orientation":str(solid.wrapped.Orientation()),"location":transform(solid.wrapped),"infinite_point_classification":str(c.State()),"signed_volume":scalar(solid.Volume())})
    for i,shell in enumerate(shells):
        result["shells"].append({"index":i,"orientation":str(shell.wrapped.Orientation()),"location":transform(shell.wrapped),"Closed_flag":shell.wrapped.Closed(),"face_indices":[index(x.wrapped,faces) for x in shell.Faces()]})
    for i,vertex in enumerate(vertices):
        local=TopoDS.Vertex_s(vertex.wrapped.Located(TopLoc_Location()))
        result["vertices"].append({"index":i,"orientation":str(vertex.wrapped.Orientation()),"location":transform(vertex.wrapped),"local_point_exact":exact(BRep_Tool.Pnt_s(local).Coord()),"native_global_point_exact":exact(BRep_Tool.Pnt_s(vertex.wrapped).Coord()),"tolerance":scalar(BRep_Tool.Tolerance_s(vertex.wrapped))})
    for i,edge in enumerate(edges):
        local=TopoDS.Edge_s(edge.wrapped.Located(TopLoc_Location()))
        record={"index":i,"orientation":str(edge.wrapped.Orientation()),"location":transform(edge.wrapped),"Closed_flag":edge.wrapped.Closed(),"degenerated":BRep_Tool.Degenerated_s(edge.wrapped),"tolerance":scalar(BRep_Tool.Tolerance_s(edge.wrapped)),"vertex_indices":[index(v.wrapped,vertices) for v in edge.Vertices()]}
        try:record.update(local_curve=curve_record(BRepAdaptor_Curve(local),3),native_global_curve=curve_record(BRepAdaptor_Curve(edge.wrapped),3))
        except Exception as exc:record["curve_failure"]={"type":type(exc).__name__,"message":str(exc)};result["incomplete_inventory"].append("edge-"+str(i))
        result["edges"].append(record)
    for i,face in enumerate(faces):
        local=TopoDS.Face_s(face.wrapped.Located(TopLoc_Location()))
        record={"index":i,"orientation":str(face.wrapped.Orientation()),"location":transform(face.wrapped),"native_valid":face.isValid(),"native_area":scalar(face.Area()),"tolerance":scalar(BRep_Tool.Tolerance_s(face.wrapped)),"local_surface":surface_record(BRepAdaptor_Surface(local,True)),"native_global_surface":surface_record(BRepAdaptor_Surface(face.wrapped,True)),"wires":[]}
        try:outer=face.outerWire().wrapped
        except Exception:outer=None
        for wi,wire in enumerate(face.Wires()):
            wr={"index":wi,"orientation":str(wire.wrapped.Orientation()),"location":transform(wire.wrapped),"Closed_flag":wire.wrapped.Closed(),"native_IsClosed":wire.IsClosed(),"is_outer":outer is not None and wire.wrapped.IsSame(outer),"edge_occurrences":[]}
            it=TopoDS_Iterator(wire.wrapped,True,True)
            while it.More():
                e=TopoDS.Edge_s(it.Value());er={"edge_index":index(e,edges),"orientation":str(e.Orientation()),"location":transform(e),"closed_on_this_face":BRep_Tool.IsClosed_s(e,face.wrapped)}
                try:er["pcurve"]=curve_record(BRepAdaptor_Curve2d(e,face.wrapped),2)
                except Exception as exc:er["pcurve_failure"]={"type":type(exc).__name__,"message":str(exc)};result["incomplete_inventory"].append("face-"+str(i)+"-wire-"+str(wi))
                if er["edge_index"] is None:result["incomplete_inventory"].append("unmapped-edge")
                wr["edge_occurrences"].append(er);it.Next()
            record["wires"].append(wr)
        result["faces"].append(record)
    return result


def main():
    require(sys.flags.optimize==0,"optimized Python execution is refused")
    out=Path(sys.argv[1]);out.mkdir(exist_ok=False);begin=time.monotonic()
    binding=json.loads((HERE/"INPUT_BINDING.json").read_text())
    report={"schema":"L8-complete-native-boundary-extraction-v1","extractor_sha256":sha(__file__),"input_binding_sha256":sha(HERE/"INPUT_BINDING.json"),"preregistration_sha256":sha(HERE/"CAPACITY_AND_METHOD_PREREGISTRATION.json"),
      "runtime":{"python":sys.version.split()[0],"python_executable":sys.executable,"flags":str(sys.flags),"optimize":sys.flags.optimize,"OCP":OCP.__version__,"packages":{n:importlib.metadata.version(n) for n in ("cadquery","cadquery-ocp","numpy","scipy")}},
      "original_volume_guard_sha256":sha(HERE/"source-s4/straight_envelope.py"),"new_Boolean_operations":0,"geometry_or_tolerances_modified":False,"operands":[],"completed":False}
    try:
        for item in binding["inputs"]:
            file=HERE/item["path"];require(sha(file)==item["sha256"] and file.stat().st_size==item["bytes"],"original input identity differs")
            native=TopoDS_Shape();require(BinTools.Read_s(native,str(file)),"native input read failed");shape=cq.Shape.cast(native)
            record={"input":item,"boundary":inspect(shape)};report["operands"].append(record)
            require(time.monotonic()-begin<120 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<768*2**20,"registered capacity limit")
            (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
            print(json.dumps({"case":item["case_id"],"role":item["role"],"counts":record["boundary"]["counts"],"types":[f["local_surface"]["type"] for f in record["boundary"]["faces"]],"incomplete":record["boundary"]["incomplete_inventory"]}),flush=True)
        report["completed"]=len(report["operands"])==16
    except Exception as exc:report["failure"]={"type":type(exc).__name__,"message":str(exc)}
    report["elapsed_seconds"]=time.monotonic()-begin;report["peak_RSS_bytes"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report.get(k) for k in ("completed","failure","elapsed_seconds","peak_RSS_bytes")}))
    return 0 if report["completed"] else 2


if __name__=="__main__":raise SystemExit(main())
