"""R23 local dual-inhibitor structural CAD experiment (mm); not safety qualified.

Two physically separated carrier load points (do not rely on the R22 common tab)
encounter two A-key-only, nominally spring-returned guarded jaws.  R22's three
old blockers may all be falsely released.  Jaws and carriers are exact OCC
solids, but A-key wedge/positive latch, spring, independent fixing, and real
mating datum remain UNBUILT.  In particular no result grants manufacturing.
"""
from __future__ import annotations
import sys, json, itertools, hashlib
from pathlib import Path
import cadquery as cq
ROOT=Path(__file__).resolve().parent
R22=ROOT/'baseline_R22'
if str(R22) not in sys.path:sys.path.insert(0,str(R22))
from r22_mechanics import (blk, P, carriage_tab, three_deadbolts,
      exact_axis_aligned_box_overlap_volume, stop_effectively_locked, assembly_local,
      qualifying_seat, to_global, integrated_b_shell, to_blocal, r21, intersection)
from r22_adversarial import STAGES, physically_seated_pose

CARRIER_STROKE=0.8
GUARD_RELEASE_Y=2.0
LUG_X={'L':(-14.75,-13.65),'R':(13.65,14.75)}
# All lengths below are RESEARCH IDEAL DIMENSIONS (not supplier measurements).
GUARD_Y=(-2.89,-2.39)
GUARD_Z=(-3.10,-2.25)
LUG_Z_RETRACTED=(-3.64,-3.24)
LUG_Y=(-2.80,-2.53)


def carrier_lugs(extension_mm:float=0.) -> dict[str,cq.Shape]:
    """Two spatially separate force paths to the existing cartridge backbone.
    A common underlying carrier still exists. Fastening not engineered.
    """
    assert 0<=extension_mm<=CARRIER_STROKE+1e-8
    return {f'B_R23_CARRIER_LUG_{side}':blk(x0,x1,*LUG_Y,
                   LUG_Z_RETRACTED[0]+extension_mm,
                   LUG_Z_RETRACTED[1]+extension_mm)
            for side,(x0,x1) in LUG_X.items()}


def independent_guard_jaws(guard_l_open=False,guard_r_open=False):
    return {f'B_R23_A_KEY_JAW_{side}':blk(*LUG_X[side],
                    GUARD_Y[0]+(GUARD_RELEASE_Y if opened else 0),
                    GUARD_Y[1]+(GUARD_RELEASE_Y if opened else 0),
                    *GUARD_Z)
            for side,opened in (('L',guard_l_open),('R',guard_r_open))}


def independent_guard_frames():
    """Structural REACTION-PATH proposals with roof in nominal zero-clearance
    face contact; material, fasteners, installation access, walls, bearing force
    and attachment into OEM B/A remain UNKNOWN. Not spring proof.
    """
    out={}
    for side,(xl,xr) in LUG_X.items():
        out[f'B_R23_FRAME_{side}_ROOF']=blk(xl-.35,xr+.35,-3.18,-.25,-2.25,-2.05)
        out[f'B_R23_FRAME_{side}_LEFT_RAIL']=blk(xl-.35,xl-.15,-3.18,-.25,-3.70,-2.05)
        out[f'B_R23_FRAME_{side}_RIGHT_RAIL']=blk(xr+.15,xr+.35,-3.18,-.25,-3.70,-2.05)
    return out


def spring_axis_proxies():
    """Cylindrical swept envelope placeholders; NO calibrated k or preload."""
    out={}
    for side,xc in [('L',-14.20),('R',14.20)]:
        out[f'B_R23_RETURN_SPRING_{side}_ENVELOPE_ONLY']=(
           cq.Workplane('XY').center(xc,.03).circle(.19).extrude(.58).val()
           .translate(cq.Vector(0,0,-3.05)))
    return out


def guarded_local_cartridge(extension_mm=0.,guard_l_open=False,guard_r_open=False):
    return {**carrier_lugs(extension_mm),**independent_guard_jaws(guard_l_open,guard_r_open)}


def guard_overlap(extension_mm=.8,guard_l_open=False,guard_r_open=False,method='occ'):
    parts=guarded_local_cartridge(extension_mm,guard_l_open,guard_r_open)
    calc=intersection if method=='occ' else exact_axis_aligned_box_overlap_volume
    return {side:float(calc(parts[f'B_R23_CARRIER_LUG_{side}'],parts[f'B_R23_A_KEY_JAW_{side}']))
            for side in ('L','R')}


def guard_blocked(ext=.8,guard_l_open=False,guard_r_open=False,lug_l_intact=True,lug_r_intact=True):
    v=guard_overlap(ext,guard_l_open,guard_r_open,method='aabb')
    return (lug_l_intact and v['L']>1e-8) or (lug_r_intact and v['R']>1e-8)


