"""Read-only R13 closeout audit; no producer, CAD, numerical solve or tests run.

This checks serialized inventory and exact arithmetic accounting. It does not
replace the producer's geometric theorem or its independent scientific review.
"""
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
from pathlib import Path
import gzip
import hashlib
import json

BASE = Path('/workspace/scratch/1b842ca762be')
ENV = BASE / 'r13_envelope_work'
GEO = BASE / 'r13_geometry_work'
IMPORTED = BASE / 'RAZR-SLIDE/engineering/engineering-followup-20261030-r13'
OUT = Path(__file__).resolve().parent / 'ENVELOPE_AND_MOTION_SCOPE_REVIEW.json'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def record(p):
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)}


def read(p):
    if p.suffix == '.gz':
        with gzip.open(p, 'rt') as f:
            return json.load(f)
    return json.loads(p.read_text())


def bound(row, p):
    assert p.is_file(), f'missing {p}'
    if 'bytes' in row:
        assert p.stat().st_size == row['bytes'], f'length mismatch {p}'
    assert sha(p) == row['sha256'], f'SHA mismatch {p}'


def inside(q, interval):
    lo, hi, inc_lo, inc_hi = interval
    lo, hi = F(lo['exact']), F(hi['exact'])
    return (q > lo or (q == lo and inc_lo)) and (q < hi or (q == hi and inc_hi))


manifest = read(ENV / 'R13_ENVELOPE_DELIVERY_MANIFEST.json')
rows = manifest['files']
names = [r['path'] for r in rows]
assert len(names) == len(set(names)) == manifest['file_count_excluding_self'] == 51
assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in names)
actual = {str(p.relative_to(ENV)) for p in ENV.rglob('*') if p.is_file()}
assert actual == set(names) | {'R13_ENVELOPE_DELIVERY_MANIFEST.json'}
for r in rows:
    bound(r, ENV / r['path'])
    bound(r, IMPORTED / 'envelope' / r['path'])
assert sum(r['bytes'] for r in rows) == manifest['bytes_excluding_self'] == 8256338
bound(record(ENV / 'R13_ENVELOPE_DELIVERY_MANIFEST.json'), IMPORTED / 'envelope/R13_ENVELOPE_DELIVERY_MANIFEST.json')
assert manifest['native_or_physical_qualification_release'] is False

im = read(ENV / 'inputs/INPUT_MANIFEST.json')
assert len(im['files']) == im['count'] == 14
assert sum(r['bytes'] for r in im['files']) == im['bytes'] == 7675316
for r in im['files']:
    bound(r, ENV / 'inputs' / r['path'])
    bound(r, Path(r['source_path']))

scope = read(ENV / 'R13_ENVELOPE_SCOPE.json')
assert sha(ENV / 'R13_ENVELOPE_SCOPE.json') == manifest['scope_sha256']
for group in ('scientific_reports', 'model_and_frontier'):
    for r in scope[group]:
        bound(r, ENV / r['path'])
bound(scope['seal_source'], ENV / scope['seal_source']['path'])
false_flags = [
    'native_original_BREP_mutated', 'native_endpoints_snapped_or_healed',
    'old_B0_only_bound_replaced', 'actual_native_B0_membership_proved',
    'actual_native_T_membership_proved',
    'existence_of_full_global_actual_native_material_realizing_B0_and_T_proved',
    'recorded_native_tolerance_is_uniform_compiled_error_bound',
    'uniform_compiled_error_proved', 'fixed_version_OCCT_source_binary_equivalence_proved',
    'current_native_aperture_proved_by_literal_source_context', 'actual_collision_proved',
    'physical_allowed_domain_proved', 'continuous_G2', 'whole_15D_G2',
    'G3', 'G4', 'G5', 'manufacturing_go',
]
assert all(scope[k] is False for k in false_flags)
threshold = F(scope['original_float64_threshold_exact'])
assert threshold == F(1e-7)
assert (scope['original_split_limit'], scope['original_depth_limit'], scope['new_splits'], scope['new_depth']) == (4096, 24, 0, 0)

