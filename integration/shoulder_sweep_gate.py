"""Actual whole-translation gate for the nominal STOW pawl and all fixed parts.

Exports old/new roots, original pawls and full swept solids for independent
reverse-direction reconstruction. A successful geometric gate is not a phone,
force, toleranced-clearance or physical qualification.
"""
from pathlib import Path
import argparse, hashlib, json, platform, time
import shoulder_clearance as s
b=s.b


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def export_one(shape, path):
    b.participant(shape)
    b.cq.exporters.export(shape,str(path))
    return {'path':path.name,'sha256':sha(path),'certificate':b.participant(shape)}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    out=args.output.resolve()
    if out==s.ROOT or s.ROOT in out.parents:raise ValueError('new external output required')
    out.mkdir(parents=True,exist_ok=False)
    snapshot=json.loads((s.GROUP/'stable-snapshot.json').read_text())
    before={row['path']:sha(s.ROOT/row['path']) for row in snapshot['files']}
    if any(before[row['path']]!=row['sha256'] for row in snapshot['files']):raise ValueError('frozen spring input mismatch')
    start=time.monotonic();rows=[]
    for side in 'LR':
        original,_=s.parent.scene('STOW',side);fixed,audit=s.fixed_geometry(side)
        vector=b.identity.evec('STOW',side,1.1)
        swept,method=s.planar_translation_sweep(original['PAWL'],vector)
        old_common=b.strict_common(original[s.ROOT_NAME],swept)
        if old_common['checked_volume_mm3']<=b.EPS:raise ValueError('original negative control did not reproduce')
        checks={name:b.strict_common(shape,swept) for name,shape in fixed.items() if name!='PAWL'}
        parked=original['PAWL'].translate(vector)
        insertion,insert_method=s.planar_translation_sweep(parked,b.rvec('STOW',10.))
        old_insert_common=b.strict_common(original[s.ROOT_NAME],insertion)
        install_fixed={name:shape for name,shape in fixed.items() if name not in ('PAWL','KEY','OLD_COVER') and not name.startswith(('SPRING_','CAP_','SCREW_'))}
        install_checks={name:b.strict_common(shape,insertion) for name,shape in install_fixed.items()}

        # Pose containment cross-checks construction; they are not the sweep itself.
        containment=[]
        for index in range(23):
            pose=original['PAWL'].translate(b.identity.evec('STOW',side,1.1*index/22))
            residual=sum(s.volume_leaves(pose.cut(swept)))
            if residual>1e-7:raise ValueError('full sweep lost a sampled input solid')
            containment.append(residual)
        exports={role:export_one(shape,out/(side+'_'+role+'.step')) for role,shape in {
            'original_root':original[s.ROOT_NAME], 'candidate_root':fixed[s.ROOT_NAME],
            'original_pawl':original['PAWL'],'forward_sweep':swept,
            'parked_pawl':parked,'insertion_sweep':insertion}.items()}
        row={'side':side,'insertion_method':insert_method,'insertion_checks':install_checks,
             'original_insertion_common':old_insert_common,'insertion_positive_parts':[name for name,res in install_checks.items() if res['checked_volume_mm3']>b.EPS],
             'modification':audit,'sweep_method':method,'original_root_positive_common':old_common,
             'all_fixed_part_checks':checks,'positive_parts':[name for name,result in checks.items() if result['checked_volume_mm3']>b.EPS],
             'sampled_source_containment_residual_mm3':containment,'exports':exports}
        rows.append(row);(out/'progress.json').write_text(json.dumps({'rows':rows,'manufacturing_go':False},indent=2)+'\n')
        print(side,'fixed_parts',len(checks),'positive',row['positive_parts'],flush=True)
    after={name:sha(s.ROOT/name) for name in before}
    if before!=after:raise ValueError('historical source bytes changed')
    report={'host':platform.node(),'CadQuery':b.cq.__version__,'source_sha256':sha(__file__),
            'repair_source_sha256':sha(s.__file__),'parent_scene_sha256':sha(s.parent.__file__),
            'frozen_source_SHA256':before,'frozen_sources_unchanged':True,'rows':rows,
            'full_translation_length_mm':1.1,'fixed_part_pairs':sum(len(row['all_fixed_part_checks']) for row in rows),
            'installation_fixed_part_pairs':sum(len(row['insertion_checks']) for row in rows),
            'installation_positive_pairs':sum(len(row['insertion_positive_parts']) for row in rows),
            'positive_pairs':sum(len(row['positive_parts']) for row in rows),'sweep_is_sample_union':False,
            'nominal_stow_translation_geometry_clear':not any(row['positive_parts'] for row in rows),
            'nominal_parked_insertion_geometry_clear':not any(row['insertion_positive_parts'] for row in rows),
            'continuous_key_or_multi_axis_phone_motion_qualified':False,'mechanical_strength_qualified':False,
            'physical_qualification':False,'candidate_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    if report['positive_pairs'] or report['installation_positive_pairs']:raise ValueError('nominal translation sweep intersects fixed parts; evidence retained')
    print(json.dumps({k:report[k] for k in ['fixed_part_pairs','positive_pairs','nominal_stow_translation_geometry_clear','manufacturing_go']}))


if __name__=='__main__':main()
