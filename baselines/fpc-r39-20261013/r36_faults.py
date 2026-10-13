"""R36 traces exactly what newly added keeper stops, and what still fails."""
import json
from r25_capture import ROOT

def run(write=True):
    i=json.loads((ROOT/'verification/R36_integration.json').read_text())
    d=json.loads((ROOT/'verification/R36_dynamic.json').read_text())
    t=json.loads((ROOT/'verification/R36_tolerance.json').read_text())
    r35=json.loads((ROOT/'verification/R35_faults.json').read_text())
    stop=[x for x in d['stages'] if x['action']=='R35_pin_axial_pull' and x['offset_mm']==.05]
    screw=[x for x in d['stages'] if x['action']=='R36_M08_unthreaded_screw_axial_pull']
    keeper_back=[x for x in d['stages'] if x['action']=='keeper_backout_after_screw_lost']
    square_nut=[x for x in i['parts']]
    out=dict(revision='R36 conditional keeper demonstrates upstream screw loss, NOT fail-safe',
      R35_original_fault_states=r35['original_R34_mechanical_joint_modes'],
      R35_original_joint_unsafe=r35['original_R34_unsafe_joint_modes'],
      electrical_single_bypass=r35['electrical_single_point_bypass_count'],
      old_R35_direct_pin_axial_loss_blocked_at_0p05_when_keeper_present=all(x['pin_hits_keeper']>1e-5 for x in stop),
      blocked_pin_overlap_by_side_mm3={x['side']:x['pin_hits_keeper'] for x in stop},
      M0p8_screw_unthreaded_bore_can_withdraw_without_OCC_contact=all(x['screw_hits_B']<1e-7 and x['screw_hits_keeper']<1e-7 for x in screw),
      keeper_can_withdraw_after_screw_lost=all(x['keeper_hits_B']<1e-7 for x in keeper_back),
      after_screw_then_keeper_loss_original_R35_pin_can_be_removed=True,
      pin_head_shear_defeats_head_only_keeper=True,
      square_nut_AABB_collides_B_each_side_mm3={x['side']:x['square_nut_catalogue_vs_B'] for x in square_nut},
      rejected_nut_pocket_operations=i['rejected_square_nut_pockets'],
      DIN6799_0p8_application_shaft_diameter_mm=1.2,R35_original_shaft_diameter_mm=.22,
      E_ring_requires_shaft_redesign=True,
      maker_M0p8x2_screw_candidate_catalogue_dimensions_only=True,
      maker_square_nut_catalogue_dimensions_only=True,
      retaining_screw_tapped_thread_or_nut_engagement_unimplemented=True,
      fastener_axial_retention_and_breakaway_force_not_measured=True,
      keeper_plate_shear_and_fatigue_unqualified=True,
      no_A_mating_pad=True,
      STOW_and_OPEN_fail_closed_capture_not_closed=True,
      earlier_36_of_64_still_unresolved=True,
      TE_catalogue_spring_cannot_be_used_for_battery_main_or_USB_SI_without_tests=True,
      OLED_oem_static_width_dynamic_radius_force_fatigue_absent=True,
      battery_and_PCB_bodies_not_imported=True,
      real_force_displacement_contact_timing_not_measured=True,
      research_tolerance_0p05=t['aggregation']['0.05'],
      manufacturing_go=False)
    if write:(ROOT/'verification/R36_faults.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print('R36 FAULTS pin head catch',out['old_R35_direct_pin_axial_loss_blocked_at_0p05_when_keeper_present'],
          'screw backout',out['M0p8_screw_unthreaded_bore_can_withdraw_without_OCC_contact'],
          'old 36 unsafe',flush=True)
    return out
if __name__=='__main__':run()
