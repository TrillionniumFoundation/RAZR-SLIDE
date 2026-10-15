"""Safety-negative architecture gate, not a verified physical electrical design."""
import json,itertools
from r25_capture import ROOT
from r38_parts import PUBLISHED_MATING_CYCLES,TARGET_SLIDE_CYCLES_ASSUMED,constant_z_u_loop_budget

def run(write=True):
    old=json.loads((ROOT/'verification/R37_faults.json').read_text())
    rows=[]
    for flex_continuous,insulation_intact,isolation_effective,pcb_bypass,mechanical_captured in itertools.product((False,True),repeat=5):
        live_exposed=pcb_bypass or not isolation_effective
        rows.append(dict(flex_loom_continuous=flex_continuous,
            flex_insulation_intact=insulation_intact,
            electric_isolation_effective=isolation_effective,
            pcb_single_point_bypass=pcb_bypass,
            mechanical_captured=mechanical_captured,
            electrical_hazard_unmitigated=(live_exposed or not insulation_intact),
            operating_link_qualified=False))
    out=dict(revision='R38 architectural negative-fault model (NOT measured electrical proof)',
        hypothetical_fault_states=len(rows),
        hypothetical_fault_matrix=rows,
        R37_legacy_unsafe_count=old['previous_legacy_unsafe_mechanical_modes'],
        R37_original_mechanical_states=old['previous_legacy_mechanical_modes'],
        R37_original_power_single_bypass=old['previous_single_point_electric_bypasses'],
        static_connector_catalogue_mate_cycles=PUBLISHED_MATING_CYCLES,
        required_slide_cycles_for_design_study=TARGET_SLIDE_CYCLES_ASSUMED,
        direct_mate_every_slide_rejected=PUBLISHED_MATING_CYCLES<TARGET_SLIDE_CYCLES_ASSUMED,
        fixed_mated_connector_architecture_requires_dynamic_fpc_qualified=True,
        insulation_loss_open_circuit_short_test_missing=True,
        actual_fpc_circuit_not_built=True,
        actual_dual_battery_isolation_circuit_not_built=True,
        no_real_flex_strain_cycle_or_SI_results=True,
        planar_U_budget=constant_z_u_loop_budget(),
        IEC_62715_6_42_is_not_OLED_lifetime_cert=True,
        manufacturing_go=False)
    if write:(ROOT/'verification/R38_faults.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    return out
if __name__=='__main__':run()
