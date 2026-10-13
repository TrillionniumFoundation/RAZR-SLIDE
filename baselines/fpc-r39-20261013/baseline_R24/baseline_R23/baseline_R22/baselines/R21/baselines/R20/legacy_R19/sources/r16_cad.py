"""Parametric 3D end-clearance CAD, no OEM parts or validated fasteners. mm."""
from pathlib import Path
import json,hashlib
import cadquery as cq
from r16_model import G,M,ROOT
CAD=ROOT/'cad';CAD.mkdir(exist_ok=True)

def blk(x0,x1,y0,y1,z0,z1):
    assert x1>x0 and y1>y0 and z1>z0
    return cq.Workplane('XY').box(x1-x0,y1-y0,z1-z0,centered=False).translate((x0,y0,z0)).val()
def cyl_x(x0,x1,y,z,r):
    return cq.Solid.makeCylinder(r,x1-x0,cq.Vector(x0,y,z),cq.Vector(1,0,0))
def volume_overlap(a,b):
    return float(a.intersect(b).Volume())

def A_frame(g):
    w=g.W/2;Y=g.Y;H=g.H;t=g.T;end=H-g.bridge_end_relief
    shapes=[blk(-34.,34.,0,Y,0,t),
            blk(34.,w,0,Y,0,t),blk(-w,-34.,0,Y,0,t),
            blk(g.overlap_outer_lane_x0,w,Y,end,0,t),
            blk(-w,-g.overlap_outer_lane_x0,Y,end,0,t),
            blk(-33.5,33.5,Y,end,t-g.bridge_thickness,t)]
    v=shapes[0]
    for sh in shapes[1:]:v=v.fuse(sh)
    v=v.clean()
    # 2 bore channels per side, axis X. Pure geometric locking candidates.
    for dy in (4.,10.):
      yy=Y+dy
      v=v.cut(cyl_x(35.45,w+.15,yy,t/2,.71))
      v=v.cut(cyl_x(-w-.15,-35.45,yy,t/2,.71))
    v=v.clean()
    assert v.isValid() and len(v.Solids())==1,('A invalid',len(v.Solids()))
    return v

def B_frame_local(g):
    w=g.W/2;O=g.O;H=g.H;t=g.T
    shapes=[blk(-34.,34.,O,H,0,t),
            blk(34.,w,O,H,0,t),blk(-w,-34.,O,H,0,t),
            blk(g.overlap_inner_lane_x0,g.overlap_inner_lane_x1,0,O,0,t),
            blk(-g.overlap_inner_lane_x1,-g.overlap_inner_lane_x0,0,O,0,t)]
    v=shapes[0]
    for sh in shapes[1:]:v=v.fuse(sh)
    v=v.clean()
    for localY in (4.,10.):
      v=v.cut(cyl_x(33.80,35.30,localY,t/2,.90))
      v=v.cut(cyl_x(-35.30,-33.80,localY,t/2,.90))
    v=v.clean()
    assert v.isValid() and len(v.Solids())==1,('B invalid',len(v.Solids()))
    return v

def locking_pin(g,side,yoff=4.,extended=False):
    # A pocket/retracted: x=35.75..36.75. Engaged: x=34.15..36.75.
    x0,x1=(34.15 if extended else 35.75),36.75
    sh=cyl_x(x0,x1,g.Y+yoff,g.T/2,.55)
    return sh if side==1 else sh.mirror('YZ')

def scenario_shapes(g,s=None,z=0.,dx=0.,dy=0.,locked=False):
    s=g.Y if s is None else s
    a=A_frame(g)
    b=B_frame_local(g).translate(cq.Vector(dx,s+dy,-g.Z+z))
    pins=[locking_pin(g,side,yoff,locked) for side in (-1,1) for yoff in (4.,10.)]
    return a,b,pins

def interference(a,b,pins,locked=False):
    r={'A_B_core_and_rail_intersection_mm3':volume_overlap(a,b)}
    for j,p in enumerate(pins):
       r['pin%02d_A_intersection_mm3'%j]=volume_overlap(p,a)
       r['pin%02d_B_intersection_mm3'%j]=volume_overlap(p,b)
    return r

def cad_check(g,write=True):
    scenarios=[
       ('01_STOWED',0.,0.,0.,0.,False),
       ('02_Y_HALF',g.Y/2,0.,0.,0.,False),
       ('03_Y_FULL_Z_BEHIND',g.Y,0.,0.,0.,False),
       ('04_Z_HALF',g.Y,g.Z/2,0.,0.,False),
       ('05_SEATED_UNLOCKED',g.Y,g.Z,0.,0.,False),
       ('06_SEATED_4PINS_LOCKED',g.Y,g.Z,0.,0.,True),
       ('07_WORST_OFFSET_LOCKED',g.Y,g.Z,.10,.20,True),
       ('08_EARLY_Z_FORCE_COLLISION',g.Y-.60,g.Z,0.,0.,False),
       ('09_LOCKED_FORCE_REVERSE_COLLISION',g.Y-1.,g.Z,0.,0.,True),
       ('10_LIMIT_EARLY_DOCK_UNSAFE',g.Y-.20,g.Z,0.,0.,False)
    ]
    results=[]
    for name,s,z,dx,dy,locked in scenarios:
        a,b,pins=scenario_shapes(g,s,z,dx,dy,locked)
        metrics=interference(a,b,pins,locked)
        ass=cq.Assembly(name='R16_'+name)
        ass.add(a,name='A_fixed_functional_core_and_end_bridge_PROXY',color=cq.Color(.43,.47,.55))
        ass.add(b,name='B_rear_to_upper_functional_core_and_inner_tongues_PROXY',color=cq.Color(.19,.57,.84))
        for j,p in enumerate(pins):ass.add(p,name=f'SIDE_LATERAL_LOCK_PIN_PROXY_{j+1}',color=cq.Color(.96,.66,.23))
        fn=CAD/(f'R16_{name}.step')
        if write:
            ass.save(str(fn),exportType='STEP')
            reopen=cq.importers.importStep(str(fn)).solids().vals()
            assert all(v.isValid() for v in reopen)
            n_reopen=len(reopen)
            digest=hashlib.sha256(fn.read_bytes()).hexdigest()
        else:n_reopen=None;digest=None
        rec={'scenario':name,'s_mm':s,'z_mm':z,'dx_mm':dx,'dy_mm':dy,'locked':locked,
            'valid_proxy_solids':all(x.isValid() for x in [a,b,*pins]),
            'STEP_reimport_solids':n_reopen,'STEP_sha256':digest,'intersection':metrics}
        results.append(rec)
        print(name, 'A_B_mm3',round(metrics['A_B_core_and_rail_intersection_mm3'],5),
              'pins_to_B_max',round(max(metrics[f'pin{j:02d}_B_intersection_mm3'] for j in range(4)),5),flush=True)
    out={'revision':'R16 prototype complementary end envelopes',
         'results':results,'two_simplified_full_cabins_and_4_pins_only':True,
         'OEM_display_FPC_actuation_bearings_springs_screws_omitted':True,
         'manufacturing_approved':False}
    if write:(ROOT/'verification'/'R16_CAD_reimport_intersections.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
    return out

if __name__=='__main__':cad_check(G())
