"""Conditional component-corner arithmetic, not electrical measurement."""
from pathlib import Path
from itertools import product
import json, math

rows=[]
for v,r1,r2,drive_drop,vl,bias in product([3.135,3.465],[.99,1.01],[.99,1.01],[0,.1],[0,.1],[-15e-9,15e-9]):
    rd=47000*r1;rr=47000*r2;rth=rd*rr/(rd+rr)
    hi=(v-drive_drop)*rr/(rd+rr)+bias*rth
    lo=vl*rr/(rd+rr)+bias*rth
    # Resistor threshold corners and an explicit 10mV allocation, not a
    # guaranteed total error: comparator hysteresis has only a typical value.
    hlo_max=v*(10000*1.01)/(15000*.99+10000*1.01)+.010
    hhi_min=v*(15000*.99)/(10000*1.01+15000*.99)-.010
    lhi_min=v*(10000*.99)/(90900*1.01+10000*.99)-.010
    rows.append({'rail_V':v,'high_V':hi,'low_V':lo,
                 'high_lower_margin_V':hi-hlo_max,
                 'high_upper_margin_V':hhi_min-hi,
                 'low_upper_margin_V':lhi_min-lo})
min_margins={k:min(r[k] for r in rows) for k in ['high_lower_margin_V','high_upper_margin_V','low_upper_margin_V']}
assert min(min_margins.values())>0
vmax=3.465;rdmin=47000*.99;cmax=1.1e-9;cmin=.9e-9
max_probe_current=vmax/rdmin
source={'corner_cases':len(rows),'cases':rows,'minimum_conditional_margins_V':min_margins,
 'assumptions':{'bench_rail_V':[3.135,3.465],'drive_VOH_drop_V_at_output_load_le_100uA_max':.1,
   'drive_VOL_V_at_output_load_le_100uA_max':.1,'sense_input_bias_sum_abs_A':15e-9,
   'resistor_tolerance_fraction':.01,'capacitor_tolerance_fraction':.1,
   'allocated_comparator_total_threshold_error_V':.010,
   'allocation_is_manufacturer_guaranteed_total_error':False,
   'hysteresis_max_and_selected_resistor_capacitor_leakage_not_controlled':True},
 'dry_probe_short_current_max_A':max_probe_current,
 'dry_probe_capacitor_stored_energy_max_J':cmax*vmax**2/2,
 'dry_probe_energy_at_230ms_continuous_high_short_J':max_probe_current*vmax*.230,
 'main_power_fault_energy_J':None,
 'high_to_low_hold_slope_bound_V_per_s':max_probe_current/cmin,
 'analog_settling_7tau_s_healthy_max':7*(47000*1.01/2)*1.1e-9,
 'analog_settling_7tau_s_open_max':7*47000*1.01*1.1e-9,
 'clock_period_guarantee_s':None,
 'sample_hold_valid_with_actual_C_and_driver_waveform_measured':False,
 'watchdog_timeout_ms':[170,230],
 'watchdog_timeout_is_qualified_main_fault_energy_limit':False,
 'WDI_interface':{'rail_V_nominal':3.3,'WDI_VIH_required_V_nominal':2.64,
   'logic_VOH_min_at_100uA_V_nominal':3.2,'actual_WDI_node_has_inverter_input_max_uA':5,
   'WDI_node_pulldown_ohm':100000,'series_ohm':1000,
   'max_WDI_input_leakage_uA_from_datasheet':None,
   'complete_high_level_load_bound_proven':False,
   'reason':'TPS3431 WDI input leakage maximum absent; 100uA output condition cannot be asserted without controlled characterization'},
 'physical_measurements':0,'manufacturing_go':False}
Path(__file__).with_name('component_corner_receipt.json').write_text(json.dumps(source,indent=2)+'\n')
print(json.dumps({k:source[k] for k in ['corner_cases','minimum_conditional_margins_V','dry_probe_short_current_max_A','dry_probe_capacitor_stored_energy_max_J','manufacturing_go']}))