native = read(ENV / 'native-attempt1/report.json')
corridors = read(ENV / 'producer-attempt1/complete_trim_corridors.json')
native_counts = (
    len(native['faces']),
    sum(len(f['wires']) for f in native['faces']),
    sum(len(w['edges']) for f in native['faces'] for w in f['wires']),
    sum(len(w['joins']) for f in native['faces'] for w in f['wires']),
    sum(len(e['oriented_vertices']) for f in native['faces'] for w in f['wires'] for e in w['edges']),
)
assert native_counts == (6, 12, 48, 48, 96)
nonzero_gaps = sum(any(F(c) for c in j['original_exact_pcurve_gap']) for f in corridors['faces'] for w in f['wires'] for j in w['joins'])
assert nonzero_gaps == scope['original_nonzero_exact_endpoint_joins_preserved'] == 44

producer = read(ENV / 'producer-attempt1/report.json')
independent = read(ENV / 'independent-review/R13_TRIM_INDEPENDENT_REVIEW.json')
negatives = read(ENV / 'independent-review/trim-negative-controls/report.json')
assert len(negatives['complete_variants']) == 8
assert negatives['all_replayed_rejections'] is True
for r in negatives['complete_variants']:
    bound(r, ENV / 'independent-review' / r['complete_variant_file'])
    assert r['replay']['rejected'] is True
assert sha(ENV / 'independent-review/audit_r13_trim_independently.py') == independent['source_sha256'] == negatives['checker_sha256']
assert sha(ENV / 'independent-review/R13_TRIM_INDEPENDENT_REVIEW.json') == negatives['original_independent_review_sha256']

pair_results, gaps = [], []
for key in ('L_KEY', 'R_KEY'):
    new = read(ENV / f'producer-attempt1/{key}-completed-trim-ledger.json.gz')
    old = read(ENV / f'inputs/R12_{key}_exterior.json.gz')
    boxes = new['original_positive_boxes']
    old_boxes = old['original_positive_boxes']
    assert len(boxes) == len(old_boxes)
    assert len({tuple(b['locator']) for b in boxes}) == len(boxes)
    counts = Counter(b['kind'] for b in boxes)
    old_sum, new_sum, coarse_sum, trim_count = F(0), F(0), F(0), 0
    for b, previous in zip(boxes, old_boxes):
        assert b['locator'] == previous['locator']
        assert b['box_exact'] == previous['box_exact']
        full = F(1)
        for lo, hi in b['box_exact']:
            assert F(hi) > F(lo)
            full *= F(hi) - F(lo)
        assert full == F(b['original_positive_full_box_volume_exact']) == F(previous['positive_full_box_volume_exact'])
        assert F(b['R12_upper_exact']) == F(previous['upper_exact'])
        u = F(b['upper_under_B0_and_T_exact'])
        if b['kind'] == 'retained_positive_full_box':
            assert u == full and u > 0
        elif b['kind'] == 'inherited_KEY_exterior':
            assert u == F(previous['upper_exact']) == 0
        else:
            assert b['kind'] == 'new_panel_completed_trim_exterior'
            assert u == 0 and F(previous['upper_exact']) == full
            witnesses = b['all_298_complete_face_witnesses']
            assert len(witnesses) == 298
            assert {w['face_index'] for w in witnesses} == set(range(298))
            for w in witnesses:
                if w['method'] == 'all_completion_corridors_disjoint_and_opposite_complete_wire_windings':
                    trim_count += 1
                    assert w['total_winding'] == 0
                    assert sorted(x['reference_winding'] for x in w['wires']) == [-1, 1]
                    assert w['native_filled_domain_membership_proved'] is False
                    gaps.extend(F(c['strict_gap_exact']) for wire in w['wires'] for c in wire['all_complete_edge_corridors_strictly_outside_query'])
        coarse_sum += full
        old_sum += F(previous['upper_exact'])
        new_sum += u
    sr = next(p for p in scope['pairs'] if p['key'] == key)
    pr = next(p for p in producer['pairs'] if p['key'] == key)
    ir = next(p for p in independent['pairs'] if p['key'] == key)
    assert coarse_sum == F(new['original_coarse_sum_exact']) == F(old['original_full_bound_exact'])
    assert old_sum == F(new['unchanged_R12_B0_only_sum_exact']) == F(old['remaining_full_bound_exact']) == F(sr['unchanged_B0_only_upper_exact_mm3']) == F(pr['R12_B0_only_upper_exact']) == F(ir['unchanged_R12_B0_only_exact'])
    assert new_sum == F(new['new_B0_and_T_sum_exact']) == F(sr['new_B0_and_T_upper_exact_mm3']) == F(pr['B0_and_T_upper_exact']) == F(ir['conditional_B0_and_T_exact'])
    assert 0 < new_sum <= threshold < old_sum
    assert dict(counts) == new['counts'] == pr['counts'] == ir['counts']
    assert sr['nominal_only_q_exact'] == ['0', '12']
    for k in ('actual_native_T_membership_proved', 'actual_native_B0_membership_proved', 'uniform_compiled_error_proved', 'continuous_G2'):
        assert new[k] is False
    pair_results.append({'key': key, 'original_positive_boxes': len(boxes), 'counts': dict(counts), 'old_B0_only_exact': str(old_sum), 'new_B0_and_T_exact': str(new_sum), 'new_bound_strictly_positive': new_sum > 0, 'old_B0_threshold_passes': old_sum <= threshold, 'new_conditional_threshold_passes': new_sum <= threshold, 'trim_query_face_certificates': trim_count})
