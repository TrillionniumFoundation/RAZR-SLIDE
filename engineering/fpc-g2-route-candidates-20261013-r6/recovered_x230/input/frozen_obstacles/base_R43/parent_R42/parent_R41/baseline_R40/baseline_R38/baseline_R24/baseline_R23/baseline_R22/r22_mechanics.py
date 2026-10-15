"""R22 mechanical safety-stop design-research CAD, millimetres, NOT a manufactured linkage.

Upgrades R21 with 3 independent *positive-solid* stops on the single contact
carriage: L and R keyed load-face bolts, plus an independent face-captured
central deadbolt. The legacy L/R dog releases are NOT inputs to centre stop.

IMPORTANT: The movement of the stops is a prescribed ideal-kinematic proxy.
Neither spring/preload nor positively captive drive cam/gauge has been built.
CAD interference of this proxy is not a proof of physical fail-safe behavior.
"""
from __future__ import annotations
from pathlib import Path
import sys, json, itertools, math
import cadquery as cq
ROOT=Path(__file__).resolve().parent
R21=ROOT/'baselines'/'R21'
if str(R21) not in sys.path:sys.path.insert(0,str(R21))
import r21_geom as r21
from r21_geom import P, blk, intersection, STOW_Y, STOW_PAD_Z, OPEN_PAD_Z, union_solids
from r20_cad import local_assembly
from r20_model import p as contact_p

# These parameters are *invented* sensitivity targets and NOT dimensional control.
EXTRA_POCKET_CLEARANCE_MM = 0.12
SEAT_MAX_GAP_MM = 0.02  # exact-seat proxy; never a fielded mechanical fit tolerance
CAM_SETBACK_MM = 0.8
# Three blockers each remain normally engaged (fail-closed) without A-face keys.
SIDE_THROW_MM = 4.0
CENTRE_THROW_Y_MM = 1.4


def station_position(port:str)->tuple[float,float]:
    if port=='STOW':return STOW_Y,STOW_PAD_Z+P.z_travel
    if port=='OPEN':return 5.,OPEN_PAD_Z
    raise ValueError(port)


def to_blocal(solid:cq.Shape,port:str)->cq.Shape:
    y,z=station_position(port)
    return solid.translate(cq.Vector(0,y,z))


def to_global(solid:cq.Shape,port:str,s:float,q:float)->cq.Shape:
    y,z=station_position(port)
    return solid.translate(cq.Vector(0,y+s,z-P.z_travel+q))


def three_deadbolts(side_l_seated=False,side_r_seated=False,face_center_seated=False):
    """Solid obstructions: 'false open old L/R dogs' cannot move these."""
    left = blk(-9.5,-7.2,-3.05,-2.23,-3.00,-2.39)
    right= blk(7.2,9.5,-3.05,-2.23,-3.00,-2.39)
    center=blk(-1.25,1.25,-3.05,-2.23,-3.00,-2.39)
    if side_l_seated:left=left.translate(cq.Vector(-SIDE_THROW_MM,0,0))
    if side_r_seated:right=right.translate(cq.Vector(SIDE_THROW_MM,0,0))
    if face_center_seated:center=center.translate(cq.Vector(0,CENTRE_THROW_Y_MM,0))
    return {'B_LOAD_FACE_BOLT_L':left,'B_LOAD_FACE_BOLT_R':right,'B_INDEPENDENT_CENTRE_STOP':center}


def carriage_tab(retracted=True):
    dz=-contact_p.retract if retracted else 0.
    # continuous bar joins the inherited backbone (overlap, same rigid body)
    return blk(-10.0,10.0,-2.85,-2.45,-2.82+dz,-2.45+dz)


def assembly_local(retracted=True,side_l_seated=False,side_r_seated=False,center_seated=False,
                   old_dog_l_open=False,old_dog_r_open=False):
    pieces=local_assembly(retracted,old_dog_l_open,old_dog_r_open)
    pieces['B_CARRIAGE_SAFETY_TAB']=carriage_tab(retracted)
    pieces.update(three_deadbolts(side_l_seated,side_r_seated,center_seated))
    return pieces


