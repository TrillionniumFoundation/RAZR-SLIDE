"""Exact whole-representation support along supplied covectors; no CAD calls."""
from fractions import Fraction as F
from math import isqrt


def V(items):return tuple(map(F,items))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def scalar(c,interval):return tuple(sorted((c*interval[0],c*interval[1])))
def plus(a,b):return a[0]+b[0],a[1]+b[1]
def sqrt_up(q):
    if q<0:raise ValueError('nonnegative square required')
    if not q:return F(0)
    exponent=q.numerator.bit_length()-q.denominator.bit_length()
    if q<F(2)**exponent:exponent-=1
    step=F(2)**(exponent//2-128);s=q/(step*step);k=isqrt(s.numerator//s.denominator)
    result=k*step
    return result if result*result==q else (k+1)*step


def curve_support(q,n):
    kind=q['type'];first,last=map(F,q['complete_trim_parameter_interval'])
    if kind=='GeomAbs_Line':
        center=dot(V(q['origin']),n);delta=scalar(dot(V(q['direction']),n),(first,last))
        return center+delta[0],center+delta[1]
    if kind in ('GeomAbs_Circle','GeomAbs_Ellipse'):
        center=dot(V(q['center']),n)
        r=sqrt_up((F(q['major'])*dot(V(q['x_direction']),n))**2+(F(q['minor'])*dot(V(q['y_direction']),n))**2)
        return center-r,center+r
    if kind=='GeomAbs_BSplineCurve':
        assert q['degree']==1 and all(F(w)==1 for w in q['weights'])
        knots=V(q['knots']);poles=[V(p) for p in q['poles']];values=[]
        for t in [first,last,*[k for k in knots if first<k<last]]:
            i=0 if t<=knots[0] else len(knots)-2 if t>=knots[-1] else next(i for i in range(len(knots)-1) if knots[i]<=t<=knots[i+1])
            w=(t-knots[i])/(knots[i+1]-knots[i]);point=tuple((1-w)*a+w*b for a,b in zip(poles[i],poles[i+1]))
            values.append(dot(point,n))
        return min(values),max(values)
    raise ValueError('unsupported complete world curve '+kind)


def face_support(face,n):
    p=face['recipe'];uv=[V(iv) for iv in face['complete_pcurve_UV']]
    center=dot(V(p['origin']),n)
    if p['kind']=='affine_plane':
        interval=plus((center,center),scalar(dot(V(p['x_direction']),n),uv[0]))
        interval=plus(interval,scalar(dot(V(p['y_direction']),n),uv[1]))
    elif p['kind']=='complete_cylinder':
        radius=F(p['radius'])*sqrt_up(dot(V(p['x_direction']),n)**2+dot(V(p['y_direction']),n)**2)
        interval=plus((center-radius,center+radius),scalar(dot(V(p['axis']),n),uv[1]))
    else:raise ValueError('unsupported complete source surface')
    values=[interval]+[curve_support(e['curve3d'],n) for e in face['edges']]
    values += [(dot(V(point),n),dot(V(point),n)) for point in face['vertices']]
    movement=dot(V(face['motion_exact']),n)
    return min(v[0] for v in values)+min(F(0),movement),max(v[1] for v in values)+max(F(0),movement)


NORMALS=((1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,-1,0))


def all_faces(body):
    return [[[str(x) for x in face_support(face,V(n))] for n in NORMALS] for face in body['faces']]


def box_projection(B,n):
    lo=hi=F(0)
    for c,iv in zip(n,B):
        a,b=scalar(F(c),iv);lo+=a;hi+=b
    return lo,hi


def channel_proof(B,face_projections):
    assert all(a<b for a,b in B)
    tubes=[box_projection(B,n) for n in NORMALS]
    witnesses=[]
    for i,projections in enumerate(face_projections):
        found=None
        for k,iv in enumerate(projections):
            a,b=map(F,iv);lo,hi=tubes[k]
            if b<=lo:found={'face':i,'normal':k,'relation':'boundary_at_or_below_open_channel'};break
            if a>=hi:found={'face':i,'normal':k,'relation':'boundary_at_or_above_open_channel'};break
        if found is None:return None
        witnesses.append(found)
    return {'open_channel_bounds_exact':[[str(a),str(b)] for a,b in B],
            'all_face_separation_witnesses':witnesses}
