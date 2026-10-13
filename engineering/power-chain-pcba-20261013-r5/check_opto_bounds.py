"""Datasheet-condition arithmetic only, not a physical optocoupler test."""
from pathlib import Path
import json
# TI SLVSFC9C p9, Vishay 83465 p3. Optocoupler limits below are 25 C.
rpd_min=47000*.99;rpd_max=47000*1.01
load_max=4.4/rpd_min+.1e-6
off_max=(.1e-6+.1e-6)*rpd_max
on_min=2.7-.4
led_min=(3.3*.95-1.5)/(1500*1.01)
led_max=(3.3*1.05)/(1500*.99)
assert load_max<.25e-3 and off_max<.45 and on_min>1.223 and led_min>1e-3 and led_max<50e-3
d={'conditions':{'ambient_C':25,'minimum_actual_local_eFuse_VIN_V':2.7,'maximum_local_VIN_V':4.4,'driver_V':[3.135,3.465],'R_EN_PD_ohm':47000,'R_LED_ohm':1500,'resistor_tolerance_fraction':.01},'exact_opto':'VOS618A-8X001T','CTR_min_percent':130,'CTR_test_IF_A':.001,'CTR_test_VCE_V':5,'CTR_test_ambient_C':25,'CTR_not_used_as_a_guaranteed_low_VCE_or_full_temperature_bound':True,'family_VCEsat_max_V':.4,'family_VCEsat_test_IF_A':.001,'family_VCEsat_test_IC_A':.00025,'dark_current_max_A':100e-9,'dark_current_test_VCE_V':10,'dark_current_test_ambient_C':25,'TPS_EN_leak_abs_max_A':.1e-6,'TPS_UVLO_rise_max_V':1.223,'TPS_lowest_shutdown_fall_min_V':.45,'calculated_collector_load_max_A':load_max,'calculated_off_EN_max_V':off_max,'conditional_on_EN_min_V':on_min,'conditional_LED_current_A':[led_min,led_max],'LED_VF_max_at_50mA_used_at_lower_current_requires_monotonic_IV_inference':True,'using_saturation_test_at_IF_greater_than_1mA_and_IC_less_than_0p25mA_is_an_inference':True,'all_temperature_guarantee_available':False,'dynamic_off_delay_or_energy_measured':False,'component_3750Vrms_test_is_not_board_isolation_qualification':True,'physical_qualification':False,'manufacturing_go':False}
(Path(__file__).resolve().parent/'opto_bound_receipt.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:d[k] for k in ['calculated_collector_load_max_A','calculated_off_EN_max_V','conditional_on_EN_min_V','all_temperature_guarantee_available','manufacturing_go']}))
