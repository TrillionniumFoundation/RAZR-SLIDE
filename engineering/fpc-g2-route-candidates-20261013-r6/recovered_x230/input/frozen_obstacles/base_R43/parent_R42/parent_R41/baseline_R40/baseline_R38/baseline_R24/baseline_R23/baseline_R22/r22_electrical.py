"""R22 electrical safety topology study; NO fabricated PCB, connector rating, or SI evidence."""
from dataclasses import dataclass,asdict
from pathlib import Path
import json,itertools
ROOT=Path(__file__).resolve().parent

# Public vendor facts. Citation URLs in vendor/sources.md. These are NOT interchangeable devices.
TE_2199001 = dict(part='TE 2199001-1',rated_current_A=1.5,
  application='Signal',working_height_mm=[.7,1.0],free_height_mm=1.2,
  lifecycle_cycles_certified_for_slide_application=None,
  differential_impedance_or_usb_eye_test_available=False,
  approved_for_power=False,approved_for_usb_high_speed=False,
  original_manufacturer_source='https://www.te.com/en/product-2199001-1.html')
HARWIN_S1961 = dict(part='Harwin S1961-46R',rated_current_A=14.,
  body_xyz_mm=[4.63,3.70,3.55],manufacturer_durability_min_cycles=3000,
  proposed_slide_lifecycle_cycles=300000,demonstrated_slide_qualification=False,
  engineering_screen_lifetime_shortfall_ratio=100,
  source='https://www.harwin.com/products/S1961-46R',
  durability_source='https://cdn.harwin.com/pdfs/Harwin_SMT_Spring_Contacts_Comparison_Chart.pdf')
MILL_MAX_0985 = dict(part='Mill-Max 0985 family',maximum_current_A_30C_rise=8.,
  derated_current_A=6.4,manufacturer_mechanical_life_cycles=100000,
  slide_target_cycles=300000,qualified_as_installed=False,
  source='https://www.mill-max.com/products/discrete-spring-loaded-pins/spring-loaded-pin-with-standard-tail/0985')

MILL_MAX_0900 = dict(part='Mill-Max 0900-0-15-20-76-14-11-0',
   manufacturer_family_durability_cycles_range=[100000,1000000],
   nominal_max_continuous_A_from_family_brochure=2.0,
   nominal_peak_A_from_family_brochure=3.0,
   initial_height_mm=3.48,stroke_mm=0.991,
   important='Promising long-life RFQ only: exact 300k approval, current, 3.48mm packaged clearances and contact force NOT verified',
   fits_R21_TE_recess_directly=False,
   qualifying_300k_power_connector_approved=False,
   source='https://www.mill-max.com/sites/default/files/external/assets/2017-12/SMT%20Spring-Loaded%20Connectors.pdf',
   dimension_source='https://www.westfloridacomponents.com/mm5/graphics/U10/0900-0-15-20-76-14-11-0.pdf')

# Chosen architecture for the R22 *concept*, not an implemented circuit:
# USB-C and USB PHY are both within moving B; avoid unqualified cross-cabin USB.
# Two independent PCM/BMS-controlled batteries, absolutely NOT raw-paralleled.
# A->B supplemental power needs vendor-qualified GND/POWER contacts at either
# endpoint, precharge, hot-swap back-to-back FETs, isolation, fuses, and thermal tests.
ARCHITECTURE = dict(
 B_cabin=['SoC','USB-C_PHY','USB-C_receptacle_unplaced','B_local_battery_BMS',
          'system_power_rail','USB_and_display_on_B_only'],
 A_cabin=['larger_A_battery_target_NOT_FITTED','A_local_BMS','fuse',
          'back_to_back_BAT_FETs','precharge_limiter','temperature_sense'],
 cross_cabin_signal='ONLY slow control / wake or sensor signals as an exploratory lane; no qualified TE electrical implementation',
 cross_cabin_usb='NOT ROUTED: USB-C placed in B by architectural decision; no claim on actual B mechanical fit',
 cross_cabin_power='DEDICATED qualified-power connector class REQUIRED, specific supplier NOT SELECTED',
 two_end_stations='STOW and OPEN each have independent keyed sets; never both selected',
 raw_battery_positive_direct_parallel=False,
 intended_mechanical_life_cycles=300000,
 target_total_capacity_mAh=4700,target_total_capacity_proven=False,
 battery_thermal_mechanical_safety_qualified=False)

@dataclass(frozen=True)
class InterconnectInputs:
 stow_seat:bool=False
 open_seat:bool=False
 independent_load_faces:bool=False
 center_seat_key:bool=False
 both_dogs_closed_or_seated:bool=False
 bms_A_healthy:bool=False
 bms_B_healthy:bool=False
 power_qualified:bool=False
 precharge_completed:bool=False
 voltage_delta_in_window:bool=False
 measured_contact_temp_ok:bool=False
 system_enabled:bool=False
 both_power_fets_verified_healthy:bool=False


