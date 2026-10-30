"""Replay one original depth-24 parent with exact primitive correlations."""
import argparse
from collections import Counter
from fractions import Fraction as F
import gc
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import signal
import time
import traceback
import source_quadric_r8 as math

def identity(p):
    p=Path(p)
    return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()}

def need(v,message):
    if not v: raise ValueError(message)

def volume(B):
    answer=F(1)
    for lo,hi in B: answer*=hi-lo
    return answer

def channel_for(B,whole,axis,end):
    channel=list(B)
    channel[axis]=(min(whole[axis][0]-1,B[axis][0]-1),B[axis][1]) if end==0 else (B[axis][0],max(whole[axis][1]+1,B[axis][1]+1))
    return tuple(channel)

def leaves(certificate):
    for root_index,root in enumerate(certificate['roots']):
        nodes=root['tree']['nodes']; pending=[(0,math.box(root['root_box_exact']),0)]; total=F(0);seen=set()
        while pending:
            i,B,depth=pending.pop(); need(i not in seen,'duplicate old node');seen.add(i); n=nodes[i]
            need(n['id']==i,'old node id mismatch')
            if n['kind']=='split':
                axis=n['axis'];c=F(n['cut_exact']);need(B[axis][0]<c<B[axis][1],'old split not internal')
                low=list(B);high=list(B);low[axis]=(B[axis][0],c);high[axis]=(c,B[axis][1])
                pending.extend([(n['children'][1],tuple(high),depth+1),(n['children'][0],tuple(low),depth+1)])
            else:
                v=volume(B);need(v==F(n['positive_directed_volume_exact']) and v>0,'old directed volume mismatch');total+=v
                if n['kind']=='retained':yield {'locator':[root_index,i],'box':B,'depth':depth,'node':n,'volume':v}
        need(len(seen)==len(nodes) and total==volume(math.box(root['root_box_exact'])),'incomplete original tree')

def old_separate(piece,channel):
    B=math.box(piece['box_exact'])
    for k in range(3):
        if B[k][1]<=channel[k][0]:return str(2*k)
        if B[k][0]>=channel[k][1]:return str(2*k+1)
    for slab in piece['additional_slabs']:
        lo,hi=math.interval_dot(math.vec(slab['normal_exact']),channel);a,b=map(F,slab['bounds_exact'])
        if b<=lo:return '6'
        if a>=hi:return '7'
    return None

def load_inputs(root,case,frame):
    E=root/'r7-envelope'; original=root/'r7-recovery/r3e/native-and-math'
    contract=json.loads((E/'edge189-source-diagnostic-v1/R7E_EDGE189_LINE_SUPPORT_DIAGNOSTIC_CONTRACT_V1.json').read_text())
    material_reports=[]; ids=[]
    for kind in ('producer','reader'):
        p=original/kind/'worker/report.json'; ident=identity(p); ref=contract['inputs']['native_original_'+kind]
        need(all(ident[k]==ref[k] for k in ('bytes','sha256')),'native original inventory identity changed')
        doc=json.loads(p.read_text());need(doc['execution_completed'] and len(doc['operands'])==53,'complete native inventory required')
        material_reports.append({(r['input']['case_id'],r['input']['material_id']):r for r in doc['operands'] if r['input']['case_id']==case})
        ids.append(ident); del doc;gc.collect()
    need(material_reports[0]==material_reports[1],'native producer/reader record mismatch')
    report_path=root/'r7-recovery/v7/r5-local-v7/input-snapshot-v1/base-v6/all-primitive-support-frames/report.json'
    report=json.loads(report_path.read_text());row=next(x for x in report['frames'] if x['case_id']==case and x['frame']==frame)
    p=report_path.parent/(case+'-frame-'+str(frame)+'-primitive-support.json.gz');ident=identity(p)
    need(all(ident[k]==row['certificate'][k] for k in ('bytes','sha256')),'original V6 certificate identity changed')
    certificate=json.loads(gzip.decompress(p.read_bytes()));need(certificate['frame']==row,'certificate/report frame differs')
    ids.extend([identity(report_path),ident]);sources=certificate['boundary_refinement']['sources'];models=[]
    for source in sources:
        record=material_reports[0][tuple(source['material_key'])];boundary=record['boundary'];need(not boundary['incomplete_inventory'],'incomplete original boundary')
        for k in ('faces','edges','vertices'):need(len(boundary[k])==boundary['counts'][k],'whole boundary census differs')
        mapping={}
        for kind,plural in [('face','faces'),('edge','edges')]:
            for record in boundary[plural]:mapping[(kind,record['index'])]=math.source_model(record,kind)
        models.append(mapping)
    return row,certificate,models,ids,material_reports[0]

