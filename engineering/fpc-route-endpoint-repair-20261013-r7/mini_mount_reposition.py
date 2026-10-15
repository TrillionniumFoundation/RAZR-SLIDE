#!/usr/bin/env python3
"""Two last bounded static mount placements; no new dynamic-grid scan."""
from pathlib import Path
import json,platform,sys,time
sys.dont_write_bytecode=True
from corner_bay_followup import mini_mount
from endpoint_relocation import ROOT,R6,POSES,sha,write,participant,pairs,failures,free,export,inside_budget
from actual_obstacle_and_jacobian import obstacle_factory
def run():
    start=time.monotonic();factory,_=obstacle_factory();original=mini_mount();rows=[]
    before={str(p.relative_to(R6)):sha(p) for p in sorted(R6.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    own_before={f:sha(ROOT/f) for f in ['mini_mount_reposition.py','corner_bay_followup.py','endpoint_relocation.py']}
    for name,delta in [('CENTER_X20_Y89P4',(-8.5,4.4,0.)),('CENTER_X20_Y88P0',(-8.5,3.,0.))]:
        mount={n:s.translate(delta) for n,s in original.items()};poses=[]
        for pose,s,q in POSES:
            ob=factory(s,q);pc=pairs(mount,ob)
            poses.append({'pose':pose,'pairs':pc,'positive_or_rejected':failures(pc),'sampled_obstacle_clear':free(pc),
              'all_parts_within_original_A_research_proxy_bbox':all(inside_budget(b,participant(ob['A_R38_CORE'])['bounds_mm']) for b in mount.values())})
        ex=export(mount,'RESEARCH_UNROUTED_MINI_MOUNT_'+name+'.step')
        rows.append({'case':name,'translation_from_rejected_mini_mount_xyz_mm':list(delta),'static_substrate_center_xyz_mm':[28.5+delta[0],85+delta[1],4.1],
          'conditional_moving_FPC_exit_xyz_mm':[24+delta[0],85+delta[1],5.35],'pose_rows':poses,'export':ex,
          'unrouted_substrates_do_not_resize_frozen_R2_PCBA':True,'same_moved_A_coordinate_as_three_pose_G2_experiment':False,
          'real_clamp_stiffener_pinout_and_full_PCB_supplied':False,'manufacturing_go':False})
        print(name,'clear',sum(r['sampled_obstacle_clear'] for r in poses), 'budget',all(r['all_parts_within_original_A_research_proxy_bbox'] for r in poses),flush=True)
    after={str(p.relative_to(R6)):sha(p) for p in sorted(R6.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};own_after={f:sha(ROOT/f) for f in own_before}
    if before!=after or own_before!=own_after:raise ValueError('input source bytes changed')
    write(ROOT/'mini_mount_reposition_receipt.json',{'host':platform.node(),'own_sources_before':own_before,'own_sources_after':own_after,'frozen_R6_sources_unchanged':True,
      'rows':rows,'static_mount_clear_candidates_count':sum(all(p['sampled_obstacle_clear'] for p in r['pose_rows']) for r in rows),
      'all_finished_equal_housing_cavities_are_proven_by_proxy_bbox':False,'large_A_battery_allocation_verified':False,
      'continuous_dynamic_FPC_path_or_fatigue_verified':False,'capture_or_retraction_safety_qualified':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start})
if __name__=='__main__':run()