assert sum(p['original_positive_boxes'] for p in pair_results) == 169
assert sum(p['counts']['retained_positive_full_box'] for p in pair_results) == 157
assert sum(p['trim_query_face_certificates'] for p in pair_results) == 12
assert min(gaps) == F(scope['minimum_query_to_complete_corridor_gap_exact_mm']) > 0

motion = read(GEO / 'COMPLETE_SOURCE_MOTION_DOMAIN.json')
assert motion['source_sha256'] == sha(GEO / 'analyze_complete_source_motion.py')
for rel in ('README.md', 'COMPLETE_SOURCE_MOTION_DOMAIN.json', 'R13_GEOMETRY_SCOPE.json', 'analyze_complete_source_motion.py'):
    bound(record(GEO / rel), IMPORTED / 'geometry' / rel)
K = F(motion['coefficient_K']['exact'])
A = F(motion['crosshead_absolute_bound_A_mm']['exact'])
B = F(motion['crosshead_minus_KEY_bound_B_mm']['exact'])
W = F(motion['output_offset_bound_W_mm']['exact'])
assert W == A + B and K * F(79.75) >= 12
pair_counts = Counter()
for p in motion['all_25_left_right_merged_branch_pairs']:
    ok = p['feasible_under_shared_slide_real_projection']
    pair_counts[str(ok)] += 1
    if ok:
        lift = p['exact_feasible_lift']
        s = F(lift['slide_mm']['exact'])
        assert 0 <= s <= F(79.75)
        for side in ('L', 'R'):
            row = lift['sides'][side]
            q, dq, dx = (F(row[k]['exact']) for k in ('q_mm', 'dq_mm', 'dx_mm'))
            assert 0 <= q <= 12 and q == K * s + dq and abs(dx) <= A and abs(dx - dq) <= B
            assert inside(q, p[f'{side}_interval'])
    else:
        assert F(p['separation_distance_infimum_mm']['exact']) > 2 * W
assert pair_counts == Counter({'True': 17, 'False': 8})
for k in ('exact_float64_acceptance_set_equivalence_proved', 'uniform_float64_profile_error_bound_proved', 'actual_physical_allowed_domain_proved', 'spring_force_preload_or_stop_strength_proved', 'current_full_15D_collision_clear', 'full_G2', 'G3', 'G4', 'G5', 'manufacturing_go'):
    assert motion['scope'][k] is False

