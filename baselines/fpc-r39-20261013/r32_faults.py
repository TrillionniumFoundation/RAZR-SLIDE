"""R32 adversarial carry-over: geometrical witnesses + actuator indistinguishability.

A cartridge G A U G E cannot be counted as a connector, anti-false latch,
force-limited retractor or electrical isolator. A PASS here is correctly
preserving the inherited fatal counterexamples.
"""
from __future__ import annotations
import json,hashlib
from r25_capture import ROOT,intersection
from r31_tolerance import lift_with_offset
from r30_mechanics import gate,carrier


def run(write=True):
    inherited=json.loads((ROOT/'verification'/'R31_faults.json').read_text())
    power=json.loads((ROOT/'verification'/'R27_power_faults.json').read_text())
    q_pre=8.15;q_done=8.20
    # q-dz is the *same physical head position* for distinct true poses.
    # Thus a single continuous cam threshold cannot classify BOTH under
    # unknown datum displacement: no software logic can fix an ambiguous cam.
    indistinguishable=[
      dict(early_q_mm=q_pre,early_datum_error_z_mm=-.05,
           seated_q_mm=q_done,seated_datum_error_z_mm=0.,
           early_shelf_stroke_mm=round(lift_with_offset(q_pre,0,0,-.05),7),
           seated_shelf_stroke_mm=round(lift_with_offset(q_done,0,0,0.),7)),
      dict(early_q_mm=q_pre,early_datum_error_z_mm=0.,
           seated_q_mm=q_done,seated_datum_error_z_mm=.05,
           early_shelf_stroke_mm=round(lift_with_offset(q_pre,0,0,0.),7),
           seated_shelf_stroke_mm=round(lift_with_offset(q_done,0,0,.05),7))
    ]
    carrier_clash=[]
    for side in 'LR':
        for ext in (0.,.07,.08,.80):
            carrier_clash.append(dict(side=side,carrier_extension_mm=ext,
                closed_gate_intersection_mm3=round(intersection(gate(side,0),carrier(side,ext)),9)))
    d=dict(revision='R32 no-A capture and contact live-state adversarial evidence',
        R31_original_faults_sha256=hashlib.sha256((ROOT/'verification'/'R31_faults.json').read_bytes()).hexdigest(),
        R27_power_faults_sha256=hashlib.sha256((ROOT/'verification'/'R27_power_faults.json').read_bytes()).hexdigest(),
        inherited_mechanical_fault_space=inherited['old_R30_original_64_fault_modes'],
        inherited_mechanical_escape_counterexamples=inherited['old_R30_original_36_escapes'],
        inherited_double_interposer_stuck_release_escapes=inherited['new_cross_product_escapes_sum'],
        R32_nonenergized_dummy_has_no_anti_false_latch_or_elimination_of_old_faults=True,
        identical_follower_position_distinct_true_seat_witnesses=indistinguishable,
        cannot_make_zero_false_release_and_zero_seated_jam_by_threshold_alone_under_assumed_plusminus_0p05=True,
        carrier_residual_clash=carrier_clash,
        contact_first_make_last_break_position_from_supplier_missing=True,
        physical_retraction_limiting_force_and_safe_stall_missing=True,
        STOW_endpoint_independent_capture_not_built=True,
        power_fault_model_states=power['enumerated_fault_states'],
        power_minimal_dangerous_cut_set_count=len(power['minimal_cut_sets']),
        power_single_fault_dangerous_minimal_cut_count=len(power['one_fault_dangerous_minimal_cuts']),
        true_contact_voltage_contact_resistance_heating_thermal_arcing_not_measured=True,
        no_exact_OLED_panel_full_packaging_CAD_or_Rmin_qualification=True,
        manufacturing_go=False)
    if write:(ROOT/'verification'/'R32_faults.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    return d
if __name__=='__main__':
    d=run();print('R32 FAULTS',d['inherited_mechanical_escape_counterexamples'],d['power_minimal_dangerous_cut_set_count'],d['power_single_fault_dangerous_minimal_cut_count'],d['identical_follower_position_distinct_true_seat_witnesses'],flush=True)
