"""R30 real OCC fault witnesses; passing these tests means dangerous cases
are truthfully detected, NOT that they were eliminated.  No real electrical contact.
"""
from __future__ import annotations
import json,hashlib
from r25_capture import ROOT,intersection
from r30_mechanics import gate,carrier,extension_at,web_budget

def run(write=True):
 nominal=[];late=[];stuck=[]
 for side in 'LR':
  for i in range(19):
   t=round(.9*i/18,6);e=extension_at(t)
   g=gate(side,t);c=carrier(side,e)
   nominal.append(dict(side=side,gate_mm=t,extension_mm=round(e,6),
       gate_valid=g.isValid() and len(g.Solids())==1,
       carrier_valid=c.isValid() and len(c.Solids())==1,
       clash_mm3=round(intersection(g,c),10)))
  closed=gate(side,0.)
  for e in (0.,.02,.05,.06,.07,.075,.08,.09,.15,.4,.8):
   late.append(dict(side=side,extension_mm=e,
         shutter_closed_clash_mm3=round(intersection(closed,carrier(side,e)),10)))
  for t in (0.,.225,.45,.675,.9):
   stuck.append(dict(side=side,shutter_mm=t,carrier_stuck_0p8=True,
      collision_mm3=round(intersection(gate(side,t),carrier(side,.8)),10)))
  print('R30 FAULTS',side,flush=True)
 inherited=json.loads((ROOT/'verification'/'R29_faults.json').read_text())
 prior_path=ROOT/'verification'/'R29_faults.json'
 out=dict(revision='R30 rebased guide with inherited R29 mechanical and common-cause faults',
  normal_nominal_positions=len(nominal),normal_poses_all_collision_free=all(z['clash_mm3']<1e-8 and z['gate_valid'] and z['carrier_valid'] for z in nominal),
  normal_rows=nominal,closed_gate_lost_motion=late,
  stuck_carrier_rows=stuck,
  closed_gate_witness_at_e0p07_mm3=[x['shutter_closed_clash_mm3'] for x in late if x['extension_mm']==.07],
  inherited_R29_fault_sha256=hashlib.sha256(prior_path.read_bytes()).hexdigest(),
  inherited_original_fault_escape_counterexamples=inherited['inherited_original_fault_escape_counterexamples'],
  inherited_joint_fault_modes=inherited.get('inherited_joint_fault_modes'),
  no_A_key_false_capture_still_possible=True,
  guide_boss_is_not_a_power_isolation_device=True,
  pin_break_or_stuck_carrier_has_no_force_limited_recovery=True,
  physical_anti_false_capture_key_spring_default_not_built=True,
  vendor_contact_electrical_mate_stroke_unknown=True,
  manufacturing_go=False)
 if write:(ROOT/'verification'/'R30_faults.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 return out
if __name__=='__main__':
 r=run();print('R30 common fault escape',r['inherited_original_fault_escape_counterexamples'])
