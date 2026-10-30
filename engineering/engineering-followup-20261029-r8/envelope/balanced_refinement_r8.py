"""Exact-volume priority refinement with balanced radial midpoint cuts."""
import argparse
from collections import Counter
from fractions import Fraction as F
import gzip
import heapq
import json
from pathlib import Path
import resource
import signal
import time
import traceback
import run_original_depth24_r8 as common
import source_quadric_r8 as math

def choose_cut(B,observation,models,sources):
    radial=[]
    for channel in observation['observations']:
        fail=channel['failure']
        if fail is None:continue
        side=channel['material_side'];piece=sources[side]['pieces'][fail['piece_index']]
        model=models[side].get((piece['kind'],piece['index']))
        if model and model['type'] in ('GeomAbs_Cylinder','GeomAbs_Circle'):radial.append(model['basis'])
    if radial:
        scores=[max((abs(b['a'][k])+abs(b['b'][k]))*(B[k][1]-B[k][0]) for b in radial) for k in range(3)]
        rule='maximum_dual_radial_width'
    else:scores=[hi-lo for lo,hi in B];rule='longest_axis'
    axis=max(range(3),key=lambda k:(scores[k],-k));cut=(B[axis][0]+B[axis][1])/2
    return axis,cut,{'rule':rule,'scores_exact':list(map(str,scores))}

def select_root(replay,originals):
    rows=[]
    for frame in replay['frames']:
        if frame['new_conditional_gate_passed']:continue
        path=Path(frame['proof']['path'])
        with gzip.open(path,'rt') as f:
            for line in f:
                row=json.loads(line)
                if not row['result']['excluded']:
                    rows.append((-F(row['volume_exact']),frame['case_id'],frame['frame'],row['locator'],row))
    best=min(rows,key=lambda x:x[:4])
    _,case,frame,locator,row=best
    common.need(row['depth']==0 and locator[1]==0,'fixed largest pilot must be original unsplit root')
    return case,frame,locator,row

def run(root,sources,models,D,report,max_splits,TOL):
    nodes=[];queue=[];pending=F(0);removed=F(0);splits=0
    def append(B,depth):
        nonlocal pending,removed
        idx=len(nodes);v=common.volume(B);obs=common.attempt(B,sources,models,D,report)
        n={'id':idx,'depth':depth,'box_exact':math.encbox(B),'volume_exact':str(v),'observation':obs,
           'kind':'excluded' if obs['excluded'] else 'retained'}
        nodes.append(n)
        if obs['excluded']:removed+=v
        else:
            pending+=v
            if depth<24:heapq.heappush(queue,(-v,idx,B,depth))
        return idx
    append(root,0)
    milestones=[]
    while queue and splits<max_splits and pending>TOL:
        neg,idx,B,depth=heapq.heappop(queue);n=nodes[idx];v=-neg
        axis,cut,witness=choose_cut(B,n['observation'],models,sources)
        lo=list(B);hi=list(B);lo[axis]=(B[axis][0],cut);hi[axis]=(cut,B[axis][1])
        common.need(common.volume(lo)==common.volume(hi)==v/2,'balanced partition mismatch')
        pending-=v;n.update(kind='split',axis=axis,cut_exact=str(cut),cut_witness=witness)
        n['children']=[append(tuple(lo),depth+1),append(tuple(hi),depth+1)];splits+=1
        if splits in (1,2,4,8,16,32,64,128,256,512,1024,2048,4096):milestones.append({'splits':splits,'retained_exact':str(pending),'retained_display':float(pending),'excluded_display':float(removed)})
        if report['counts']['pieces']>12000000:raise RuntimeError('new experiment original piece cap exceeded')
    common.need(pending+removed==common.volume(root),'positive directed volume conservation failed')
    return {'nodes':nodes,'new_splits':splits,'maximum_depth':max(n['depth'] for n in nodes),'retained_exact':str(pending),
            'retained_display':float(pending),'excluded_exact':str(removed),'excluded_display':float(removed),
            'root_volume_exact':str(common.volume(root)),'original_TOL_exact':str(TOL),'conditional_root_gate_passed':pending<=TOL,
            'all_closed_boundaries_retained_as_zero_volume_carriers':True,'milestones':milestones}

def main():
    p=argparse.ArgumentParser();p.add_argument('--originals',type=Path,required=True);p.add_argument('--prior-replay',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(805306368,805306368));signal.signal(signal.SIGALRM,lambda a,b:(_ for _ in ()).throw(TimeoutError('64-split pilot wall limit')));signal.alarm(60)
    r={'schema':'razr-r8-balanced-original-root-pilot','execution_completed':False,'counts':Counter(),'source':common.identity(__file__),'math_source':common.identity(math.__file__),'common_source':common.identity(common.__file__),
       'prior_replay':common.identity(args.prior_replay),'new_computation_cost_separate_from_prior_runs':True,
       'limits':{'maximum_splits':64,'maximum_depth':24,'wall_seconds':60,'RSS_bytes':805306368},
       'scope':{'conditional_source_model_only':True,'full_continuous_G2':False,'native_error_bound_verified':False,'all_blockers_closed':False}}
    try:
        prior=json.loads(args.prior_replay.read_text());common.need(prior['execution_completed'] and prior['phase']=='all16','completed actual prior replay required')
        case,frame,locator,selected=select_root(prior,args.originals);row,cert,models,ids,native=common.load_inputs(args.originals,case,frame);r['inputs']=ids
        root=math.box(cert['roots'][locator[0]]['root_box_exact']);common.need(root==math.box(selected['box_exact']),'selected prior leaf differs from original root')
        r['selection']={'case_id':case,'frame':frame,'locator':locator,'selection_rule':'largest_exact_pending_volume_then_case_frame_locator','root_box_exact':math.encbox(root)}
        result=run(root,cert['boundary_refinement']['sources'],models,math.box(row['original_remaining_displacement_box_exact']),r,64,F(1e-7));r['D_exact']=row['original_remaining_displacement_box_exact']
        proof=args.output/'balanced-tree.json.gz'
        with gzip.open(proof,'wt',encoding='utf-8') as f:json.dump(result,f,separators=(',',':'))
        r['proof']=common.identity(proof);r['result']={k:v for k,v in result.items() if k!='nodes'};r['execution_completed']=True
    except Exception as exc:r['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0);r['seconds']=time.monotonic()-start;r['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'completed':r['execution_completed'],'seconds':r['seconds'],'result':{k:r.get('result',{}).get(k) for k in ['retained_display','excluded_display','new_splits','maximum_depth','conditional_root_gate_passed','milestones']},'counts':r['counts'],'error':r.get('error')}))
    if not r['execution_completed']:raise SystemExit(1)

if __name__=='__main__':main()