def exact_axis_aligned_box_overlap_volume(a,b):
    """Analytic Boolean for deliberately AXIS-ALIGNED BOX primitives ONLY.

    We compare this to exact OpenCascade Boolean for every stop state in
    test_r22.py; never generalize to arbitrary OEM/filleted/rotated solids.
    """
    a=a.BoundingBox();b=b.BoundingBox()
    return max(0., min(a.xmax,b.xmax)-max(a.xmin,b.xmin))*\
           max(0., min(a.ymax,b.ymax)-max(a.ymin,b.ymin))*\
           max(0., min(a.zmax,b.zmax)-max(a.zmin,b.zmin))


def stop_contact_metrics(parts):
    tab=parts['B_CARRIAGE_SAFETY_TAB']
    return {k:round(exact_axis_aligned_box_overlap_volume(tab,parts[k]),9) for k in (
        'B_LOAD_FACE_BOLT_L','B_LOAD_FACE_BOLT_R','B_INDEPENDENT_CENTRE_STOP')}


def stop_effectively_locked(parts,eps=1e-7):
    return any(v>eps for v in stop_contact_metrics(parts).values())


def qualifying_seat(port,s,q,fixture_l=True,fixture_r=True,fixture_center=True,
                     xdatum_error_mm=0.,left_gap_override_mm=0.,right_gap_override_mm=0.):
    """Only a geometric pose/datum ORACLE.  Need a physically captured cam.

    Qualifying face flushness is unresolved pending datum GD&T and bearing-load
    tests. This function expressly does not use legacy L/R dogs as evidence.
    """
    if port=='STOW':
        primary=abs(s);transverse=abs(q)
    elif port=='OPEN':
        primary=abs(P.z_travel-q);transverse=abs(P.travel-s)
    else:raise ValueError(port)
    aligned=transverse<=SEAT_MAX_GAP_MM and abs(xdatum_error_mm)<=SEAT_MAX_GAP_MM
    left=fixture_l and aligned and primary+abs(left_gap_override_mm)<=SEAT_MAX_GAP_MM
    right=fixture_r and aligned and primary+abs(right_gap_override_mm)<=SEAT_MAX_GAP_MM
    # Captive central key demands both *independent A load faces* PLUS a separate
    # center receiver. A software 'both dog open' signal cannot move this gate.
    center=fixture_center and left and right and aligned and primary<=SEAT_MAX_GAP_MM
    return dict(left_face_proxied_seated=bool(left),right_face_proxied_seated=bool(right),
                captive_A_center_key_proxied_seated=bool(center),
                min_unseated_gap_mm=round(primary,6),transverse_error_mm=round(transverse,6),
                reference_only=True,actual_bearing_force_and_captured_linkage_unproved=True)


def cut_bounds(shapes:list[cq.Shape],padding_mm=EXTRA_POCKET_CLEARANCE_MM):
    bbs=[x.BoundingBox() for x in shapes]
    return blk(min(x.xmin for x in bbs)-padding_mm,max(x.xmax for x in bbs)+padding_mm,
               min(x.ymin for x in bbs)-padding_mm,max(x.ymax for x in bbs)+padding_mm,
               min(x.zmin for x in bbs)-padding_mm,max(x.zmax for x in bbs)+padding_mm)


def stop_pocket_local():
    """Machining-volume union of carrier stroke and three normal/open deadbolts."""
    candidate=[]
    for retract in (True,False):candidate.append(carriage_tab(retract))
    locked=three_deadbolts(False,False,False)
    cleared=three_deadbolts(True,True,True)
    for k in locked:candidate.extend([locked[k],cleared[k]])
    # With a single x-y-z bbox we'd remove huge volumes; separate swept bodies.
    return [cut_bounds([carriage_tab(True),carriage_tab(False)]),
            *[cut_bounds([locked[k],cleared[k]]) for k in locked]]


