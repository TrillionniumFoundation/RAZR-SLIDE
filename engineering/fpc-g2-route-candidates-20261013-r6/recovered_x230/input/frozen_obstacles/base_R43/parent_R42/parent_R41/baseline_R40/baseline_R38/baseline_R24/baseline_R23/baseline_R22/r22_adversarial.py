"""R22 independent fault-injection addendum.  Geometry only; NOT a certified safety mechanism.

The old R22 matrix ties the three deadbolts to an idealized seating oracle.
Here their fail-to-close or spurious-withdrawal states are independent of pose,
A-side seat, and the legacy dogs.  This deliberately exposes the common-cause
triple-release hazard instead of hiding it behind the oracle.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from itertools import product
from pathlib import Path
import json

from r22_mechanics import (ROOT, P, assembly_local, carriage_tab,
                           three_deadbolts, stop_contact_metrics,
                           exact_axis_aligned_box_overlap_volume, stop_effectively_locked)

STAGES = (
    ("STOW_SEATED", 0.0, 0.0),
    ("STOW_DEPART_0P03", .03, 0.0),
    ("STOW_DEPART_0P20", .20, 0.0),
    ("MID_TRAVEL", P.travel/2, 0.0),
    ("OPEN_Y_ONLY", P.travel, 0.0),
    ("OPEN_Z_NEAR_0P03", P.travel, P.z_travel-.03),
    ("OPEN_Z_NEAR_0P20", P.travel, P.z_travel-.20),
    ("OPEN_SEATED", P.travel, P.z_travel),
)


def physically_seated_pose(port, s, q, tol=1e-8):
    # Exact mathematical station for model classification; not actual latch datum.
    return (abs(s)<=tol and abs(q)<=tol) if port=="STOW" else (
        abs(s-P.travel)<=tol and abs(q-P.z_travel)<=tol)


def full_release_matrix():
    totals=dict(states=0, seated=0, unseated=0, unseated_blocked=0,
                unseated_unblocked=0, premature_all_three_open=0,
                legacy_both_open_centre_still_closed_blocked=0,
                one_stop_remaining_unseated_failures=0, two_or_more_remaining_unseated_failures=0)
    negative_samples=[]
    # Eight independent three-stop positions: cache actual CadQuery solid geometry.
    # The four old-dog combinations are intentionally NOT input to these stops.
    stop_cache={}
    for mask in product((False,True),repeat=3):
        solids=assembly_local(retracted=False,side_l_seated=mask[0],
             side_r_seated=mask[1],center_seated=mask[2])
        stop_cache[mask]=stop_effectively_locked(solids)
    for port in ("STOW", "OPEN"):
        for label,s,q in STAGES:
            seated=physically_seated_pose(port,s,q)
            for l_open,r_open,c_open,dog_l_open,dog_r_open in product((False,True), repeat=5):
                # Independent failure injection: NONE of the three stop positions
                # is inferred from position or the other two stops.
                blocked=stop_cache[(l_open,r_open,c_open)]
                remaining=sum(not x for x in (l_open,r_open,c_open))
                totals['states']+=1
                totals['seated' if seated else 'unseated']+=1
                if not seated:
                    totals['unseated_blocked' if blocked else 'unseated_unblocked']+=1
                    if remaining==0 and not blocked:
                        totals['premature_all_three_open']+=1
                        if len(negative_samples)<5:
                            negative_samples.append(dict(port=port,stage=label,
                                old_dog_l_open=dog_l_open,old_dog_r_open=dog_r_open,
                                new_stops_spuriously_all_open=True,
                                blocked=False,unseated=True))
                    if remaining==1 and not blocked:
                        totals['one_stop_remaining_unseated_failures']+=1
                    if remaining>=2 and not blocked:
                        totals['two_or_more_remaining_unseated_failures']+=1
                    if dog_l_open and dog_r_open and l_open and r_open and not c_open and blocked:
                        totals['legacy_both_open_centre_still_closed_blocked']+=1
    return dict(scope='Idealized box proxies: two stations x eight poses x eight independent new-stop states x four old-dog states',
        **totals,critical_negative_samples=negative_samples,
        no_actual_A_side_mechanical_capture_or_spring_model=True,
        complete_triple_release_has_a_proven_proxy_escape_path=True,
        engineering_gate_pass=False)


def first_hard_stop_interference(stops_open=(False,False,False),samples=801):
    """Exact AABB Z-axis travel sweep for BOX proxies, not electrical touch onset.

    All underlying solids are CadQuery/OCC boxes; once their bounding boxes are
    measured, evaluating translations numerically avoids 801 costly OCP copies.
    A separate test cross-checks the first positive overlap against OCC.
    """
    parked_box=carriage_tab(True).BoundingBox()
    bolts=three_deadbolts(*stops_open)
    boxes={k:v.BoundingBox() for k,v in bolts.items()}
    last_clear=None
    first_hit=None
    for n in range(samples):
        extension=n*.8/(samples-1)
        collision={}
        for name,b in boxes.items():
            dx=max(0.,min(parked_box.xmax,b.xmax)-max(parked_box.xmin,b.xmin))
            dy=max(0.,min(parked_box.ymax,b.ymax)-max(parked_box.ymin,b.ymin))
            dz=max(0.,min(parked_box.zmax+extension,b.zmax)-max(parked_box.zmin+extension,b.zmin))
            collision[name]=dx*dy*dz
        if any(v>1e-9 for v in collision.values()):
            first_hit=dict(extension_mm=round(extension,6),contacts=collision)
            break
        last_clear=round(extension,6)
    return dict(ideal_full_extension_mm=0.8,last_clear_sample_mm=last_clear,
                first_positive_solid_intersection=first_hit,
                contact_make_travel_mm='UNKNOWN - OEM contacts and pad stack missing',
                force_to_override_stop_N='UNKNOWN - no material/FEA/spring/fastener',
                not_hardware_pass=True)


def qualification_contract():
    return dict(
        M_LOCK={
            'A_side_center_key_geometry_captive_and_unforgeable_by_B_actuator':False,
            'positive_load_bearing_faces_with_material_FEA_and_safety_factor':False,
            'two_independent_default_engaged_retraction_springs':False,
            'contacts_forced_fully_retracted_before_any_A_B_separation':False,
            'power_isolated_before_power_contacts_separate':False,
            '30万次_污染_热循环_冲击_偏载_失弹试验':False,
            'positive_solid_box_proxy_only':True,
            'qualified':False},
        E_SEPARATE={'B_usbC_PHY_port_real_placement_CAD':False,
                    'TE_signal_aging_cycle_qualification':False,
                    'power_mating_connector_300k_OEM_approval':False,
                    'A_and_B_BMS_fuses_back_to_back_FET_schematic_PCB':False,
                    'FET_weld_open_short_thermal_hardware_tests':False,
                    'qualified':False},
        D_OLED={'7inch_full_package_step_from_supplier':False,
                'authorized_R3p4_dynamic_300k':False,
                'long_stow_residual_set_and_flattening_data':False,
                'full_boundary_tolerance_stack_pass':False,
                'qualified':False},
        overall='MANUFACTURING_NO_GO')


def run(write=True):
    m=full_release_matrix()
    assert m['states']==512
    assert m['unseated']==448
    assert m['unseated_unblocked']==56
    assert m['unseated_blocked']==392
    assert m['one_stop_remaining_unseated_failures']==0
    assert m['two_or_more_remaining_unseated_failures']==0
    motion={
        'all_stops_engaged':first_hard_stop_interference((False,False,False)),
        'only_center_engaged':first_hard_stop_interference((True,True,False)),
        'all_three_spuriously_released':first_hard_stop_interference((True,True,True))}
    assert motion['all_stops_engaged']['first_positive_solid_intersection'] is not None
    assert motion['only_center_engaged']['first_positive_solid_intersection'] is not None
    assert motion['all_three_spuriously_released']['first_positive_solid_intersection'] is None
    report=dict(revision='R22 adversarial verification addendum 2026-10-10',
                prior_320_cases_not_an_all_independent_stop_release_scan=True,
                exhaustive_512_case_matrix=m,continuous_carriage_travel=motion,
                unresolved_hardware_contract=qualification_contract(),
                verdict='NO_GO: centre physical capture and true sequence interlock still missing',
                manufacturing_go=False)
    if write:
        p=ROOT/'verification'/'R22_adversarial_results.json'
        p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

if __name__=='__main__':
    r=run()
    print(json.dumps({'matrix':{k:v for k,v in r['exhaustive_512_case_matrix'].items() if isinstance(v,int)},
                      'first_stop':r['continuous_carriage_travel']['all_stops_engaged']['first_positive_solid_intersection'],
                      'status':r['verdict']},ensure_ascii=False,indent=2))
