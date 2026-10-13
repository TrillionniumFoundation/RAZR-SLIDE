"""R27 physical geometric witnesses + explicitly unsafe independent faults.

An interference is NOT equivalent to safely retracting an already extended
contact.  The improved shutter may simply jam.  Both forced-gate failures and
carrier-ear fractures still let a contact escape in the idealized model.
"""
from __future__ import annotations
import json,itertools
from r25_capture import ROOT,intersection
from r26_open_mechanics import open_carrier_ear,open_gate,open_pawl,OPEN_GATE_STROKE
from r27_mechanics import open_gate_captive,swept_first_contact

def run(write=True):
    rows=[]
    for side in 'LR':
        old=open_gate(side,0.)
        new=open_gate_captive(side,0.)
        sweeps=[]
        for i in range(41):
            extension=round(i*.02,4)
            ear=open_carrier_ear(side,extension)
            sweeps.append(dict(extension_mm=extension,
                R26_closed_overlap_mm3=round(intersection(old,ear),9),
                R27_closed_overlap_mm3=round(intersection(new,ear),9),
                R27_open_overlap_mm3=round(intersection(open_gate_captive(side,.9),ear),9)))
        rows.append(dict(side=side,
            gate_R26_single_body=old.isValid() and len(old.Solids())==1,
            gate_R27_single_body=new.isValid() and len(new.Solids())==1,
            old_end_point_bypass_at_ext_0p8=(intersection(old,open_carrier_ear(side,.8))<1e-9),
            R27_endpoint_captive_contact_mm3=round(intersection(new,open_carrier_ear(side,.8)),9),
            R27_closed_gate_retracted_clear=intersection(new,open_carrier_ear(side,0.))<1e-9,
            R27_manual_open_at_full_extension_clear=intersection(open_gate_captive(side,.9),open_carrier_ear(side,.8))<1e-9,
            R27_first_sampled_contact_mm=swept_first_contact(side),
            R27_park_pawl_still_vetoes_0p2=intersection(open_gate_captive(side,.2),open_pawl(side,False))>1e-5,
            R27_captured_pawl_allows_full_gate_stroke=all(intersection(open_gate_captive(side,t),open_pawl(side,True))<1e-9 for t in (0.,.2,.45,.9)),
            sweep=sweeps))
    # Reproduce inherited six-axis fault family. New blade shares each gate's
    # load path: a *broken* gate is still broken. Do not count endpoint fix as
    # closing common-cause safety counterexamples.
    faults=[]
    for l_open,r_open,l_ear_broken,r_ear_broken,l_false,r_false in itertools.product((False,True),repeat=6):
        l_barrier=(not l_open) and (not l_ear_broken)
        r_barrier=(not r_open) and (not r_ear_broken)
        faults.append(dict(L_gate_forced_open=l_open,R_gate_forced_open=r_open,
            L_ear_broken=l_ear_broken,R_ear_broken=r_ear_broken,
            L_pawl_false_capture=l_false,R_pawl_false_capture=r_false,
            model_dangerous_escape_if_all_inherited_stops_broken=not (l_barrier or r_barrier),
            open_gate_false_presence_may_command_unlock=(l_open and r_open and l_false and r_false)))
    escaped=sum(x['model_dangerous_escape_if_all_inherited_stops_broken'] for x in faults)
    out=dict(revision='R27 hard continuous carrier interceptor plus conservative fault audit',
        geometry=rows,joint_fault_cases=len(faults),joint_fault_escape_cases=escaped,
        joint_fault_rows=faults,
        R26_endpoint_miss_fixed_in_R27_nominal=True,
        pressed_extended_carrier_may_JAM_instead_of_force_RETRACT=True,
        early_R24_cam_release_still_possible=True,
        absent_A_false_pawl_capture_not_mechanically_excluded=True,
        common_cause_force_breakage_still_escapes=True,
        no_real_captive_springs_shaft_guide_or_safe_retraction_force=True,
        no_real_power_isolation_or_OLED_supplier_approval=True,
        manufacturing_go=False)
    if write:(ROOT/'verification'/'R27_faults.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    return out

if __name__=='__main__':
    r=run();print('R27 faults:',r['joint_fault_cases'],'modes',r['joint_fault_escape_cases'],'still escape',flush=True)
