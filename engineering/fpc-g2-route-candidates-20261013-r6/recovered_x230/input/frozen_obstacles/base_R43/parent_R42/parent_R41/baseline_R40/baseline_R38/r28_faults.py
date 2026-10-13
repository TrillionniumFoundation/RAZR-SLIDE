"""R28 independent OCC positive-pullback research witness + fault counterexamples.

A collision when the carrier jams is a FAILURE, not evidence that an intact
operator can safely retract it. No real springs, pin shear capacity, contact
conductivity, live voltage, or coupled motor were measured.
"""
from __future__ import annotations
import json,itertools,math
from r25_capture import ROOT,intersection
from r27_mechanics import open_gate_captive
from r26_open_mechanics import open_carrier_ear
from r28_retraction import (pullback_gate,carrier_with_pin,theoretical_extension,
                            OPEN_GATE_STROKE,CARRIER_TRAVEL,CAM_DWELL_MM)

def run(write=True):
 trajectories=[]
 for side in 'LR':
  points=[]
  for i in range(19):
   gate_t=round(OPEN_GATE_STROKE*i/18,6)
   ext=theoretical_extension(gate_t)
   sh=pullback_gate(side,gate_t);ear=carrier_with_pin(side,ext)
   points.append(dict(gate_stroke_mm=gate_t,ideal_carrier_extension_mm=round(ext,8),
      gate_pin_carrier_interference_mm3=round(intersection(sh,ear),9),
      physically_one_piece_gate=sh.isValid() and len(sh.Solids())==1,
      physically_one_piece_carrier_and_pin=ear.isValid() and len(ear.Solids())==1))
  # A held/blocked carrier cannot follow the cam: record the actual OCC jam.
  stuck=[]
  for t in (.9,.81,.72,.63,.54,.45,.36,.27,.18,.09,0.):
   stuck.append(dict(gate_stroke_mm=t,carrier_extension_stuck_mm=.8,
        OCC_jam_mm3=round(intersection(pullback_gate(side,t),carrier_with_pin(side,.8)),9)))
  # Inherited static R27 veto still stops one carrier extension at final gate.
  stop0=[dict(ext_mm=e,full_gate_closed_contact_mm3=round(intersection(pullback_gate(side,0.),carrier_with_pin(side,e)),9))
         for e in (0.,.08,.15,.4,.8)]
  trajectories.append(dict(side=side,nominal_dwell_and_pullback=points,
       held_carrier_fault_scan=stuck,closed_gate_veto=stop0,
       old_R27_preextended_0p8_still_blocked=intersection(open_gate_captive(side,0.),open_carrier_ear(side,.8))>1e-6))
 # Retain exactly comparable 64 inherited failure states. The extra pin
 # failures only affect ability to pull back, NOT magically repair a broken
 # gate or contact ear. Never report model escapes as real-world rates.
 original=[]
 for gates in itertools.product((False,True),repeat=6):
  lg,rg,le,re,lf,rf=gates
  left_stop=(not lg) and (not le);right_stop=(not rg) and (not re)
  original.append(dict(L_gate_broken=lg,R_gate_broken=rg,L_ear_broken=le,R_ear_broken=re,
      L_false_pawl_capture=lf,R_false_pawl_capture=rf,
      contact_exposure_escape_if_BOTH_mechanical_ear_gate_paths_lost=not(left_stop or right_stop)))
 extensions=[]
 for (lp,rp,lg,rg,le,re,lf,rf) in itertools.product((False,True),repeat=8):
  # New pin shear modes can leave a preextended live contact; stage2 gate
  # may jam on contact and cannot be assumed automatically returned.
  retraction_missing=lp or rp
  barrier_escape=((lg or le) and (rg or re))
  extensions.append(dict(L_pullback_pin_sheared=lp,R_pullback_pin_sheared=rp,
      L_gate_broken=lg,R_gate_broken=rg,L_carrier_ear_broken=le,R_carrier_ear_broken=re,
      L_false_capture=lf,R_false_capture=rf,
      demanded_retraction_unverified=retraction_missing,
      hard_intercept_missing_both_sides=barrier_escape,
      unseated_false_captures_likely_bypass_command=(lf and rf),
      physical_exposure_not_proven_safe=barrier_escape or retraction_missing or (lf and rf)))
 out=dict(revision='R28 L/R carrier pin inside physical moving gate cam slot with two-stage pullback dwell',
    real_Occ_shutter_and_pin_trajectory=trajectories,
    trajectory_samples=sum(len(r['nominal_dwell_and_pullback']) for r in trajectories),
    original_fault_family_cases=len(original),
    original_fault_escape_counterexamples=sum(r['contact_exposure_escape_if_BOTH_mechanical_ear_gate_paths_lost'] for r in original),
    original_fault_family=original,
    R28_extended_fault_family_cases=len(extensions),
    R28_extended_hazard_heuristic_cases=sum(r['physical_exposure_not_proven_safe'] for r in extensions),
    R28_extended_fault_family=extensions,
    positive_retraction_has_real_mechanical_guide_slot_but_no_physical_force_test=True,
    pin_is_not_axially_captive_no_backing_clips_or_screws=True,
    stuck_carrier_causes_JAM_not_demonstrated_safe_retraction=True,
    absent_A_pawl_false_capture_STILL_undefeated=True,
    old_R24_early_CAM_risk_STILL_undefeated=True,
    common_cause_double_gate_double_ear_failures_STILL_unsafe=True,
    battery_contact_power_hazard_STILL_unqualified=True,
    OLED_supplier_permission_STILL_unqualified=True,
    manufacturing_go=False)
 if write:(ROOT/'verification'/'R28_faults.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 return out
if __name__=='__main__':
 r=run();print('R28 CAM',r['trajectory_samples'],'original escapes',r['original_fault_escape_counterexamples'],'extended ambiguous',r['R28_extended_hazard_heuristic_cases'])
