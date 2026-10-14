"""Native STEP extraction and proof envelopes; no scene builder import.
All positions use the STOW e/q/r frame. Proof cages are not manufactured parts.
"""
from __future__ import annotations
import math
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from cam_contact_profile import ContactProfile
from straight_envelope import whole_material, single, fuse, swept_cylinder
TOL=1e-7

def world(side,e,q,r):
    if side not in ('L','R'):raise ValueError('invalid STOW side')
    return cq.Vector((-34.75-e) if side=='L' else (34.75+e),1.2-q,10+r)

def local(side,p):
    x,y,z=p.toTuple() if hasattr(p,'toTuple') else p
    return ((-x-34.75) if side=='L' else (x-34.75),1.2-y,z-10)

def box(side,e0,e1,q0,q1,r0,r1):
    a=world(side,e0,q0,r0);b=world(side,e1,q1,r1)
    lo=[min(x,y) for x,y in zip(a.toTuple(),b.toTuple())];hi=[max(x,y) for x,y in zip(a.toTuple(),b.toTuple())]
    return cq.Solid.makeBox(*(y-x for x,y in zip(lo,hi)),cq.Vector(*lo))

def bounds(side,shape):
    b=shape.BoundingBox();a=local(side,(b.xmin,b.ymin,b.zmin));z=local(side,(b.xmax,b.ymax,b.zmax))
    return tuple((min(x,y),max(x,y)) for x,y in zip(a,z))

def common(a,b):
    single(a);single(b);shape=a.intersect(b);_,vol=whole_material(shape,empty=True)
    if vol>min(a.Volume(),b.Volume())+TOL:raise ValueError('invalid signed common bound')
    return vol

def extract_profile(key,stop,side):
    single(key);single(stop);pins=[]
    for index,face in enumerate(stop.Faces()):
        if face.geomType()!='CYLINDER':continue
        c=BRepAdaptor_Surface(face.wrapped).Cylinder();axis=c.Axis().Direction()
        if abs(abs(axis.X())-1)<1e-9:
            p=c.Location();_,q,r=local(side,(p.X(),p.Y(),p.Z()));vv=[local(side,v.Center()) for v in face.Vertices()]
            pins.append((index,c.Radius(),q,r,min(x[0] for x in vv),max(x[0] for x in vv)))
    if len(pins)!=1:raise ValueError('missing or ambiguous transverse pin')
    index,radius,pinq,pinr,emin,emax=pins[0];floor=pinr-radius;floors=[];ramps=[]
    for i,face in enumerate(key.Faces()):
        if face.geomType()!='PLANE':continue
        n=face.normalAt();eqr=local(side,face.Center());vv=[local(side,v.Center()) for v in face.Vertices()]
        if abs(n.z-1)<1e-9 and abs(eqr[2]-floor)<TOL and -.61<eqr[0]<-.19:floors.append((i,vv))
        if abs(n.x)<1e-9 and n.y>1e-5 and n.z>1e-5 and -.61<eqr[0]<-.19 and floor-1.2<eqr[2]<floor:ramps.append((i,n.y/n.z,vv))
    if len(floors)!=1 or len(ramps)!=1:raise ValueError('native floor/ramp not uniquely identified')
    fi,fv=floors[0];ri,slope,rv=ramps[0];corner=min(v[1] for v in fv)
    if not any(abs(v[1]-corner)<TOL and abs(v[2]-floor)<TOL for v in rv):raise ValueError('ramp misses plateau corner')
    if any(abs(v[2]-(floor+slope*(v[1]-corner)))>TOL for v in rv):raise ValueError('inconsistent native ramp')
    if abs(radius-.1)>TOL or abs(slope-2)>TOL or abs(pinq)>TOL or abs(emin+.85)>TOL or abs(emax+.18)>TOL:raise ValueError('unrecognized source contact family')
    profile=ContactProfile(radius,floor,corner,slope,pinq,pinr-1.16)
    if abs(profile.evaluate(0)[0]-pinr)>TOL:raise ValueError('native home height differs')
    axis=cq.Vector(-1 if side=='L' else 1,0,0)
    pin=single(cq.Solid.makeCylinder(radius,emax-emin,world(side,emin,pinq,pinr),axis))
    outside=whole_material(pin.cut(stop),empty=True)[1]
    if outside>TOL:raise ValueError('pin carrier not inside native STOP')
    remainder=stop.cut(pin).clean();rem=whole_material(remainder)[1]
    if abs(rem+pin.Volume()-stop.Volume())>TOL:raise ValueError('STOP decomposition loses material')
    return profile,pin,remainder,{'pin_face':index,'floor_face':fi,'ramp_face':ri,'pin_e_extent_mm':[emin,emax],
        'native_pin_center_qr':[pinq,pinr],'native_pin_radius_mm':radius,'native_plane_slope':slope,
        'native_floor_corner_q_mm':corner,'native_floor_height_mm':floor,'native_STOP_volume_mm3':stop.Volume(),
        'full_pin_volume_mm3':pin.Volume(),'remainder_volume_mm3':rem,'pin_carrier_outside_native_STOP_mm3':outside,'profile':profile.receipt()}

