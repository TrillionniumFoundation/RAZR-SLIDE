"""Complete native primitive inventory for the nine original local cases."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import native_axis_inventory_r11 as raw
from OCP.BRep import BRep_Builder,BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface,BRepAdaptor_Curve,BRepAdaptor_Curve2d
from OCP.BRepTools import BRepTools
from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS,TopoDS_Shape


def read_original(path):
    shape=TopoDS_Shape()
    if not BRepTools.Read_s(shape,str(path),BRep_Builder()):raise ValueError('original ASCII BREP read failed')
    return shape


def curve_record(curve,dimensions):
    point=raw.xyz if dimensions==3 else raw.xy
    row={'type':raw.enum(curve.GetType()),'range_exact':[raw.exact(curve.FirstParameter()),raw.exact(curve.LastParameter())]}
    if row['type']=='GeomAbs_Line':
        g=curve.Line();row.update(origin_exact=point(g.Location()),direction_exact=point(g.Direction()))
    elif row['type']=='GeomAbs_Circle':
        g=curve.Circle();row.update(origin_exact=point(g.Location()),X_exact=point(g.XAxis().Direction()),
                                   Y_exact=point(g.YAxis().Direction()),radius_exact=raw.exact(g.Radius()))
    return row


def inventory(shape):
    out={'metrics':raw.metrics(shape),'faces':[],'edges':[],'vertices':[]}
    fm=raw.unique(shape,TopAbs_FACE);em=raw.unique(shape,TopAbs_EDGE);vm=raw.unique(shape,TopAbs_VERTEX)
    for i in range(1,vm.Extent()+1):
        v=TopoDS.Vertex_s(vm.FindKey(i));out['vertices'].append({'index':i,'point_exact':raw.xyz(BRep_Tool.Pnt_s(v)),
                                                               'tolerance_exact':raw.exact(BRep_Tool.Tolerance_s(v))})
    for i in range(1,em.Extent()+1):
        e=TopoDS.Edge_s(em.FindKey(i));r=curve_record(BRepAdaptor_Curve(e),3)
        v=raw.unique(e,TopAbs_VERTEX)
        out['edges'].append({'index':i,'curve':r,'vertex_indices':[vm.FindIndex(v.FindKey(j)) for j in range(1,v.Extent()+1)],
                             'orientation':raw.enum(e.Orientation()),'tolerance_exact':raw.exact(BRep_Tool.Tolerance_s(e))})
    for i in range(1,fm.Extent()+1):
        f=TopoDS.Face_s(fm.FindKey(i));ad=BRepAdaptor_Surface(f,False);kind=raw.enum(ad.GetType())
        s={'type':kind,'UV_exact':[raw.exact(v) for v in BRepTools.UVBounds_s(f)]}
        if kind=='GeomAbs_Plane':
            g=ad.Plane().Position();s.update(origin_exact=raw.xyz(g.Location()),X_exact=raw.xyz(g.XDirection()),
                                           Y_exact=raw.xyz(g.YDirection()),axis_exact=raw.xyz(g.Direction()))
        elif kind=='GeomAbs_Cylinder':
            g=ad.Cylinder();s.update(origin_exact=raw.xyz(g.Location()),X_exact=raw.xyz(g.XAxis().Direction()),
                                    Y_exact=raw.xyz(g.YAxis().Direction()),axis_exact=raw.xyz(g.Axis().Direction()),radius_exact=raw.exact(g.Radius()))
        elif kind=='GeomAbs_SurfaceOfExtrusion':
            base=ad.BasisCurve();s['basis_curve']=curve_record(base,3);s['extrusion_direction_exact']=raw.xyz(ad.Direction())
            if raw.enum(base.GetType())=='GeomAbs_Line':
                g=base.Line();s.update(origin_exact=raw.xyz(g.Location()),X_exact=raw.xyz(g.Direction()),Y_exact=raw.xyz(ad.Direction()),affine_line_basis=True)
        face={'index':i,'surface':s,'orientation':raw.enum(f.Orientation()),'tolerance_exact':raw.exact(BRep_Tool.Tolerance_s(f)),
              'pcurves':[],'edge_indices':[],'vertex_indices':[]}
        ex=TopExp_Explorer(f,TopAbs_EDGE)
        while ex.More():
            edge=TopoDS.Edge_s(ex.Current());eid=em.FindIndex(edge);face['edge_indices'].append(eid)
            face['pcurves'].append({'edge_index':eid,'orientation':raw.enum(edge.Orientation()),'curve':curve_record(BRepAdaptor_Curve2d(edge,f),2)})
            ex.Next()
        fv=raw.unique(f,TopAbs_VERTEX);face['vertex_indices']=[vm.FindIndex(fv.FindKey(j)) for j in range(1,fv.Extent()+1)]
        out['faces'].append(face)
    return out
