"""R37 negative fault model. Original 36/64 unsafe modes remain intact.
A boltless lip nominally arrests the bridge even when R36 M0.8 screw is gone,
but a broken lip immediately recovers the legacy escape path. There is no
measured fatigue, elastic mounting or positive independent A-key locking.
"""
import json
from r25_capture import ROOT,intersection
from r37_parts import lip
from r35_parts import bored_cap

def run(write=True):
    old=json.loads((ROOT/'verification/R36_faults.json').read_text())
    rows=[]
    for side in 'LR':
        intact=lip(side);cap=bored_cap(side)
        arrested=intersection(intact,cap.translate((0,-.05,0)))
        for intact_hook in (False,True):
            for missing_r36_screw in (False,True):
                for missing_original_pin in (False,True):
                    overlap=arrested if intact_hook else 0.
                    rows.append(dict(side=side,lip_intact=intact_hook,
                        original_M08_screw_lost=missing_r36_screw,
                        original_R35_pin_lost=missing_original_pin,
                        cap_0p05_hard_stop_overlap_mm3=round(overlap,9),
                        cap_extraction_not_arrested=overlap<1e-8))
    old_unsafe=old['R35_original_joint_unsafe']
    original_el=old['electrical_single_bypass']
    out=dict(revision='R37 independent integral B-lip hard stop negative fault matrix',
       joint_r36_physical_fault_scenarios=len(rows),
       joint_r36_scenarios=rows,
       intact_lip_blocks_cap_with_unthreaded_M08_screw_absent=all(r['cap_0p05_hard_stop_overlap_mm3']>0
          for r in rows if r['lip_intact'] and r['original_M08_screw_lost']),
       single_integral_lip_fracture_exposes_that_side=all(r['cap_extraction_not_arrested'] for r in rows if not r['lip_intact']),
       no_qualified_lip_spring_or_snap_assembly=True,
       early_A_key_false_seating_not_addressed=True,
       previous_legacy_unsafe_mechanical_modes=old_unsafe,
       previous_legacy_mechanical_modes=old['R35_original_fault_states'],
       previous_single_point_electric_bypasses=original_el,
       OEM_power_USB_OLED_qualification_missing=True,
       physical_pullout_force_not_measured=True,
       manufacturing_go=False)
    if write:(ROOT/'verification/R37_faults.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    return out
if __name__=='__main__':run()
