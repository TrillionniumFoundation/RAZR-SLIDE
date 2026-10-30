"""Zero-split conservative reclassification of every original V6 retained leaf.

Run a 64-leaf fixed-order cost pilot before admitting --all. Existing old
exclusions are carried unchanged; every nonexcluded old leaf keeps its full
exact volume. Proof rows stream to gzip to bound live memory.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import resource
import signal
import time
import traceback
import run_original_depth24_r8 as old
import source_quadric_r8 as math

def main():
    p=argparse.ArgumentParser();p.add_argument('--originals',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--pilot',action='store_true');mode.add_argument('--all',action='store_true')
    p.add_argument('--pilot-report',type=Path)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(805306368,805306368))
    limit=60 if args.pilot else 600
    signal.signal(signal.SIGALRM,lambda a,b:(_ for _ in ()).throw(TimeoutError('registered wall limit')));signal.alarm(limit)
    start=time.monotonic();r={'schema':'razr-r8-original-leaf-reclassification','execution_completed':False,'phase':'pilot64' if args.pilot else 'all16',
       'counts':Counter(),'new_splits':0,'original_depth_limit':24,'original_split_count_preserved':4096,'wall_limit_seconds':limit,
       'scope':{'conditional_source_model_only':True,'native_error_bound_verified':False,'native_filling_verified':False,'full_continuous_G2':False,'all_blockers_closed':False},
       'source':old.identity(__file__),'driver_source':old.identity(old.__file__),'math_source':old.identity(math.__file__),'frames':[]}
    try:
        root=args.originals/'r7-recovery/v7/r5-local-v7/input-snapshot-v1/base-v6/all-primitive-support-frames'
        orig=json.loads((root/'report.json').read_text());r['original_report']=old.identity(root/'report.json');TOL=F(orig['original_TOL_exact']);tiny=F(orig['capacity']['tiny_retained_volume_exact'])
        if args.all:
            old.need(args.pilot_report is not None,'actual pilot required');pilot=json.loads(args.pilot_report.read_text());r['pilot']=old.identity(args.pilot_report)
            old.need(pilot['execution_completed'] and pilot['phase']=='pilot64','completed pilot required')
            old.need(pilot['math_source']['sha256']==r['math_source']['sha256'],'pilot math source differs')
            old.need(pilot['capacity_basis']['all_remaining_leaves_estimated_seconds']<limit,'actual pilot does not support all-frame time')
        seen=0;geom_start=None;pilot_limited=False
        for f in orig['frames']:
            if args.pilot and f['primitive_support_model_conditional_clearance_gate_passed']:continue
            row,cert,models,ids,native=old.load_inputs(args.originals,f['case_id'],f['frame'])
            prefix=f['case_id']+'-frame-'+str(f['frame']);proof=args.output/(prefix+'-reclassification.jsonl.gz')
            before=F(row['retained_leaf_sum_exact']);retained=F(0);excluded=F(0);counts=Counter();maxdepth=0
            D=math.box(row['original_remaining_displacement_box_exact']);sources=cert['boundary_refinement']['sources']
            with gzip.open(proof,'wt',encoding='utf-8') as out:
                for leaf in old.leaves(cert):
                    maxdepth=max(maxdepth,leaf['depth']);old.need(leaf['depth']<=24,'old leaf exceeds original depth')
                    record={'locator':leaf['locator'],'depth':leaf['depth'],'box_exact':math.encbox(leaf['box']),'volume_exact':str(leaf['volume'])}
                    if args.pilot and seen>=64:
                        pilot_limited=True;break
                    if row['primitive_support_model_conditional_clearance_gate_passed'] or leaf['volume']<=tiny:
                        result={'excluded':False,'reason':'original_pass_or_tiny_leaf_preserved'};counts['preserved_without_new_test']+=1
                    else:
                        if geom_start is None:geom_start=time.monotonic()
                        result=old.attempt(leaf['box'],sources,models,D,r);seen+=1;counts['tested']+=1
                    record['result']=result
                    if result['excluded']:excluded+=leaf['volume'];counts['excluded']+=1
                    else:retained+=leaf['volume'];counts['retained']+=1
                    out.write(json.dumps(record,separators=(',',':'))+'\n')
                    if r['counts']['pieces']>12000000:raise RuntimeError('original 12000000 piece-test cap exceeded')
            if not args.pilot:old.need(retained+excluded==before,'old retained positive volume not conserved')
            bounds={'case_id':f['case_id'],'frame':f['frame'],'original_bound_exact':str(before),'original_bound_display':float(before),
                 'retained_exact':str(retained),'retained_display':float(retained),'newly_excluded_exact':str(excluded),'newly_excluded_display':float(excluded),
                 'old_volume_conserved':retained+excluded==before,'original_gate_passed':row['primitive_support_model_conditional_clearance_gate_passed'],
                 'new_conditional_gate_passed':retained<=TOL if not args.pilot else None,'counts':counts,'maximum_inherited_depth':maxdepth,
                 'source_piece_counts':row['source_piece_counts'],'original_inputs':ids,'proof':old.identity(proof)}
            r['frames'].append(bounds)
            if pilot_limited:break
        r['geometry_seconds']=time.monotonic()-geom_start if geom_start else 0;r['tested_leaves']=seen
        if args.pilot:
            old.need(seen==64,'pilot did not test prescribed 64 leaves')
            # Original retained count is 4,943, including tiny/pass leaves.
            # Scale pilot by all 4,943 as a conservative count, plus one
            # complete two-inventory read per frame. This is a cost estimate,
            # not a guarantee or an inferred clearance pass.
            estimate=r['geometry_seconds']/64*4943+32
            r['capacity_basis']={'fixed_order_sample_count':64,'all_original_retained_leaf_count_upper':4943,
                  'all_remaining_leaves_estimated_seconds':estimate,'estimate_is_not_runtime_guarantee':True,
                  'geometry_count_bound':4943*12*4096,'actual_pilot_piece_tests':r['counts']['pieces'],
                  'full_run_hard_piece_limit':12000000,'full_run_hard_wall_seconds':600,'no_added_splits':True}
        else:r['new_conditional_pass_count']=sum(f['new_conditional_gate_passed'] for f in r['frames'])
        r['execution_completed']=True
    except Exception as exc:r['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0);r['seconds']=time.monotonic()-start;r['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'completed':r['execution_completed'],'seconds':r['seconds'],'tested':r.get('tested_leaves'),'new_passes':r.get('new_conditional_pass_count'),'counts':r['counts'],'error':r.get('error'),'capacity':r.get('capacity_basis')}))
    if not r['execution_completed']:raise SystemExit(1)

if __name__=='__main__':main()
