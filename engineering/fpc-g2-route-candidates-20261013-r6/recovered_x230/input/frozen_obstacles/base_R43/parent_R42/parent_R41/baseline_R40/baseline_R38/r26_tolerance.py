"""R26 NEW OPEN-port hypothetical X/Y/Z perturbations (not approved GD&T).

The locked shutter arrests *a path* but not an already fully extended carrier.
216 entries = 2 sides x 2 widths x 27 offsets x (pawl and ear separate rows).
"""
import cadquery as cq
import json,itertools
from r25_capture import ROOT,P,a_key,intersection,to_global
from r26_open_mechanics import open_pawl,open_gate,open_carrier_ear

def run(write=True):
    rows=[]
    A=cq.importers.importBrep(str(ROOT/'cad'/'R25_A_R24_KEYS.brep')).val()
    for width in (.02,.05):
      for side in 'LR':
        park=open_pawl(side,False)
        locked_gate=open_gate(side,0.)
        actuated_gate=open_gate(side,.20)
        ear0=open_carrier_ear(side,0.)
        ear150=open_carrier_ear(side,.15)
        for dx,dy,dz in itertools.product((-width,0.,width),repeat=3):
          vec=cq.Vector(dx,dy,dz)
          moved_park=park.translate(vec)
          moved_ear0=ear0.translate(vec)
          moved_ear150=ear150.translate(vec)
          rows.append(dict(part='parked_pawl',width_mm=width,side=side,dx=dx,dy=dy,dz=dz,
             A_whole_shell_clash_at_dock_mm3=round(intersection(A,to_global(moved_park,'OPEN',P.travel,P.z_travel)),9),
             gate_initial_closed_clash_mm3=round(intersection(moved_park,locked_gate),9),
             parked_pawl_veto_on_attempt_gate_0p2_mm3=round(intersection(moved_park,actuated_gate),9)))
          rows.append(dict(part='lower_ear',width_mm=width,side=side,dx=dx,dy=dy,dz=dz,
             gate_closed_vs_retracted_ear_mm3=round(intersection(moved_ear0,locked_gate),9),
             gate_closed_vs_ext_0p15_mm3=round(intersection(moved_ear150,locked_gate),9)))
    groups=[]
    for width in (.02,.05):
      parks=[r for r in rows if r['width_mm']==width and r['part']=='parked_pawl']
      ears=[r for r in rows if r['width_mm']==width and r['part']=='lower_ear']
      groups.append(dict(hypothetical_xyz_offset_magnitude_mm=width,
         parked_pawl_cases=len(parks),ear_cases=len(ears),
         A_shell_collision_at_seat=sum(r['A_whole_shell_clash_at_dock_mm3']>1e-9 for r in parks),
         false_jam_gate_stays_closed=sum(r['gate_initial_closed_clash_mm3']>1e-9 for r in parks),
         parked_pawl_fails_to_block_open_attempt_0p2=sum(r['parked_pawl_veto_on_attempt_gate_0p2_mm3']<=1e-9 for r in parks),
         gate_jams_fully_retracted_carrier=sum(r['gate_closed_vs_retracted_ear_mm3']>1e-9 for r in ears),
         gate_fails_arrest_carrier_at_ext_0p15=sum(r['gate_closed_vs_ext_0p15_mm3']<=1e-9 for r in ears)))
    out=dict(revision='R26 bilateral OPEN-port partial rigid-body hypothetical +/-0.02/0.05 XYZ perturbation',
        rows=rows,groups=groups,real_OEM_GDT_and_material_limits_absent=True,
        individual_shutter_tolerance_unqualified=True,
        long_term_wear_thermal_stackups_unqualified=True,
        force_modulated_return_and_shear_unqualified=True,
        manufacturing_go=False)
    if write:(ROOT/'verification'/'R26_tolerance.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    return out
if __name__=='__main__':
 r=run();print(json.dumps(r['groups'],indent=2,ensure_ascii=False))