def attempt(cell, sources,models,D,report,all_channels=False):
    observations=[]
    for side,source in enumerate(sources):
        shift=D if side==0 else ((F(0),F(0)),)*3
        for axis in range(3):
            for end in (0,1):
                channel=channel_for(cell,math.box(source['known_whole_exact']),axis,end);codes=[];claims=[];failure=None
                report['counts']['channels']+=1
                for index,piece in enumerate(source['pieces']):
                    report['counts']['pieces']+=1;code=old_separate(piece,channel)
                    if code is not None:codes.append(code);continue
                    model=models[side].get((piece['kind'],piece['index']))
                    if model is None: failure={'piece_index':index,'reason':'unsupported_original_primitive'};break
                    report['counts']['new_correlations']+=1
                    claim=math.correlate(model,math.box(piece['box_exact']),channel,shift)
                    if claim is None:
                        failure={'piece_index':index,'reason':'correlation_inconclusive','source_kind':piece['kind'],'source_index':piece['index'],'source_type':model['type']};break
                    code={'plane':'P','line':'L','quadric':'Q','empty_closed_intersection':'E'}[claim['code']]
                    claim.update(material_key=source['material_key'],piece_index=index,original_kind=piece['kind'],original_index=piece['index'],channel_exact=math.encbox(channel))
                    claims.append(claim);codes.append(code);report['counts']['new_'+claim['code']]+=1
                item={'material_side':side,'axis':axis,'end':end,'channel_exact':math.encbox(channel),'codes':''.join(codes),'new_claims':claims,'failure':failure}
                observations.append(item)
                if failure is None:
                    need(len(codes)==len(source['pieces']),'whole channel missing a piece');item['complete_channel_pass']=True
                    if not all_channels:return {'excluded':True,'observations':observations}
    return {'excluded':any(x['failure'] is None for x in observations),'observations':observations}

def main():
    p=argparse.ArgumentParser();p.add_argument('--originals',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
    signal.signal(signal.SIGALRM,lambda a,b: (_ for _ in ()).throw(TimeoutError('registered 60-second diagnostic limit')));signal.alarm(60)
    started=time.monotonic();r={'schema':'razr-r8-original-depth24-primitive-correlation','execution_completed':False,'counts':Counter(),
      'scope':{'new_conditional_serialized_source_model':True,'native_error_bound_verified':False,'native_filling_verified':False,'full_continuous_G2':False,'all_blockers_closed':False},
      'new_splits':0,'original_depth_limit':24,'source':identity(__file__),'math_source':identity(math.__file__)}
    try:
        row,certificate,models,ids,native=load_inputs(args.originals,'case-028',1);r['inputs']=ids
        parents=list(leaves(certificate));parent=next(x for x in parents if x['locator']==[78,375]);need(parent['depth']==24,'actual parent depth changed')
        r['original_parent']={k:(math.encbox(v) if k=='box' else str(v) if k=='volume' else v) for k,v in parent.items() if k!='node'}
        r['D_exact']=row['original_remaining_displacement_box_exact'];r['original_TOL_exact']=str(F(1e-7));r['source_piece_counts']=[len(s['pieces']) for s in certificate['boundary_refinement']['sources']]
        r['result']=attempt(parent['box'],certificate['boundary_refinement']['sources'],models,math.box(r['D_exact']),r,all_channels=True)
        r['execution_completed']=True
    except Exception as exc:
        r['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0);r['seconds']=time.monotonic()-started;r['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'completed':r['execution_completed'],'excluded':r.get('result',{}).get('excluded'),'seconds':r['seconds'],'counts':r['counts'],'error':r.get('error')}))
    if not r['execution_completed']:raise SystemExit(1)

if __name__=='__main__':main()
