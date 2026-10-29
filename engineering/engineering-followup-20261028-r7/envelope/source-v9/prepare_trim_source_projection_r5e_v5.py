"""Lossless source selection only; no new native or mathematical qualification.

Copies complete candidate planar faces from the original native inventory,
retaining every original pcurve, parameter, orientation, location and tolerance.
"""
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import time


def ident(path):
    with path.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
    return {'bytes':path.stat().st_size,'sha256':h}


def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def candidate(wire):
    if wire['is_outer'] or len(wire['edge_occurrences'])!=4:return False
    for edge in wire['edge_occurrences']:
        curve=edge['pcurve']
        if not curve['type'].endswith('GeomAbs_Line'):return False
        if tuple(map(F,curve['direction_exact'])) not in [(F(1),F(0)),(F(-1),F(0)),(F(0),F(1)),(F(0),F(-1))]:return False
    return True


def main():
    root=Path(__file__).resolve().parent;workspace=root.parent;start=time.monotonic()
    original=workspace/'recovered-inputs/RAZR-R3E-COMPLETE-SCIENTIFIC-EVIDENCE-20261027/native-and-math/producer/worker/report.json'
    r4=workspace/'razr-current/engineering/engineering-followup-20261027-r4/envelope'
    r4_report=json.loads((r4/'support-v4/report.json').read_text())
    expected=next(x for x in r4_report['input_identities'] if x['path']=='native-and-math/producer/worker/report.json')
    if ident(original)!={k:expected[k] for k in ['bytes','sha256']}:raise ValueError('original native inventory identity differs')
    native=json.loads(original.read_text());by={(r['input']['case_id'],r['input']['material_id']):r for r in native['operands']}
    if not native['execution_completed'] or len(by)!=53:raise ValueError('original complete inventory not qualified')
    records={};bindings=[]
    for row in r4_report['frames']:
        with gzip.open(r4/'support-v4'/row['proof']['path'],'rt') as f:proof=json.load(f)
        materials=[]
        for label in ['moving_input','fixed_input']:
            inp=proof[label];key=(inp['case_id'],inp['material_id']);source=by[key]
            if source['input']['sha256']!=inp['sha256']:raise ValueError('actual whole material identity differs')
            materials.append(list(key))
            if key in records:continue
            boundary=source['boundary'];faces=[]
            for face in boundary['faces']:
                if not face['local_surface']['type'].endswith('GeomAbs_Plane'):continue
                eligible=[wire['index'] for wire in face['wires'] if candidate(wire)]
                if eligible:faces.append({'face_index':face['index'],'candidate_inner_wire_indices':eligible,'complete_original_face':face,'complete_original_face_canonical_sha256':canonical(face)})
            records[key]={'input':source['input'],'original_complete_boundary_counts':boundary['counts'],
                          'original_complete_boundary_canonical_sha256':canonical(boundary),
                          'candidate_faces':faces,'full_original_face_records_unchanged':True}
        bindings.append({'case_id':row['case_id'],'frame':row['frame'],'moving_and_fixed_material_keys':materials,
                         'original_full_D':row['full_remaining_displacement_box_exact'],'original_R4_raw_proof_identity':row['proof']})
    output={'schema':'razr-r5e-original-planar-trim-source-projection-v5','original_native_inventory_identity':{k:expected[k] for k in ['bytes','sha256']},
            'original_native_inventory_relative_path':expected['path'],'original_public_R4_report_identity':ident(r4/'support-v4/report.json'),
            'native_inventory_was_preexisting_actual_evidence':True,'new_native_operations':0,'new_mathematical_qualification':False,
            'original_pcurve_values_changed':False,'native_trim_class_membership_verified':False,
            'records':list(records.values()),'frame_bindings':bindings}
    path=root/'R5E_V5_PLANAR_TRIM_SOURCE.json.gz'
    if path.exists():raise ValueError('new source projection name required')
    raw=(json.dumps(output,sort_keys=True,separators=(',',':'))+'\n').encode()
    with path.open('wb') as f:
        with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z:z.write(raw)
    receipt={'schema':'razr-r5e-trim-source-projection-receipt-v5','source':ident(original),'projected_input':ident(path),
             'uncompressed_JSON_bytes':len(raw),'material_records':len(records),'complete_candidate_faces':sum(len(r['candidate_faces']) for r in records.values()),
             'candidate_inner_wires':sum(len(f['candidate_inner_wire_indices']) for r in records.values() for f in r['candidate_faces']),
             'cases':[{'case_id':r['input']['case_id'],'material_id':r['input']['material_id'],'candidate_faces':[f['face_index'] for f in r['candidate_faces']]} for r in records.values()],
             'mechanical_source_projection_only':True,'formal_worker_executed':False,'new_geometric_pass_claimed':False,'seconds':time.monotonic()-start}
    (root/'R5E_V5_PLANAR_TRIM_SOURCE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