def pin_path_envelope(profile,side,emin,emax):
    r=profile.pin_radius;axis=cq.Vector(-1 if side=='L' else 1,0,0);pieces=[];methods=[]
    def center(q):return world(side,emin,profile.pin_q-q,profile.evaluate(q)[0])
    a,b,c=profile.breakpoints
    for name,q0,q1 in [('free_lower_stop',profile.q_max,c),('ramp',c,b),('plateau',a,0.)]:
        start=center(q0);move=center(q1).sub(start)
        part,kind=swept_cylinder(start,axis,r,emax-emin,move);pieces.append(part)
        methods.append({'branch':name,'q_interval':[min(q0,q1),max(q0,q1)],'construction':kind})
    # Corner-center path has radius r. Its complete disk sweep is a radius-2r
    # sector plus endpoint disks. This is not a discrete pose union.
    t0=math.atan2(1.,-profile.ramp_slope);t1=math.pi/2
    origin=world(side,emin,profile.floor_corner_q,profile.floor_height)
    def point(t):return world(side,emin,profile.floor_corner_q+2*r*math.cos(t),profile.floor_height+2*r*math.sin(t))
    p0=point(t0);p1=point(t1);pm=point((t0+t1)/2)
    wire=cq.Wire.assembleEdges([cq.Edge.makeLine(origin,p0),cq.Edge.makeThreePointArc(p0,pm,p1),cq.Edge.makeLine(p1,origin)])
    sector=single(cq.Solid.extrudeLinear(wire,[],axis.multiply(emax-emin)))
    caps=[single(cq.Solid.makeCylinder(r,emax-emin,center(q),axis)) for q in (a,b)]
    pieces.append(fuse([sector,*caps]))
    methods.append({'branch':'rounded_corner','q_interval':[a,b],'construction':'radius_2r_sector_plus_endpoint_cylinders','sector_angles_rad':[t1,t0]})
    return fuse(pieces),{'branches':methods,'full_q_interval_mm':[0,profile.q_max],'native_pin_radius_mm':r,
        'construction_is_not_discrete_pose_union':True,'analytic_C1_corner_offset':True,'dynamic_force_qualified':False}

def remainder_cages(remainder,profile,side):
    # Partition proof enclosures only; no design material is selected/discarded.
    eb,qb,rb=bounds(side,remainder);cuts=[eb[0]-.01,-.61,.19,eb[1]+.01];out=[];sumvol=0
    for a,b in zip(cuts,cuts[1:]):
        piece=remainder.intersect(box(side,a,b,qb[0]-.01,qb[1]+.01,rb[0]-.01,rb[1]+.01))
        leaves,vol=whole_material(piece,empty=True);sumvol+=vol
        if not leaves:continue
        e,q,r=bounds(side,piece);shift=profile.lower_stop_height-(profile.floor_height+profile.pin_radius)
        cage=single(box(side,e[0],e[1],q[0]-profile.q_max,q[1],r[0]+shift,r[1]))
        if whole_material(piece.cut(cage),empty=True)[1]>TOL:raise ValueError('proof cage loses native material')
        out.append((cage,{'e_slab_mm':[a,b],'source_piece_volume_mm3':vol,'source_bounds_eqr_mm':[e,q,r],
            'motion_enclosure_eqr_mm':[e,[q[0]-profile.q_max,q[1]],[r[0]+shift,r[1]]],
            'uses_full_analytic_height_extrema':True,'conservative_box_not_exact_sweep':True}))
    if abs(sumvol-remainder.Volume())>TOL:raise ValueError('proof partition loses material')
    return out
