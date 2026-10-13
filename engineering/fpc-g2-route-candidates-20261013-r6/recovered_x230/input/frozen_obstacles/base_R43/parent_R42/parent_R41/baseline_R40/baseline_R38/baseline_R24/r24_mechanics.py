"""R24 CAD ACTUATOR CANDIDATE, NOT ACTUAL LATCH QUALIFICATION. mm.

R23's centre OPEN A-key candidate collides with the moving U-bend of the OLED.
Instead place two distinct A-face actuator keys outside x=+-33.66 (nominal
OLED envelope) and route *proposed* moving carrier arms out from R23 carrier
lugs to independent outboard deadbolt/jaw pairs at each station.

STOW needs an A fixed longitudinal pusher, OPEN uses a 45deg Z/Y wedge.
Both are actual CAD solids with geometric contact-derived ideal motions.
Neither contains: captive shoulders, rigid follower bearings, preload,
retention screws, force/torque, OEM tolerance stack, anti-pick cover or 300k.
The CAM OPENINGS OCCUR TOO EARLY; an unsafe gap survives. NO MANUFACTURING.
"""
from __future__ import annotations
import sys, json, itertools
from pathlib import Path
import cadquery as cq
ROOT=Path(__file__).resolve().parent
R23=ROOT/'baseline_R23'
if str(R23) not in sys.path:sys.path.insert(0,str(R23))
from r23_gate import (P, r21, blk, intersection, to_global,to_blocal,
  carrier_lugs, guard_blocked, guard_overlap, independent_guard_jaws)

KEY_X_CENTERS={'L':-34.75,'R':34.75}
KEY_W=.40
LUG_CENTERS={'L':-34.26,'R':34.26}
LUG_W=.26
INBOARD_OLED_X_HALF=33.66045998455  # R17 param assumed full width; not OEM
JAW_Y=(-4.89,-4.39);LUG_Y=(-4.80,-4.53)
JAW_Z=(-3.10,-2.25);LUG_Z=(-3.64,-3.24)
CAM_STROKE=2.0
CARRIER_STROKE=.8
STOW_FACE_Y=15.61
OPEN_RAMP_START_Z=2.0;OPEN_RAMP_END_Z=4.0


def yz_prism(x0,x1,polygon):
    shape=cq.Workplane('YZ').polyline(polygon).close().extrude(x1-x0).val().translate((x0,0,0))
    assert shape.isValid() and len(shape.Solids())==1
    return shape


def a_key(port,side):
    x=KEY_X_CENTERS[side];lo,hi=x-KEY_W/2,x+KEY_W/2
    if port=='STOW':
        # Extends through A's 0 mm bottom; 0.30 mm intentional anchor overlap.
        return blk(lo,hi,13.20,STOW_FACE_Y,-3.40,.30)
    if port=='OPEN':
        # A outer rail is x>=35.6 (right), <=-35.6 (left).
        # Root intentionally overlaps this rail; 7-inch screen x<=33.66.
        rx0,rx1=(-36.05,-34.55) if side=='L' else (34.55,36.05)
        root=blk(rx0,rx1,80.0,81.0,6.15,6.65)
        nose=yz_prism(lo,hi,[(79.01,2.0),(79.86,2.0),(81.86,4.0),
                              (81.86,6.33),(79.01,6.33)])
        return root.fuse(nose).clean()
    raise ValueError(port)


def a_keys():
    return {f'A_R24_KEY_{port}_{side}':a_key(port,side)
            for port in ('STOW','OPEN') for side in ('L','R')}


def a_keyed_shell():
    a=r21.r17_assembly(P,0,0,0)['A']
    for key in a_keys().values():a=a.fuse(key).clean()
    return a


def outboard_lugs(extension=0.):
    assert 0<=extension<=CARRIER_STROKE
    return {f'B_R24_OUTBOARD_LUG_{side}':blk(LUG_CENTERS[side]-LUG_W/2,LUG_CENTERS[side]+LUG_W/2,*LUG_Y,
               LUG_Z[0]+extension,LUG_Z[1]+extension)
       for side,x in KEY_X_CENTERS.items()}


def outboard_jaws(shifts=None):
    if shifts is None:shifts=dict(L=0.,R=0.)
    return {f'B_R24_OUTBOARD_JAW_{side}':blk(*((-34.95,-34.08) if side=='L' else (34.08,34.95)),
              JAW_Y[0]+shifts[side],JAW_Y[1]+shifts[side],*JAW_Z)
       for side,x in KEY_X_CENTERS.items()}


def carrier_arms(extension=0.):
    """Each planar diagonal arm overlaps a distinct existing R23 lug AND the
    new outer lug in an ideal monolithic assembly. No fatigue/deflection proof.
    """
    out={}
    from shapely.geometry import LineString
    outline=LineString([(14.1,-2.665),(34.26,-4.665)]).buffer(.09,cap_style=2,join_style=2)
    sh=cq.Workplane('XY').polyline(list(outline.exterior.coords)).close().extrude(.20).val().translate((0,0,LUG_Z[0]+.01+extension))
    assert sh.isValid()
    out['B_R24_ARM_R']=sh
    out['B_R24_ARM_L']=sh.mirror('YZ')
    return out


def guard_overlap(extension=.8,shift_l=0.,shift_r=0.):
    lugs=outboard_lugs(extension);jaws=outboard_jaws(dict(L=shift_l,R=shift_r))
    return {side:intersection(lugs[f'B_R24_OUTBOARD_LUG_{side}'],
             jaws[f'B_R24_OUTBOARD_JAW_{side}']) for side in 'LR'}


