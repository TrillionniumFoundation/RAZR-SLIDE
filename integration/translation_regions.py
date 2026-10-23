"""Finite straight-translation enclosure as individually valid overlapping regions.
A material point first enters through an advancing boundary face. Planar
advancing faces contribute exact prisms; non-axial cylindrical faces contribute
full-carrier supersets. Axial cylinder normals have zero velocity projection
and contribute no advancing material. Start/end payloads are included whole.
The regions are proof enclosures, not selected/discarded manufactured pieces.
Their sum volume is not asserted to be the union volume. No global fuse needed.
"""
import math
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Vec
from straight_envelope import single, whole_material, swept_cylinder
import cadquery as cq

def regions(shape,vector):
    single(shape);move=cq.Vector(vector)
    if not all(math.isfinite(x) for x in move.toTuple()) or move.Length<=1e-12:raise ValueError('finite nonzero displacement required')
    out=[shape,shape.translate(move)];types=['whole_start','whole_end'];skipped=[]
    for i,face in enumerate(shape.Faces()):
        kind=face.geomType()
        if kind=='PLANE':
            if face.normalAt().dot(move)>1e-12:
                # Extrude the already-valid native face including its complete
                # trim topology; do not reconstruct it from wire closed flags.
                prism=BRepPrimAPI_MakePrism(face.wrapped,gp_Vec(*move.toTuple()),True)
                if not prism.IsDone():raise ValueError('native face prism construction failed')
                out.append(single(cq.Shape.cast(prism.Shape())));types.append('planar_face_'+str(i))
        elif kind=='CYLINDER':
            a=BRepAdaptor_Surface(face.wrapped);c=a.Cylinder();d=c.Axis().Direction();axis=cq.Vector(d.X(),d.Y(),d.Z())
            if axis.cross(move).Length<=1e-10:
                skipped.append(i);continue
            lo,hi=a.FirstVParameter(),a.LastVParameter()
            if not all(math.isfinite(x) for x in (lo,hi)) or hi<=lo:raise ValueError('unbounded cylindrical carrier')
            pos=c.Location();base=cq.Vector(pos.X(),pos.Y(),pos.Z()).add(axis.multiply(lo))
            carrier,method=swept_cylinder(base,axis,c.Radius(),hi-lo,move);out.append(single(carrier));types.append('cylinder_face_'+str(i)+'_'+method)
        else:raise ValueError('unsupported advancing surface '+kind)
    return out,{'translation_mm':move.toTuple(),'region_count':len(out),'region_kinds':types,'axial_cylinder_faces_without_advancing_normal':skipped,'overlaps_allowed_sum_not_union_volume':True,'complete_translation_not_pose_samples':True,'conservative_for_nonaxial_cylinders':True,'manufacturing_go':False}

def subtract_regions(shape,parts):
    result=shape
    for region in parts:
        # A validated empty compound is the mathematical empty set. Do not
        # submit it to another Boolean operation (some kernels return null).
        leaves,_=whole_material(result,empty=True)
        if not leaves:return result
        result=result.cut(region).clean()
    whole_material(result,empty=True)
    return result

def sum_common_upper_bound(values):
    """Union overlap is at most the sum of its nonnegative region overlaps.

    This is a conservative upper bound, never the union's measured volume.
    Applying a tolerance independently to each region can mask a larger total
    overlap assembled from several individually sub-tolerance intersections.
    """
    values=list(values)
    if not values or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values):
        raise ValueError('nonempty finite nonnegative region Common values required')
    total=math.fsum(values)
    if not math.isfinite(total):raise ValueError('nonfinite region Common upper bound')
    return total

def checks(parts,fixed):
    """Each positive region/obstacle common is retained; no cancellation."""
    single(fixed);values=[]
    for i,part in enumerate(parts):
        common=part.intersect(fixed);_,v=whole_material(common,empty=True)
        if v>min(part.Volume(),fixed.Volume())+1e-7:raise ValueError('impossible common volume')
        values.append(v)
    upper=sum_common_upper_bound(values)
    return {'region_common_mm3':values,'positive_region_count':sum(x>1e-7 for x in values),
        'common_upper_bound_mm3':upper,'common_upper_bound_is_sum_not_union_volume':True,
        'all_regions_clear':upper<=1e-7}
