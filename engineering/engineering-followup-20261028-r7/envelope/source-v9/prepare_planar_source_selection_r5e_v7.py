"""Bind a real V6 retained leaf and immutable archive; no new geometry run."""
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import resource
import signal
import time

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
ACTUAL = ROOT / 'r5-local-v6/attempt-1'
started = time.monotonic()
signal.signal(signal.SIGALRM, lambda n,f: (_ for _ in ()).throw(TimeoutError('90-second source-only preparation budget')))
signal.alarm(90)
resource.setrlimit(resource.RLIMIT_AS, (402653184,402653184))


def ident(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream,'sha256').hexdigest()
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':digest}


def equal(a,b): return all(a[k] == b[k] for k in ('bytes','sha256'))
def read(path): return json.loads(Path(path).read_text())
def bounded_gzip(path, maximum):
    with gzip.open(path,'rb') as stream:
        data = stream.read(maximum+1)
    assert len(data) <= maximum
    return json.loads(data)


outputs = [HERE/name for name in ('R5E_V7_BASE_V6_INPUT_BRIDGE.json','R5E_V7_REAL_RETAINED_LEAF.json','R5E_V7_STATIC_SOURCE_CAPACITY.json','R5E_V7_SOURCE_PREPARATION_RECEIPT.json')]
assert not any(p.exists() for p in outputs), 'Preserve frozen source-selection outputs'
pipeline = read(ACTUAL/'pipeline.json')
producer = read(ACTUAL/'all-primitive-support-frames/report.json')
checker = read(ACTUAL/'verify-all/report.json')
manifest_path = ROOT/'r5-local-v6/R5_V6_LOCAL_ACTUAL_OUTPUT_MANIFEST.json'
manifest = read(manifest_path)
assert pipeline['completed'] and producer['execution_completed'] and checker['execution_completed']
assert producer['primitive_support_model_conditional_clearance_passes'] == checker['primitive_support_model_conditional_clearance_passes'] == 8
assert pipeline['source_lock_identity']['sha256'] == '5cf2c18e7971912949e7e7167451cf547e291be421f205d78ef668fd7ab5b499'
rows = []
for row in manifest['files']:
    path = ACTUAL/row['path']; actual = ident(path); assert equal(actual,row)
    rows.append(dict(actual,path=row['path']))
assert len(rows) == 53 and len({r['path'] for r in rows}) == 53
bridge = {'schema':'razr-r5e-immutable-actual-v6-input-bridge-v7',
          'actual_execution_kind':'local_owned_pipeline','actual_pipeline_source_lock_sha256':pipeline['source_lock_identity']['sha256'],
          'actual_pipeline_identity':dict(ident(ACTUAL/'pipeline.json'),path='pipeline.json'),
          'actual_complete_output_manifest':ident(manifest_path),
          'public_repository_relative_root':'engineering/engineering-followup-20261028-r5/envelope/local/attempt-v6-1',
          'files':rows,'original_reports_or_certificates_edited':False,'path_mapping_only':True,
          'actual_GitHub_run_claimed':False,'source_V6_passes':8,'source_V6_frames':16}
frame = next(r for r in producer['frames'] if (r['case_id'],r['frame']) == ('case-028',1))
certificate_path = ACTUAL/'all-primitive-support-frames'/frame['certificate']['path']
assert equal(ident(certificate_path),frame['certificate'])
certificate = bounded_gzip(certificate_path,67108864)
root_index = 76; node_index = 47
root = certificate['roots'][root_index]
pending = [(0,root['root_box_exact'],0)]; found = None
while pending:
    index, cell, depth = pending.pop(); node = root['tree']['nodes'][index]
    if index == node_index:
        found = (cell,depth,node); break
    if node['kind'] == 'split':
        a = node['axis']; cut = node['cut_exact']; low = [list(p) for p in cell]; high = [list(p) for p in cell]
        low[a][1] = cut; high[a][0] = cut
        pending.extend([(node['children'][0],low,depth+1),(node['children'][1],high,depth+1)])
assert found is not None
cell, depth, node = found
assert depth == 24 and node['kind'] == 'retained' and node['reason'] == 'path_depth_limit_retained'
volume = F(1)
for low,high in cell:
    volume *= F(high)-F(low)