def solve_jaw_shift_by_A_contact(port,side,s,q,tol=1e-5):
    """Ideal *push-only* prismatic follower. Geometry drives displacement;
    no fictitious Boolean 'seated' switch. Implied preloaded return spring
    and internal axes are NOT physical. Solver finds zero CAD overlap only.
    """
    key=a_key(port,side)
    lug=outboard_jaws({side:0., ('R' if side=='L' else 'L'):0.})[f'B_R24_OUTBOARD_JAW_{side}']
    dx=0;dy,dz=to_global(lug,port,s,q).BoundingBox().ymin-lug.BoundingBox().ymin,(-P.z_travel+q)+(8.05 if port=='STOW' else 6.25)
    # A world vs moving B local at this station is explicit 3D OCC placement.
    def clash(shift):
        moved=lug.translate(cq.Vector(0,shift,0))
        return intersection(key,to_global(moved,port,s,q))>1e-9
    if not clash(0.):return 0.
    if clash(CAM_STROKE+0.00005):return None # wedge still physically blocks at end of slot
    lo,hi=0.,CAM_STROKE+0.00005
    for _ in range(21):
        mid=(lo+hi)/2
        if clash(mid):lo=mid
        else:hi=mid
        if hi-lo<tol:break
    return round(hi,6)


def expected_ideal_release(port,s,q):
    """Predicted cam-only stroke from proposed known faces, used as independent
    analytic cross-check against OCC, not as the truth of real spring motion.
    """
    if port=='STOW':
        # At q=0, jaw path runs toward fixed face at y=15.61 as s decreases.
        # Nonzero q is an illegal lateral path and not passed as nominal.
        return min(2.,max(0.,2.-s)) if abs(q)<1e-8 else None
    if port=='OPEN':
        return min(2.,max(0.,q-6.2)) if abs(s-P.travel)<1e-8 else None
    raise ValueError(port)


def nominal_kinematic_table():
    poses=[('STOW',s,0.) for s in (3.0,2.0,1.8,1.7,1.6,1.59,1.0,0.2,0.)]
    poses += [('OPEN',P.travel,q) for q in (0.,4.,6.,6.2,6.4,6.6,6.61,7.,7.9,8.0,8.18,8.2)]
    out=[]
    for port,s,q in poses:
        L=solve_jaw_shift_by_A_contact(port,'L',s,q)
        R=solve_jaw_shift_by_A_contact(port,'R',s,q)
        aim=expected_ideal_release(port,s,q)
        # This is still an ideal Cam-contact solver, NOT force-qualified dynamics.
        if L is not None and aim is not None and abs(L-aim)>0.015:
            raise ValueError((port,s,q,L,R,aim))
        o=guard_overlap(.8, L or 0.,R or 0.) if L is not None and R is not None else {'L':0,'R':0}
        out.append(dict(port=port,s_mm=s,q_mm=q,ideal_A_contact_shift_L_mm=L,
            ideal_A_contact_shift_R_mm=R,independent_analytic_mm=aim,
            outboard_lug_blocking_mm3={k:round(v,8) for k,v in o.items()},
            both_outboard_jaws_clear=all(v<1e-8 for v in o.values()),
            physically_both_seated=(port=='STOW' and s==0. and q==0.) or
                                   (port=='OPEN' and s==P.travel and q==P.z_travel)))
    return out


def no_oled_clash_for_actual_keys():
    # Full manufactured laminate width unknown: R17's derived OLED only.
    samples=[(s,0.,0.) for s in (0.,2.,8.,16.,32.,48.,64.,P.travel)]
    samples += [(P.travel,q,0.) for q in (0.,1.,2.,3.,4.,5.,6.,7.,8.,8.2)]
    rows=[]
    for s,q,leaf in samples:
        refs=r21.r17_assembly(P,s,q,leaf)
        for name,sh in a_keys().items():
            rows.append(dict(key=name,s=s,q=q,oled_mm3=round(intersection(sh,refs['OLED']),9),
               fpc_mm3=round(intersection(sh,refs['FPC']),9)))
    return rows


def central_open_key_counterexample():
    # Same R23 central X=14.2, OPERATIONAL RAMP: deliberate FAIL probe.
    central=yz_prism(14.0,14.4,[(80.75,2.),(81.86,2.),(83.86,4.),
                         (83.86,6.35),(80.75,6.35)])
    return round(intersection(central,r21.r17_assembly(P,0.,0.,0.)['OLED']),9)


def evaluate(write=True):
    keys=a_keys();a=a_keyed_shell();n=no_oled_clash_for_actual_keys()
    k=nominal_kinematic_table()
    early=[x for x in k if not x['physically_both_seated'] and x['both_outboard_jaws_clear']]
    results=dict(revision='R24 outboard A metal keys + outboard B satellite mechanically driven CAD candidates',
       A_key_solids=4,A_keys_inside_parametric_OLED_width=False,
       actual_A_shell_with_keys_valid=a.isValid(),actual_A_shell_one_body=len(a.Solids())==1,
       A_key_screen_FPC_probe_count=len(n),A_key_screen_FPC_probe_failures=[x for x in n if x['oled_mm3']>1e-6 or x['fpc_mm3']>1e-6],
       rejected_central_OPEN_key_OLED_clash_mm3=central_open_key_counterexample(),
       cam_contact_samples=k,uncaptured_early_outboard_release_samples=early,
       outboard_cam_opens_early_before_captive_seat=bool(early),
       spring_and_capture_shoulders_unbuilt=True,
       moving_safety_arms_stiffness_not_qualified=True,
       manufacturing_go=False)
    if write:(ROOT/'verification'/'R24_mechanics.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    return results

if __name__=='__main__':
    r=evaluate()
    print(json.dumps({k:v for k,v in r.items() if k!='cam_contact_samples'},ensure_ascii=False,indent=2))
