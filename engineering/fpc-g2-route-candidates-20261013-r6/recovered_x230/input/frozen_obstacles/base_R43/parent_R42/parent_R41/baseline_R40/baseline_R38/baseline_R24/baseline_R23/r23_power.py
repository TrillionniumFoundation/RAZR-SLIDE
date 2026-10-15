"""R23 two-battery interconnect: independent isolation *fault analysis*, not a circuit.

No real cell, harness, PCB, MOSFET, fuse, power contact, ESD or system load.
Proves limits of control-command-only checking, not physical fail-safe hardware.
"""
from __future__ import annotations
import itertools, json
from pathlib import Path
from dataclasses import dataclass,asdict
ROOT=Path(__file__).resolve().parent

@dataclass(frozen=True)
class IsolatorFault:
    upstream_welded:bool=False
    main_pair_welded:bool=False
    precharge_welded:bool=False
    raw_bat_to_pad_bypass:bool=False


def physical_energy_at_exposed_A_pad(cmd_upstream=False,cmd_main=False,cmd_precharge=False,
                                     faults=IsolatorFault(),battery_present=True):
    """Boolean topology, NOT FET electrical simulation.
       precharge live still counts as exposed energized (resistor not zero).
       All 3 independent blocking paths modelled as entire switches stuck ON.
    """
    upstream=cmd_upstream or faults.upstream_welded
    main=cmd_main or faults.main_pair_welded
    pre=cmd_precharge or faults.precharge_welded
    return bool(battery_present and (faults.raw_bat_to_pad_bypass or (upstream and (main or pre))))


def commanded_bus(seated_load_bearing:bool, stationary_latched:bool,
                  pack_A_ok:bool,pack_B_ok:bool,connector_qualified:bool,
                  temp_ok:bool,voltage_delta_ok:bool,precharge_ended:bool,
                  motion_requested:bool):
    """Reference logic alone: if physical latches / contact separation UNKNOWN,
    no command is a real authorization to move the two halves.
    """
    guard=all((seated_load_bearing,stationary_latched,pack_A_ok,pack_B_ok,
               connector_qualified,temp_ok,not motion_requested))
    return {'upstream':guard,'precharge':guard and not precharge_ended,
            'main':guard and precharge_ended and voltage_delta_ok,
            'motion_allowed_BY_LOGIC_ONLY':motion_requested and not guard}


def analysis(write=True):
    faultrows=[]
    for welded_up,welded_main,welded_pre,bypass in itertools.product((False,True),repeat=4):
        fault=IsolatorFault(welded_up,welded_main,welded_pre,bypass)
        pad_live=physical_energy_at_exposed_A_pad(faults=fault)
        faultrows.append(dict(**asdict(fault),exposed_contact_energized_despite_off_commands=pad_live,
                              fault_count=sum(asdict(fault).values())))
    single_fault_unsafe=[x for x in faultrows if x['fault_count']==1 and x['exposed_contact_energized_despite_off_commands']]
    # Missing power board insulation is itself a dangerous direct bypass, so
    # our fault model cannot claim single fault security until real PCB tested.
    assert len(faultrows)==16
    assert len(single_fault_unsafe)==1 and single_fault_unsafe[0]['raw_bat_to_pad_bypass']
    combined=[x for x in faultrows if x['fault_count']==2 and x['exposed_contact_energized_despite_off_commands']]
    faults_without_bypass=[x for x in faultrows if not x['raw_bat_to_pad_bypass'] and x['exposed_contact_energized_despite_off_commands']]
    assert len(faults_without_bypass)==3  # upstream + main; upstream + pre; all 3
    # Flow gate must be OFF and actual pad disconnected before shutters let go.
    # Logic cannot prove this if welds or topology bypass exist.
    sample_interconnects=[]
    for w in (3,5,8,12):
        i=w/(3.0*.90)
        sample_interconnects.append(dict(trial_load_W=w,assumed_bus_min_V=3.0,
          assumed_conversion_efficiency=.90,estimated_current_A=round(i,4),
          TE_2199001_signal_rated_A=1.5,TE_NOT_AUTHORIZED_FOR_BATTERY=True))
    report=dict(revision='R23 electric isolation cut-set fault tree, not wiring or sample proof',
      architecture=dict(A=['larger_cell_goal','A_local_BMS','fuse','independent_upstream_bilateral_switch',
                       'independent_main_back_to_back_FET_stage','independent_limited_precharge_branch',
                       'dedicated_Plus_and_Return_qualified_touchsafe_contacts'],
                        B=['B_local_cell_BMS','system_rail','USB_Type_C_receptacle_and_PHY_on_B','USB_Dplus_Dminus_stay_on_B'],
                        cross_cabin_low_speed='UNQUALIFIED isolated sensor/status lane, never A raw BAT positive',
                        raw_battery_cells_directly_paralleled=False),
      modeled_weld_short_bypass_combinations=len(faultrows),
      unsafe_single_faults=single_fault_unsafe,
      dual_switch_faults_can_create_live_pad=[x for x in combined if not x['raw_bat_to_pad_bypass']],
      number_unsafe_cases_excluding_bypass=len(faults_without_bypass),
      all_cases=faultrows,
      trial_current_envelopes=sample_interconnects,
      exposed_contacts_dead_when_command_off_NOT_VERIFIED_BY_HW=True,
      actual_uncharged_B_cell_inmotion_required=True,
      prerelease_requirements=['Independent physical no-load voltage proof on both A power contacts',
            'Main and precharge branches jointly isolated before mechanical unseat',
            'Two independent A-side lock keys confirmed load-bearing by mechanical captive shoulders',
            'New R23 jaws + carrier fully parked measured physically',
            'Only then allow A/B disengagement; any stuck extended contact inhibits travel'],
      must_test=['Live A pad with upstream welded & precharge welded',
          'Live A pad with upstream welded & main pair welded',
          'Direct PCB short A raw battery -> pad (single point unsafe)',
          'Off state with A and B voltage unequal and removal under load',
          'BMS failures, ESD, short circuit, contact bounce, arc and fretting at both ports',
          'Power return conductor open or mated late',
          'USB Type-C B internal package fit and actual USB-IF compliance'],
      qualifies_signal=False,qualifies_usb=False,qualifies_power=False,
      manufacturing_go=False)
    if write:(ROOT/'verification'/'R23_power_faulttree.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report

if __name__=='__main__':
    r=analysis()
    print(json.dumps({k:v for k,v in r.items() if k in ('modeled_weld_short_bypass_combinations','unsafe_single_faults','number_unsafe_cases_excluding_bypass','dual_switch_faults_can_create_live_pad')},ensure_ascii=False,indent=2))
