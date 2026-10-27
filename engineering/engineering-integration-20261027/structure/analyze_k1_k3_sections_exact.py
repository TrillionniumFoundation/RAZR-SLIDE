"""Exact source-feature accounting for K1/K3; no CAD or physical qualification.

The finite rectangular subset, its interpretation and every omitted whole-body
claim are explicit. Fractions are used both for source decimal coordinates and
for the exact rationals represented by the frozen Python binary64 coordinates.
"""
from __future__ import annotations

import argparse
import ast
from fractions import Fraction as F
import hashlib
import itertools
import json
from pathlib import Path

EXPECTED = {
    'key_forward_loop_v1.py': '3e6ebf17f1e50fd71eeaf294d059566d9361d3d830edc4365ea8763d00259578',
    'KEY_FORWARD_LOOP_V1_CONTRACT.json': '17e1532ed82eff1298e9525456d6953df56437082ef2918f3d04839cff200455',
    'panel_key_travel_stops_v1.py': '59946f42f8bff88b0cdb8bcd2ad7f578e22e6f64e65832a6b6087426e282e5a5',
    'PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json': '0f3ec4af155a2e92650f49ada7042e6d1fc1f8ad94cb43f6716a77985ecc5b84',
    'cam_coupling.py': '4a3bf1d2b86d31fa8e3d60d3412e15548bf42287ed95d756798f3d88c6c4e631',
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def value(x):
    return {'exact_rational': str(x), 'float_display_only': float(x)}


def jsonable(x):
    if isinstance(x, F):
        return value(x)
    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    return x


def box(raw, interpretation):
    convert = (lambda x: F(str(x))) if interpretation == 'source_decimal' else F
    b = tuple(tuple(convert(x) for x in p) for p in raw)
    assert len(b) == 2 and all(b[1][i] > b[0][i] for i in range(3))
    return b


def mirror(b, side):
    lo, hi = b
    return b if side == 'R' else ((-hi[0], lo[1], lo[2]), (-lo[0], hi[1], hi[2]))


def volume(b):
    result = F(1)
    for a, z in zip(*b):
        result *= z - a
    return result


def inside(point, b):
    return all(a < x < z for x, a, z in zip(point, *b))


def union_partition(named):
    """All exact coordinate cells; no grid approximation or sampled volume."""
    axes = [sorted({p[i] for b in named.values() for p in b}) for i in range(3)]
    cells = []
    for indices in itertools.product(*(range(len(x) - 1) for x in axes)):
        lo = tuple(axes[i][j] for i, j in enumerate(indices))
        hi = tuple(axes[i][j + 1] for i, j in enumerate(indices))
        middle = tuple((a + b) / 2 for a, b in zip(lo, hi))
        owners = sorted(k for k, b in named.items() if inside(middle, b))
        if owners:
            cells.append({'bounds_mm': (lo, hi), 'owners': owners, 'volume_mm3': volume((lo, hi))})
    total = sum((c['volume_mm3'] for c in cells), F())
    # Independent inclusion-exclusion of only the three input boxes.
    inclusion = F()
    names = sorted(named)
    for n in range(1, len(names) + 1):
        for subset in itertools.combinations(names, n):
            lo = tuple(max(named[k][0][i] for k in subset) for i in range(3))
            hi = tuple(min(named[k][1][i] for k in subset) for i in range(3))
            if all(hi[i] > lo[i] for i in range(3)):
                inclusion += (-1) ** (n + 1) * volume((lo, hi))
    assert total == inclusion
    return {'coordinate_axes_mm': axes, 'occupied_cells': cells, 'union_volume_mm3': total,
            'inclusion_exclusion_volume_mm3': inclusion, 'independent_exact_sums_equal': True}


def interval_overlap(a, z, b, w):
    return max(F(), min(z, w) - max(a, b))


def swept_pair(moving, fixed, qlo=F(), qhi=F(12)):
    """Exact continuous box intersection: only Y translates by real q.

    min/max of the Y overlap change affine branch only at one of four endpoint
    coincidences. Evaluating every branch endpoint proves the maximum; this is
    not a finite-pose heuristic. X/Z overlap is constant and exact.
    """
    assert qlo <= qhi
    ml, mh = moving
    fl, fh = fixed
    breaks = {qlo, qhi}
    breaks.update(t for t in (fl[1] - ml[1], fl[1] - mh[1], fh[1] - ml[1], fh[1] - mh[1])
                  if qlo < t < qhi)
    breaks = sorted(breaks)
    cross = interval_overlap(ml[0], mh[0], fl[0], fh[0]) * interval_overlap(ml[2], mh[2], fl[2], fh[2])
    at = lambda q: cross * interval_overlap(ml[1] + q, mh[1] + q, fl[1], fh[1])
    points = [{'q_mm': q, 'common_mm3': at(q)} for q in breaks]
    regions = []
    for a, b in zip(breaks, breaks[1:]):
        slope = (at(b) - at(a)) / (b - a)
        intercept = at(a) - slope * a
        assert at((a + b) / 2) == slope * (a + b) / 2 + intercept
        regions.append({'q_interval_mm': [a, b], 'common_affine_slope_mm2': slope,
                        'common_affine_intercept_mm3': intercept})
    swept_lo = (ml[0], ml[1] + qlo, ml[2])
    swept_hi = (mh[0], mh[1] + qhi, mh[2])
    gaps = [max(swept_lo[i] - fh[i], fl[i] - swept_hi[i]) for i in range(3)]
    best = max(gaps)
    return {'q_interval_mm': [qlo, qhi], 'breakpoint_values': points, 'affine_regions': regions,
            'maximum_common_mm3': max(x['common_mm3'] for x in points),
            'swept_axis_gap_mm': best, 'swept_separating_axis_if_positive': 'XYZ'[gaps.index(best)] if best > 0 else None,
            'cross_section_overlap_XZ_mm2': cross}


def constant_assignments(text):
    found = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                found[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return found


def template_boxes(text):
    tree = ast.parse(text)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'templates')
    found = []
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'box':
            try:
                bounds = tuple(ast.literal_eval(x) for x in node.args)
            except (ValueError, TypeError):
                continue
            if len(bounds) == 2:
                found.append({'bounds': bounds, 'line': node.lineno, 'source_expression': ast.get_source_segment(text, node)})
    return found


def build(source):
    raw = {name: (source / name).read_bytes() for name in EXPECTED}
    for name, digest in EXPECTED.items():
        if sha(raw[name]) != digest:
            raise ValueError('immutable input bytes differ: ' + name)
    k1 = json.loads(raw['KEY_FORWARD_LOOP_V1_CONTRACT.json'])['design_contract']
    k3 = json.loads(raw['PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json'])['design_contract']
    constants = constant_assignments(raw['key_forward_loop_v1.py'].decode())
    assert json.loads(json.dumps(constants['ADDITIONS'])) == k1['added_boxes_R_local_q0_mm']
    assert json.loads(json.dumps(constants['CUT'])) == k1['cut_box_R_local_q0_mm']
    assert json.loads(json.dumps(constants['PROTECTED_MATERIAL'])) == k1['protected_old_material_masks_R_mm']
    assert k3['required_K1_source_sha256'] == EXPECTED['key_forward_loop_v1.py']
    assert k3['required_K1_contract_sha256'] == EXPECTED['KEY_FORWARD_LOOP_V1_CONTRACT.json']
    assert k3['front_crossbar_R_q0_mm'] == k1['added_boxes_R_local_q0_mm']['front_crossbar']
    assert k3['declared_stop_contact_planes_Y_mm']['upper'] == float(k1['added_boxes_R_local_q0_mm']['front_crossbar'][1][1] + 12.)
    results = {}
    for interpretation in ('source_decimal', 'exact_binary64_coordinates_real_translation'):
        additions = {name: box(b, interpretation) for name, b in constants['ADDITIONS'].items()}
        posts = {name + '_old_post': box(b, interpretation) for name, b in constants['POSTS'].items()}
        stops = {name: box(b, interpretation) for name, b in k3['additive_boxes_R_mm'].items()}
        static = {side + '_' + name: mirror(b, side) for side in 'LR' for name, b in {**posts, **stops}.items()}
        pairs = {}
        for side in 'LR':
            for name, b in additions.items():
                for fixed_name, fixed in static.items():
                    pairs[side + '_' + name + '__' + fixed_name] = swept_pair(mirror(b, side), fixed)
        assert len(pairs) == 48
        partition = union_partition(additions)
        changed = {'declared_cutter': box(constants['CUT'], interpretation), **additions}
        protection = {}
        for name, raw_mask in constants['PROTECTED_MATERIAL'].items():
            mask = box(raw_mask, interpretation)
            all_gaps = {}
            for label, altered in changed.items():
                gaps = [max(mask[0][i] - altered[1][i], altered[0][i] - mask[1][i]) for i in range(3)]
                all_gaps[label] = {'separating_axis': 'XYZ'[gaps.index(max(gaps))], 'gap_mm': max(gaps)}
                assert max(gaps) > 0
            protection[name] = {'all_changed_source_regions': all_gaps,
                                'minimum_positive_axis_gap_mm': min(g['gap_mm'] for g in all_gaps.values())}
        upper_gap = stops['upper_toe'][0][1] - additions['front_crossbar'][1][1] - 12
        lower_gap = additions['front_crossbar'][0][1] - stops['lower_post'][1][1]
        area = ((stops['upper_toe'][1][0] - stops['upper_toe'][0][0]) *
                (stops['upper_toe'][1][2] - stops['upper_toe'][0][2]))
        eps = F('0.0000001')
        results[interpretation] = {
            'new_three_prism_union': partition,
            'protected_material_mask_open_neighborhoods': protection,
            'continuous_pair_count': len(pairs), 'continuous_pairs': pairs,
            'q_L_and_q_R_are_independent': True,
            'each_side_declared_q_interval_mm': [F(), F(12)],
            'sum_of_independent_pair_maxima_upper_mm3': sum(p['maximum_common_mm3'] for p in pairs.values()),
            'every_declared_pair_below_original_volume_gate': all(p['maximum_common_mm3'] < eps for p in pairs.values()),
            'all_declared_pairs_exactly_disjoint_in_volume': all(p['maximum_common_mm3'] == 0 for p in pairs.values()),
            'lower_endpoint_signed_gap_mm': lower_gap,
            'upper_endpoint_signed_gap_mm': upper_gap,
            'new_stop_contact_rectangle_area_mm2': area,
            'constant_area_penetration_at_1e_7_mm3_gate_mm': eps / area,
            'source_coordinates_are_not_interval_enclosures_of_native_kernel_geometry': True,
        }
    decimal = results['source_decimal']
    binary = results['exact_binary64_coordinates_real_translation']
    assert decimal['new_three_prism_union']['union_volume_mm3'] == F('3.034224')
    assert decimal['all_declared_pairs_exactly_disjoint_in_volume']
    assert binary['upper_endpoint_signed_gap_mm'] == -F(1, 2 ** 50)
    assert not binary['all_declared_pairs_exactly_disjoint_in_volume']
    assert binary['every_declared_pair_below_original_volume_gate']
    cam_boxes = template_boxes(raw['cam_coupling.py'].decode())
    tab = next(x for x in cam_boxes if x['bounds'] == ((13.2, 15.8, 4.05), (13.45, 39.6, 4.35)))
    tab_box = box(tab['bounds'], 'source_decimal')
    tab_dims = tuple(b - a for a, b in zip(*tab_box))
    assert tab_dims == (F('.25'), F('23.8'), F('.30'))
    assert tab_box[1][0] < min(box(b, 'source_decimal')[0][0] for b in constants['ADDITIONS'].values())
    # Independent source-feature arithmetic, not a new native material account.
    expected_removed = F('1.10') * F('1.50') * F('.36')
    expected_old_overlap = 2 * F('.38') * F('1.50') * F('.36')
    expected_added = decimal['new_three_prism_union']['union_volume_mm3'] - expected_old_overlap
    assert (expected_removed, expected_added, expected_added - expected_removed) == (F('.594'), F('2.623824'), F('2.029824'))
    native_upper = float(5.38 + 12.)
    assert native_upper == 17.38
    # Positive interior overlap with both endpoints clear: verifies why the
    # analytic branch partition, not only endpoint checks, is necessary.
    interior_control = swept_pair(((F(),F(),F()),(F(1),F(1),F(1))),
                                 ((F(),F(5),F()),(F(1),F(6),F(1))),F(),F(10))
    assert interior_control['breakpoint_values'][0]['common_mm3'] == 0
    assert interior_control['breakpoint_values'][-1]['common_mm3'] == 0
    assert interior_control['maximum_common_mm3'] == 1
    return jsonable({
        'schema': 'razr-K1-K3-exact-source-feature-audit-v1',
        'source_binding': {name: {'bytes': len(raw[name]), 'sha256': sha(raw[name])} for name in EXPECTED},
        'execution_kind': 'stdlib_exact_rational_source_analysis_no_native',
        'analysis_method': 'exact coordinate-cell union plus inclusion-exclusion; all affine branch endpoints for every declared box pair',
        'results': results,
        'inherited_yoke_tab': {
            'source_line': tab['line'], 'source_expression': tab['source_expression'],
            'declared_dimensions_XYZ_mm': tab_dims, 'declared_transverse_section_XZ_mm2': tab_dims[0] * tab_dims[2],
            'nominal_length_is_not_measured_unsupported_span': True,
            'declared_local_min_dimension_mm': min(tab_dims),
            'new_prism_local_section_dimensions_mm': [F('.38'), F('.36')],
            'source_feature_smaller_than_new_legs': True,
            'whole_material_may_overlap_source_feature': True,
            'whole_KEY_global_minimum_inferred': False,
        },
        'source_feature_material_targets_per_KEY': {
            'removed_mm3': expected_removed, 'union_of_added_raw_prisms_mm3': decimal['new_three_prism_union']['union_volume_mm3'],
            'old_web_overlap_with_new_prisms_assumed_for_source_target_mm3': expected_old_overlap,
            'added_new_material_mm3': expected_added, 'net_change_mm3': expected_added - expected_removed,
            'actual_whole_material_accounts_remain_in_original_native_evidence': True,
            'new_actual_native_volume_calculation': False,
        },
        'local_section_ratios': {
            'new_leg_XZ_mm2': F('.38') * F('.36'), 'old_transverse_bar_YZ_mm2': F('1.5') * F('.36'),
            'ratio_of_these_declared_sections_only': F('.38') / F('1.5'),
            'strength_ratio_inferred': False,
        },
        'binary64_distinction': {
            'frozen_upper_plane_float': 17.38, 'Python_binary64_5p38_plus_12': native_upper,
            'exact_frozen_coordinate_difference_from_real_q12_mm': binary['upper_endpoint_signed_gap_mm'],
            'native_transform_rounding_model_proved': False,
            'old_native_zero_Common_at_endpoint_is_not_overwritten': True,
        },
        'algorithm_counterexample_control': {
            'synthetic_not_candidate_geometry': True,
            'both_q_endpoints_clear_but_internal_positive_common': interior_control,
            'interior_overlap_retained_by_piecewise_algorithm': True,
        },
        'functional_surface_scope': {
            'protected_material_masks_are_not_a_complete_surface_catalogue': True,
            'exact_set_construction_preserves_open_neighborhoods_inside_masks': True,
            'existing_K3_native_proof_covers_four_old_cover_patches_and_declared_stop_contacts': True,
            'all_old_functional_faces_identified_and_qualified': False,
        },
        'unproved_scope': [
            'entire current KEY and entire current panel over continuous controls',
            'all body pairs over actual independent 15D factory domains and binary64 tolerance shells',
            'native kernel enclosure and topology of this new symbolic subset proof',
            'complete global minimum wall metric, manufacturing allowance and stress/fatigue qualification',
            'physical same-specimen stop, material, friction, tolerances and loads',
        ],
        'source_domain_reduced': False, 'global_minimum_wall_qualified': False,
        'complete_motion_clear': False, 'physical_allowed_domain_proved': False,
        'strength_qualified': False, 'candidate_go': False,
        'fixture_fabrication_go': False, 'manufacturing_go': False,
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.source_dir)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output_name': args.output.name, 'sha256': sha(args.output.read_bytes()),
                      'bytes': args.output.stat().st_size,
                      'continuous_pair_count_per_coordinate_interpretation': 48,
                      'native_executed': False, 'physical_qualification': False}))


if __name__ == '__main__':
    main()
