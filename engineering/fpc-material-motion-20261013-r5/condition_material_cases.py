#!/usr/bin/env python3
"""Apply four real nominal layer cases to the fixed-station research field.

No actual neutral axis, copper strain, lifetime or finished thickness is filled.
The 1.2 mm study width and chosen director orientation are explicit conditions.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

EXPECTED='2b2ddb766b53eb1298a283bcf298d68c90a099a965bfabd24cb2fe8b33fc037b'
def main():
    p=argparse.ArgumentParser();p.add_argument('--history',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    source=Path(__file__).with_name('conditional_section_inputs.json');digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if digest!=EXPECTED:raise ValueError('nominal layer source changed')
    cases=json.loads(source.read_text())['sections'];history=np.load(a.history);k=history['curvatures'];defined=history['frame_defined']
    if defined.shape!=k.shape[:2] or np.any(np.isfinite(k[~defined])):raise ValueError('zero-radius material stations must remain undefined')
    rows=[]
    for case in cases:
        if case['neutral_axis_um'] is not None or case['copper_distance_um'] is not None or case['finished_thickness_max_um'] is not None or case['manufacturing_go'] is not False:raise ValueError('input scope unexpectedly promoted actual material')
        height=case['nominal_unprocessed_thickness_um']/1000;bound=case['conditional_max_copper_distance_upper_um']/1000
        variants=[]
        for angle,kw,kt in [(0,k[...,0],k[...,1]),(90,k[...,1],-k[...,0])]:
            section_index=.6*np.abs(kw)+height/2*np.abs(kt)
            copper_distance_bound=.6*np.abs(kw)+bound*np.abs(kt)
            where=np.unravel_index(np.nanargmax(section_index),section_index.shape)
            variants.append({'global_director_rotation_deg':angle,'full_width_hypothesis_mm':1.2,'maximum_centerline_section_fibre_distance_index':float(np.nanmax(section_index)),
              'maximum_conditional_uniform_layer_positive_modulus_copper_distance_index_upper':float(np.nanmax(copper_distance_bound)),
              'max_section_index_pose_slide_normal_mm':history['states'][where[0]].tolist(),'max_section_index_fixed_material_sigma_mm':float(history['sigma'][where[1]]),
              'real_trace_width_placement_and_lateral_neutral_axis':None,'true_3D_CAD_of_this_rotated_or_thinner_section_exists':False,'is_actual_copper_strain_or_fatigue':False})
        rows.append({'base_part':case['base_part'],'coverlay_part':case['coverlay_part'],'nominal_unprocessed_total_um':case['nominal_unprocessed_thickness_um'],
         'finished_thickness_max_um':None,'actual_neutral_axis_um':None,'actual_copper_strain':None,'actual_project_cycles_qualified':None,'conditional_geometric_cases':variants,'manufacturing_go':False})
    result={'frozen_nominal_section_source':'../fpc-layer-stackup-20261013-r5/conditional_sections.json','frozen_nominal_section_sha256':digest,'section_case_count':len(rows),'station_pose_count':int(np.prod(defined.shape)),
     'undefined_zero_radius_station_poses_retained':int(np.sum(~defined)),'zero_radius_joints_are_unbounded_not_finite_indices':True,'conditional_layer_order_and_positive_modulus_bounds_are_not_project_artwork_or_NA':True,
     'actual_coverlay_press_process_or_tolerance_not_inferred':True,'cases':rows,'manufacturing_go':False}
    a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({'conditional_nominal_cases':len(rows),'manufacturing_go':False}))

if __name__=='__main__':main()
