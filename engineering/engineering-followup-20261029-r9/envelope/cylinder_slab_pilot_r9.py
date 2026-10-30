"""Actual retained-cell pilot with independent channel and bound readback."""
import argparse
from collections import Counter
import copy
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import sys
import time
import cylinder_slab_r9 as producer
import check_cylinder_slab_r9 as checker

R8=Path(__file__).resolve().parents[2]/'engineering-followup-20261029-r8/envelope'
sys.path.insert(0,str(R8))
import run_original_depth24_r8 as common
import source_quadric_r8 as math


def main():
    p=argparse.ArgumentParser();p.add_argument('--originals',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    row,cert,models,ids,native=common.load_inputs(args.originals,'case-037',2)
    old=Path(__file__).with_name('balanced-all16-attempt1')/'case-037-frame-2-balanced-tree.json.gz'
    saved=json.loads(gzip.decompress(old.read_bytes()));root=saved['roots'][60];node=root['nodes'][671]
    common.need(node['kind']=='retained','actual retained node');B=math.box(node['box_exact']);D=math.box(row['original_remaining_displacement_box_exact']);sources=cert['boundary_refinement']['sources']
    report={'schema':'razr-r9-cylinder-slab-pilot','source':common.identity(__file__),'producer':common.identity(producer.__file__),'checker':common.identity(checker.__file__),
            'original_inputs':ids,'saved_tree':common.identity(old),'box_exact':node['box_exact'],'D_exact':row['original_remaining_displacement_box_exact'],
            'counts':Counter(),'functional_pass':False,'scope':{'conditional_source_model_only':True,'native_error_bound_verified':False,'full_continuous_G2':False}}
    result=producer.evaluate(B,sources,models,D,report)
    checked_counts=Counter();bound=checker.verify(result,B,sources,native,D,checked_counts)
    common.need(report['counts']['pieces']==checked_counts['pieces'] and report['counts']['channels']==checked_counts['channels'],'independent full accounting')
    controls=[]
    mutations=[('drop_original_displacement',lambda x:x['cylinder'].__setitem__('source_shift_exact',[['0','0']]*3),'full_cylinder_displacement'),
               ('remove_boundary_projection',lambda x:x['slab']['piece_projections'].pop(),'all_unresolved_piece_projections'),
               ('lower_unsupported_radical',lambda x:x['combination'].__setitem__('support_sqrt_upper_exact','0'),'outward_support_square_root'),
               ('reduce_positive_volume_bound',lambda x:x['combination'].__setitem__('bound_exact','0'),'conservative_positive_volume_bound'),
               ('reverse_outward_direction',lambda x:x['cylinder'].__setitem__('outward_direction',-x['cylinder']['outward_direction']),'exact_outward_cylinder_derivative'),
               ('use_one_material_twice',lambda x:x.__setitem__('slab_channel',x['cylinder_channel']),'two_distinct_materials')]
    for name,change,expected in mutations:
        mutated=copy.deepcopy(result);change(mutated);failure=None
        try:checker.verify(mutated,B,sources,native,D,Counter())
        except ValueError as e:failure=str(e)
        common.need(failure==expected,'specific mutation rejection:'+name)
        controls.append({'name':name,'expected':expected,'actual':failure,'passed':True})
    path=args.output/'actual-cell-certificate.json.gz'
    with gzip.open(path,'wt') as f:json.dump(result,f,separators=(',',':'))
    report.update(functional_pass=True,actual_bound_exact=str(bound),actual_bound_display_mm3=float(bound),original_cell_volume_exact=str(common.volume(B)),
                  independent_counts=checked_counts,certificate=common.identity(path),mutation_controls=controls,seconds=time.monotonic()-start)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'bound':float(bound),'old_volume':float(common.volume(B)),'counts':report['counts'],'seconds':report['seconds'],'controls':len(controls)}))


if __name__=='__main__':main()
