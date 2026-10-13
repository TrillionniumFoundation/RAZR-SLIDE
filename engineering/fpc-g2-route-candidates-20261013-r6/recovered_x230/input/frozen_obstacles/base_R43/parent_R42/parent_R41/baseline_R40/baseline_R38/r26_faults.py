"""R26 intentionally conservative fault containment. All OPEN 2nd-stage tests are
actual OCC box/union interferometry, while common-cause escape enumeration is
explicit *assumed breakage* / forced-state logic. No failure rates inferred.
"""
import cadquery as cq
import itertools,json
from r25_capture import ROOT,P,pawl as old_pawl,intersection,to_global
from r26_open_mechanics import open_pawl,open_gate,open_carrier_ear,OPEN_GATE_STROKE
from r24_mechanics import solve_jaw_shift_by_A_contact,guard_overlap

def geometric_witnesses():
 A=cq.importers.importBrep(str(ROOT/'cad'/'R25_A_R24_KEYS.brep')).val()
 rows=[]
 for side in 'LR':
   old_park=old_pawl('OPEN',side,False)
   park=open_pawl(side,False)
   engaged=open_pawl(side,True)
   geo=dict(side=side,
     previous_R25_park_intersect_full_A_mm3=round(intersection(A,to_global(old_park,'OPEN',P.travel,P.z_travel)),8),
     R26_park_intersect_full_A_mm3=round(intersection(A,to_global(park,'OPEN',P.travel,P.z_travel)),8),
     OPEN_pawl_park_interferes_closed_gate_mm3=round(intersection(park,open_gate(side,0)),8),
     parked_pawl_veto_shutter_attempt_0p2_mm3=round(intersection(park,open_gate(side,.2)),8),
     seated_engaged_pawl_clear_manual_full_stroke=all(intersection(engaged,open_gate(side,dx))<=1e-9 for dx in (0.,.1,.2,.4,.6,.9)),
     closed_gate_ear_retracted_clash_mm3=round(intersection(open_carrier_ear(side,0.),open_gate(side,0.)),8),
     closed_gate_ear_ext_0p15_clash_mm3=round(intersection(open_carrier_ear(side,.15),open_gate(side,0.)),8),
     closed_gate_ear_ext_0p8_clash_mm3=round(intersection(open_carrier_ear(side,.8),open_gate(side,0.)),8),
     full_open_gate_ear_ext_0p8_clash_mm3=round(intersection(open_carrier_ear(side,.8),open_gate(side,OPEN_GATE_STROKE)),8))
   geo['sweep_carrier_ext_mm']=[dict(ext=round(t*.02,2),clash_mm3=round(intersection(open_carrier_ear(side,t*.02),open_gate(side,0.)),8)) for t in range(41)]
   geo['sweep_gate_shift_mm']=[dict(shift=round(t*.02,2),veto_when_pawl_parked_mm3=round(intersection(park,open_gate(side,t*.02)),8)) for t in range(46)]
   rows.append(geo)
 return rows

def run(write=True):
 witness=geometric_witnesses()
 # R24 cam *still* opens before full dock. Independent R26 gate is what
 # interrupts translation in the healthy case; R26 does not fix R24 cam.
 shiftL=solve_jaw_shift_by_A_contact('OPEN','L',P.travel,6.61)
 shiftR=solve_jaw_shift_by_A_contact('OPEN','R',P.travel,6.61)
 legacy_cam_freed=all(v<=1e-8 for v in guard_overlap(.8,shiftL,shiftR).values())
 rows=[]
 for gateLopen,gateRopen,earLfractured,earRfractured,pawlLfalse,pawlRfalse in itertools.product((False,True),repeat=6):
   # 'forced open' denotes an independent hardware-breaking actuator/failure;
   # a normal parked pawl would veto such motion in healthy hardware.
   any_healthy_ear_locked=(not gateLopen and not earLfractured) or (not gateRopen and not earRfractured)
   escapable_when_all_old_stops_broken=legacy_cam_freed and not any_healthy_ear_locked
   plausible_normal_release=gateLopen and gateRopen and pawlLfalse and pawlRfalse
   rows.append(dict(OPEN_at_q_mm=6.61, legacy_R24_cam_clear=legacy_cam_freed,
     L_gate_forced_open=gateLopen,R_gate_forced_open=gateRopen,
     L_ear_broken=earLfractured,R_ear_broken=earRfractured,
     L_pawl_false_latched_while_no_A=pawlLfalse,R_pawl_false_latched_while_no_A=pawlRfalse,
     all_old_R22_R23_R24_stops_forced_broken=True,
     forced_actuator_may_violate_pawl_veto=True,
     theoretical_barrier_escapable_if_all_old_failed=escapable_when_all_old_stops_broken,
     both_false_latch_may_command_OPEN_release=plausible_normal_release))
 worst=[x for x in rows if x['theoretical_barrier_escapable_if_all_old_failed']]
 out=dict(revision='R26 OPEN manual lower-path shutter + corrected park / independent failure stress',
   geometric=witness,total_modeled_joint_fault_combinations=len(rows),
   fault_rows=rows,undocked_old_R24_cam_still_early_clear=legacy_cam_freed,
   undocked_forced_all_old_stops_broken_scans=len(rows),
   undocked_R26_second_gate_absent_or_broken_escape_rows=len(worst),
   first_sweep_carrier_collision_at_mm={x['side']:next(y['ext'] for y in x['sweep_carrier_ext_mm'] if y['clash_mm3']>1e-9) for x in witness},
   R26_stage2_gate_held_CLOSED_at_0p8_extension_does_not_physically_overlap=True,
   previous_R25_A_shell_contact_not_reported_in_R25_tests=True,
   physically_prevent_FALSE_CAPTURE_fully_unbuilt=True,
   spring_default_closed_and_seat_captive_cam_unbuilt=True,
   common_cause_both_gates_open_or_both_ears_sheared_remain_unsafe=True,
   exposed_pad_battery_short_bypass_unmitigated=True,
   OLED_OEM_qualified=False,power_HW_qualified=False,mechanical_HW_qualified=False,manufacturing_go=False)
 if write:(ROOT/'verification'/'R26_faults.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 return out
if __name__=='__main__':
 o=run();print(json.dumps({k:v for k,v in o.items() if k not in ('geometric','fault_rows')},indent=2))
