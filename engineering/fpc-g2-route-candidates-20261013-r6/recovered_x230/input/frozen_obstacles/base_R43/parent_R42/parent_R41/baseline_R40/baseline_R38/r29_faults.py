"""Mechanical attack witnesses for R29; all qualified states are *research* only.

Geometric overlap is evidence of an obstructed path, NOT evidence that the
spring can recover an already deployed conductive carrier safely under load.
"""
from __future__ import annotations
import json,hashlib
from r25_capture import ROOT,intersection
from r29_mechanics import pullback_gate,carrier_with_pin,theoretical_extension
from r26_open_mechanics import open_carrier_ear

STUCK_STATES=(.9,.675,.45,.225,0.)
def run(write=True):
 rows=[];stuck=[];at_closed=[]
 for side in 'LR':
  for i in range(19):
   t=round(.9*i/18,6); e=theoretical_extension(t)
   gate=pullback_gate(side,t);ear=carrier_with_pin(side,e)
   rows.append(dict(side=side,shutter_mm=t,prescribed_extension_mm=round(e,6),
      gate_one_valid=gate.isValid() and len(gate.Solids())==1,
      ear_one_valid=ear.isValid() and len(ear.Solids())==1,
      nominal_jam_mm3=round(intersection(gate,ear),9)))
  for t in STUCK_STATES:
   stuck.append(dict(side=side,gate_stroke_mm=t,carrier_stuck_at_0p8mm=True,
      interference_mm3=round(intersection(pullback_gate(side,t),carrier_with_pin(side,.8)),9)))
  for e in (0.,.03,.05,.07,.08,.095,.15,.8):
   at_closed.append(dict(side=side,extension_mm=e,
      closed_gate_clash_mm3=round(intersection(pullback_gate(side,0.),carrier_with_pin(side,e)),9)))
  print('R29 FMEA',side,flush=True)
 orig=(ROOT/'verification'/'R28_faults.json').read_bytes()
 orig_j=json.loads(orig)
 out=dict(revision='R29 19 prescribed poses/side and loaded-carrier static clash, not a force proof',
  rows=rows,prescribed_pose_count=len(rows),
  all_prescribed_nominal_geometries_valid=all(x['gate_one_valid'] and x['ear_one_valid'] and x['nominal_jam_mm3']<1e-8 for x in rows),
  stuck=stuck,closed_gate_lost_motion=at_closed,
  old_R28_faults_sha256=hashlib.sha256(orig).hexdigest(),
  inherited_original_fault_escape_counterexamples=orig_j['original_fault_escape_counterexamples'],
  inherited_joint_fault_modes=orig_j.get('joint_fault_modes'),
  dual_gate_common_faults_not_remedied=True,prevent_false_capture_when_no_A=False,
  powered_contact_jam_force_safe=False,
  bearing_pin_shear_spring_retention_and_brake_unverified=True,
  manufacturing_go=False)
 if write:(ROOT/'verification'/'R29_faults.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 return out
if __name__=='__main__':
 r=run();print('R29 NOMINAL',r['all_prescribed_nominal_geometries_valid'],'unfixed common escape',r['inherited_original_fault_escape_counterexamples'])
