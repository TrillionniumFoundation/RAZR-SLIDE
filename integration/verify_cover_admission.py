"""Builder-free native reimport and replay of the exact accepted/blocked prefix.
This reads every exported cell and reconstructs the finite cell cover from
native participant STEPs. Same CAD kernel/generic cells, not cross-engine.
"""
from pathlib import Path
import argparse,hashlib,json,tarfile,tempfile,sys,platform,time
import cam_contact_native as n
from admission_cells import AssemblyState,Stage,translation_cells
from verify_contact_motion import PARTS

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def material_equal(a,b):
    return max(n.whole_material(a.cut(b),empty=True)[1],n.whole_material(b.cut(a),empty=True)[1])<=1e-7

def independent_common(a,b):
    aa,bb=a.BoundingBox(),b.BoundingBox()
    if any(getattr(aa,ax+'max')<=getattr(bb,ax+'min') or getattr(bb,ax+'max')<=getattr(aa,ax+'min') for ax in 'xyz'):return 0.
    return n.common(a,b)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True);ap.add_argument('--sha256',required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();begin=time.monotonic()
    if sha(a.receipt)!=a.sha256:raise ValueError('producer bytes changed')
    r=json.loads(a.receipt.read_text());inputs={str(a.receipt):sha(a.receipt)};shapes={}
    for role,item in r['exports'].items():
        p=a.receipt.parent/item['path']
        if p.resolve().parent!=a.receipt.resolve().parent or sha(p)!=item['sha256']:raise ValueError('native identity/path changed')
        roots=n.cq.importers.importStep(str(p)).vals()
        if len(roots)!=1:raise ValueError('extra STEP roots')
        sh=n.single(roots[0]);bb=sh.BoundingBox()
        if abs(sh.Volume()-item['volume_mm3'])>1e-7 or any(abs(getattr(bb,k)-v)>1e-7 for k,v in item['bounds_mm'].items()):raise ValueError('STEP certificate differs')
        inputs[str(p)]=sha(p);shapes[role]=sh
    source=a.repo/'engineering/keycover-geometry-20261014';manifest=json.loads((source/'geometry-manifest.json').read_text());archive=source/'project-owned-geometry.tar.gz'
    if sha(archive)!=manifest['archive_sha256']:raise ValueError('prior validated geometry changed')
    entries={x['path']:x for x in manifest['files']};inputs[str(archive)]=sha(archive);compared=[];sides=[]
    with tempfile.TemporaryDirectory() as tmp,tarfile.open(archive,'r:gz') as tar:
        for side in 'LR':
            for name in sorted(PARTS):
                member='motion/'+side+'_'+name+'.step';content=tar.extractfile(member).read()
                if hashlib.sha256(content).hexdigest()!=entries[member]['sha256']:raise ValueError('prior component identity changed')
                p=Path(tmp)/(side+'_'+name+'.step');p.write_bytes(content);old=n.single(n.cq.importers.importStep(str(p)).val());new=shapes[side+'_'+name]
                expected=old
                if name=='OLD_COVER' and not r['original_closed_locator']:expected=old.cut(n.box(side,-3.16,-2.68,2.98,3.22,-7.25,-6.43)).clean()
                if not material_equal(expected,new):raise ValueError('unexpected changed component '+name)
                compared.append({'side':side,'part':name,'exact_expected_shape':True,'intentional_locator_window':name=='OLD_COVER' and not r['original_closed_locator']})
            outward=-20. if side=='L' else 20.;inward=-outward;park=-1.1 if side=='L' else 1.1
            plan=[Stage('COVER_ON_SUPPORTS','OLD_COVER',(0,0,20.),(0,0,0)),Stage('HOLD_DOWN','JIG_HOLD_DOWN',(0,0,20.),(0,0,0)),Stage('UNPARKED_PAWL_FROM_BELOW','PAWL',(0,0,-20.),(0,0,0)),Stage('PARK_PAWL','PAWL',(0,0,0),(park,0,0)),Stage('INNER_ROOT_SIDE_ENTRY','ROOT_INNER',(inward,0,0),(0,0,0)),Stage('STOP_0_SIDE_ENTRY','STOP_0',(outward,0,0),(0,0,0)),Stage('STOP_1_SIDE_ENTRY','STOP_1',(outward,0,0),(0,0,0)),Stage('OUTER_ROOT_CLOSE','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS',(outward,0,0),(0,0,0))]
            data=next(x for x in r['rows'] if x['side']==side);state=AssemblyState({'JIG_BASE_SUPPORTS':(0,0,0)});records=[]
            for i,producer in enumerate(data['records']):
                stage=plan[i]
                if producer['stage']!=stage.name or producer['part']!=stage.part or tuple(producer['start_world_mm'])!=stage.start or tuple(producer['end_world_mm'])!=stage.end:raise ValueError('declared plan changed')
                names=state.fixed_names(stage)
                if set(producer['fixed_part_poses'])!=set(names):raise ValueError('placed obstacle omitted')
                for name in names:
                    if tuple(producer['fixed_part_poses'][name])!=state.poses[name]:raise ValueError('fixed part teleported')
                moving=shapes[side+'_'+stage.part];end=moving if all(x==0 for x in stage.end) else moving.translate(stage.end);vec=tuple(x-y for x,y in zip(stage.start,stage.end));cells,method=translation_cells(end,vec)
                positive=[];pair_count=0
                for label,cell in cells:
                    for name in names:
                        v=independent_common(cell,shapes[side+'_'+name].translate(state.poses[name]));pair_count+=1
                        if v>1e-7:positive.append({'cell':label,'fixed':name,'volume_mm3':v})
                passed=not positive
                if passed!=producer['passed']:raise ValueError('independent prefix result differs')
                witnesses=[]
                for w in producer['actual_pose_witnesses']:
                    pose=tuple(x+w['fraction']*(y-x) for x,y in zip(stage.start,stage.end))
                    if any(abs(x-y)>1e-10 for x,y in zip(pose,w['offset_world_mm'])):raise ValueError('witness pose not on declared path')
                    actual=independent_common(moving.translate(pose),shapes[side+'_'+w['fixed']].translate(state.poses[w['fixed']]))
                    if actual<=1e-7 or abs(actual-w['volume_mm3'])>1e-7:raise ValueError('actual witness failed')
                    if 'native_witness_STEP' in w:
                        item=w['native_witness_STEP'];p=a.receipt.parent/item['path']
                        if p.resolve().parent!=a.receipt.resolve().parent or sha(p)!=item['sha256']:raise ValueError('witness STEP identity changed')
                        roots=n.cq.importers.importStep(str(p)).vals()
                        if len(roots)!=1:raise ValueError('extra witness roots')
                        leaves,_=n.whole_material(roots[0]);inputs[str(p)]=sha(p)
                        if len(leaves)!=2 or abs(n.common(*leaves)-actual)>1e-7:raise ValueError('witness full-payload differs')
                    witnesses.append({'fraction':w['fraction'],'fixed':w['fixed'],'common_mm3':actual})
                state.finish(stage,passed,names);records.append({'stage':stage.name,'passed':passed,'independent_cell_count':len(cells),'independent_pairs':pair_count,'positive':positive,'actual_witnesses':witnesses})
            if state.blocked is None and len(records)!=len(plan):raise ValueError('truncated prefix without recorded obstruction')
            if state.completed!=data['completed_stages'] or state.blocked!=data['first_blocked_stage']:raise ValueError('incorrect final state')
            sides.append({'side':side,'completed_stages':state.completed,'blocked_stage':state.blocked,'records':records,'all_downstream_not_executed':state.blocked is not None})
    if inputs!={p:sha(p) for p in inputs}:raise ValueError('inputs changed')
    forbidden=('cover_locator_slot','cover_admission_gate','cover_admission_plan','keycover_bypass','stow_contact_slots','stow_continuous_slots','split_root_cartridges')
    if any(x.startswith(forbidden) for x in sys.modules):raise ValueError('candidate or fixture generator imported')
    result={'host':platform.node(),'source_sha256':sha(__file__),'producer_sha256':a.sha256,'input_SHA256':inputs,'inputs_unchanged':True,'whole_positive_single_solid_STEPs':len(shapes),'component_comparisons':compared,'phone_parts_compared':46,'sides':sides,'evidence_reproduced_consistently':True,'builder_imported':False,'same_CAD_kernel_and_generic_cells':True,'full_initial_assembly_passed':all(s['blocked_stage'] is None for s in sides),'fixture_force_stability_or_capture_qualified':False,'candidate_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-begin}
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('REPRODUCED',[(s['side'],len(s['completed_stages']),s['blocked_stage']) for s in sides],flush=True)
    if not result['full_initial_assembly_passed']:raise SystemExit(1)
if __name__=='__main__':main()