report = {
    'schema': 'razr-r13-independent-envelope-and-motion-closeout-review-v1',
    'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
    'review_source': record(Path(__file__).resolve()),
    'scope': 'Read-only file inventory, SHA/length identity, exact saved-ledger accounting, and documentary model-boundary review. No CAD, scientific producer, numerical solve, tests, or negative-control replay executed in this review.',
    'completed': True,
    'concrete_consistency_defects_found': [],
    'envelope_manifest': {'manifest': record(ENV / 'R13_ENVELOPE_DELIVERY_MANIFEST.json'), 'members_excluding_manifest': 51, 'bytes_excluding_manifest': 8256338, 'actual_inventory_matches_exactly': True, 'all_imported_envelope_files_identical': True},
    'original_inputs': {'members': 14, 'bytes': 7675316, 'each_input_matches_manifest_and_retained_original_source': True},
    'bound_documents': [record(ENV / n) for n in ('README_R13_ENVELOPE.md', 'R13_ENVELOPE_SCOPE.json', 'COMPLETION_MODEL_DEFINITION.md', 'MODEL_MEMBERSHIP_FRONTIER.md')],
    'native_saved_census': {'faces_wires_edges_joins_vertex_ends': native_counts, 'exact_nonzero_pcurve_joins_preserved': nonzero_gaps, 're_read_with_native_kernel_in_this_review': False},
    'exact_saved_ledger_readback': {'pairs': pair_results, 'original_threshold_exact': str(threshold), 'minimum_recorded_positive_corridor_gap_exact_mm': str(min(gaps)), 'all_remaining_157_positive_contributions_kept_at_full_box_volume': True},
    'saved_negative_control_evidence': {'complete_variant_hashes_checked': 8, 'all_saved_replay_results_reject': True, 'replayed_by_this_review': False},
    'manual_scope_conclusions': [
        'The README, scope, model definition and membership frontier retain the old B0-only bound; the new bound requires B0 AND T.',
        'The 3.1510793974117154e-15 mm3 display is a positive conditional upper bound on each nominal q in [0,12] pair, not measured collision, actual clearance, or native release.',
        'The local reference-loop existence is not promoted into existence or membership of a globally consistent actual native whole material realizing B0 AND T.',
        'Native validity, signed volume, tolerance metadata and source construction context are not promoted into a uniform compiled-error or material-filling proof.',
        'The theorem discussion uses query-wide corridor separation and homotopy; this closeout review is not a replacement independent proof of every geometric predicate.',
    ],
    'all_envelope_release_and_unproved_membership_flags_remain_false': {k: scope[k] for k in false_flags},
    'geometry_motion_projection_review': {
        'bound_documents': [record(GEO / n) for n in ('README.md', 'COMPLETE_SOURCE_MOTION_DOMAIN.json', 'R13_GEOMETRY_SCOPE.json', 'analyze_complete_source_motion.py')],
        'interpretation': 'Exact real model of the listed shared-slide plus independent side-deviation q subsystem, using frozen binary64 coefficients and thresholds.',
        'projection': '0 <= qL,qR <= 12 AND abs(qL-qR) <= 2*(A+B)',
        'valid_saved_subsystem_lifts': 17,
        'saved_pairs_with_separation_strictly_above_2W': 8,
        'claim_not_extended_to_full_15D_source_acceptance': True,
        'claim_not_extended_to_all_float64_execution_acceptance': True,
        'claim_not_extended_to_mechanically_supported_physical_domain': True,
        'integration_wording_requirement': 'Use the explicit shared-slide/side-deviation q-subsystem qualifier; do not shorten it to a proof of the full 15D allowed domain.',
    },
    'integrated_root_readme_ledger_current_entrypoints_reviewed': False,
    'reason_integration_not_yet_reviewed': 'Root integration documents were still being written when this bounded first-stage review was made.',
}
assert not OUT.exists(), 'Do not overwrite a sealed review; use a new receipt.'
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'completed': True, 'review': record(OUT)}, ensure_ascii=False))
