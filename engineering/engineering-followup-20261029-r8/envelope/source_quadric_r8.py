"""Exact serialized primitive correlations, with no native-error claim.

The old boxes, slabs, source order and full displacement box are retained.
Cylinder bounds use the inverse of the *stored* basis, never normalization.
"""
from fractions import Fraction as F
from itertools import product, combinations
import hashlib
import json

IDENTITY = [['1','0','0','0'], ['0','1','0','0'], ['0','0','1','0']]

def q(v):
    return F(v['exact'] if isinstance(v, dict) else v)

def vec(v): return tuple(map(q,v))
def box(v): return tuple(tuple(map(q,i)) for i in v)
def encbox(v): return [[str(x) for x in i] for i in v]
def dot(a,b): return sum((x*y for x,y in zip(a,b)), F(0))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def canonical(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def interval_dot(n,B):
    return (sum((min(n[k]*B[k][0],n[k]*B[k][1]) for k in range(3)),F(0)),
            sum((max(n[k]*B[k][0],n[k]*B[k][1]) for k in range(3)),F(0)))

def square_interval(i):
    a,b=i
    return (F(0) if a<=0<=b else min(a*a,b*b), max(a*a,b*b))

def quadric_basis(source, kind):
    data=source['local_surface' if kind=='face' else 'local_curve']
    O=vec(data['origin_exact' if kind=='face' else 'center_exact'])
    X,Y,Z=map(vec, (data['X_exact'],data['Y_exact'],data['axis_exact']))
    det=dot(X,cross(Y,Z))
    if not det: raise ValueError('singular original primitive basis')
    a=tuple(x/det for x in cross(Y,Z)); b=tuple(x/det for x in cross(Z,X))
    assert dot(a,X)==dot(b,Y)==1 and dot(a,Y)==dot(a,Z)==dot(b,X)==dot(b,Z)==0
    radius=q(data['radius'])
    if radius<=0: raise ValueError('nonpositive source radius')
    return {'origin':O,'X':X,'Y':Y,'Z':Z,'radius':radius,'a':a,'b':b,'determinant':det}

def quadric_range(basis,B, exact=True):
    """Closed-box minimum and maximum of a rank-two PSD quadratic.

    A maximum of a convex function on a box occurs at a vertex. A rank-two
    quadratic in 3D has a nonzero null direction. Every interior minimizer
    can follow that direction to the boundary without changing value.
    On each face either the 2x2 Hessian is nonsingular (one stationary
    candidate), or a null direction leads to its boundary. Thus vertices,
    the 12 edge stationary points and the six face stationary points suffice.
    Zero-width axes cause duplicate candidates, which remain valid.
    """
    O,a,b=basis['origin'],basis['a'],basis['b']
    Y=tuple((lo-O[k],hi-O[k]) for k,(lo,hi) in enumerate(B))
    ia,ib=square_interval(interval_dot(a,Y)),square_interval(interval_dot(b,Y))
    quick=(ia[0]+ib[0],ia[1]+ib[1])
    if not exact: return {'lower':quick[0],'upper':quick[1],'method':'interval_squares','candidate_count':0}
    def value(x): return dot(a,x)**2+dot(b,x)**2
    vertices=[tuple(Y[k][bits[k]] for k in range(3)) for bits in product((0,1),repeat=3)]
    values=[value(x) for x in vertices]
    best=min(zip(values,vertices),key=lambda v:v[0]); count=8
    for free_count in (1,2):
        for free in combinations(range(3),free_count):
            fixed=tuple(k for k in range(3) if k not in free)
            for bits in product((0,1),repeat=len(fixed)):
                x=[F(0)]*3
                for k,bit in zip(fixed,bits): x[k]=Y[k][bit]
                A=dot(a,x); C=dot(b,x)
                if free_count==1:
                    i=free[0]; denom=a[i]*a[i]+b[i]*b[i]
                    if not denom: continue
                    x[i]=-(a[i]*A+b[i]*C)/denom
                else:
                    i,j=free
                    aa=a[i]*a[i]+b[i]*b[i]; bb=a[j]*a[j]+b[j]*b[j]; ab=a[i]*a[j]+b[i]*b[j]
                    determinant=aa*bb-ab*ab
                    if not determinant: continue
                    ci=-(a[i]*A+b[i]*C); cj=-(a[j]*A+b[j]*C)
                    x[i]=(ci*bb-cj*ab)/determinant
                    x[j]=(cj*aa-ci*ab)/determinant
                if any(not Y[k][0]<=x[k]<=Y[k][1] for k in free): continue
                v=value(x); count+=1
                if v<best[0]: best=(v,tuple(x))
    assert quick[0]<=best[0]<=max(values)<=quick[1]
    return {'lower':best[0],'upper':max(values),'method':'vertices_edges_faces_exact',
            'candidate_count':count,'minimum_point':tuple(best[1][k]+O[k] for k in range(3)),
            'maximum_corner':vertices[values.index(max(values))]}

def source_model(record,kind):
    if record.get('location',{}).get('matrix_3x4_exact')!=IDENTITY: return None
    local='local_surface' if kind=='face' else 'local_curve' if kind=='edge' else None
    if local is None: return None
    global_key='native_global_surface' if kind=='face' else 'native_global_curve'
    d=record[local]
    if d!=record.get(global_key): return None
    typ=d['type'].rsplit('.',1)[-1]
    out={'kind':kind,'type':typ,'record_sha256':canonical(record),'record':record}
    if typ=='GeomAbs_Plane':
        O,X,Y=map(vec,(d['origin_exact'],d['X_exact'],d['Y_exact'])); n=cross(X,Y)
        if not any(n): return None
        out.update(origin=O,normal=n)
    elif typ=='GeomAbs_Line':
        O,V=map(vec,(d['origin_exact'],d['direction_exact'])); I=(q(d['first_parameter']),q(d['last_parameter']))
        if I[0]>I[1] or not any(V): return None
        out.update(origin=O,direction=V,parameter_interval=I)
    elif typ in ('GeomAbs_Cylinder','GeomAbs_Circle'):
        try: out['basis']=quadric_basis(record,kind)
        except ValueError: return None
    else: return None
    return out

def correlate(model,old_box,channel,D,exact_quadric=True):
    B=tuple((max(i[0],j[0]),min(i[1],j[1])) for i,j in zip(old_box,channel))
    if any(lo>hi for lo,hi in B): return {'code':'empty_closed_intersection'}
    stationary=tuple((lo-D[k][1],hi-D[k][0]) for k,(lo,hi) in enumerate(B))
    base={'kind':model['type'],'original_record_canonical_sha256':model['record_sha256'],
          'intersection_box_exact':encbox(B),'stationary_query_box_exact':encbox(stationary),
          'full_D_exact':encbox(D)}
    typ=model['type']
    if typ=='GeomAbs_Plane':
        n=model['normal']; support=dot(n,model['origin']); lo,hi=interval_dot(n,stationary)
        if support<lo or support>hi:
            return dict(base,code='plane',normal_exact=list(map(str,n)),support_exact=str(support),query_projection_exact=[str(lo),str(hi)])
    elif typ=='GeomAbs_Line':
        lo,hi=model['parameter_interval']; trace=[]
        for k in range(3):
            O,V=model['origin'][k],model['direction'][k]; left,right=stationary[k]
            if not V:
                if not left<=O<=right: return dict(base,code='line',empty_axis=k,zero_direction_coordinate_outside=True,parameter_trace=trace)
                continue
            interval=sorted(((left-O)/V,(right-O)/V));lo,hi=max(lo,interval[0]),min(hi,interval[1])
            trace.append({'axis':k,'parameter_interval_exact':list(map(str,interval)),'retained_interval_exact':[str(lo),str(hi)]})
            if lo>hi: return dict(base,code='line',empty_axis=k,zero_direction_coordinate_outside=False,parameter_trace=trace)
    else:
        basis=model['basis'];r2=basis['radius']**2; qr=quadric_range(basis,stationary,exact=False)
        if qr['lower']<=r2<=qr['upper'] and exact_quadric: qr=quadric_range(basis,stationary,exact=True)
        if qr['lower']>r2 or qr['upper']<r2:
            return dict(base,code='quadric',lower_exact=str(qr['lower']),upper_exact=str(qr['upper']),radius_squared_exact=str(r2),
                        range_method=qr['method'],candidate_count=qr['candidate_count'],
                        basis={k:([str(x) for x in v] if isinstance(v,tuple) else str(v)) for k,v in basis.items()},
                        classification='above_radius' if qr['lower']>r2 else 'below_radius')
    return None