assert volume == F(node['positive_directed_volume_exact']) and volume > F(1e-7)
selection = {'schema':'razr-r5e-actual-v6-retained-leaf-selection-v7','case_id':'case-028','frame':1,
             'V6_root_index':root_index,'V6_node_index':node_index,'base_V5_leaf_locator':root['base_V5_leaf_locator'],
             'actual_V6_root_record_canonical_sha256':hashlib.sha256(json.dumps(root,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
             'actual_V6_leaf_record':node,'actual_leaf_box_exact':cell,'actual_leaf_depth':depth,
             'positive_directed_volume_exact':str(volume),'positive_directed_volume_mm3':float(volume),
             'whole_pair':frame['pair'],'original_full_D':frame['original_remaining_displacement_box_exact'],
             'actual_V6_certificate':dict(ident(certificate_path),path='all-primitive-support-frames/'+frame['certificate']['path']),
             'actual_V6_report':dict(ident(ACTUAL/'all-primitive-support-frames/report.json'),path='all-primitive-support-frames/report.json'),
             'actual_V6_independent_report':dict(ident(ACTUAL/'verify-all/report.json'),path='verify-all/report.json'),
             'actual_V6_pipeline':bridge['actual_pipeline_identity'],'no_new_geometry_execution':True}
del certificate, root
projection_path = HERE/'R5E_V6_PRIMITIVE_SOURCE.json.gz'
projection = bounded_gzip(projection_path,8388608)
planes = [c for r in projection['records'] for c in r['candidate_faces'] if c['source_primitive'] == 'GeomAbs_Plane']
curves = Counter(o['pcurve']['type'].split('.')[-1] for c in planes for w in c['complete_original_face']['wires'] for o in w['edge_occurrences'])
assert len(planes) == 48 and curves == {'GeomAbs_Line':472,'GeomAbs_Circle':48}
retained = checker['total_new_positive_leaves_verified']-checker['total_actual_new_excluded_leaves_verified']
assert retained == 4943
capacity = {'schema':'razr-r5e-v7-static-source-capacity','original_source_projection':ident(projection_path),
            'original_projection_materials':len(projection['records']),'plane_occurrences':48,'wire_count':48,
            'Line_occurrences':472,'Circle_occurrences':48,'source_edge_occurrences':520,
            'fixed_circle_angular_patches':64,'maximum_total_UV_pieces':472+48*64+520,
            'maximum_UV_pieces_per_face':225,'actual_V6_retained_roots':retained,
            'maximum_new_splits':4096,'maximum_depth':24,'maximum_new_forest_nodes':retained+2*4096,
            'maximum_new_forest_leaves':retained+4096,'maximum_combined_boundary_piece_tests':12000000,
            'maximum_combined_support_inequality_tests':12000000,'original_float64_TOL_unchanged':True,
            'new_primitive_or_planar_enclosures_computed':False,'new_channel_search_executions':0,
            'new_mathematical_qualification':False,'larger_run_requires_actual_selected_leaf_and_independent_pass':True,
            'full_run_requires_actual_all16_preflight':True}
for path,value in zip(outputs[:3],(bridge,selection,capacity)):
    path.write_text(json.dumps(value,indent=2)+'\n')
assert all(equal(ident(ACTUAL/r['path']),r) for r in rows)
receipt = {'schema':'razr-r5e-v7-source-only-preparation-receipt','source':ident(__file__),
           'created_utc':datetime.now(timezone.utc).isoformat(),'source_V6_manifest':ident(manifest_path),
           'outputs':[ident(p) for p in outputs[:3]],'runtime_seconds':time.monotonic()-started,
           'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
           'budget_wall_seconds':90,'budget_address_space_bytes':402653184,
           'new_planar_enclosure_or_geometric_search_executions':0,'native_operations':0,'new_mathematical_qualification':False}
outputs[3].write_text(json.dumps(receipt,indent=2)+'\n')
signal.alarm(0)
print(json.dumps({'source_files':len(rows),'selected_V6_locator':[root_index,node_index],'retained_roots':retained,
                  'runtime_seconds':receipt['runtime_seconds'],'peak_RSS_bytes':receipt['peak_RSS_bytes']}))