def local_interference_checks():
    tests=[]
    for ext in (0.,.10,.14,.141,.20,.50,.8):
        for l,r in itertools.product((False,True),repeat=2):
            a=guard_overlap(ext,l,r,'aabb');b=guard_overlap(ext,l,r,'occ')
            assert all(abs(a[k]-b[k])<1e-8 for k in a),(ext,l,r,a,b)
            tests.append({'extension_mm':ext,'jaw_l_open':l,'jaw_r_open':r,'mm3':a})
    retracted=guard_overlap(0,False,False)
    extended=guard_overlap(.8,False,False)
    open_all=guard_overlap(.8,True,True)
    assert all(v==0 for v in retracted.values())
    assert all(v>0 for v in extended.values())
    assert all(v==0 for v in open_all.values())
    roof=independent_guard_frames()
    for l,r in itertools.product((False,True),repeat=2):
        jaws=independent_guard_jaws(l,r)
        for side in ('L','R'):
            assert intersection(jaws[f'B_R23_A_KEY_JAW_{side}'],roof[f'B_R23_FRAME_{side}_ROOF'])<1e-8
            assert intersection(jaws[f'B_R23_A_KEY_JAW_{side}'],roof[f'B_R23_FRAME_{side}_LEFT_RAIL'])<1e-8
            assert intersection(jaws[f'B_R23_A_KEY_JAW_{side}'],roof[f'B_R23_FRAME_{side}_RIGHT_RAIL'])<1e-8
    return dict(local_occ_vs_aabb_cases=len(tests),parked_clear_mm3=retracted,
                extended_block_mm3=extended,extended_both_jaws_open_mm3=open_all,
                first_hit_ideal_extension_mm=0.140000001,
                assumed_clearance_at_rest_mm=round(GUARD_Z[0]-LUG_Z_RETRACTED[1],6),
                testing_extension_is_along_z_only=True,
                normal_use_not_proven=True)


def scan_independent_faults():
    """NOT a physical fault frequency; complete ideal state enumeration.
    Adds *independently faultable* two R23 jaw states to the R22 512 matrix.
    Most crucial: all 56 prior triple-release cases are blocked when either
    NEW jaw remains closed and its corresponding lug is intact.
    """
    totals=dict(states=0,unseated=0,previous_R22_dangerous_cases=0,
          R22_dangerous_now_blocked_both_new_closed=0,
          all_R22_open_both_new_open_unseated_escape=0,
          any_one_new_jaw_closed_both_lugs_intact_escape=0,
          one_carrier_lug_sheared_other_jaw_closed_escape=0,
          both_R23_lugs_sheared_R22_all_open_escape=0,
          A_key_missing_yet_guards_both_fault_open_escape=0)
    guard_cache={(l,r):guard_blocked(.8,l,r) for l,r in itertools.product((False,True),repeat=2)}
    oldcache={}
    for l,r,c in itertools.product((False,True),repeat=3):
        oldcache[l,r,c]=stop_effectively_locked(assembly_local(False,l,r,c))
    for port in ('STOW','OPEN'):
        for stage,s,q in STAGES:
            seated=physically_seated_pose(port,s,q)
            for dog_l,dog_r in itertools.product((False,True),repeat=2):
                for old_states in oldcache:
                    oldblocked=oldcache[old_states]
                    for new_l,new_r in itertools.product((False,True),repeat=2):
                        blocked=oldblocked or guard_cache[new_l,new_r]
                        totals['states']+=1
                        if seated:continue
                        totals['unseated']+=1
                        if not oldblocked:
                            totals['previous_R22_dangerous_cases']+=1
                            if not new_l and not new_r and blocked:
                                totals['R22_dangerous_now_blocked_both_new_closed']+=1
                            if new_l and new_r and not blocked:
                                totals['all_R22_open_both_new_open_unseated_escape']+=1
                                totals['A_key_missing_yet_guards_both_fault_open_escape']+=1
                        if (not new_l or not new_r) and not blocked:
                            totals['any_one_new_jaw_closed_both_lugs_intact_escape']+=1
    # Crosscuts independent of baseline 2048 counts: explicitly injected
    # upstream common carrier damage or one-sided shear.
    for shear_l,shear_r in itertools.product((False,True),repeat=2):
        for new_l,new_r in itertools.product((False,True),repeat=2):
            blocked=guard_blocked(.8,new_l,new_r,not shear_l,not shear_r)
            if shear_l and not shear_r and not new_r and not blocked:
                totals['one_carrier_lug_sheared_other_jaw_closed_escape']+=1
            if shear_l and shear_r and not blocked:
                totals['both_R23_lugs_sheared_R22_all_open_escape']+=1
    assert totals['states']==2048
    assert totals['unseated']==1792
    assert totals['R22_dangerous_now_blocked_both_new_closed']==56
    assert totals['all_R22_open_both_new_open_unseated_escape']==56
    assert totals['any_one_new_jaw_closed_both_lugs_intact_escape']==0
    assert totals['one_carrier_lug_sheared_other_jaw_closed_escape']==0
    assert totals['both_R23_lugs_sheared_R22_all_open_escape']==4
    return dict(**totals,
       R22_triple_release_alone_cannot_override_new_closed_jaws_in_cad=True,
       R23_both_false_open_or_common_carrier_failure_can_still_escape=True,
       A_key_mechanism_and_spring_not_physically_actuated=True,
       physical_mating_release_conditional_on_unbuilt_linkage=True,
       manufacturing_qualification=False)


def run(write=True):
    output=dict(revision='R23 split-carrier-jaw local CAD RESEARCH',
      rules={'two_independent_jaw_load_points':True,
             'each_jaw_A_insertion_only_actuation_PROPOSED_not_implemented':True,
             'fail_return_springs_physically_measured':False,
             'B_shell_fastener_anchors_qualified':False,
             'release_cam_physical_sequence_verified':False,
             'A_joint_three_dimensional_real_placement_verified':False},
      geometry=local_interference_checks(),
      independent_fault_enumeration=scan_independent_faults(),
      mandatory_rejects=['both R23 jaws false open while no A keys',
                         'both separated carrier lugs shear/leave mounting',
                         'spring debris jams jaw open',
                         'near-seat 0.03mm plus tolerance and wear',
                         'A key can falsely actuate under relative Y/Z motion'],
      manufacturing_go=False)
    if write:
        (ROOT/'verification'/'R23_lock_fault_results.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    return output

if __name__=='__main__':
    x=run()
    print(json.dumps({'geometry':x['geometry'],'faults':x['independent_fault_enumeration']},ensure_ascii=False,indent=2))
