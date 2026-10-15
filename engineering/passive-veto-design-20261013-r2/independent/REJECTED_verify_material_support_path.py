#!/usr/bin/env python3
"""Actual STEP rigid support-contact perturbations; no force or strength proof."""
import hashlib,json,platform,sys
from pathlib import Path
import cadquery as cq
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE))
from verify_exported_veto import identify_side, load_step, checked_common, world_e_delta

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    rows=[];inputs={}
    for port in ('STOW','OPEN'):
        path=HERE.parent/'cad'/f'{port}_FULL_KEYS_CAPTURED.step'
        inputs[str(path.relative_to(HERE.parent))]=sha(path)
        solids=load_step(path)
        for side in 'LR':
            p=identify_side(solids,port,side)
            lifted=p['stop']
            rvec=lambda d:(0,0,d) if port=='STOW' else (0,d,0)
            closed=lifted.translate(rvec(-1.2))
            lateral=[]
            for delta in (0.,.01,.02,.03):
                shifted=closed.translate(world_e_delta(port,side,delta))
                lateral.append({'rigid_stop_e_shift_mm':delta,
                    'actual_connected_root_common_mm3':checked_common(shifted,p['root'])})
            bottom=checked_common(closed.translate(rvec(-.03)),p['root'])
            upper={n:checked_common(lifted.translate(rvec(.03)),s) for n,s in p.items() if n not in ('stop','key','pawl')}
            rows.append({'port':port,'side':side,'actual_lateral_bearing_contacts':lateral,
                'lower_rigid_stop_vs_connected_root_mm3':bottom,
                'upper_rigid_stop_vs_unfastened_caps_and_root_mm3':upper,
                'material_continuity_to_its_own_root_is_CAD_only':True,
                'fastener_retention_and_physical_stiffness_N_per_mm':None,
                'load_or_shear_strength_N':None})
            if lateral[-1]['actual_connected_root_common_mm3']<=1e-7 or bottom<=1e-7 or max(upper.values())<=1e-7:
                raise ValueError('Actual geometric load-path support contact absent')
    report={'environment':{'host':platform.node(),'cadquery':cq.__version__},
        'source_sha256':sha(__file__),'input_step_sha256':inputs,
        'actual_STEP_support_contact_rows':rows,'physical_force_strength_or_qualifications':False,
        'unfastened_caps_do_not_supply_proven_restraint':True,'manufacturing_go':False}
    (HERE/'material-support-contact-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'actual_side_support_paths':len(rows),'manufacturing_go':False},indent=2))
if __name__=='__main__':main()
