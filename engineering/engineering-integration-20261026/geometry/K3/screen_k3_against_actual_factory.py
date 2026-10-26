"""Byte-bound AABB placement screen against an actual complete K2 factory.

A nonseparating AABB is a pending native Common, not a collision proof.
This performs no CAD, contact, material-join, or allowed-domain qualification.
"""
from fractions import Fraction as F
from pathlib import Path
import argparse
import hashlib
import io
import json
import sys
import urllib.request
import zipfile


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inspection',type=Path,required=True);ap.add_argument('--contract',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();req=json.load(sys.stdin)
    evidence=json.loads(a.inspection.read_text());assert evidence['finite_endpoint_complete']
    meta=req['artifact'];assert meta['id']==evidence['artifact_id'] and meta['digest']=='sha256:'+evidence['official_ZIP_sha256']
    with urllib.request.urlopen(req['file_uri'],timeout=90) as stream:data=stream.read(evidence['official_ZIP_bytes']+1)
    assert len(data)==evidence['official_ZIP_bytes'] and sha(data)==evidence['official_ZIP_sha256']
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        mb=z.read('ENGINEERING_MANIFEST.json');assert sha(mb)==evidence['engineering_manifest_sha256']
        manifest=json.loads(mb);rp=z.read('factory/worker/report.engineering.json')
        assert sha(rp)==evidence['results']['factory']['projection_sha256']
        wrapper=json.loads(rp);r=wrapper['engineering_record']
        assert r['execution_completed'] and r['finite_pose_clear'] and len(r['body_exports'])==evidence['expected_participant_count']
        c=json.loads(a.contract.read_text())['design_contract'];pieces={}
        for side in 'LR':
            for role,(low,high) in c['additive_boxes_R_mm'].items():
                lo,hi=list(low),list(high)
                if side=='L':lo[0],hi[0]=-hi[0],-lo[0]
                pieces[side+'_'+role]=[v for pair in zip(lo,hi) for v in pair]
        bodies={name:entry['signature_before'] for name,entry in r['body_exports'].items()}
        rows=[]
        for name,bounds in pieces.items():
            aa=list(map(F,bounds))
            for role,sig in sorted(bodies.items()):
                bb=list(map(F,sig['bounds_mm']))
                gaps=[max(aa[2*i]-bb[2*i+1],bb[2*i]-aa[2*i+1]) for i in range(3)]
                gap=max(gaps)
                rows.append({'proposed_component':name,'existing_participant':role,
                    'exact_binary64_recorded_AABB_axis_gaps_mm':list(map(str,gaps)),
                    'recorded_AABB_has_positive_axis_gap':gap>0,
                    'requires_native_whole_material_Common':gap<=0})
        pending=[{'proposed_component':x['proposed_component'],'existing_participant':x['existing_participant']} for x in rows if x['requires_native_whole_material_Common']]
        report={'schema':'razr-K3-actual-K2-factory-AABB-placement-screen-v1',
            'actual_source_run_id':evidence['run_id'],'actual_source_head_sha':evidence['head_sha'],
            'actual_pose':evidence['pose'],'actual_artifact_id':evidence['artifact_id'],
            'actual_ZIP_sha256':sha(data),'actual_factory_projection_sha256':sha(rp),
            'actual_original_factory_report_sha256':wrapper['original']['sha256'],
            'actual_participant_count':len(bodies),'original_actual_pose_input':r['pose_input'],
            'proposed_K3_contract_sha256':sha(a.contract.read_bytes()),
            'current_K3_source_sha256':json.loads(a.contract.read_text())['candidate_source_sha256'],
            'all_actual_body_signature_records':bodies,'proposed_component_bounds_mm':pieces,
            'all_component_to_participant_rows':rows,'total_AABB_rows':len(rows),
            'recorded_AABB_separated_count':len(rows)-len(pending),'pending_native_Common_pairs':pending,
            'existing_material_bounds_remeasured_by_this_script':False,
            'native_K3_geometry_or_boolean_executed':False,
            'native_endpoint_contact_or_join_proved':False,
            'positive_AABB_gap_is_screen_only_not_new_full_CAD_clearance_certificate':True,
            'whole_candidate_factory_all_pairs_complete':False,
            'physical_allowed_domain_proved':False,'strength_qualified':False,'candidate_go':False}
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'pose':evidence['pose'],'total_AABB_rows':len(rows),
            'recorded_AABB_separated_count':len(rows)-len(pending),'pending_native_Common_pairs':pending,
            'native_K3_execution':False},indent=2))


if __name__=='__main__':main()
