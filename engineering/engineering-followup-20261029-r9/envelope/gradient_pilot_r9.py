"""Fixed-root 64-split comparison of the locally sensitive midpoint rule."""
import argparse
from collections import Counter
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import resource
import signal
import sys
import time
import traceback

R8=Path(__file__).resolve().parents[2]/'engineering-followup-20261029-r8/envelope'
sys.path.insert(0,str(R8))
import run_original_depth24_r8 as common
import source_quadric_r8 as math
import balanced_refinement_r8 as balanced
import gradient_cut_r9 as local_cut


def main():
    p=argparse.ArgumentParser();p.add_argument('--originals',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(805306368,805306368))
    signal.signal(signal.SIGALRM,lambda a,b:(_ for _ in ()).throw(TimeoutError('60-second sensitivity pilot')));signal.alarm(60)
    r={'schema':'razr-r9-local-gradient-pilot64','execution_completed':False,'counts':Counter(),
       'source':common.identity(__file__),'cut_source':common.identity(local_cut.__file__),
       'math_source':common.identity(math.__file__),'common_source':common.identity(common.__file__),
       'basis':common.identity(Path(__file__).with_name('GRADIENT_PILOT_BASIS.md')),
       'limits':{'maximum_splits':64,'maximum_depth':24,'wall_seconds':60,'address_space_bytes':805306368},
       'scope':{'conditional_source_model_only':True,'native_error_bound_verified':False,'full_continuous_G2':False}}
    try:
        row,cert,models,ids,native=common.load_inputs(args.originals,'case-037',2)
        root=cert['roots'][66];B=math.box(root['root_box_exact'])
        r['original_inputs']=ids;r['selection']={'case_id':'case-037','frame':2,'root_index':66,'root_box_exact':root['root_box_exact']}
        r['D_exact']=row['original_remaining_displacement_box_exact']
        balanced.choose_cut=local_cut.choose_cut
        result=balanced.run(B,cert['boundary_refinement']['sources'],models,math.box(r['D_exact']),r,64,F(1e-7))
        proof=args.output/'balanced-tree.json.gz'
        with gzip.open(proof,'wt') as f:json.dump(result,f,separators=(',',':'))
        r['proof']=common.identity(proof);r['result']={k:v for k,v in result.items() if k!='nodes'};r['execution_completed']=True
    except Exception as e:r['failure']={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0);r['seconds']=time.monotonic()-start;r['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'completed':r['execution_completed'],'seconds':r['seconds'],
                      'retained':r.get('result',{}).get('retained_display'),'depth':r.get('result',{}).get('maximum_depth'),'failure':r.get('failure')}))


if __name__=='__main__':main()
