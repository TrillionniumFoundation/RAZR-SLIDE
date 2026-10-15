"""R24 independent stop fault enumeration; frequencies/strength NOT inferred."""
import itertools,json
from r24_mechanics import (ROOT,P,guard_overlap as outboard_overlap,
   solve_jaw_shift_by_A_contact,nominal_kinematic_table)
from r23_gate import guard_blocked as r23_blocked
from r22_mechanics import assembly_local,stop_effectively_locked
from r22_adversarial import STAGES,physically_seated_pose


def r24_blocked(ext=.8,shift_l=0.,shift_r=0.,lug_l=True,lug_r=True):
    overlap=outboard_overlap(ext,shift_l,shift_r)
    return (lug_l and overlap['L']>1e-8) or (lug_r and overlap['R']>1e-8)


def scan(write=True):
    totals=dict(states=0,unseated=0,
                legacy_R22_unblocked_and_R23_both_false_open=0,
                R24_both_fault_open_still_escapes=0,
                one_R24_false_open_other_intact_unseated_escapes=0,
                two_R24_outboard_arms_fractured_escape_against_old_all_open=0)
    old_cache={(l,r,c):stop_effectively_locked(assembly_local(False,l,r,c))
         for l,r,c in itertools.product((False,True),repeat=3)}
    # OCC geometric blockers depend only on faulted follower state, not on
    # legacy dog combinations; precompute to avoid 8192 repeated booleans.
    r23_cache={(l,r):r23_blocked(.8,l,r) for l,r in itertools.product((False,True),repeat=2)}
    r24_cache={(l,r):r24_blocked(.8,2. if l else 0.,2. if r else 0.) for l,r in itertools.product((False,True),repeat=2)}
    for port in ('STOW','OPEN'):
        for stage,s,q in STAGES:
            seated=physically_seated_pose(port,s,q)
            for old_dog_l,old_dog_r in itertools.product((False,True),repeat=2):
                for old_state,old_blocked in old_cache.items():
                    for r23_l,r23_r in itertools.product((False,True),repeat=2):
                        r23_stop=r23_cache[(r23_l,r23_r)]
                        for r24_l,r24_r in itertools.product((False,True),repeat=2):
                            r24_stop=r24_cache[(r24_l,r24_r)]
                            blocked=old_blocked or r23_stop or r24_stop
                            totals['states']+=1
                            if seated:continue
                            totals['unseated']+=1
                            if not old_blocked and r23_l and r23_r:
                                totals['legacy_R22_unblocked_and_R23_both_false_open']+=1
                                if r24_l and r24_r and not blocked:
                                    totals['R24_both_fault_open_still_escapes']+=1
                            if (not r24_l or not r24_r) and not blocked:
                                totals['one_R24_false_open_other_intact_unseated_escapes']+=1
    for break_l,break_r in itertools.product((False,True),repeat=2):
        if break_l and break_r and not r24_blocked(.8,0.,0.,False,False):
            totals['two_R24_outboard_arms_fractured_escape_against_old_all_open']+=1
    assert totals['states']==8192
    assert totals['unseated']==7168
    assert totals['R24_both_fault_open_still_escapes']==56
    assert totals['one_R24_false_open_other_intact_unseated_escapes']==0
    early=[]
    for row in nominal_kinematic_table():
        if row['both_outboard_jaws_clear'] and not row['physically_both_seated']:
            early.append(row)
    # Analysis carries the early-clear state even WITHOUT any R24 jaw fault.
    # It is dangerous if original three and the R23 two are all false-released.
    report=dict(revision='R24 R22+R23+new outboard stop Boolean faults + physical contact-derived early-release',
       inherited_states=totals,early_clear_unseated_count=len(early),
       early_release_examples=[dict(port=x['port'],s=x['s_mm'],q=x['q_mm'],
                      shifts=[x['ideal_A_contact_shift_L_mm'],x['ideal_A_contact_shift_R_mm']])
                 for x in early],
       current_R24_nominal_cam_fails_strict_seat_interlock=bool(early),
       all_five_stop_false_open_still_escapes_in_56_legacy_states=True,
       outboard_arms_are_both_coupled_to_a_shared_carrier_not_independent_drive=True,
       per_position_unmeasured_contact_overtravel_and_contact_normal_force=True,
       full_multi_axis_perturbed_collision_and_fatigue_unverified=True,
       manufacturing_go=False)
    if write:(ROOT/'verification'/'R24_fault_matrix.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    return report

if __name__=='__main__':
    t=scan()
    print(json.dumps({k:v for k,v in t.items() if k!='early_release_examples'},indent=2))
