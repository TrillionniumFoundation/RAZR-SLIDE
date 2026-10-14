"""Full nominal rigid straight stages for a reordered, fixed STOW assembly.
No spring force, fixture/gripping, toleranced fit, or full-phone qualification.
"""
from pathlib import Path
import argparse,json,hashlib,time,platform
import stow_contact_slots as s
from straight_envelope import envelope, whole_material
b=s.b

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True,type=Path);args=ap.parse_args();out=args.output.resolve()
    if out==s.ROOT or s.ROOT in out.parents:raise ValueError('use external run directory')
    out.mkdir(parents=True,exist_ok=False);rows=[];exports={};static=[];start=time.monotonic()
    own=[Path(__file__),Path(s.__file__),Path(s.previous.__file__),Path(s.previous.prior.__file__),Path(s.parent.__file__),Path(__file__).with_name('straight_envelope.py')]
    before={str(p.relative_to(s.ROOT)):sha(p) for p in own}
    def export(n,shape):
        b.participant(shape);p=out/(n+'.step');b.cq.exporters.export(shape,str(p));exports[n]={'path':p.name,'sha256':sha(p),'certificate':b.participant(shape)}
    for side in 'LR':
        parts,source=s.scene('STOW',side);reference,candidate,relative,construction=s.fixed_design(side)
        park=parts['PAWL'].translate(b.identity.evec('STOW',side,1.1));stages=[]
        sweep,method=s.previous.planar_translation_sweep(park,b.rvec('STOW',10.))
        checks={'ROOT_INNER':b.strict_common(sweep,parts['ROOT_INNER'])}
        stages.append({'stage':'1_PAWL_BEFORE_STOPS','method':method,'checks':checks})
        old={n:b.strict_common(sweep,parts[n]) for n in ('STOP_0','STOP_1')}
        if any(x['checked_volume_mm3']<=b.EPS for x in old.values()):raise ValueError('old insertion negative control missing')
        export(side+'_PAWL_INSERTION',sweep);export(side+'_PARKED_PAWL',park)
        for i in range(2):
            swept,method=envelope(parts[f'STOP_{i}'],b.identity.evec('STOW',side,10.))
            fixed={'ROOT_INNER':parts['ROOT_INNER'],'PARKED_PAWL':park}
            if i:fixed['STOP_0']=parts['STOP_0']
            checks={n:b.strict_common(swept,p) for n,p in fixed.items()}
            stages.append({'stage':f'{2+i}_STOP_{i}_AFTER_PAWL','method':method,'checks':checks})
            export(side+f'_STOP_{i}_SWEEP',swept)
        stages.append({'stage':'4_OUTER_ROOT_LAST','relative_displacement_mm':list(b.identity.evec('STOW',side,-10.)),
                       'checks':{n:b.strict_common(candidate,v) for n,v in relative.items()},
                       'methods':construction['full_relative_slot_methods']})
        returned,method=s.previous.planar_translation_sweep(parts['PAWL'],b.identity.evec('STOW',side,1.1))
        stages.append({'stage':'5_FINAL_PAWL_RETURN','method':method,'checks':{n:b.strict_common(returned,p) for n,p in parts.items() if n!='PAWL'}})
        export(side+'_PAWL_RETURN',returned)
        for n,p in parts.items():export(side+'_'+n,p)
        static_pairs=s.pairs(parts);static.extend([{'side':side,**r} for r in static_pairs])
        for n,v in relative.items():export(side+'_RELATIVE_'+n,v)
        rows.append({'side':side,'construction':construction,'stages':stages,'old_order_insertion_negative':old,
                     'all_original_non_root_parts_unchanged':True})
        positive=[(r['stage'],n,c['checked_volume_mm3']) for r in stages for n,c in r['checks'].items() if c['checked_volume_mm3']>b.EPS]
        print(side,'NEW_STAGES_POSITIVE',positive,'STATIC_POSITIVE',sum(r['checked_common_mm3']>b.EPS for r in static_pairs),flush=True)
        (out/'progress.json').write_text(json.dumps({'rows':rows,'manufacturing_go':False},indent=2))
    after={p:sha(s.ROOT/p) for p in before};assert before==after
    count=sum(len(stage['checks']) for row in rows for stage in row['stages'])
    pos=[{'side':row['side'],'stage':stage['stage'],'part':n,'volume_mm3':c['checked_volume_mm3']} for row in rows for stage in row['stages'] for n,c in stage['checks'].items() if c['checked_volume_mm3']>b.EPS]
    result={'host':platform.node(),'source_SHA256':before,'source_bytes_unchanged':True,'rows':rows,'exports':exports,'static_checks':static,
            'stage_common_pairs':count,'positive_stage_pairs':pos,'positive_static_pairs':[r for r in static if r['checked_common_mm3']>b.EPS],
            'new_order_nominal_geometry_clear':not pos and not any(r['checked_common_mm3']>b.EPS for r in static),
            'old_order_negative_pairs':4,'reordered_only_initial_subassembly':True,'no_parts_or_fixtures_physically_built':True,
            'real_fixture_access_force_capture_and_fatigue_qualified':False,'continuous_key_stop_coupled_motion_qualified':False,
            'candidate_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print('RESULT',count,'positive',len(pos),flush=True)
    if not result['new_order_nominal_geometry_clear']:raise SystemExit(1)
if __name__=='__main__':main()