def integrated_b_shell():
    """R21 B shell with BOTH station deadbolt/tab travel cavities subtracted.

    This is an actual OCC cut + connected-solids inspection, not a drawing.
    Does NOT embody a machinable captive cam, axial pin, A-side seat key or
    a designed spring preload. Any B stability approval therefore remains false.
    """
    original=r21.run_dock_integration()['built_b_core']
    b=original
    rows=[]
    for port in ('STOW','OPEN'):
        pockets=[to_blocal(x,port) for x in stop_pocket_local()]
        this=[{'pocket_index':i,'mm3':round(p.Volume(),6),'overlap_with_original_B_mm3':round(intersection(original,p),6)}
              for i,p in enumerate(pockets)]
        for shape in pockets:b=b.cut(shape).clean()
        rows.append(dict(station=port,carved=this))
    return dict(R21_b=original,R22_b=b,cut_from_R21_mm3=round(original.Volume()-b.Volume(),6),
                valid=b.isValid(),one_connected_body=len(b.Solids())==1,
                solid_count=len(b.Solids()),pocket_rows=rows)


def regression_scenario(port,s,q, old_dogs_l=False,old_dogs_r=False,
                        forced_contact_extend=True, fixture_l=True,fixture_r=True,fixture_center=True,
                        left_gap_override_mm=0.,right_gap_override_mm=0.):
    datum=qualifying_seat(port,s,q,fixture_l,fixture_r,fixture_center,
                          left_gap_override_mm=left_gap_override_mm,right_gap_override_mm=right_gap_override_mm)
    solids=assembly_local(retracted=not forced_contact_extend,
        side_l_seated=datum['left_face_proxied_seated'],
        side_r_seated=datum['right_face_proxied_seated'],
        center_seated=datum['captive_A_center_key_proxied_seated'],
        old_dog_l_open=old_dogs_l,old_dog_r_open=old_dogs_r)
    stop_metrics=stop_contact_metrics(solids)
    block=stop_effectively_locked(solids)
    return dict(port=port,s_mm=s,q_mm=q,old_dogs_both_false_open=bool(old_dogs_l and old_dogs_r),
                force_extension_attempted=bool(forced_contact_extend),seat=datum,
                stop_interference_mm3=stop_metrics,mechanically_blocks_forced_extension=block,
                model_permission=(not block and not datum['actual_bearing_force_and_captured_linkage_unproved']),
                actual_hardware_verified=False)


def fault_scan():
    rows=[]
    states=[('STOW_SEAT',0.,0.),('STOW_DEPART_0p03',.03,0.),('STOW_DEPART_0p2',.2,0.),
            ('MID_SLIDE',P.travel/2,0.),('OPEN_PREDOCK',P.travel,0.),
            ('OPEN_NEAR_0p03',P.travel,P.z_travel-.03),
            ('OPEN_NEAR_0p2',P.travel,P.z_travel-.2),('OPEN_SEAT',P.travel,P.z_travel)]
    for port in ('STOW','OPEN'):
        for name,s,q in states:
            for dog_l,dog_r in itertools.product((False,True),repeat=2):
                for fl,fr,fc in ((True,True,True),(False,True,True),(True,False,True),
                                 (True,True,False),(False,False,False)):
                    r=regression_scenario(port,s,q,dog_l,dog_r,True,fl,fr,fc)
                    r.update(stage=name,fixture_L=fl,fixture_R=fr,fixture_center=fc)
                    rows.append(r)
    bad=[r for r in rows if r['force_extension_attempted'] and not r['seat']['captive_A_center_key_proxied_seated']
         and not r['mechanically_blocks_forced_extension']]
    seated=[r for r in rows if r['seat']['captive_A_center_key_proxied_seated']]
    fail_single=[r for r in rows if not r['seat']['captive_A_center_key_proxied_seated']]
    return dict(scenarios=len(rows),false_unlock_blocking_failures=len(bad),
                false_unlock_failures=bad,nominal_seated_arrangements=len(seated),
                unseated_arrangements=len(fail_single),
                all_unseated_extensions_physically_interfere_in_selected_local_proxy=len(bad)==0)

if __name__=='__main__':
    print(json.dumps({'mechanism':integrated_b_shell()['cut_from_R21_mm3'],'faults':fault_scan()},indent=2))
