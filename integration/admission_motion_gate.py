"""Prove declared STOW lower-branch nominal motion with complete finite enclosures.
No physical restoring force, friction, fatigue, fixture, or phone qualification.
"""
from pathlib import Path
import argparse,json,hashlib,time,platform,sys
import cover_admission as s
import cam_contact_native as n
from straight_envelope import envelope


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();out=a.output.resolve()
    if out==s.ROOT or s.ROOT in out.parents:raise ValueError('new external run directory required')
    out.mkdir(parents=True,exist_ok=False);start=time.monotonic();rows=[];exports={}
    own=[Path(__file__),Path(s.__file__),Path(n.__file__),Path(__file__).with_name('cam_contact_profile.py'),Path(__file__).with_name('straight_envelope.py'),Path(s.baseline.__file__)]
    before={str(p.relative_to(s.ROOT)):sha(p) for p in own}
    def export(role,body):
        n.single(body);p=out/(role+'.step');n.cq.exporters.export(body,str(p));bb=body.BoundingBox()
        exports[role]={'path':p.name,'sha256':sha(p),'volume_mm3':body.Volume(),'bounds_mm':{k:getattr(bb,k) for k in ('xmin','xmax','ymin','ymax','zmin','zmax')}}
    for side in 'LR':
        parts,raw=s.scene('STOW',side);original,new,relative,audit=s.fixed_design(side);audit=s.design(side)[4];v2=s.baseline.fixed_design(side)[1];key=parts['KEY'];profiles=[]
        park=parts['PAWL'].translate((-1.1 if side=='L' else 1.1,0,0))
        export(side+'_OLD_V2_ROOT',v2)
        for name,body in parts.items():export(side+'_'+name,body)
        export(side+'_PARKED_PAWL',park)
        fixed={name:body for name,body in parts.items() if name not in ('KEY','STOP_0','STOP_1','PAWL','SPRING_0_OD_TOL_ENVELOPE','SPRING_1_OD_TOL_ENVELOPE')}
        fixed['PARKED_PAWL']=park
        for i in range(2):
            profile,pin,rem,geometry=n.extract_profile(key,parts[f'STOP_{i}'],side)
            swept,method=n.pin_path_envelope(profile,side,*geometry['pin_e_extent_mm']);pin_check=n.common(swept,key)
            cages=n.remainder_cages(rem,profile,side);cage_checks=[n.common(cage,key) for cage,rc in cages]
            actual_stop_sweep=s.full_stop_envelopes(side)[f'STOP_{i}']
            old_collision=n.common(v2,actual_stop_sweep)
            if old_collision<=n.TOL:raise ValueError('point-fit V2 negative control not reproduced')
            fixed_checks={name:n.common(actual_stop_sweep,shape) for name,shape in fixed.items()}
            contacts=[]
            for q in [0.,.005,.025,.05,.075,.1,.15,.25,.3,.35,.45,.5,.55,.6,.63,.64,.7,1.,12.]:
                h,dh,branch=profile.evaluate(q);body=parts[f'STOP_{i}'].translate((0,0,h-profile.evaluate(0)[0]));mkey=key.translate((0,-q,0));common=n.common(body,mkey);distance=body.distance(mkey)
                if common>n.TOL or (branch!='lower_stop' and distance>n.TOL):raise ValueError('native contact cross-check differs')
                contacts.append({'q_mm':q,'height_mm':h,'slope':dh,'branch':branch,'native_common_mm3':common,'native_distance_mm':distance})
            export(side+f'_PIN_{i}_COMPLETE_PATH',swept);export(side+f'_STOP_{i}_COMPLETE_R',actual_stop_sweep)
            for j,(cage,rc) in enumerate(cages):export(side+f'_STOP_{i}_REST_CAGE_{j}',cage)
            profiles.append({'stop':i,'native_profile':geometry,'complete_pin_path':method,'complete_pin_KEY_common_mm3':pin_check,
                'nonpin_cages':[{'construction':rc,'whole_common_with_KEY_mm3':cage_checks[j]} for j,(cage,rc) in enumerate(cages)],
                'complete_STOP_fixed_pairs':fixed_checks,'old_V2_full_stroke_collision_mm3':old_collision,'sample_contact_crosscheck':contacts})
            print(side,i,'PIN',pin_check,'REST',cage_checks,'FIXED_POS',[(x,y) for x,y in fixed_checks.items() if y>n.TOL],flush=True)
        # q translates monotonically through the whole [0,12] range. Springs
        # stay laterally outside KEY; maximal OD cages bound nominal occupancy.
        key_sweep,key_method=envelope(key.translate((0,-12.,0)),(0,12.,0))
        key_fixed=dict(fixed)
        for i in range(2):
            eb,qb,rb=n.bounds(side,parts[f'SPRING_{i}_OD_TOL_ENVELOPE'])
            cage=n.single(n.box(side,*eb,*qb,rb[0]-1.16,rb[1]));name=f'SPRING_{i}_MAX_NOMINAL_OCCUPANCY';key_fixed[name]=cage;export(side+'_'+name,cage)
        key_checks={name:n.common(key_sweep,body) for name,body in key_fixed.items()};export(side+'_KEY_COMPLETE_Q',key_sweep)
        sync_common=n.common(parts['STOP_0'],parts['STOP_1'])
        p0=profiles[0]['native_profile']['profile'];p1=profiles[1]['native_profile']['profile']
        if any(abs(a-b)>1e-7 for a,b in zip(p0['breakpoints_q_mm'],p1['breakpoints_q_mm'])):raise ValueError('two STOP displacements not synchronous')
        rows.append({'side':side,'repair':audit,'contacts':profiles,'full_KEY_path':key_method,'full_KEY_fixed_pairs':key_checks,'synchronous_STOP_pair_common_mm3':sync_common,
                     'synchronous_pair_is_rigid_translation_of_native_pair':True})
        (out/'progress.json').write_text(json.dumps({'rows':rows,'manufacturing_go':False},indent=2)+'\n')
    after={p:sha(s.ROOT/p) for p in before}
    if before!=after:raise ValueError('sources changed during native experiment')
    values=[]
    for row in rows:
        values.extend(row['full_KEY_fixed_pairs'].values());values.append(row['synchronous_STOP_pair_common_mm3'])
        for c in row['contacts']:
            values.append(c['complete_pin_KEY_common_mm3']);values.extend(x['whole_common_with_KEY_mm3'] for x in c['nonpin_cages']);values.extend(c['complete_STOP_fixed_pairs'].values())
    report={'host':platform.node(),'source_SHA256':before,'source_bytes_unchanged':True,'rows':rows,'exports':exports,
            'complete_enclosure_pair_count':len(values),'positive_complete_enclosure_pairs':sum(x>n.TOL for x in values),
            'STOW_nominal_selected_lower_branch_geometrically_clear':not any(x>n.TOL for x in values),
            'full_pin_paths_and_conservative_remainder_cages_not_sample_only':True,
            'q_domain_mm':[0.,12.],'full_STOP_stroke_mm':1.16,'OPEN_coupled_contact_checked':False,
            'lower_restoring_force_assumed_not_verified':True,'engagement_velocity_slope_discontinuous':True,
            'dynamic_contact_friction_fatigue_tolerance_fixture_or_phone_qualification':False,
            'candidate_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('COMPLETE',len(values),'POSITIVE',report['positive_complete_enclosure_pairs'],flush=True)
    if not report['STOW_nominal_selected_lower_branch_geometrically_clear']:raise SystemExit(1)

if __name__=='__main__':main()
