"""R31 directed adversarial physical proxy, including remaining common faults.
A passed test may mean a dangerous failure was correctly detected.
"""
from __future__ import annotations
import json
from r25_capture import ROOT,intersection
from r30_mechanics import gate,carrier
from r31_presence import (interposer,follower_down,pawl_position,
                           PAWL_LATERAL_STROKE,pawl_transit_block)

def run(write=True):
    old=json.loads((ROOT/'verification'/'R30_faults.json').read_text())
    rows=[]
    for side in 'LR':
        for q in (7.8,8.,8.1,8.15,8.18,8.19,8.2):
            d=follower_down(q)
            path=pawl_transit_block(side,d)
            rows.append({'side':side,'q_mm':q,'ideal_down_mm':round(d,6),
                         'pawl_midstroke_blocking_mm3':[float(x) for x in path],
                         'path_is_blocked':any(x>1e-8 for x in path)})
    # For absent A, each independently defaulted interposer cuts off the pawl
    # X travel even if all R22/R23/R26 legacy mechanisms are forced released.
    for_side={s:all(x>1e-8 for x in pawl_transit_block(s,0.)) for s in 'LR'}
    # Explicit state cross product: 64 inherited old combined fault choices,
    # crossed with 4 new interposer stuck-down choices, A physically absent.
    # The count 36 is inherited counterexamples, NOT 36 measured executions.
    inherited_old_fault_space=64
    inherited_old_escapes=old['inherited_original_fault_escape_counterexamples']
    model=[]
    for brokenL,brokenR in ((False,False),(True,False),(False,True),(True,True)):
        any_good=(not brokenL and for_side['L']) or (not brokenR and for_side['R'])
        model.append({'left_plunger_stuck_released':brokenL,'right_plunger_stuck_released':brokenR,
                      'old_fault_combinations':inherited_old_fault_space,
                      'no_A_escaping_assuming_new_spring_default_and_hard_guides':0 if any_good else inherited_old_escapes,
                      'new_barrier_mechanically_available':any_good})
    # The old 0.07 mm unblocked carrier motion & absent force-limited retraction
    # remain independent from anti-false-capture gate geometry.
    blocked_carrier=[round(intersection(gate(s,0),carrier(s,e)),10)
                     for s in 'LR' for e in (0.,.07,.08,.8)]
    out={'revision':'R31 A-shelf actuated B no-A occupancy; research bounded fault injection',
         'q_samples':rows,'no_A_default_each_pawl_path_blocked':for_side,
         'old_R30_original_64_fault_modes':inherited_old_fault_space,
         'old_R30_original_36_escapes':inherited_old_escapes,
         'cross_product_old_plus_two_independent_interposer_states':model,
         'new_cross_product_escapes_sum':sum(x['no_A_escaping_assuming_new_spring_default_and_hard_guides'] for x in model),
         'shared_spring_support_corrosion_and_debris_can_defeat_both':True,
         'no_A_blocking_requires_unbuilt_positive_return_and_captive_guides':True,
         'STOW_endpoint_false_capture_still_unremedied':True,
         'R30_closed_shutter_contact_carrier_interference_at_ext_0p07_mm3':blocked_carrier[1:2]+blocked_carrier[5:6],
         'physical_electrical_contact_onset_unknown':True,
         'force_limited_stuck_carrier_recovery_unverified':True,
         'unqualified_spring_fracture_shear_wear_load_and_assembly':True,
         'manufacturing_go':False}
    if write:(ROOT/'verification'/'R31_faults.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    return out
if __name__=='__main__':
 r=run();print('R31 FAULTS',r['old_R30_original_36_escapes'],r['new_cross_product_escapes_sum'],flush=True)
