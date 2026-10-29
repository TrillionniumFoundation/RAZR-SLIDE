"""Cross-author static review only; does not import or execute the checker."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import signal
import time

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
SRC = ROOT / 'source-v9'
started = time.monotonic()
resource.setrlimit(resource.RLIMIT_AS, (134217728, 134217728))
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('30-second static review budget')))
signal.alarm(30)
checks = []


def need(ok, label):
    if not ok:
        raise ValueError(label)
    checks.append(label)


def identity(path):
    data = path.read_bytes()
    return {'path': str(path.resolve()), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def functions(source):
    return {n.name: n for n in ast.parse(source).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def field(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('missing field ' + name)


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    paths = [SRC / name for name in ('verify_planar_exterior_r5e_v7.py', 'verify_planar_exterior_r7e_v9.py',
            'planar_exterior_model_r5e_v7.py', 'planar_exterior_model_r7e_v9.py',
            'planar_exterior_refinement_r7e_v9.py', 'run_portable_planar_r7e_v9.py',
            'R7E_V9_ORIGINAL_LINE_PLANE_PROJECTION.json', 'R7E_V9_STATIC_SOURCE_CAPACITY.json',
            'R5E_PORTABLE_SOURCE_LOCK_V7.json')]
    before = [identity(p) for p in paths]
    checker_path = SRC / 'verify_planar_exterior_r7e_v9.py'
    need(identity(checker_path)['sha256'] == 'd79fa404ce3311ecb9c8ab0f89791bde7bc33c738d4f791a09d1376081d89435',
         'exact cross-author checker source reviewed')
    old_text = (SRC / 'verify_planar_exterior_r5e_v7.py').read_text()
    text = checker_path.read_text()
    old, new = functions(old_text), functions(text)
    unchanged = []
    modified = {'verify_models', 'fixed_limits', 'model_controls', 'validate_static_capacity',
                'validate_producer_prerequisites', 'main'}
    for name, node in old.items():
        if name in modified:
            continue
        need(ast.dump(node, include_attributes=False) == ast.dump(new[name], include_attributes=False),
             'unchanged original independent function: ' + name)
        unchanged.append(name)
    need(len(unchanged) == 60, 'complete census of unchanged original checker functions')
    for original, renamed in [('verify_models', 'verify_legacy_models'),
                              ('validate_static_capacity', 'validate_legacy_static_capacity')]:
        actual = ast.dump(new[renamed], include_attributes=False).replace("name='" + renamed + "'", "name='" + original + "'", 1)
        need(actual == ast.dump(old[original], include_attributes=False), 'original independent function retained under explicit name: ' + original)
    core = ['verify_tree', 'check_exclusion', 'verify_uv_exclusion', 'verify_uv_unresolved', 'check_unresolved',
            'registered_cut', 'spatial_separator', 'analytic_controls', 'uv_channel_controls']
    need(all(name in unchanged for name in core), 'all nine original tree/volume/channel/analytic proof functions unchanged')
    tree = ast.parse(text)
    producer_tree = ast.parse((SRC / 'planar_exterior_refinement_r7e_v9.py').read_text())
    need(tuple(field(tree, 'SHARED_INPUT_FIELDS')) == tuple(field(producer_tree, 'SHARED_INPUT_FIELDS')),
         'complete producer/checker input identity fields match including supplemental original source')
    imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)] + [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    need(not any(x and ('cadquery' in x or x == 'OCP' or 'planar_exterior_model' in x or 'planar_exterior_refinement' in x) for x in imports),
         'no static import of native geometry or producer/helper')
    calls = [n for n in ast.walk(new['main']) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'prior_module']
    names = [ast.literal_eval(n.args[0].slice) for n in calls if isinstance(n.args[0], ast.Subscript)]
    need(sorted(names) == ['base_V5_verifier_source', 'base_V6_verifier_source', 'base_verifier_source'],
         'only frozen prior independent readers are dynamically imported')
    projection = json.loads((SRC / 'R7E_V9_ORIGINAL_LINE_PLANE_PROJECTION.json').read_text())
    expected = {27: '384f8ba42b9a7f4569bc4fa0c6312bec01c19e8d53e35518973319b4847c490c',
                42: 'ec7ed32eec43f6d9ff96f1e80db30528a53b6d2461e62c3f84a888d9631493c8'}
    need([c['face_index'] for c in projection['records'][1]['candidate_faces']] == [27, 42],
         'exact original two-face order from completed source diagnosis')
    for c in projection['records'][1]['candidate_faces']:
        need(canonical(c['complete_original_face']) == c['complete_original_face_canonical_sha256'] == expected[c['face_index']],
             'independent checker hard-binds exact original face ' + str(c['face_index']))
    body = ast.get_source_segment(text, new['independent_line_domain_and_corners'])
    need('for t in (start,end)' in body and 'for u in domain[0] for v in domain[1]' in body,
         'checker independently enumerates complete exact Line endpoints and every affine UV corner')
    supplementary = ast.get_source_segment(text, new['independent_supplementary_model'])
    need('reconstructed == original_swept' in supplementary and 'stationary[k][0]+shift[k][0]' in supplementary and
         'stationary[k][1]+shift[k][1]' in supplementary,
         'strict complete-D forward equality at all six original AABB endpoints is mandatory')
    capacity = json.loads((SRC / 'R7E_V9_STATIC_SOURCE_CAPACITY.json').read_text())
    need((capacity['plane_occurrences'], capacity['Line_occurrences'], capacity['Circle_occurrences'],
          capacity['source_edge_occurrences'], capacity['maximum_total_UV_pieces']) == (50,490,48,538,4100),
         'new finite source census includes all 36 added Line/closure pieces')
    controls = ast.get_source_segment(text, new['supplemental_controls'])
    need('len(rows) == 12' in controls and 'actual_rejected' in controls and
         "value['complete_original_face_canonical_sha256'] = canonical(value['complete_original_face'])" in controls,
         'twelve actual supplemental controls include recomputed source digests before independent rejection')
    root_controls = ast.get_source_segment(text, new['main'])
    need("totals['model_additional_applied_plane_count'],12" in root_controls and
         "totals['planar'],7,'No actual saved new u proof.'" in root_controls,
         'actual supplemental and actual UV proof controls retain explicit target-dependent applicability')
    limits = ast.get_source_segment(text, new['fixed_limits'])
    need(all(token in limits for token in ['600', '805306368', '4096', '24', '12000000', 'TOL/100000', '4943']),
         'original worker/algorithm/TOL limits remain fixed')
    source_lock = json.loads((SRC / 'R5E_PORTABLE_SOURCE_LOCK_V7.json').read_text())
    old_row = next(r for r in source_lock['r5_files'] if r['path'] == 'verify_planar_exterior_r5e_v7.py')
    old_identity = identity(SRC / 'verify_planar_exterior_r5e_v7.py')
    need(all(old_identity[k] == old_row[k] for k in ('bytes', 'sha256')), 'legacy checker is the exact original frozen V7 file')
    need(before == [identity(p) for p in paths], 'all reviewed sources remained unchanged')
    report = {'schema': 'razr-r7e-v9-cross-author-independent-checker-static-review-v2',
              'created_utc': datetime.now(timezone.utc).isoformat(), 'completed': True,
              'checker_source': identity(checker_path), 'reviewer_source': identity(Path(__file__)),
              'independent_checker_author_is_root': True, 'reviewer_is_envelope_producer_author': True,
              'source_identities': before, 'checks': checks, 'check_count': len(checks),
              'unchanged_original_checker_functions': unchanged, 'unchanged_major_proof_functions': core,
              'reviewed_changed_functions': sorted(modified),
              'semantic_review': {
                  'source_chain': 'Native producer+independent reader identities bind to original R4 report; exact full original face canonical hashes bind independently; raw/public proof bridge retains complete D.',
                  'new_arithmetic': 'Complete original Line endpoints and all four plane corners are independently enumerated; producer uses interval support. Missing or unsupported original data fails explicitly.',
                  'preservation': 'Legacy source model records retain original order and full serialization hash before appended extras; original 3D face/edge/vertex/cylinder carriers and nine core proof functions remain unchanged.',
                  'actual_control_scope': 'Twelve new actual target mutations, including three source rehashes, are required only with actual applicable supplemental targets. Seven actual UV proof mutations remain N/A without a saved u proof.',
                  'gates': 'Source-only census grows by the two exact original faces; worker budgets, proof semantics, directed volumes, retained leaves and original first-leaf u/TOL gate are unchanged.'},
              'static_findings_requiring_revision': [], 'eligible_for_registered_execution': True,
              'new_checker_or_producer_executed_during_review': False,
              'mathematical_or_native_qualification_claimed': False, 'all_blockers_closed': False,
              'all_reviewed_sources_unchanged': True,
              'elapsed_seconds': time.monotonic()-started,
              'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
              'wall_budget_seconds':30, 'address_space_budget_bytes':134217728}
    path = HERE / 'R7E_V9_CROSS_AUTHOR_CHECKER_STATIC_REVIEW_V2.json'
    if path.exists():
        raise ValueError('new review output required')
    assert report['check_count'] == len(report['checks'])
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'report': identity(path), 'checks':report['check_count'],
                      'seconds':report['elapsed_seconds'], 'peak_RSS_bytes':report['peak_RSS_bytes']}))


if __name__ == '__main__':
    main()
