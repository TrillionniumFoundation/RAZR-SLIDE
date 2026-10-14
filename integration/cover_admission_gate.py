"""Run actual, state-consistent cover-first assembly stages with finite fixture.
Failure stops each side; no absent part is silently added after a failed stage.
"""
from pathlib import Path
import argparse,hashlib,json,platform,time
from admission_native_inputs import load_parts,at
import cam_contact_native as n
from admission_cells import AssemblyState,translation_cells
from cover_admission_plan import fixture,stages
ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def checked_common(a,b):
    aa,bb=a.BoundingBox(),b.BoundingBox()
    for axis in 'xyz':
        if getattr(aa,axis+'max')<=getattr(bb,axis+'min') or getattr(bb,axis+'max')<=getattr(aa,axis+'min'):
            return {'volume_mm3':0.,'method':'strict_axis_bound_nonoverlap'}
    return {'volume_mm3':n.common(a,b),'method':'strict_complete_native_common'}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True,type=Path);ap.add_argument('--original-closed-locator',action='store_true');a=ap.parse_args();out=a.output.resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('new external directory required')
    out.mkdir(parents=True,exist_ok=False);start=time.monotonic();exports={};rows=[]
    source_files=list((ROOT/'integration').glob('*.py'))+list((ROOT/'engineering/passive-return-spring-recovery-20261013-r6').rglob('*.py'))
    source_hashes={str(p.relative_to(ROOT)):sha(p) for p in source_files}
    def export(role,shape):
        n.single(shape);p=out/(role+'.step');n.cq.exporters.export(shape,str(p));bb=shape.BoundingBox()
        exports[role]={'path':p.name,'sha256':sha(p),'volume_mm3':shape.Volume(),'bounds_mm':{k:getattr(bb,k) for k in ('xmin','xmax','ymin','ymax','zmin','zmax')}}
    for side in 'LR':
        parts,part_identity=load_parts(side,original_closed_locator=a.original_closed_locator);parts.update(fixture(side));plan=stages(side)
        for name,body in parts.items():export(side+'_'+name,body)
        state=AssemblyState({'JIG_BASE_SUPPORTS':(0,0,0)});records=[]
        for i,stage in enumerate(plan):
            fixed_names=state.fixed_names(stage)
            fixed={name:parts[name].translate(state.poses[name]) for name in fixed_names}
            initial=parts[stage.part].translate(stage.start);vector=tuple(b-a for a,b in zip(stage.start,stage.end))
            # The swept set is unchanged on reversing time. Construct every
            # cell from the pinned endpoint, rather than repeatedly rebuilding
            # translated wires at remote approach poses. Invalid topology is
            # still a failure; the rejected start-anchor run is retained.
            endpoint=at(parts[stage.part],stage.end)
            cell_vector=tuple(x-y for x,y in zip(stage.start,stage.end))
            cells,method=translation_cells(endpoint,cell_vector)
            method['construction_anchor']='stage_end';checks=[];positive=[]
            for cell_name,body in cells:
                export(f'{side}_STAGE_{i}_{cell_name}',body)
                for name,obstacle in fixed.items():
                    c=checked_common(body,obstacle);row={'cell':cell_name,'fixed':name,**c};checks.append(row)
                    if c['volume_mm3']>1e-7:positive.append(row)
            passed=not positive;witnesses=[]
            if not passed:
                for t in [0.,.25,.5,.75,.9,.99,.99325,.9975,1.]:
                    pose=tuple(x+t*v for x,v in zip(stage.start,vector));moving=parts[stage.part].translate(pose)
                    for name,obstacle in fixed.items():
                        c=checked_common(moving,obstacle)
                        if c['volume_mm3']>1e-7:
                            witnesses.append({'fraction':t,'offset_world_mm':pose,'fixed':name,**c})
                if witnesses:
                    w=witnesses[-1];moving=parts[stage.part].translate(w['offset_world_mm']);p=out/f'{side}_STAGE_{i}_ACTUAL_COLLISION.step';n.cq.exporters.export(n.cq.Compound.makeCompound([moving,fixed[w['fixed']]]),str(p))
                    w['native_witness_STEP']={'path':p.name,'sha256':sha(p),'solid_count':2}
            state.finish(stage,passed,fixed_names)
            records.append({'index':i,'stage':stage.name,'part':stage.part,'start_world_mm':stage.start,'end_world_mm':stage.end,
                'fixed_part_poses':{name:state.poses[name] for name in fixed_names},'cell_method':method,'checks':checks,
                'positive_cells':positive,'actual_pose_witnesses':witnesses,'passed':passed})
            print(side,stage.name,'PASS' if passed else 'BLOCKED','cells',len(cells),'fixed',len(fixed),'positive',len(positive),flush=True)
            (out/'progress.json').write_text(json.dumps({'completed_sides':rows,'current_side':side,'current_records':records,'manufacturing_go':False},indent=2)+'\n')
            if not passed:break
        rows.append({'side':side,'part_identity':part_identity,'records':records,'completed_stages':state.completed,'first_blocked_stage':state.blocked,
            'part_poses_actually_reached':state.poses,'downstream_not_executed':[s.name for s in plan[len(records):]],
            'full_initial_plan_passed':state.blocked is None})
    if source_hashes!={p:sha(ROOT/p) for p in source_hashes}:raise ValueError('source changed during execution')
    result={'host':platform.node(),'source_SHA256':source_hashes,'source_bytes_unchanged':True,'original_closed_locator':a.original_closed_locator,
        'rows':rows,'exports':exports,'fixture_parts_per_side':2,'fixture_is_native_finite_geometry':True,
        'fixture_holding_force_stability_material_and_fastening_qualified':False,
        'full_motion_cells_not_sample_only':True,'cover_locator_capture_boundary_changed':not a.original_closed_locator,
        'full_initial_plan_passed':all(r['full_initial_plan_passed'] for r in rows),
        'full_phone_or_all_downstream_assembly_qualified':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['full_initial_plan_passed']:raise SystemExit(1)
if __name__=='__main__':main()
