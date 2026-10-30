"""Exact rational carriers for complete saved face representations.

Include every trim pcurve, every 3-D edge and every vertex.  Bounds are for the
serialized analytic representations.  They do not assert an independently
proved OpenCascade filling interpretation or a uniform compiled-evaluator
error.  In particular, no edge is replaced by a few sampled points.
"""
from fractions import Fraction as F
import math
from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve, BRepAdaptor_Curve2d
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS

def string_ranges(ranges):
    return [[str(a),str(b)] for a,b in ranges]

def point(p):
    return list(p.Coord())

def sqrt_upper(q):
    # Exact exponent-scaled dyadic outward bound, including arbitrary tiny q.
    # 128 bits relative resolution; no intermediate floating conversion.
    assert q>=0
    if q==0:return F(0)
    exponent=q.numerator.bit_length()-q.denominator.bit_length()
    if q<F(2)**exponent:exponent-=1
    assert F(2)**exponent<=q<F(2)**(exponent+1)
    step=F(2)**(exponent//2-128)
    scaled=q/(step*step)
    k=math.isqrt(scaled.numerator//scaled.denominator)
    low=k*step
    upper=low if low*low==q else (k+1)*step
    assert upper*upper>=q
    assert upper==0 or (upper-step)**2<q or upper*upper==q
    return upper


def union_ranges(ranges):
    assert ranges
    return [(min(r[i][0] for r in ranges),max(r[i][1] for r in ranges)) for i in range(len(ranges[0]))]

def point_range(p):
    return [(F(v),F(v)) for v in p]

def curve_range(ad,dimension):
    first,last=F(ad.FirstParameter()),F(ad.LastParameter())
    assert first<=last
    kind=str(ad.GetType()).rsplit('.',1)[-1]
    row={'type':kind,'complete_trim_parameter_interval':[str(first),str(last)]}
    if kind=='GeomAbs_Line':
        line=ad.Line();p=point(line.Location());direction=point(line.Direction())
        ranges=[]
        for a,b in zip(p,direction):
            lo,hi=sorted((F(b)*first,F(b)*last));ranges.append((F(a)+lo,F(a)+hi))
        row.update(origin=p,direction=direction,method='exact_affine_complete_trim')
    elif kind in ('GeomAbs_Circle','GeomAbs_Ellipse'):
        c=ad.Circle() if kind=='GeomAbs_Circle' else ad.Ellipse()
        p=point(c.Location());x=point(c.XAxis().Direction());y=point(c.YAxis().Direction())
        major=F(c.Radius()) if kind=='GeomAbs_Circle' else F(c.MajorRadius())
        minor=major if kind=='GeomAbs_Circle' else F(c.MinorRadius())
        radii=[sqrt_upper((major*F(x[i]))**2+(minor*F(y[i]))**2) for i in range(dimension)]
        ranges=[(F(p[i])-radii[i],F(p[i])+radii[i]) for i in range(dimension)]
        row.update(center=p,x_direction=x,y_direction=y,major=str(major),minor=str(minor),
                   exact_support_radius_upper=list(map(str,radii)),method='full_analytic_conic_support_contains_complete_trim')
    elif kind=='GeomAbs_BSplineCurve':
        c=ad.BSpline();degree=c.Degree()
        poles=[point(c.Pole(i)) for i in range(1,c.NbPoles()+1)]
        knots=[F(c.Knot(i)) for i in range(1,c.NbKnots()+1)]
        mult=[c.Multiplicity(i) for i in range(1,c.NbKnots()+1)]
        weights=[F(c.Weight(i)) for i in range(1,c.NbPoles()+1)]
        assert degree==1 and not c.IsPeriodic() and all(w==1 for w in weights),'unsupported rational/high-degree/periodic spline'
        assert len(knots)==len(poles) and mult==[2]+[1]*(len(knots)-2)+[2], 'noncanonical degree1 knots'
        assert all(a<b for a,b in zip(knots,knots[1:]))
        evaluations=[]
        for t in [first,last,*[k for k in knots if first<k<last]]:
            if t<=knots[0]:j=0
            elif t>=knots[-1]:j=len(knots)-2
            else:j=next(i for i in range(len(knots)-1) if knots[i]<=t<=knots[i+1])
            w=(t-knots[j])/(knots[j+1]-knots[j])
            evaluations.append([(1-w)*F(poles[j][i])+w*F(poles[j+1][i]) for i in range(dimension)])
        ranges=[(min(p[i] for p in evaluations),max(p[i] for p in evaluations)) for i in range(dimension)]
        row.update(degree=degree,poles=poles,knots=list(map(str,knots)),multiplicities=mult,
                   weights=list(map(str,weights)),trim_overruns_native_knots=first<knots[0] or last>knots[-1],
                   method='all_affine_pieces_plus_explicit_terminal_affine_continuation',
                   terminal_extrapolation_native_semantics_formally_proved=False)
    else:
        raise ValueError('unsupported complete analytic curve '+kind)
    row['exact_range']=string_ranges(ranges)
    return ranges,row

def full_face_support(face,motion):
    ad=BRepAdaptor_Surface(face.wrapped);kind=face.geomType()
    assert kind in ('PLANE','CYLINDER')
    base_uv=[(F(ad.FirstUParameter()),F(ad.LastUParameter())),(F(ad.FirstVParameter()),F(ad.LastVParameter()))]
    uv_ranges=[base_uv];world_ranges=[];edges=[]
    explorer=TopExp_Explorer(face.wrapped,TopAbs_EDGE)
    occurrences=[]
    while explorer.More():
        occurrences.append(TopoDS.Edge_s(explorer.Current()))
        explorer.Next()
    for index,edge in enumerate(occurrences):
        pc,pc_row=curve_range(BRepAdaptor_Curve2d(edge,face.wrapped),2)
        ec,ec_row=curve_range(BRepAdaptor_Curve(edge),3)
        uv_ranges.append(pc);world_ranges.append(ec)
        edges.append({'index':index,'occurrence_orientation':str(edge.Orientation()),'pcurve':pc_row,'curve3d':ec_row})
    uv=union_ranges(uv_ranges)
    if kind=='PLANE':
        p=ad.Plane();origin=point(p.Location());x=point(p.XAxis().Direction());y=point(p.YAxis().Direction())
        surface=[]
        for i in range(3):
            xa,xb=sorted((F(x[i])*uv[0][0],F(x[i])*uv[0][1]))
            ya,yb=sorted((F(y[i])*uv[1][0],F(y[i])*uv[1][1]))
            surface.append((F(origin[i])+xa+ya,F(origin[i])+xb+yb))
        recipe={'origin':origin,'x_direction':x,'y_direction':y,'kind':'affine_plane'}
    else:
        c=ad.Cylinder();origin=point(c.Location());x=point(c.XAxis().Direction());y=point(c.YAxis().Direction());axis=point(c.Axis().Direction());r=F(c.Radius())
        surface=[];radii=[]
        for i in range(3):
            radius=r*sqrt_upper(F(x[i])**2+F(y[i])**2);radii.append(radius)
            va,vb=sorted((F(axis[i])*uv[1][0],F(axis[i])*uv[1][1]))
            surface.append((F(origin[i])+va-radius,F(origin[i])+vb+radius))
        recipe={'origin':origin,'x_direction':x,'y_direction':y,'axis':axis,'radius':str(r),
                'full_circle_support_radius_upper':list(map(str,radii)),'kind':'complete_cylinder'}
    vertices=[list(v.toTuple()) for v in face.Vertices()]
    world_ranges += [surface]+[point_range(p) for p in vertices]
    support=union_ranges(world_ranges)
    motion=list(map(F,motion))
    swept=[(a+min(F(0),motion[i]),b+max(F(0),motion[i])) for i,(a,b) in enumerate(support)]
    volume=math.prod(b-a for a,b in swept)
    row={'kind':kind,'recipe':recipe,'reported_native_UV':string_ranges(base_uv),
         'complete_pcurve_UV':string_ranges(uv),'edges':edges,'vertices':vertices,
         'complete_analytic_face_world_support':string_ranges(support),
         'motion_exact':list(map(str,motion)),'complete_swept_support':string_ranges(swept),
         'exact_carrier_volume_upper_mm3':str(volume),
         'all_complete_trim_curves_edges_vertices_included':True,
         'edge_occurrences_including_opposite_cylinder_seams_enumerated':True,
         'sample_points_used_for_continuity_claim':False,
         'native_filling_semantics_or_uniform_compiled_error_proved':False}
    return swept,row