def selective_power_enable(s:InterconnectInputs):
 """Fail-closed *reference logic*. Hardware must be independently built/tested.

 A-side contact stays dead when parked and before precharge; no bare
 BAT+ across movable exposed mating pads. A bus gets connected only
 if all physical and electrical interlocks prove well defined.
 """
 one_dock = s.stow_seat ^ s.open_seat
 # The precharge path itself carries electrical energy: it is NOT allowed
 # through unknown, floating or unseated mating contacts.
 protected = bool(one_dock and s.independent_load_faces and s.center_seat_key
     and s.both_dogs_closed_or_seated and s.power_qualified and s.bms_A_healthy
     and s.bms_B_healthy and s.measured_contact_temp_ok and s.system_enabled
     and s.both_power_fets_verified_healthy)
 precharge_request = protected
 main_enable = bool(protected and s.precharge_completed and s.voltage_delta_in_window)
 return dict(port=('STOW' if s.stow_seat and not s.open_seat else
                   'OPEN' if s.open_seat and not s.stow_seat else None),
             precharge_request=precharge_request,main_bus_enable=main_enable,
             signal_lane_approved=False,
             usb_highspeed_lane_approved=False,
             real_circuit_built=False)


def sweep_logic():
 failures=[]
 checks=0; precharge_enabled_states=0;main_enabled_states=0
 fields=list(InterconnectInputs.__dataclass_fields__)
 # This predicate is an independently written specification -- do not
 # evaluate the production function against its own returned guard values.
 guard_fields=('independent_load_faces','center_seat_key','both_dogs_closed_or_seated',
    'bms_A_healthy','bms_B_healthy','power_qualified',
    'measured_contact_temp_ok','system_enabled','both_power_fets_verified_healthy')
 def independent_spec(s):
  valid=(bool(s.stow_seat)!=bool(s.open_seat) and
         all(getattr(s,k) for k in guard_fields))
  return valid, bool(valid and s.precharge_completed and s.voltage_delta_in_window)
 # Full 2**N exhaustive truth-table for **reference logic only**.
 for row in itertools.product((False,True),repeat=len(fields)):
  s=InterconnectInputs(**dict(zip(fields,row)))
  x=selective_power_enable(s);checks+=1
  precharge,main=independent_spec(s)
  precharge_enabled_states+=bool(x['precharge_request'])
  main_enabled_states+=bool(x['main_bus_enable'])
  if (x['precharge_request'],x['main_bus_enable']) != (precharge,main):
   failures.append(dict(inputs=asdict(s),predicted=(precharge,main),actual=x))
 # A deliberately unsafe implementation has no all-good seated-contact
 # control and MUST be rejected by the independent specification.
 mutant=InterconnectInputs(stow_seat=True,open_seat=False,
  independent_load_faces=True,center_seat_key=False,both_dogs_closed_or_seated=True,
  bms_A_healthy=True,bms_B_healthy=True,power_qualified=True,
  precharge_completed=True,voltage_delta_in_window=True,
  measured_contact_temp_ok=True,system_enabled=True,both_power_fets_verified_healthy=True)
 mutated_enable=bool(mutant.stow_seat and mutant.bms_A_healthy and mutant.system_enabled)
 guard_should_block=independent_spec(mutant)[1] is False
 return dict(logic_states_checked=checks,logic_false_energization_failures=len(failures),
             all_logic_guards_pass=(not failures),faults=failures[:5],
             active_precharge_states=precharge_enabled_states,
             active_main_states=main_enabled_states,
             mutation_bad_controller_rejected=mutated_enable and guard_should_block,
             hardware_PCB_BMS_FET_power_contact_fuse_and_usb_qualification=False)


def trial_current_envelope(P_W,Vmin=3.0,efficiency=0.9):
 """Sensitivity ONLY, not product load measured or contact selection."""
 return dict(trial_load_W=P_W,assumed_pack_bus_min_V=Vmin,
   assumed_DCDC_efficiency=efficiency,constant_power_current_A=round(P_W/(Vmin*efficiency),3),
   rating_is_sufficient_to_approve_connector=False)


def report(write=True):
 out=dict(revision='R22 electrical partition and fail-closed reference model only',
   sources=dict(te_signal=TE_2199001,power_vendor_RFI_only=[HARWIN_S1961,MILL_MAX_0985,MILL_MAX_0900]),
   architecture=ARCHITECTURE,logic=sweep_logic(),
   trial_power_current_sensitivity=[trial_current_envelope(p) for p in (3,5,8,12)],
   physical_blockers=[
      'Power connector approved in vertical/horizontal mating orientation and 300k full-assembly cycles MISSING; examine Mill-Max 0900 but its 3.48mm height cannot drop into 1.2mm TE pocket',
      'Dedicated power and return physical pinout, make/break ordering, creepage and blindmate protection MISSING',
      'Actual design-current envelope and load dump/short/welded contacts MISSING',
      'Board-level FET/protection/precharge and actual mated voltage/thermal transients MISSING',
      'Active-current derating, fretting corrosion, salt-dust-temperature-wear contact resistance MISSING',
      'USB-C physical location and electrical compliance in B MISSING',
      'Sensor and sideband TE 2199001-1 real STEP, SI/ESD and lifetime NOT QUALIFIED'],
   qualified_power=False,qualified_usb=False,qualified_signal=False,manufacture_go=False)
 if write:(ROOT/'verification'/'R22_electrical_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
 return out
if __name__=='__main__':print(json.dumps(report(),ensure_ascii=False,indent=2))
