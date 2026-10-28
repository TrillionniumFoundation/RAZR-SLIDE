#!/usr/bin/env python3
"""Read-only independent source-projection audit, not trim mathematics execution."""
import datetime as dt
from fractions import Fraction as Q
import gzip
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
R5=BASE/'r5-envelope'
R4=BASE/'razr-current/engineering/engineering-followup-20261027-r4/envelope'
ORIGINAL=BASE/'recovered-inputs/RAZR-R3E-COMPLETE-SCIENTIFIC-EVIDENCE-20261027/native-and-math/producer/worker/report.json'
OUTPUT=HERE/'R5_V5_INDEPENDENT_SOURCE_PROJECTION_AUDIT.json'
REGISTRATION=HERE/'R5_V5_SOURCE_PROJECTION_REVIEW_BUDGET.json'
checks=0


def need(value,message):
    global checks
    checks+=1
    if not value:raise ValueError(message)


def identity(path):
    with Path(path).open('rb') as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'bytes':Path(path).stat().st_size,'sha256':h}


def canonical(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def selected_rectangle_candidate(wire):
    if wire['is_outer'] or len(wire['edge_occurrences'])!=4:return False
    directions={(Q(1),Q(0)),(Q(-1),Q(0)),(Q(0),Q(1)),(Q(0),Q(-1))}
    for edge in wire['edge_occurrences']:
        pcurve=edge['pcurve']
        if pcurve['type'].rsplit('.',1)[-1]!='GeomAbs_Line':return False
        if tuple(Q(x) for x in pcurve['direction_exact']) not in directions:return False
    return True


def main():
    start=time.monotonic();registration=json.loads(REGISTRATION.read_text())
    report={'schema':'razr-r5-v5-cross-author-source-projection-audit-v1','started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'audit_completed':False,'source_projection_only':True,'V5_worker_or_checker_or_driver_executed':False,'producer_or_checker_code_imported':False,'new_native_operations':0,'new_mathematical_qualification':False,'native_trim_class_membership_verified':False,'full_continuous_G2':False,'all_blockers_closed':False,'materials':[],'frame_bindings':[]}
    def timeout(signum,frame):raise TimeoutError('registered source-only audit wall budget exceeded')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(registration['wall_seconds']);resource.setrlimit(resource.RLIMIT_AS,(registration['address_space_limit_bytes'],registration['address_space_limit_bytes']))
    try:
        need(identity(__file__)==registration['audit_source_identity'],'registered reviewer source changed')
        need(sys.flags.isolated==1 and sys.flags.no_site==1 and sys.flags.optimize==0,'isolated audit entry required')
        report['audit_source_identity']=identity(__file__);report['registration_identity']=identity(REGISTRATION)
        baseline=json.loads((R4/'support-v4/report.json').read_text());bridge=json.loads((R5/'R5E_PUBLIC_INPUT_BRIDGE.json').read_text());bridges={r['path']:r for r in bridge['files']}
        original_id=identity(ORIGINAL)
        old=next(r for r in baseline['input_identities'] if r['path']=='native-and-math/producer/worker/report.json')
        need(original_id=={k:old[k] for k in ('bytes','sha256')}==registration['original_native_inventory_identity'],'original native inventory identity differs')
        need(original_id['bytes']<=registration['maximum_native_inventory_JSON_bytes'],'native inventory readback cap exceeded')
        with ORIGINAL.open() as stream:native=json.load(stream)
        original_by={(r['input']['case_id'],r['input']['material_id']):r for r in native['operands']}
        need(native['execution_completed'] is True and len(original_by)==len(native['operands'])==53,'original inventory complete/unique material set differs')
        projection_path=R5/'R5E_V5_PLANAR_TRIM_SOURCE.json.gz';projection_id=identity(projection_path)
        receipt=json.loads((R5/'R5E_V5_PLANAR_TRIM_SOURCE_RECEIPT.json').read_text())
        need(projection_id==receipt['projected_input']==registration['projection_identity'],'source projection bytes changed')
        with gzip.open(projection_path,'rb') as stream:raw=stream.read(registration['maximum_projection_decoded_bytes']+1)
        need(len(raw)<=registration['maximum_projection_decoded_bytes'] and len(raw)==receipt['uncompressed_JSON_bytes'],'projection decoded size differs')
        projection=json.loads(raw);del raw
        need(projection['original_native_inventory_identity']==original_id==receipt['source'],'projection original source detached')
        need(projection['original_public_R4_report_identity']==identity(R4/'support-v4/report.json'),'original public report binding differs')
        need(projection['native_inventory_was_preexisting_actual_evidence'] is True and projection['new_native_operations']==0 and projection['new_mathematical_qualification'] is False and projection['original_pcurve_values_changed'] is False and projection['native_trim_class_membership_verified'] is False,'projection scope changed')
        need(receipt['mechanical_source_projection_only'] is True and receipt['formal_worker_executed'] is False and receipt['new_geometric_pass_claimed'] is False,'projection receipt invents worker qualification')
        records={(r['input']['case_id'],r['input']['material_id']):r for r in projection['records']}
        need(len(records)==len(projection['records'])==32==receipt['material_records'],'projection material set incomplete/duplicated')
        total_faces=total_wires=0
        for key, projected in records.items():
            source=original_by[key];boundary=source['boundary']
            need(projected['input']==source['input'],'complete original input record changed')
            need(projected['original_complete_boundary_counts']==boundary['counts'] and projected['original_complete_boundary_canonical_sha256']==canonical(boundary),'complete boundary identity/counts changed')
            need(projected['full_original_face_records_unchanged'] is True,'projection lost complete-face scope')
            expected=[]
            for face in boundary['faces']:
                if face['local_surface']['type'].rsplit('.',1)[-1]!='GeomAbs_Plane':continue
                wires=[w['index'] for w in face['wires'] if selected_rectangle_candidate(w)]
                if wires:expected.append((face,wires))
            need([r['face_index'] for r in projected['candidate_faces']]==[f['index'] for f,w in expected],'candidate planar face set omitted/reordered/added')
            face_rows=[]
            for face_row,(original_face,wires) in zip(projected['candidate_faces'],expected):
                need(face_row['complete_original_face']==original_face,'complete original face/pcurve/orientation/location/tolerance fields changed')
                need(face_row['complete_original_face_canonical_sha256']==canonical(original_face),'canonical source face identity changed')
                need(face_row['candidate_inner_wire_indices']==wires,'candidate inner wire membership changed')
                total_faces+=1;total_wires+=len(wires)
                face_rows.append({'face_index':original_face['index'],'candidate_inner_wire_indices':wires,'complete_original_face_canonical_sha256':face_row['complete_original_face_canonical_sha256'],'complete_original_face_equal':True})
            report['materials'].append({'case_id':key[0],'material_id':key[1],'input_identity':{k:source['input'][k] for k in ('bytes','sha256')},'whole_original_boundary_canonical_sha256':projected['original_complete_boundary_canonical_sha256'],'complete_source_faces':face_rows})
        need(total_faces==40==receipt['complete_candidate_faces'] and total_wires==80==receipt['candidate_inner_wires'],'complete projection candidate totals differ')
        expected_frames=[(r['case_id'],r['frame']) for r in baseline['frames']]
        need(len(expected_frames)==16 and [(x['case_id'],x['frame']) for x in projection['frame_bindings']]==expected_frames,'original full frame binding sequence changed')
        used=set();header_bytes=0
        for binding,row in zip(projection['frame_bindings'],baseline['frames']):
            proof_path=R4/'support-v4'/row['proof']['path'];public=bridges['support-v4/'+row['proof']['path']]
            need(identity(proof_path)==public['public_identity'] and public['raw_identity']=={k:row['proof'][k] for k in ('bytes','sha256')},'header source gzip identity mismatch')
            with gzip.open(proof_path,'rb') as stream:head=stream.read(registration['maximum_decoded_header_bytes_per_proof'])
            header_bytes+=len(head)
            marker=b',"complete_raw_boundary_slab_cover":'
            at=head.find(marker);need(at>0,'required input metadata not contained in registered bounded proof header')
            metadata=json.loads(head[:at]+b'}')
            need(metadata['case_id']==row['case_id'] and metadata['frame']==row['frame'] and metadata['original_pair']==row['pair'],'proof header case/frame/material role mismatch')
            keys=[]
            for role in ('moving_input','fixed_input'):
                material=metadata[role];key=(material['case_id'],material['material_id']);keys.append(list(key));used.add(key)
                need(key in records and key in original_by,'bound material absent from complete projection')
                need(all(material[k]==original_by[key]['input'][k] for k in ('case_id','material_id','bytes','sha256','relative_path')),'proof whole material identity differs from native inventory')
            need(binding['moving_and_fixed_material_keys']==keys,'moving/fixed material mapping reversed or replaced')
            need(binding['original_full_D']==metadata['full_remaining_displacement_box_exact']==row['full_remaining_displacement_box_exact'],'original full D changed')
            need(binding['original_R4_raw_proof_identity']==row['proof'],'original raw proof identity lost')
            report['frame_bindings'].append({'case_id':row['case_id'],'frame':row['frame'],'pair':row['pair'],'moving_and_fixed_material_keys':keys,'full_original_D':binding['original_full_D'],'public_proof_identity':public['public_identity'],'bounded_decoded_header_bytes_read':len(head),'original_raw_proof_identity':row['proof']})
        need(used==set(records),'projection has omitted/extra material relative to all16 source frames')
        report['source_inputs']={'original_inventory':original_id,'original_public_R4_report':identity(R4/'support-v4/report.json'),'projection':projection_id,'projection_receipt':identity(R5/'R5E_V5_PLANAR_TRIM_SOURCE_RECEIPT.json'),'projection_builder_source':identity(R5/'prepare_trim_source_projection_r5e_v5.py')}
        report['result']={'original_inventory_materials':53,'projected_frame_materials':32,'complete_candidate_faces':total_faces,'candidate_inner_wires':total_wires,'original_frame_bindings':16,'complete_face_field_equality_checks':total_faces,'original_proof_headers_decoded':16,'total_decoded_header_bytes_read':header_bytes,'full_R4_support_proofs_decoded':0,'V5_mathematical_controls_executed':0,'candidate_wire_classification_is_not_rectangle_or_native_trim_validity_proof':True,'source_projection_is_lossless_for_all_selected_complete_faces':True}
        report['audit_completed']=True
    except BaseException as exc:report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0);report['finished_utc']=dt.datetime.now(dt.timezone.utc).isoformat();report['audit_seconds']=time.monotonic()-start;report['audit_peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024;report['checks']=checks
        report['registered_budget_respected']=report['audit_seconds']<=registration['wall_seconds'] and report['audit_peak_RSS_bytes']<=registration['RSS_limit_bytes']
        data=(json.dumps(report,indent=2)+'\n').encode();need(len(data)<=registration['maximum_output_bytes'],'source audit output budget exceeded');OUTPUT.write_bytes(data)
        print(json.dumps({k:report.get(k) for k in ('audit_completed','audit_seconds','audit_peak_RSS_bytes','registered_budget_respected','result','failure')}))
    return 0 if report['audit_completed'] and report['registered_budget_respected'] else 2


if __name__=='__main__':raise SystemExit(main())
