"""Builder-free complete STEP reimport of STOW contact and material closure.
This uses the same CAD kernel and generic geometry routines, not a cross-kernel
or physical proof. Signed common/cut failures reject rather than become zero.
"""
from pathlib import Path
import argparse,json,hashlib,sys,platform,time
import cam_contact_native as n
from straight_envelope import envelope, whole_material
import material_partition_checks as material_partitions
import translation_regions

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
PARTS={'ROOT_INNER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS','KEY','PAWL','STOP_0','STOP_1','OLD_COVER','CAP_0','CAP_1'}
PARTS.update(f'SCREW_{i}_{j}' for i in range(2) for j in range(2))
PARTS.update(f'{name}_{i}' for name in ('SPRING_GUIDE','SPRING_CAP') for i in range(2))
PARTS.update(f'SPRING_{i}_OD_TOL_ENVELOPE' for i in range(2))
PARTS.update(f'SPRING_SCREW_{i}_M1x3_NOMINAL' for i in range(2))
PARTS.update(f'ROOT_JOIN_SCREW_{i}_M1x3_NOMINAL' for i in range(2))

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',required=True,type=Path);ap.add_argument('--receipt',required=True,type=Path);ap.add_argument('--expected-sha256',required=True);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args()
    source_paths=[Path(__file__),Path(n.__file__),Path(__file__).with_name('cam_contact_profile.py'),
                  Path(__file__).with_name('straight_envelope.py'),Path(material_partitions.__file__),Path(translation_regions.__file__)]
    source_before={str(path.resolve()):sha(path) for path in source_paths}
    if sha(a.receipt)!=a.expected_sha256:raise ValueError('receipt hash changed')
    p=a.receipt.resolve().parent;r=json.loads(a.receipt.read_text());shapes={};inputs={str(a.receipt):sha(a.receipt)};started=time.monotonic()
    expected={side+'_'+name for side in 'LR' for name in PARTS|{'OLD_V2_ROOT','PARKED_PAWL','KEY_COMPLETE_Q','SPRING_0_MAX_NOMINAL_OCCUPANCY','SPRING_1_MAX_NOMINAL_OCCUPANCY'}}
    for side in 'LR':
        for i in range(2):
            expected.add(side+f'_PIN_{i}_COMPLETE_PATH');expected.add(side+f'_STOP_{i}_COMPLETE_R')
            expected.update(side+f'_STOP_{i}_REST_CAGE_{j}' for j in range(3))
    if set(r['exports'])!=expected or len(expected)!=76:raise ValueError('complete native participant set changed')
    for role,item in r['exports'].items():
        f=p/item['path']
        if f.parent!=p or sha(f)!=item['sha256']:raise ValueError('native file identity differs')
        raw=n.cq.importers.importStep(str(f)).vals()
        if len(raw)!=1:raise ValueError('extra roots')
        shape=n.single(raw[0]);b=shape.BoundingBox()
        if abs(shape.Volume()-item['volume_mm3'])>1e-7 or any(abs(getattr(b,k)-v)>1e-7 for k,v in item['bounds_mm'].items()):raise ValueError('native certificate mismatch')
        shapes[role]=shape;inputs[str(f)]=sha(f)
    oldpath=a.repo/'engineering/passive-return-spring-recovery-20261013-r6/split-root-repair/cad/STOW_ROOT_SPLIT_ASSEMBLED.step'
    inputs[str(oldpath)]=sha(oldpath);oldroots=n.cq.importers.importStep(str(oldpath)).vals()
    if len(oldroots)!=1:raise ValueError('old source complete root count changed')
    original_leaves=whole_material(oldroots[0])[0]
    if len(original_leaves)!=46:raise ValueError('old complete STOW assembly missing material')
    matches=[];pairs=[];equivalence=[];witness=[];material=[];partition_inputs=[]
    def equal(x,y,label):
        xy=whole_material(x.cut(y),empty=True)[1];yx=whole_material(y.cut(x),empty=True)[1]
        if max(xy,yx)>1e-7:raise ValueError('native reconstructed envelope differs: '+label)
        equivalence.append({'label':label,'a_minus_b_mm3':xy,'b_minus_a_mm3':yx})
    def check(side,kind,part,x,y,expected_volume):
        value=n.common(x,y)
        if abs(value-expected_volume)>1e-7:raise ValueError('independent geometry differs from retained producer result')
        pairs.append({'side':side,'kind':kind,'part':part,'common_mm3':value,'positive_interference':value>1e-7})
        return value
    fixed=PARTS-{'KEY','STOP_0','STOP_1','PAWL','SPRING_0_OD_TOL_ENVELOPE','SPRING_1_OD_TOL_ENVELOPE'}|{'PARKED_PAWL'}
    if [row['side'] for row in r['rows']]!=['L','R']:raise ValueError('side coverage differs')
    for row in r['rows']:
        side=row['side'];get=lambda name:shapes[side+'_'+name];key=get('KEY');new=get('ROOT_OUTER_CONNECTED_ALL_FRAGMENTS');v2=get('OLD_V2_ROOT')
        # Locate the original v9 root independently in the complete source file.
        candidates=[]
        for i,sh in enumerate(original_leaves):
            b=sh.BoundingBox();nb=new.BoundingBox()
            if abs(sh.Volume()-row['repair']['old_root_volume_mm3'])<1e-7 and all(abs(getattr(b,k)-getattr(nb,k))<1e-7 for k in ('xmin','xmax','ymin','ymax','zmin','zmax')):candidates.append((i,sh))
        if len(candidates)!=1 or candidates[0][0] in matches:raise ValueError('ambiguous original material identity')
        idx,original=candidates[0];matches.append(idx)
        extra=v2.cut(new);ev=whole_material(extra,empty=True)[1]
        originally_removed=whole_material(extra.intersect(original),empty=True)[1]
        if originally_removed>1e-7 or abs(v2.Volume()-ev-new.Volume())>1e-7 or whole_material(new.cut(v2),empty=True)[1]>1e-7:raise ValueError('protected original material changed')
        material.append({'side':side,'additional_V2_sheet_removed_mm3':ev,'additional_original_v9_material_removed_mm3':originally_removed,'original_root_index':idx,'new_root_single_positive_solid':True})
        for c in row['contacts']:
            i=c['stop'];stop=get(f'STOP_{i}');profile,pin,rest,geo=n.extract_profile(key,stop,side)
            expected_geo=c['native_profile']
            if any(abs(x-y)>1e-7 for x,y in zip(profile.breakpoints,expected_geo['profile']['breakpoints_q_mm'])):raise ValueError('native profile changed')
            full,method=n.pin_path_envelope(profile,side,*geo['pin_e_extent_mm']);equal(full,get(f'PIN_{i}_COMPLETE_PATH'),side+f'_pin{i}')
            pin_common=check(side,'complete_PIN_KEY',str(i),full,key,c['complete_pin_KEY_common_mm3'])
            remainder_common=[]
            cages=n.remainder_cages(rest,profile,side)
            if len(cages)!=3:raise ValueError('complete STOP remainder decomposition changed')
            for j,(cage,desc) in enumerate(cages):
                equal(cage,get(f'STOP_{i}_REST_CAGE_{j}'),side+f'_cage{i}_{j}')
                remainder_common.append(check(side,'STOP_REMAINDER_KEY',f'{i}/{j}',cage,key,c['nonpin_cages'][j]['whole_common_with_KEY_mm3']))
            partition_inputs.append({'side':side,'stop':i,'pin_common_mm3':pin_common,'remainder_common_mm3':remainder_common})
            full_r,_=envelope(stop.translate((0,0,-1.16)),(0,0,1.16));equal(full_r,get(f'STOP_{i}_COMPLETE_R'),side+f'_r{i}')
            if set(c['complete_STOP_fixed_pairs'])!=fixed:raise ValueError('fixed obstacle coverage changed')
            for name in sorted(fixed):check(side,'complete_STOP_FIXED',f'{i}/{name}',full_r,get(name),c['complete_STOP_fixed_pairs'][name])
            old=n.common(full_r,v2)
            if old<=.0004 or abs(old-c['old_V2_full_stroke_collision_mm3'])>1e-7:raise ValueError('old V2 negative control disappeared')
            height=profile.evaluate(.55)[0];pose=stop.translate((0,0,height-profile.evaluate(0)[0]));w=n.common(pose,v2)
            if w<=1e-7:raise ValueError('actual unsampled-pose witness not reproduced')
            witness.append({'side':side,'stop':i,'q_mm':.55,'old_V2_actual_pose_common_mm3':w,'old_V2_full_stroke_common_mm3':old})
        fullq,_=envelope(key.translate((0,-12,0)),(0,12,0));equal(fullq,get('KEY_COMPLETE_Q'),side+'_q')
        keyfixed=fixed|{'SPRING_0_MAX_NOMINAL_OCCUPANCY','SPRING_1_MAX_NOMINAL_OCCUPANCY'}
        if set(row['full_KEY_fixed_pairs'])!=keyfixed:raise ValueError('KEY obstacle coverage changed')
        for name in sorted(keyfixed):check(side,'complete_KEY_FIXED',name,fullq,get(name),row['full_KEY_fixed_pairs'][name])
        check(side,'synchronous_STOP_pair','STOP0_STOP1',get('STOP_0'),get('STOP_1'),row['synchronous_STOP_pair_common_mm3'])
        print('VERIFIED',side,'total pairs',len(pairs),flush=True)
    if len(pairs)!=130 or len(witness)!=4:raise ValueError('native checks omitted')
    partition_checks=material_partitions.stop_key_partition_checks(partition_inputs,n.TOL)
    unresolved_partitions=[x for x in partition_checks if not x['whole_STOP_KEY_proved_clear']]
    if source_before!={path:sha(path) for path in source_before}:raise ValueError('verification sources changed during execution')
    if inputs!={p:sha(p) for p in inputs}:raise ValueError('source bytes changed during verification')
    if any(x.startswith(('stow_contact_slots','stow_continuous_slots','stow_motion_slots','stow_web_repair','split_root_cartridges','build_spring_cartridges')) for x in sys.modules):raise ValueError('design builder was imported')
    result={'host':platform.node(),'source_sha256':sha(__file__),'producer_sha256':a.expected_sha256,'input_SHA256':inputs,'input_bytes_unchanged':True,
        'verification_source_SHA256':source_before,'verification_source_bytes_unchanged':True,
        'whole_STOP_KEY_material_partition_checks':partition_checks,
        'unresolved_whole_STOP_KEY_material_partitions':unresolved_partitions,
        'complete_STOP_KEY_material_partitions_proved_clear':not unresolved_partitions,
        'complete_positive_STEP_files':76,'complete_original_assembly_leaves':46,'recomputed_complete_enclosure_pairs':130,'equivalence_checks':equivalence,
        'pairs':pairs,'material_checks':material,'retained_actual_pose_negative_controls':witness,
        'positive_complete_enclosure_pairs':[x for x in pairs if x['positive_interference']],
        'evidence_reproduced_consistently':True,'whole_fixed_assembly_motion_clear':not any(x['positive_interference'] for x in pairs) and not unresolved_partitions,
        'builder_imported':False,'same_CAD_kernel_and_generic_geometry_not_cross_engine':True,
        'STOW_pin_and_STOP_selected_lower_branch_clear':not any(x['positive_interference'] for x in pairs if x['kind']!='complete_KEY_FIXED') and not unresolved_partitions,
        'OPEN_continuous_motion_verified':False,
        'restoring_force_friction_fixture_tolerance_strength_or_phone_qualification':False,'candidate_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-started}
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('REPRODUCED',130,'complete enclosures; POSITIVE',len(result['positive_complete_enclosure_pairs']),flush=True)
    if not result['whole_fixed_assembly_motion_clear']:raise SystemExit(1)

if __name__=='__main__':main()
