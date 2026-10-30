"""Recorded original-root and actual retained-leaf candidate-search pilot."""
import argparse
from collections import Counter
import copy
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import time
import selected_cylinder_slab_r9 as producer
import check_selected_cylinder_slab_r9 as checker
import original_input_cache_r9 as inputs
from cylinder_slab_r9 import common,math


def main():
    p=argparse.ArgumentParser();p.add_argument('--originals',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    report={'schema':'razr-r9-prefix-selected-original-case-pilot','completed':False,
            'source':common.identity(__file__),'producer':common.identity(producer.__file__),
            'independent_checker':common.identity(checker.__file__),'input_cache':common.identity(inputs.__file__),
            'scope':{'conditional_source_model_only':True,'native_error_bound_verified':False,'full_continuous_G2':False},'cases':[]}
    loader=inputs.Inputs(args.originals);report['input_seconds']=time.monotonic()-start
    row,certificate,models,ids,native=loader.load('case-037',2)
    old=Path(__file__).with_name('balanced-all16-attempt1')/'case-037-frame-2-balanced-tree.json.gz'
    with gzip.open(old,'rt') as stream:saved=json.load(stream)
    root=saved['roots'][60];original=certificate['roots'][60]
    common.need(root['root_box_exact']==original['root_box_exact'] and root['base_V5_leaf_locator']==original['base_V5_leaf_locator'],'actual saved original root identity')
    pending=[(0,math.box(original['root_box_exact']))];B=None
    while pending:
        index,box=pending.pop();node=root['nodes'][index]
        common.need(math.box(node['box_exact'])==box,'actual saved path reconstruction')
        if index==671:B=box;break
        if node['kind']=='split':
            axis=node['axis'];cut=F(node['cut_exact']);lo,hi=list(box),list(box)
            common.need(box[axis][0]<cut<box[axis][1],'saved internal split')
            lo[axis],hi[axis]=(box[axis][0],cut),(cut,box[axis][1])
            pending.extend([(node['children'][0],tuple(lo)),(node['children'][1],tuple(hi))])
    common.need(B is not None and node['kind']=='retained','actual saved retained leaf exists')
    targets=[('saved-case037-frame2-root60-node671',row,certificate,models,ids,native,B)]
    for case,frame in [('case-028',1),('case-037',2)]:
        row,certificate,models,ids,native=loader.load(case,frame)
        roots=sorted(enumerate(certificate['roots']),key=lambda x:F(x[1]['root_directed_volume_exact']),reverse=True)[:2]
        for index,root in roots:
            targets.append((case+'-frame'+str(frame)+'-original-root'+str(index),row,certificate,models,ids,native,math.box(root['root_box_exact'])))
    actual=None
    for name,row,certificate,models,ids,native,B in targets:
        D=math.box(row['original_remaining_displacement_box_exact']);sources=certificate['boundary_refinement']['sources']
        stats={'counts':Counter()};tick=time.monotonic()
        proof=producer.evaluate(B,sources,models,D,stats);producer_seconds=time.monotonic()-tick
        counts=Counter();tick=time.monotonic();bound=checker.verify(proof,B,sources,native,D,counts);reader_seconds=time.monotonic()-tick
        common.need(stats['counts']['pieces']==counts['pieces'] and stats['counts']['channels']==counts['channels'],'all prefix and complete tests counted')
        path=args.output/(name+'.json.gz')
        with gzip.open(path,'wt') as stream:json.dump(proof,stream,separators=(',',':'))
        result={'name':name,'case_id':row['case_id'],'frame':row['frame'],'box_exact':math.encbox(B),'D_exact':math.encbox(D),
                'original_inputs':ids,'proof':common.identity(path),'kind':proof['kind'],'bound_exact':str(bound),
                'box_volume_exact':str(common.volume(B)),'counts':stats['counts'],'reader_counts':counts,
                'producer_seconds':producer_seconds,'independent_reader_seconds':reader_seconds,
                'complete_channels':sum(o['scan_mode']=='complete' for o in proof['observations'])}
        report['cases'].append(result);print(json.dumps(result),flush=True)
        if name.startswith('saved-'):actual=(proof,B,sources,native,D,models)
    proof,B,sources,native,D,models=actual
    with gzip.open(Path(__file__).with_name('cylinder-slab-pilot-attempt1')/'actual-cell-certificate.json.gz','rt') as stream:full=json.load(stream)
    common.need(proof['kind']=='cylinder_slab_upper_bound' and F(proof['bound_exact'])==F(full['bound_exact']),'same actual full-channel proof bound')
    controls=[]
    def truncate_selected(item):
        observation=item['observations'][item['cylinder_channel']];length=observation['codes'].index('?')+1
        observation['codes']=observation['codes'][:length];observation['scan_mode']='prefix'
        observation['new_claims']=[x for x in observation['new_claims'] if x['piece_index']<length]
        observation['unresolved_piece_indices']=[length-1]
    mutations=[('use_partial_selected_census',truncate_selected,'selected_channels_have_complete_piece_censuses'),
               ('prefix_given_proof_authority',lambda x:x.__setitem__('candidate_search_is_proof',True),'candidate_selection_has_no_proof_authority'),
               ('drop_required_projection',lambda x:x['slab']['piece_projections'].pop(),'all_unresolved_piece_projections')]
    for name,mutate,expected in mutations:
        altered=copy.deepcopy(proof);mutate(altered);failure=None
        try:checker.verify(altered,B,sources,native,D,Counter())
        except ValueError as exc:failure=str(exc)
        common.need(failure==expected,'specific real-certificate rejection:'+name)
        controls.append({'name':name,'expected':expected,'actual':failure,'passed':True})
    fallback=producer.evaluate(B,sources,[{},{}],D,{'counts':Counter()})
    bound=checker.verify(fallback,B,sources,native,D,Counter())
    common.need(fallback['kind']=='unresolved_full_box' and bound==common.volume(B),'unsupported candidate falls back to full original box')
    controls.append({'name':'unsupported_candidates_full_box_fallback','passed':True,'bound_exact':str(bound)})
    report.update(completed=True,controls=controls,saved_tree=common.identity(old),seconds=time.monotonic()-start,
                  matching_actual_leaf_bound_exact=proof['bound_exact'],input_identities=loader.native_identities)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
