#!/usr/bin/env python3
"""Recompute changed R4 cap/head mounting pairs after a real withdrawal fail.

Same 620 positions; controlled single geometry parameter delta, typed immutable
validated solid inputs. All new pairs are checked; no R3 qualification replay.
"""
from __future__ import annotations
import hashlib,importlib.util,itertools,json,platform,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
import build_fastened_caps as final
spec=importlib.util.spec_from_file_location('r4_immutable_guard',HERE/'independent/strict_intersections.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
CheckedBody,Checker=guard.CheckedBody,guard.Checker
EPS=1e-7
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require_controlled_source_delta():
    source=(HERE/'rejected-cap-withdraw-layout/build_fastened_caps.py').read_text()
    expected=source.replace("x=-2.35 if variant=='final' else -1.65","x=-2.60 if variant=='final' else -1.65").replace("p=scene(port,side,variant='compact-rejected')","p=scene(port,side,q=1.15,retreat=1.,variant='compact-rejected')").replace("'screw_center_x_mm':-2.35","'screw_center_x_mm':-2.60")
    if expected!=(HERE/'build_fastened_caps.py').read_text():raise ValueError('Source change exceeds one geometry parameter and diagnostic pose/metadata')
    report=json.loads((HERE/'rejected-cap-withdraw-layout/build-receipt.json').read_text())
    if report['builder_sha256']!=sha(HERE/'rejected-cap-withdraw-layout/build_fastened_caps.py'):raise ValueError('Failed native source digest differs')
    if report['actual_motion_row_count']!=620 or len(report['unexpected_collision_rows'])!=16:raise ValueError('Failed predecessor differs from actual captured run')
    return report

def main():
    started=time.monotonic();old=require_controlled_source_delta();before=final.protected()
    checker=Checker();rows=[];rejected=[];exports=[];static_cache={};static_pair_cache={}
    def checked_scene(port,side,q=0.,retreat=0.,present=True,jam=None,variant='final'):
        key=(port,side,variant)
        if key not in static_cache:
            raw,dx=final.modified(port,side,variant)
            static_cache[key]=({n:CheckedBody(s) for n,s in raw.items()},dx)
        ref,dx=static_cache[key];p={n:b for n,b in ref.items() if n!='KEY'}
        p['PAWL']=ref['PAWL'].translate((dx*retreat,0,0))
        for i in range(2):p['STOP_'+str(i)]=ref['STOP_'+str(i)].translate(final.r3.delta_r(port,(jam or {}).get(i,final.r3.lift(q) if present else 0.)))
        if present:p['KEY']=ref['KEY'].translate(final.r3.delta_q(port,q))
        return p
    def pairs(p,port,side,variant='final'):
        changed={n for n in p if n.startswith(('CAP_','SCREW_')) or n=='ROOT'}
        fixed=changed|{'OLD_COVER_UNFASTENED'};out=[]
        for a,b in itertools.combinations(p,2):
            if a not in changed and b not in changed:continue
            key=(port,side,variant,a,b)
            if a in fixed and b in fixed and key in static_pair_cache:
                aa,bb,value=static_pair_cache[key]
                if not p[a].shape.isSame(aa.shape) or not p[b].shape.isSame(bb.shape):raise ValueError('Static cache actual OCP identity changed')
            else:
                value=checker.common(p[a],p[b])
                if a in fixed and b in fixed:static_pair_cache[key]=(p[a],p[b],value)
            out.append({'parts':[a,b],**value})
        return out
    for port in ('STOW','OPEN'):
        for side in 'LR':
            p=checked_scene(port,side,q=1.15,retreat=1.,variant='compact-rejected')
            bad=[x for x in pairs(p,port,side,'compact-rejected') if x['checked_common_mm3']>EPS]
            rejected.append({'port':port,'side':side,'q_mm':1.15,'actual_collisions':bad})
            for state,q,pres,jam in [('FULL',0,True,None),('SEAT_0p10',.1,True,None),('ABSENT',0,False,None),('PRIMARY_JAM_ABSENT',0,False,{0:1.2}),('SECONDARY_JAM_ABSENT',0,False,{1:1.2}),('DOUBLE_JAM_ABSENT_ESCAPE',0,False,{0:1.2,1:1.2})]:
                for i in range(23):
                    p=checked_scene(port,side,q,i/22,pres,jam)
                    rows.append({'port':port,'side':side,'state':state,'fraction':i/22,'pairs':pairs(p,port,side)})
            for q in (0.,.02,.05,.10,.15,.20,.25,.4,.7,.8,1.,1.2,1.4,2.,4.,8.,12.):
                p=checked_scene(port,side,q,1.)
                rows.append({'port':port,'side':side,'state':'NORMAL_KEY_WITHDRAW','q_mm':q,'pairs':pairs(p,port,side)})
            print(json.dumps({'port':port,'side':side,'rows':len(rows),'actual_OCC_common_queries':checker.actual_occ_common_count}),flush=True)
        for name,q,pres,jam,f in [('SEATED',0,True,None,0),('RELEASED',0,True,None,1),('ABSENT',0,False,None,0),('NORMAL_KEY_WITHDRAW_1p4',1.4,True,None,1)]:
            combined={}
            for side in 'LR':combined.update({side+'_'+n:s for n,s in final.scene(port,side,q,f,pres,jam).items()})
            exports.append(final.save(combined,port+'_'+name))
    bad=[{'port':r['port'],'side':r['side'],'state':r['state'],'q_mm':r.get('q_mm'),'fraction':r.get('fraction'),'pair':p} for r in rows for p in r['pairs'] if p['checked_common_mm3']>EPS]
    unchanged=before==final.protected()
    report={'environment':{'host':platform.node(),'python':platform.python_version(),'cadquery':final.cq.__version__},'executed_delta_verifier_sha256':sha(__file__),'final_builder_sha256':sha(HERE/'build_fastened_caps.py'),'failed_predecessor_source_sha256':old['builder_sha256'],'failed_predecessor_receipt_sha256':sha(HERE/'rejected-cap-withdraw-layout/build-receipt.json'),'exact_source_delta_required':True,'one_geometry_parameter_change_x_mm':{'before':-2.35,'after':-2.60},'diagnostic_pose_corrected_from_q0_to_q1p15':True,'original_620_pose_grid_not_expanded':True,'actual_motion_rows':rows,'actual_motion_row_count':len(rows),'added_or_changed_pair_check_count':sum(len(r['pairs']) for r in rows),'unexpected_collision_rows':bad,'compact_withdrawal_counterexamples':rejected,'STEP_exports':exports,'actual_OCC_common_queries':checker.actual_occ_common_count,'validated_actual_AABB_proofs':checker.validated_actual_AABB_proven_zero_count,'fixed_pair_cache_requires_isSame_on_both_retained_bodies':True,'protected_r3_bytes_unchanged':unchanged,'protected_r3_sha256':before,'thread_clamp_return_force_or_strength_qualified':False,'finite_retraction_limit_N':None,'fixture_fabrication_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-started}
    (HERE/'delta-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    if bad:raise ValueError('Shifted cap/head still has actual collision; delta receipt kept')
    if not unchanged:raise ValueError('Frozen R3 bytes changed')
    # q=1.15 passes the STOW rear station (q=1.20); the OPEN rear station is
    # q=6.10. Expecting OPEN to collide here was an actual rejected diagnostic
    # assertion. Its observed clearance is retained and is not changed into a
    # fake collision; the two observed STOW counterexamples reject this layout.
    if {r['side'] for r in rejected if r['port']=='STOW' and r['actual_collisions']}!={'L','R'}:raise ValueError('Observed STOW compact withdrawal negative controls missing')
    if len(rows)!=620:raise ValueError('Original pose count changed')
    print(json.dumps({'native_result':'completed','rows':len(rows),'pair_checks':report['added_or_changed_pair_check_count'],'actual_OCC_queries':checker.actual_occ_common_count,'STEP':len(exports),'unexpected_collisions':len(bad),'elapsed_seconds':report['elapsed_seconds']}),flush=True)

if __name__=='__main__':main()
