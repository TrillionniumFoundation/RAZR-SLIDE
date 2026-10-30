"""Inspect every blocker in the largest retained cell, not just a prefix."""
import argparse
from collections import Counter
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import sys
import time

R8=Path(__file__).resolve().parents[2]/'engineering-followup-20261029-r8/envelope'
sys.path.insert(0,str(R8))
import run_original_depth24_r8 as common
import source_quadric_r8 as math
import cached_predicates_r9 as cached


def main():
    p=argparse.ArgumentParser();p.add_argument('--originals',type=Path,required=True);p.add_argument('--proof',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();start=time.monotonic()
    proof=json.loads(gzip.decompress(args.proof.read_bytes()))
    row,cert,models,ids,native=common.load_inputs(args.originals,proof['case_id'],proof['frame'])
    choices=[(F(n['volume_exact']),root['root_index'],n['id'],n) for root in proof['roots'] for n in root['nodes'] if n['kind']=='retained']
    volume,root_index,node_index,node=max(choices,key=lambda x:(x[0],-x[1],-x[2]))
    B=math.box(node['box_exact']);D=math.box(proof['D_exact']);channels=[]
    for side,source in enumerate(cert['boundary_refinement']['sources']):
        shift=D if side==0 else ((F(0),F(0)),)*3
        for axis in range(3):
            for end in (0,1):
                channel=common.channel_for(B,math.box(source['known_whole_exact']),axis,end)
                codes=[];unresolved=[]
                for index,piece in enumerate(source['pieces']):
                    code=cached.old_separate(piece,channel)
                    if code is not None:codes.append(code);continue
                    model=models[side].get((piece['kind'],piece['index']))
                    claim=math.correlate(model,math.box(piece['box_exact']),channel,shift) if model else None
                    if claim is not None:codes.append(claim['code']);continue
                    codes.append(None)
                    unresolved.append({'piece_index':index,'kind':piece['kind'],'index':piece['index'],
                                       'type':model['type'] if model else None,
                                       'source_record':model['record'] if model else None,
                                       'piece':piece})
                channels.append({'side':side,'axis':axis,'end':end,'channel_exact':math.encbox(channel),
                                 'piece_count':len(source['pieces']),'codes':codes,'unresolved':unresolved})
    r={'schema':'razr-r9-all-blockers-largest-retained-cell-diagnostic','source':common.identity(__file__),
       'proof':common.identity(args.proof),'inputs':ids,'case_id':proof['case_id'],'frame':proof['frame'],
       'root_index':root_index,'node_index':node_index,'box_exact':node['box_exact'],
       'D_exact':proof['D_exact'],'volume_exact':str(volume),'channels':channels,
       'seconds':time.monotonic()-start,'geometry_qualification':False}
    args.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'seconds':r['seconds'],'cell':[root_index,node_index],'volume':float(volume),
                      'channels':[{'side':c['side'],'axis':c['axis'],'end':c['end'],
                                   'unresolved':[(u['kind'],u['index'],u['type']) for u in c['unresolved']]} for c in channels]}))


if __name__=='__main__':main()
