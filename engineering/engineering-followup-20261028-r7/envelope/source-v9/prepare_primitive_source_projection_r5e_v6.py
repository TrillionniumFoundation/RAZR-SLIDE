"""Lossless actual-source selection; does not execute V6 geometry or controls."""
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import resource
import time


def need(ok,message):
    if not ok:raise ValueError(message)


def identity(path):
    with path.open('rb') as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'bytes':path.stat().st_size,'sha256':h}


def canonical(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def exact_leaf_box(root,node_id):
    pending=[(0,[list(pair) for pair in root['root_box_exact']])]
    while pending:
        index,box=pending.pop();node=root['tree']['nodes'][index]
        if index==node_id:return box
        if node['kind']=='split':
            low=[v[:] for v in box];high=[v[:] for v in box]
            low[node['axis']][1]=high[node['axis']][0]=node['cut_exact']
            pending.extend([(node['children'][1],high),(node['children'][0],low)])
    raise ValueError('selected actual leaf is absent')


def main():
    root=Path(__file__).resolve().parent;workspace=root.parent;started=time.monotonic()
    native_path=workspace/'recovered-inputs/RAZR-R3E-COMPLETE-SCIENTIFIC-EVIDENCE-20261027/native-and-math/producer/worker/report.json'
    r4_path=workspace/'r4-envelope/public-final-v2/support-v4/report.json'
    actual=workspace/'r5-ci-results/run-40645988108'
    r4=json.loads(r4_path.read_text());report=json.loads((actual/'all-trim-model-frames/report.json').read_text())
    independent=json.loads((actual/'verify-all/report.json').read_text());pipeline=json.loads((actual/'pipeline.json').read_text())
    need(report['execution_completed'] and independent['execution_completed'] and pipeline['completed'],'actual V5 completion is required')
    need(report['trim_model_conditional_clearance_passes']==independent['trim_model_conditional_clearance_passes']==8,'original actual V5 count differs')
    need(pipeline['source_lock_identity']['sha256']=='d05a6f6a69ac5eb627d3d1180ff543c4f9b70c7c424c972dfab2b305b8a21211','actual V5 source lock differs')
    need(pipeline['environment']['github_sha']=='2ce252f25d340b056bfd350bdde8c743f915c9a4','actual V5 request commit differs')
    expected=next(r for r in r4['input_identities'] if r['path']=='native-and-math/producer/worker/report.json')
    need(identity(native_path)=={k:expected[k] for k in ('bytes','sha256')},'original inventory identity differs')
    native=json.loads(native_path.read_text());by={(r['input']['case_id'],r['input']['material_id']):r for r in native['operands']}
    need(native['execution_completed'] and len(by)==53,'complete original native inventory required')
    with gzip.open(root/'R5E_V5_PLANAR_TRIM_SOURCE.json.gz','rt') as stream:v5_source=json.load(stream)
    need(identity(root/'R5E_V5_PLANAR_TRIM_SOURCE.json.gz')['sha256']=='bc778c13f9efbc280bcb93e59edbc821d2a7b751f0b8730231d1b0bd855e2804','frozen V5 source projection differs')
    bindings={(f['case_id'],f['frame']):f for f in v5_source['frame_bindings']}
    need([(f['case_id'],f['frame']) for f in report['frames']]==[(f['case_id'],f['frame']) for f in r4['frames']],'actual full16 order differs')
    target_faces={};frame_bindings=[];retained_total=non_tiny_total=0;selected=None
    file_paths=['pipeline.json','all-trim-model-frames/report.json','verify-all/report.json',
        'all-trim-model-frames-supervision/controller.json','verify-all-supervision/controller.json',
        'all-trim-model-frames-contract.json','all-trim-model-frames-supervision-contract.json',
        'verify-all-contract.json','verify-all-supervision-contract.json']
    for frame in report['frames']:
        key=(frame['case_id'],frame['frame']);binding=bindings[key]
        relative='all-trim-model-frames/'+frame['certificate']['path'];file_paths.append(relative)
        need(identity(actual/relative)=={k:frame['certificate'][k] for k in ('bytes','sha256')},'actual V5 certificate identity differs')
        with gzip.open(actual/relative,'rt') as stream:certificate=json.load(stream)
        need(certificate['frame']=={k:v for k,v in frame.items() if k!='certificate'},'actual V5 certificate header differs')
        need(binding['original_full_D']==frame['original_remaining_displacement_box_exact'] and binding['original_R4_raw_proof_identity']==frame['original_raw_proof_identity'],
             'original full D/raw source identity differs')
        leaf_ids=[];non_tiny=[]
        for tree_root in certificate['roots']:
            for node in tree_root['tree']['nodes']:
                if node['kind']!='retained':continue
                retained_total+=1;locator=[tree_root['original_cell_index'],node['id']];leaf_ids.append(locator)
                if F(node['positive_directed_volume_exact'])<=F(1e-7)/100000:continue
                non_tiny_total+=1;non_tiny.append(locator)
                need(not frame['trim_model_conditional_clearance_gate_passed'] and node['reason']=='no_registered_model_boundary_endpoint_inside_cell',
                     'registered actual non-tiny remainder class differs')
                for obstruction in node['actual_channel_observation']['all_registered_channels_blocked']:
                    side=obstruction['material_side'];piece=certificate['boundary_refinement']['sources'][side]['pieces'][obstruction['blocking_piece_index']]
                    need(piece['kind']=='face' and piece['replacement']=='unchanged','actual blocker is not an unchanged original face')
                    material=tuple(binding['moving_and_fixed_material_keys'][side]);target_faces.setdefault(material,set()).add(piece['index'])
                if key==('case-028',1) and locator==[8,13]:
                    selected={'schema':'razr-r5e-actual-v5-retained-leaf-selection-v6','case_id':key[0],'frame':key[1],
                        'pair':frame['pair'],'original_R4_root_index':8,'actual_V5_leaf_node_index':13,
                        'actual_V5_leaf_record':node,'actual_V5_original_root_record':tree_root,
                        'leaf_box_exact':exact_leaf_box(tree_root,13),'positive_directed_volume_exact':node['positive_directed_volume_exact'],
                        'original_full_D':frame['original_remaining_displacement_box_exact'],
                        'actual_V5_certificate':dict(identity(actual/relative),path=relative),
                        'actual_V5_report':dict(identity(actual/'all-trim-model-frames/report.json'),path='all-trim-model-frames/report.json'),
                        'actual_V5_run_id':40645988108,'actual_V5_request_commit':pipeline['environment']['github_sha'],
                        'new_geometric_pass_claimed':False,'original_source_values_changed':False}
        frame_bindings.append(dict(binding,actual_V5_certificate=dict(identity(actual/relative),path=relative),
                                   actual_V5_retained_leaf_locators=leaf_ids,actual_V5_non_tiny_retained_leaf_locators=non_tiny))
    need(selected is not None and retained_total==1537 and non_tiny_total==44,'registered V5 retained-leaf inventory differs')
    records=[];planes=cylinders=0
    for old in v5_source['records']:
        material=(old['input']['case_id'],old['input']['material_id']);source=by[material]
        need(source['input']==old['input'],'complete original material identity differs')
        candidates=[]
        for index in sorted(target_faces.get(material,set())):
            face=source['boundary']['faces'][index];kind=face['local_surface']['type'].split('.')[-1]
            need(face['index']==index and kind in ('GeomAbs_Plane','GeomAbs_Cylinder'),'actual blocker outside registered primitive class')
            planes+=kind=='GeomAbs_Plane';cylinders+=kind=='GeomAbs_Cylinder'
            candidates.append({'face_index':index,'source_primitive':kind,'complete_original_face':face,
                'complete_original_face_canonical_sha256':canonical(face),
                'selection_basis':'actual first blocking piece of an original V5 non-tiny retained leaf'})
        records.append({'input':source['input'],'original_complete_boundary_counts':source['boundary']['counts'],
            'original_complete_boundary_canonical_sha256':canonical(source['boundary']),
            'candidate_faces':candidates,'full_original_face_records_unchanged':True})
    need(planes==48 and cylinders==16 and len(records)==32,'registered actual primitive source census differs')
    projection={'schema':'razr-r5e-original-primitive-source-projection-v6',
        'original_native_inventory_identity':{k:expected[k] for k in ('bytes','sha256')},
        'original_native_inventory_relative_path':expected['path'],'original_public_R4_report_identity':identity(r4_path),
        'actual_V5_run_id':40645988108,'actual_V5_request_commit':pipeline['environment']['github_sha'],
        'actual_V5_report_identity':identity(actual/'all-trim-model-frames/report.json'),
        'records':records,'frame_bindings':frame_bindings,'native_inventory_was_preexisting_actual_evidence':True,
        'new_native_operations':0,'new_mathematical_qualification':False,'original_pcurve_values_changed':False,
        'native_primitive_semantics_verified':False,'native_trim_class_membership_verified':False}
    destinations=[root/'R5E_V6_PRIMITIVE_SOURCE.json.gz',root/'R5E_V6_REAL_RETAINED_LEAF.json',root/'R5E_V6_BASE_V5_INPUT_BRIDGE.json',root/'R5E_V6_PRIMITIVE_SOURCE_RECEIPT.json']
    need(not any(p.exists() for p in destinations),'new projection output names required')
    decoded=(json.dumps(projection,sort_keys=True,separators=(',',':'))+'\n').encode()
    with destinations[0].open('wb') as raw:
        with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as stream:stream.write(decoded)
    destinations[1].write_text(json.dumps(selected,indent=2)+'\n')
    bridge={'schema':'razr-r5e-immutable-actual-v5-public-input-bridge-v6','actual_run_id':40645988108,
        'actual_request_commit':pipeline['environment']['github_sha'],
        'public_repository_relative_root':'engineering/engineering-followup-20261028-r5/envelope/actions/run-40645988108',
        'original_reports_or_certificates_edited':False,'path_mapping_only':True,
        'files':[dict(identity(actual/name),path=name) for name in file_paths]}
    destinations[2].write_text(json.dumps(bridge,indent=2)+'\n')
    receipt={'schema':'razr-r5e-v6-primitive-source-projection-receipt','source_inventory':identity(native_path),
        'outputs':[dict(identity(p),path=p.name) for p in destinations[:3]],'decoded_projection_bytes':len(decoded),
        'complete_material_records':32,'complete_plane_records':planes,'complete_cylinder_records':cylinders,
        'actual_V5_retained_leaves':retained_total,'actual_V5_non_tiny_retained_leaves':non_tiny_total,
        'actual_V5_tiny_retained_leaves':retained_total-non_tiny_total,'mechanical_source_projection_only':True,
        'formal_worker_executed':False,'new_geometric_pass_claimed':False,'seconds':time.monotonic()-started,
        'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    destinations[3].write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
