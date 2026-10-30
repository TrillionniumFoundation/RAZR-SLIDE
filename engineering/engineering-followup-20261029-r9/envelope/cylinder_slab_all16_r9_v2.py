"""Fresh original-root all16 run, with recovered failure serialization (v2)."""
import argparse
from collections import Counter
from fractions import Fraction as F
import gc
import gzip
import heapq
import json
from pathlib import Path
import resource
import signal
import time
import traceback
import cylinder_slab_r9 as geometry
from cylinder_slab_r9 import common,math
import gradient_cut_r9 as cuts
import atomic_refinement_r9 as atomic
import recovery_serialization_r9 as recovery


LIMITS={'maximum_splits':4096,'maximum_depth':24,'maximum_boundary_box_tests':12000000,
        'wall_seconds':600,'address_space_limit_bytes':805306368}


def terminal_sums(root):
    volume=bound=F(0);depth=0;splits=0
    for node in root['nodes']:
        depth=max(depth,node['depth'])
        if node['kind']=='split':splits+=1
        else:
            volume+=F(node['box_volume_exact']);bound+=F(node['bound_exact'])
    return volume,bound,depth,splits


def main():
    p=argparse.ArgumentParser();p.add_argument('--originals',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(805306368,805306368))
    signal.signal(signal.SIGALRM,lambda a,b:(_ for _ in ()).throw(TimeoutError('original complete-run 600-second deadline')));signal.alarm(600)
    here=Path(__file__).parent
    report={'schema':'razr-r9-cylinder-slab-all16-original-roots','execution_completed':False,'computation_completed':False,
            'frames':[],'counts':Counter(),'limits':LIMITS,'source':common.identity(__file__),
            'geometry_source':common.identity(geometry.__file__),'math_source':common.identity(math.__file__),
            'common_source':common.identity(common.__file__),'cut_source':common.identity(cuts.__file__),
            'atomic_source':common.identity(atomic.__file__),'recovery_source':common.identity(recovery.__file__),'cache_source':common.identity(geometry.cached.__file__),
            'proof_basis':common.identity(here/'CYLINDER_SLAB_PROOF.md'),
            'capacity_basis':common.identity(here/'CYLINDER_SLAB_ALL16_CAPACITY.md'),
            'scope':{'conditional_source_model_only':True,'native_error_bound_verified':False,
                     'native_filling_verified':False,'native_envelope_topology_verified':False,
                     'full_continuous_G2':False,'all_blockers_closed':False},
            'new_computation_from_all_original_roots':True,'previous_refinement_cost_not_reused_as_free_preprocessing':True}
    states=[];queue=[];splits=0;pending_attempt=None;TOL=F(1e-7);tiny=None
    try:
        pilot=json.loads((here/'CYLINDER_SLAB_PILOT_INDEPENDENT_V2.json').read_text())
        controls=json.loads((here/'CYLINDER_SLAB_ANALYTIC_CONTROLS.json').read_text())
        interruptions=json.loads((here/'ATOMIC_REFINEMENT_INTERRUPTION_CONTROLS.json').read_text())
        common.need(pilot['completed'] and controls['completed'] and interruptions['completed'],'required actual and analytic controls')
        common.need(all(x['passed'] for x in controls['controls']+interruptions['controls']),'all controls passed')
        report['prerequisites']=[common.identity(here/name) for name in ('CYLINDER_SLAB_PILOT_INDEPENDENT_V2.json','CYLINDER_SLAB_ANALYTIC_CONTROLS.json','ATOMIC_REFINEMENT_INTERRUPTION_CONTROLS.json')]
        base=args.originals/'r7-recovery/v7/r5-local-v7/input-snapshot-v1/base-v6/all-primitive-support-frames'
        original=json.loads((base/'report.json').read_text());report['original_report']=common.identity(base/'report.json')
        common.need(F(original['original_TOL_exact'])==TOL,'unchanged original gate');tiny=F(original['capacity']['tiny_retained_volume_exact'])
        report.update(original_TOL_exact=str(TOL),original_tiny_exact=str(tiny))

        def evaluate(state,B,index,depth):
            volume=common.volume(B)
            if volume<=tiny:
                result={'kind':'original_tiny_positive_volume_retained','bound_exact':str(volume)}
                report['counts']['tiny_nodes']+=1
            else:
                result=geometry.evaluate(B,state['sources'],state['models'],state['D'],report)
                report['counts']['tested_nodes']+=1
            bound=F(result['bound_exact']);common.need(0<=bound<=volume,'conservative cell upper-bound range')
            return {'id':index,'depth':depth,'kind':'leaf','box_exact':math.encbox(B),
                    'box_volume_exact':str(volume),'bound_exact':str(bound),'observation':result}

        def enqueue(fi,ri,node):
            bound=F(node['bound_exact']);B=math.box(node['box_exact'])
            if bound>tiny and node['depth']<24:
                heapq.heappush(queue,(-bound,fi,ri,node['id'],B,node['depth']))

        for fi,f in enumerate(original['frames']):
            row,certificate,models,identities,native=common.load_inputs(args.originals,f['case_id'],f['frame'])
            state={'row':row,'sources':certificate['boundary_refinement']['sources'],'models':models,'inputs':identities,
                   'D':math.box(row['original_remaining_displacement_box_exact']),'roots':[],'bound':F(0)}
            states.append(state)
            # Preserve the complete original partition before evaluating it.
            for ri,oldroot in enumerate(certificate['roots']):
                B=math.box(oldroot['root_box_exact']);volume=common.volume(B)
                common.need(volume==F(oldroot['root_directed_volume_exact']) and volume>0,'complete original positive root')
                node={'id':0,'depth':0,'kind':'leaf','box_exact':oldroot['root_box_exact'],
                      'box_volume_exact':str(volume),'bound_exact':str(volume),
                      'observation':{'kind':'not_evaluated','bound_exact':str(volume)}}
                state['roots'].append({'root_index':ri,'base_V5_leaf_locator':oldroot['base_V5_leaf_locator'],
                                       'root_box_exact':oldroot['root_box_exact'],'root_volume_exact':str(volume),'nodes':[node]})
                state['bound']+=volume
            for ri,root in enumerate(state['roots']):
                B=math.box(root['root_box_exact']);node=evaluate(state,B,0,0)
                replacement=dict(root,nodes=[node]);state['roots'][ri]=replacement
                state['bound']+=F(node['bound_exact'])-F(root['root_volume_exact'])
                enqueue(fi,ri,node)
            print(json.dumps({'initialized':[f['case_id'],f['frame']],'bound':float(state['bound']),'roots':len(state['roots']),
                              'seconds':time.monotonic()-start,'piece_tests':report['counts']['pieces']}),flush=True)
            del certificate,native;gc.collect()

        while queue and splits<4096:
            negative,fi,ri,ni,B,depth=heapq.heappop(queue);state=states[fi]
            if state['bound']<=TOL:continue
            root=state['roots'][ri];node=root['nodes'][ni]
            common.need(node['kind']=='leaf','one live leaf selected')
            axis,cut,witness=cuts.choose_cut(B,node['observation'],state['models'],state['sources'])
            lo,hi=list(B),list(B);lo[axis],hi[axis]=(B[axis][0],cut),(cut,B[axis][1])
            common.need(common.volume(lo)==common.volume(hi)==common.volume(B)/2,'exact original box partition')
            pending_attempt={'frame_index':fi,'root_index':ri,'original_parent_bound_exact':node['bound_exact']}
            replacement=atomic.prepare_split(root,ni,axis,cut,(tuple(lo),tuple(hi)),
                lambda child,index,d:evaluate(state,child,index,d),pending_attempt)
            replacement['nodes'][ni]['cut_witness']=witness
            # One reference assignment commits the complete new subtree. A
            # failure report recomputes totals from this committed tree.
            state['roots'][ri]=replacement
            children=[replacement['nodes'][i] for i in replacement['nodes'][ni]['children']]
            state['bound']+=sum(F(c['bound_exact']) for c in children)-F(node['bound_exact'])
            for child in children:enqueue(fi,ri,child)
            splits+=1;pending_attempt=None
            if splits in (1,2,4,8,16,32,64,128,256,512,1024,2048,4096):
                print(json.dumps({'splits':splits,'frame_bounds':[float(s['bound']) for s in states],
                                  'passes':sum(s['bound']<=TOL for s in states),'seconds':time.monotonic()-start}),flush=True)
        report['computation_completed']=True
    except Exception as exc:
        report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        signal.alarm(0)
    try:
        # On success the original deadline remains armed during serialization.
        # On failure preservation is allowed to continue, but qualification is
        # false and its complete additional time is still recorded.
        for state in states:
            row=state['row'];filename=row['case_id']+'-frame-'+str(row['frame'])+'-cylinder-slab.json.gz'
            path=args.output/filename;volume=bound=F(0);maxdepth=frame_splits=0
            for root in state['roots']:
                v,u,d,n=terminal_sums(root)
                common.need(v==F(root['root_volume_exact']),'committed exact box partition')
                volume+=v;bound+=u;maxdepth=max(maxdepth,d);frame_splits+=n
            payload={'case_id':row['case_id'],'frame':row['frame'],'D_exact':row['original_remaining_displacement_box_exact'],'roots':state['roots']}
            with gzip.open(path,'wt') as stream:json.dump(payload,stream,separators=(',',':'))
            report['frames'].append({'case_id':row['case_id'],'frame':row['frame'],'original_inputs':state['inputs'],
                                     'source_piece_counts':row['source_piece_counts'],'root_count':len(state['roots']),
                                     'root_box_volume_exact':str(volume),'intersection_upper_bound_exact':str(bound),
                                     'intersection_upper_bound_display_mm3':float(bound),
                                     'conservative_removed_volume_lower_bound_exact':str(volume-bound),
                                     'splits':frame_splits,'maximum_depth':maxdepth,
                                     'conditional_gate_passed':bound<=TOL,'proof':common.identity(path)})
        if pending_attempt is not None:
            pending_attempt['commit_state']=recovery.pending_commit_state(pending_attempt,states[pending_attempt['frame_index']]['roots'][pending_attempt['root_index']])
            path=args.output/'pending-attempt-evidence.json.gz'
            with gzip.open(path,'wt') as f:json.dump(pending_attempt,f,separators=(',',':'))
            report['pending_attempt_evidence']=common.identity(path)
        report['execution_completed']=report['computation_completed'] and len(report['frames'])==16 and time.monotonic()-start<=600
    except Exception as exc:
        report['serialization_failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        report['execution_completed']=False
        signal.alarm(0)
        try:
            payloads=[]
            for state in states:
                row=state['row']
                name=row['case_id']+'-frame-'+str(row['frame'])+'-committed-recovery.json.gz'
                payload={'case_id':row['case_id'],'frame':row['frame'],'D_exact':row['original_remaining_displacement_box_exact'],'roots':state['roots']}
                payloads.append((name,payload))
            if pending_attempt is not None:
                pending_attempt['commit_state']=recovery.pending_commit_state(pending_attempt,states[pending_attempt['frame_index']]['roots'][pending_attempt['root_index']])
            report['recovery_after_qualification_failure']=recovery.recover(payloads,args.output/'failed-serialization-recovery',pending_attempt)
        except Exception as recovery_error:
            report['recovery_failure']={'type':type(recovery_error).__name__,'message':str(recovery_error),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0)
        report.update(global_splits=sum(f['splits'] for f in report['frames']),
                      conditional_pass_count=sum(f['conditional_gate_passed'] for f in report['frames']),
                      seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        report['recorded_budget_passed']=report['execution_completed'] and report['seconds']<=600
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'completed':report['execution_completed'],'passes':report['conditional_pass_count'],
                      'splits':report['global_splits'],'seconds':report['seconds'],
                      'failure':report.get('failure'),'serialization_failure':report.get('serialization_failure')}),flush=True)
    if not report['execution_completed']:raise SystemExit(1)


if __name__=='__main__':main()
