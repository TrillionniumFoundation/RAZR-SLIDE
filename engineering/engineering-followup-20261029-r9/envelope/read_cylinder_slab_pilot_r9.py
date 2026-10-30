"""Separate-process readback of the actual pilot with source-identity controls."""
import argparse
from collections import Counter
import copy
import gzip
import json
from pathlib import Path
import sys
import time
import check_cylinder_slab_r9_v2 as checker

R8=Path(__file__).resolve().parents[2]/'engineering-followup-20261029-r8/independent-review'
sys.path.insert(0,str(R8))
from read_all16_actual_r8 import read_all_materials
from read_depth24_actual_r8 import identity,need


def main():
    p=argparse.ArgumentParser();p.add_argument('--originals',type=Path,required=True);p.add_argument('--pilot-report',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();start=time.monotonic();report=json.loads(args.pilot_report.read_text())
    need(report['functional_pass'],'actual_pilot_passed')
    certpath=Path(report['original_inputs'][3]['path']);need(identity(certpath)==report['original_inputs'][3],'original_complete_certificate_identity')
    with gzip.open(certpath,'rt') as f:certificate=json.load(f)
    sources=certificate['boundary_refinement']['sources'];materials,ids=read_all_materials(args.originals,set(tuple(s['material_key']) for s in sources))
    proofpath=args.pilot_report.parent/Path(report['certificate']['path']).name
    need(identity(proofpath)==report['certificate'],'pilot_certificate_identity')
    with gzip.open(proofpath,'rt') as f:proof=json.load(f)
    B,D=checker.math.bounds(report['box_exact']),checker.math.bounds(report['D_exact']);counts=Counter();bound=checker.verify(proof,B,sources,materials,D,counts)
    ci=proof['cylinder_channel'];obs=proof['observations'][ci];source=sources[obs['material_side']];material=materials[tuple(source['material_key'])]
    altered=copy.deepcopy(material);index=source['pieces'][proof['cylinder']['piece_index']]['index']
    altered['boundary']['faces'][index]['native_global_surface']['origin_exact'][0]='0'
    failure=None
    try:checker.verify_cylinder(proof['cylinder'],obs,source,altered,D)
    except ValueError as e:failure=str(e)
    need(failure=='cylinder_local_global_source_identity','actual_local_global_source_mismatch_rejected')
    out={'schema':'razr-r9-cylinder-slab-pilot-independent-process-v2','completed':True,
         'source':identity(__file__),'checker':identity(checker.__file__),'pilot_report':identity(args.pilot_report),
         'original_material_inventories':ids,'bound_exact':str(bound),'bound_display_mm3':float(bound),
         'complete_channel_count':counts['channels'],'complete_piece_count':counts['pieces'],
         'actual_source_mutation':{'name':'mismatched_native_global_cylinder','rejection':failure,'passed':True},
         'seconds':time.monotonic()-start,'producer_imported':False,'native_BREP_membership_qualified':False}
    args.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'completed':True,'bound':float(bound),'seconds':out['seconds']}))


if __name__=='__main__':main()
