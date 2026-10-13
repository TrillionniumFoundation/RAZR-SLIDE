"""R25 fault injection / no release claim unless geometry and hardware are proven.

Explicitly retains R24 normal early-open counterexample and the unqualified
OPEN station.  Additional STOW gate is independent of old 5/2+2 releases;
its own two-side common false release still fails.  No fault rates inferred.
"""
from __future__ import annotations
import json,itertools
from r25_capture import ROOT,P,intersection,PORT_DATA,pawl,a_key
from r25_gate import study as gate_study
from r24_faults import scan as r24_scan
from r24_mechanics import solve_jaw_shift_by_A_contact,guard_overlap
from r23_gate import guard_blocked as r23_blocked
from r22_mechanics import stop_effectively_locked,assembly_local


def vulnerability_map():
 positions=(('STOW',1.59,0.),('OPEN',P.travel,6.61))
 out=[]
 for port,s,q in positions:
  slides={x:solve_jaw_shift_by_A_contact(port,x,s,q) for x in 'LR'}
  cam_clear=all(z<1e-8 for z in guard_overlap(.8,slides['L'],slides['R']).values())
  # Mechanism fault applies only to STOW, OPEN is purposely not ported.
  for stage2_l_open,stage2_r_open in itertools.product((False,True),repeat=2):
   fully_overridden=cam_clear and stage2_l_open and stage2_r_open
   for shear_l,shear_r in itertools.product((False,True),repeat=2):
    # An intact shutter stops own ear even when R24 front cam prematurely clears.
    stage2_blocks=(port=='STOW' and ((not stage2_l_open and not shear_l) or
                            (not stage2_r_open and not shear_r)))
    all_legacy_fault_release=True # deliberate inject old R22+R23 all-open
    escape=bool(cam_clear and not stage2_blocks and all_legacy_fault_release)
    out.append(dict(port=port,at_s_mm=s,at_q_mm=q,cam_clear=cam_clear,
       gateL_forced_open=stage2_l_open,gateR_forced_open=stage2_r_open,
       carrier_earL_fractured=shear_l,carrier_earR_fractured=shear_r,
       OLD_R22_R23_forced_all_false_open=all_legacy_fault_release,
       all_solid_STOW_stops_overridden_or_unbuilt_OPEN=escape))
 return out

def run(write=True):
 rb=r24_scan(write=False)
 g=gate_study(write=False)
 cases=vulnerability_map()
 st=[x for x in cases if x['port']=='STOW'];op=[x for x in cases if x['port']=='OPEN']
 # Important: no amount of Boolean old-latch enumeration certifies real forces.
 report=dict(revision='R25 STOW independent shutter fault scan / OPEN stage2 absent',
  inherited_R24_combined_states=rb['inherited_states']['states'],
  inherited_R24_old_both_fault_open_escape=rb['inherited_states']['R24_both_fault_open_still_escapes'],
  inherited_R24_normal_early_release=rb['current_R24_nominal_cam_fails_strict_seat_interlock'],
  injected_cases=cases,total_new_fault_samples=len(cases),
  STOW_when_both_stage2_closed_ears_intact_escapes=sum(x['all_solid_STOW_stops_overridden_or_unbuilt_OPEN'] for x in st if not x['gateL_forced_open'] and not x['gateR_forced_open'] and not x['carrier_earL_fractured'] and not x['carrier_earR_fractured']),
  STOW_both_stage2_false_open_remains_unsafe=any(x['all_solid_STOW_stops_overridden_or_unbuilt_OPEN'] for x in st if x['gateL_forced_open'] and x['gateR_forced_open']),
  OPEN_old_early_fault_remains_unsafe=any(x['all_solid_STOW_stops_overridden_or_unbuilt_OPEN'] for x in op),
  unsafe_if_pawl_drives_engaged_while_no_A=True,
  actuator_present_in_B_without_complete_mounting=False,
  detached_ear_or_friction_jam_not_a_failsafe=True,
  control_state_not_independent_power_isolation_proof=True,
  mechanical_qualification=False,electrical_qualification=False,manufacturing_go=False)
 if write:
  (ROOT/'verification'/'R25_faults.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 return report

if __name__=='__main__':
 r=run();print(json.dumps({k:v for k,v in r.items() if k!='injected_cases'},indent=2))
