"""Explicit safety failure witnesses, including a complete pin-then-bridge escape sequence."""
import json
import cadquery as cq
from r25_capture import ROOT,intersection
from r35_parts import bored_cap,pin,te_signal_envelope,PIN_BORE_RADIUS,PIN_SHAFT_RADIUS

def run(write=True):
    inherited=json.loads((ROOT/'verification/R34_faults.json').read_text())
    assembly=json.loads((ROOT/'verification/R35_dynamic.json').read_text())
    tol=json.loads((ROOT/'verification/R35_tolerance.json').read_text())
    B=cq.importers.importBrep(str(ROOT/'cad/R35_B_INBOARD_RAILS_AND_GUIDES.brep')).val()
    withdraw=[]
    for side in 'LR':
        cap=bored_cap(side); p=pin(side); gauge=te_signal_envelope(side)
        for dy in (0.,-.02,-.05,-.08,-.10,-.15,-.30,-.6,-1.):
            c=cap.translate((0,dy,0))
            withdraw.append(dict(side=side,bridge_withdrawal_y_mm=dy,
                bridge_hits_B=round(intersection(c,B),9),
                bridge_hits_installed_pin=round(intersection(c,p),9),
                bridge_hits_TE_gauge=round(intersection(c,gauge),9)))
    gauge_rows=assembly['catalogue_TE_front_withdrawal_samples']
    out=dict(revision='R35 retained-front-gauge hazard analysis, NO release',
       original_R34_mechanical_joint_modes=inherited['legacy_mechanical_combined_fault_states'],
       original_R34_unsafe_joint_modes=inherited['legacy_mechanical_combined_fault_escapes'],
       electrical_fault_enumerated_states=inherited['electrical_fault_tree_enumerated_states'],
       electrical_single_point_bypass_count=inherited['electrical_single_fault_bypass_count'],
       positive_nominal_mechanical_TE_front_stop=any(x['TE_cap_installed']>1e-6 for x in gauge_rows),
       TE_nominal_reverse_blocked_by_cap_while_installed=True,
       bridge_nominal_reverse_blocked_by_nominal_pin=True,
       axial_pin_extraction_unopposed_by_B_and_bridge=all(x['pin_intersects_B']<1e-7 and x['pin_intersects_cap']<1e-7 for x in assembly['pin_axial_withdrawal_samples']),
       pin_no_axial_clip_or_thread_or_locknut=True,
       after_pin_extraction_bridge_can_be_removed_then_TE_can_exit=True,
       radial_nominal_pin_hole_play_mm=round(PIN_BORE_RADIUS-PIN_SHAFT_RADIUS,6),
       gauge_front_clearance_to_cap_nominal_mm=0.06,
       simple_sum_nominal_two_slack_mm=round(PIN_BORE_RADIUS-PIN_SHAFT_RADIUS+0.06,6),
       two_slack_sum_not_an_electrical_make_break_measurement=True,
       risky_force_B_capturing_shear_unrated=True,
       soft_deadstop_energy_absorption_not_designed=True,
       A_side_mating_pad_not_designed=True,
       real_spring_contact_deformation_not_simulated=True,
       circuit_isolation_test_not_performed=True,
       USB_high_speed_signal_integrity_unverified=True,
       exact_OLED_module_bend_fatigue_unknown=True,
       battery_4700mAh_actual_cell_geometry_unverified=True,
       R29_front_lip_prior_0p030mm_unproven=True,
       complete_A_B_equal_finish_envelope_unverified=True,
       assumption_stress_offset_0p1=B is not None and tol['aggregation']['0.1'],
       removable_bridge_witness=withdraw,manufacturing_go=False)
    if write:(ROOT/'verification/R35_faults.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print('R35 FAULTS: old',out['original_R34_unsafe_joint_modes'],'pin removable',out['axial_pin_extraction_unopposed_by_B_and_bridge'],'NO-GO',flush=True)
    return out
if __name__=='__main__':run()
