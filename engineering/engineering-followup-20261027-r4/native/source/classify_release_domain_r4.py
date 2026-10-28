"""Find the exact binary64 sufficient whole-support release threshold.

This is a sufficient source-model support condition, not a minimum physical
release stroke and not a universal compiled-kernel theorem. The original
contract remains closed at tab=0 and released at tab=3.
"""
from pathlib import Path
from fractions import Fraction as Q
import ast
import datetime as dt
import hashlib
import json
import math
import struct
import sys


ROOT = Path(__file__).resolve().parent


def identity(path):
    p = Path(path)
    return {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def scalar(x):
    x = float(x)
    return {'float': x, 'hex': x.hex(), 'exact': str(Q(x))}


def qvalue(q):
    q = Q(q); f = float(q)
    if Q(f) > q:
        f = math.nextafter(f, -math.inf)
    return {'exact': str(q), 'float_rounded_down': f}


def main():
    out = Path(sys.argv[1]); out.mkdir(exist_ok=False)
    producer_path = ROOT / 'native-producer-v2/R4_WHOLE_KEY_PAWL_NATIVE.json'
    native = json.loads(producer_path.read_text()); assert native['completed']
    endpoint_path = ROOT / 'recovered/functional-source/integration/verify_endpoint_joint_pawl.py'
    endpoint_source = endpoint_path.read_text(); tree = ast.parse(endpoint_source)
    methods = {f.name: ast.get_source_segment(endpoint_source, f) for f in tree.body if isinstance(f, ast.FunctionDef)}
    assert "for u in (0.,3.):" in methods['verify']
    assert "(u==0 and hit<=TOL) or (u==3 and hit>TOL)" in methods['verify']
    r = {'schema': 'razr-r4-original-release-domain-source-definition-v1',
         'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'source_identity': identity(__file__),
         'native_report': {'path': str(producer_path), 'identity': identity(producer_path)},
         'original_requirement_source': {'path': str(endpoint_path), 'identity': identity(endpoint_path)},
         'original_requirement': {'locked_tab_mm': 0.0, 'released_tab_mm': 3.0,
             'original_retention_gate': 'if (u==0 and hit<=TOL) or (u==3 and hit>TOL): raise ValueError',
             'tab_1_full_release_required_by_this_original_contract': False,
             'tab_1_collision_is_not_itself_a_requirement_failure': True},
         'unchanged_product_material': {'KEY_removed_mm3': 0.0, 'KEY_added_mm3': 0.0,
             'PAWL_removed_mm3': 0.0, 'PAWL_added_mm3': 0.0, 'TAB_removed_mm3': 0.0,
             'TAB_added_mm3': 0.0, 'panel_removed_mm3': 0.0, 'panel_added_mm3': 0.0},
         'sides': {}, 'comparison_scope': {'exact_scalar_binary64_support_threshold': True,
             'quantified_all_q_mm': [0, 12], 'quantified_all_flanks': [-1, 1],
             'true_minimum_material_release_tab_found': False,
             'physical_or_toleranced_release_threshold': False,
             'universal_native_transformation_certificate': False,
             'manual_hold_force_or_automatic_relock': False}}
    to_float = lambda bits: struct.unpack('>d', struct.pack('>Q', bits))[0]
    to_bits = lambda number: struct.unpack('>Q', struct.pack('>d', number))[0]
    for side in 'LR':
        slot = native['slots'][side]
        pz = Q(native['whole_inputs'][side + '_PAWL']['native_guard']['bounds_mm'][4])
        kz = Q(native['whole_inputs'][side + '_KEY']['native_guard']['bounds_mm'][5])
        def condition(u):
            z = slot['origin'] + slot['slope'] * u - slot['halfwidth']
            gap = pz + Q(z) - kz
            return gap > 0, z, gap
        assert not condition(0.0)[0] and condition(3.0)[0]
        lo, hi, trace = to_bits(0.0), to_bits(3.0), []
        while lo < hi:
            middle = (lo + hi) // 2; u = to_float(middle); clear, z, gap = condition(u)
            trace.append({'u': scalar(u), 'minimum_z': scalar(z), 'source_exact_gap_mm': qvalue(gap), 'strictly_positive': clear})
            if clear:
                hi = middle
            else:
                lo = middle + 1
        minimum = to_float(lo); previous = math.nextafter(minimum, -math.inf)
        assert condition(minimum)[0] and not condition(previous)[0] and to_bits(minimum) - to_bits(previous) == 1
        checks = []
        for u in (0., 1., previous, minimum, 2.3, 3.):
            clear, z, gap = condition(u)
            checks.append({'tab': scalar(u), 'minimum_z_translation_mm': scalar(z),
                           'source_support_gap_mm': qvalue(gap), 'strict_source_support_separation': clear})
        # The unrounded real-parameter root is a useful reference, but is not
        # substituted for the original operation order or binary64 threshold.
        real_root = (kz - pz - Q(slot['origin']) + Q(slot['halfwidth'])) / Q(slot['slope'])
        r['sides'][side] = {'native_slot': slot,
            'KEY_base_zmax_mm': qvalue(kz), 'PAWL_base_zmin_mm': qvalue(pz),
            'exact_real_parameter_reference_root': qvalue(real_root),
            'least_binary64_tab_with_strict_source_support_gap': scalar(minimum),
            'immediate_binary64_predecessor': scalar(previous),
            'checks': checks, 'binary64_search_trace': trace,
            'proof': ['Positive binary64 ordering is identical to unsigned bit ordering on [0,3].',
                'The measured slope and halfwidth are strictly positive and finite.',
                'Each + or * in origin+slope*u+flank*halfwidth is monotone on these finite operands under ordinary correctly rounded binary64 arithmetic.',
                'The minimum over every original continuous flank in [-1,1] occurs at flank=-1; q affects KEY only through its Y translation in the source model.',
                'Therefore the exact rational support-gap comparison of the resulting binary64 Z translation is monotone in u; binary search plus the checked immediate predecessor identifies the least sufficient binary64 u.',
                'This proof treats the observed whole native Z bounds as support premises and the two bodies as mathematical rigid translations. It does not prove strict BRep set semantics or all compiled-kernel transforms.'],
            'tiny_threshold_gap_is_not_a_manufacturing_or_native_tolerance_margin': True}
    r['domain_definition'] = {
        'locked_requirement': 'At original tab=0, retain the original closed-state obstruction requirement. Current whole K1/PAWL controls at q=.36 and both original flank extremes have positive Common; q=0 rest controls are clear. The source-box exclusion proof also covers all flank in the declared q=.3..4, tab=0...5 subdomain, with its explicit native bridge premises.',
        'transition': '0 < tab < sufficient support threshold is not globally classified. Some configurations are clear and some collide; retain q, separate left/right tab, flank, and original shared-slide offset correlations. A failed particular witness does not empty its whole profile cell.',
        'sufficient_source_release': 'Independently on each side, tab >= that side least binary64 support threshold and <=3 guarantees mathematical whole-bound-box Z separation for all q in [0,12] and flank in [-1,1], under the listed support/rigid-source premises.',
        'original_operating_release': 'The original tab=3 mm release requirement satisfies the sufficient source support condition with a positive margin at the worst flank. The original 3 mm stroke remains unchanged.',
        'native_confirmations_reused': ['contact_control_00/01: q0, tab0, flanks -1/+1',
            'contact_control_02/03: q.36, tab0, flanks -1/+1',
            'contact_control_04/05: q.36, tab1, flanks -1/+1 retain different outcomes',
            'contact_control_08: q.36, tab2.3, flank-1',
            'contact_control_09/10: q.36, tab3, flanks -1/+1',
            'contact_control_12: q12, tab0, flank0; pair-level endpoint only',
            'contact_control_13: q12, tab3, flank-1; pair-level endpoint only'],
        'no_new_native_experiment_needed_for_this_source_threshold': True,
        'whole_factory_or_seating_force_qualification_from_pair_checks': False}
    z1 = native['slots']['R']['origin'] + native['slots']['R']['slope'] - native['slots']['R']['halfwidth']
    r['unexecuted_early_release_proposal'] = {'name': 'pawl_early_release_floor_trim_r4_REJECTED_SCOPE_PROPOSAL',
        'status': 'NOT_EXECUTED_NO_ORIGINAL_TAB1_RELEASE_REQUIREMENT',
        'hypothetical_single_parameter_trim_height_mm': float(kz) - z1 + .001,
        'hypothetical_research_clearance_reserve_mm': .001,
        'not_a_sourced_manufacturing_clearance_requirement': True,
        'would_change_original_contact_material': True,
        'candidate_geometry_created': False, 'native_candidate_run': False,
        'decision': 'Preserve the intended lock and original geometry; finish domain definition. Reconsider this proposal only if an explicit new tab=1 full-release requirement is adopted, with all original functional/contact checks and local/global strength implications.'}
    r['completed'] = True
    (out / 'R4_ORIGINAL_RELEASE_DOMAIN.json').write_text(json.dumps(r, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'completed': True, 'threshold': r['sides']['R']['least_binary64_tab_with_strict_source_support_gap'],
                      'predecessor': r['sides']['R']['immediate_binary64_predecessor'],
                      'checks': r['sides']['R']['checks']}))


if __name__ == '__main__':
    main()
