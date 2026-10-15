#!/usr/bin/env python3
"""Machine-checkable missing-OEM-data gate; deliberately never approves manufacturing.
Vendor numerical limits must be checked against *new* collision-free OEM CAD and real tests.
"""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent
REQUIREMENTS={
 'FPC': ['vendor','part_number','stackup_drawing_revision','complete_cad','dyn_radius_min_mm','dynamic_cycles_qualified','neutral_axis','max_allowed_tension_N','connector_termination_drawing','copper_construction','bend_cycle_test_report'],
 'MECHANICAL': ['A_full_OEM_cad','B_full_OEM_cad','approved_modifiable_volume_cad','actual_shell_equal_outer_envelopes_verified','carrier_actuation_drawing','carrier_bearing_retention','GD_and_T','two_stage_mechanical_latch_proof','retraction_force_test_report'],
 'DISPLAY':['part_number','complete_OLED_CO_FPC_package_CAD','dyn_bend_radius_min_mm','long_stow_residual_set_data','flattening_force_vs_temperature','300k_cycle_test_report'],
 'POWER':['A_B_battery_BMS_diagram','peak_current_A','reverse_block_precharge_test','single_point_PCB_bypass_test','disconnect_voltage_timing_report'],
 'SIGNAL':['BOM_real_connector_pair','OEM_STEP','approved_footprints','termination_strain_relief_drawing','contact_wear_data'],
 'USB':['link_topology_and_rate','complete_stackup_and_return','connector_plus_cable_Sparams','TDR_eye_BER_test','moving_EMC_ESD_test']
}

def assess(data):
 missing={category:[k for k in keys if data.get(category,{}).get(k) in (None,'',[],{})] for category,keys in REQUIREMENTS.items()}
 # Even complete vendor-document packets would not automatically authorize build;
 # independent tests, stress/GD&T and accountable technical signoff are needed.
 return {'missing_by_gate':missing,'all_vendor_inputs_complete':all(not v for v in missing.values()),
         'requires_separate_OEM_collision_rebuild':True,'requires_independent_physical_test':True,
         'cad_candidate_go':False,'manufacturing_go':False}

def run():
 p=ROOT/'R43_vendor_input_template.json'
 if not p.exists():p.write_text(json.dumps({cat:{k:None for k in keys} for cat,keys in REQUIREMENTS.items()},ensure_ascii=False,indent=2)+'\n')
 x=assess(json.loads(p.read_text()));(ROOT/'verification/R43_vendor_gate.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
 print('MISSING BY GATE', {k:len(v) for k,v in x['missing_by_gate'].items()})
 return x
if __name__=='__main__':run()
