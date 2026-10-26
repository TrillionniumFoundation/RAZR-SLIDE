"""Named research KEY bridge candidate; never an S4 production-default change.

The original transverse bridge crosses the fixed panel's cover-backing posts.
This candidate replaces only that bridge's central strip by a forward U loop.
The complete original KEY, all removed and all added material are accounted.
It requires completed S4 full-factory and independent-reader witnesses first.
No strength, manufacturing allowance or whole-motion acceptance is implied.
"""
from __future__ import annotations
from fractions import Fraction
import hashlib
import math
from pathlib import Path

NAME = 'key_forward_loop_v1'
S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
TOL = 1e-7
Q_DOMAIN = (0., 12.)
# Right-hand, q=0, A coordinate system, millimetres. Left side is mirrored X.
CUT = ((17.38, 13.99, 4.01), (18.48, 15.51, 4.39))
ADDITIONS = {
    'inboard_leg': ((16.96, 5.00, 4.02), (17.34, 15.50, 4.38)),
    'outboard_leg': ((18.52, 5.00, 4.02), (18.90, 15.50, 4.38)),
    'front_crossbar': ((16.96, 5.00, 4.02), (18.90, 5.38, 4.38)),
}
POSTS = {
    'front': ((17.43, 18.30, .50), (18.43, 19.50, 7.00)),
    'rear': ((17.43, 22.35, .50), (18.43, 23.80, 7.00)),
}
# These are material-protection masks, not measured contact patches. Every old
# KEY atom outside CUT is separately retained by the complete difference check.
PROTECTED_MATERIAL = {
    'pawl_end_and_inboard_connection': ((5.0, 0., 0.), (16.90, 95., 8.)),
    'original_outer_cam_and_stop_features': ((20.60, 0., 0.), (32., 95., 8.)),
    'coupling_yoke_and_rear_tab': ((5.0, 16., 0.), (32., 95., 8.)),
}


def record(value):
    if value.get('derived_projection_not_raw_original') is True:
        return value['engineering_record']
    return value


def require_witness(factory, reader):
    factory_hash = factory.get('original', {}).get('sha256')
    if not isinstance(factory_hash, str) or len(factory_hash) != 64:
        raise ValueError('byte-addressed original factory report required')
    factory, reader = record(factory), record(reader)
    for label, r in (('factory', factory), ('reader', reader)):
        if r.get('functional_source_commit') != S4 or r.get('execution_completed') is not True:
            raise ValueError(label + ' must be completed exact-S4 evidence')
        if r.get('all_unordered_pairs_present_once') is not True or len(r.get('pairs', [])) != 11781:
            raise ValueError(label + ' complete 11781-pair record required')
        if len(r.get('participant_names', [])) != 154 or r.get('evaluation_failures'):
            raise ValueError(label + ' missing bodies or unresolved evaluations')
        identity = r.get('source_identity_projection', {})
        if (identity.get('source_commit_before') != S4
                or identity.get('source_commit_after') != S4
                or identity.get('worktree_clean_before') is not True
                or identity.get('source_bytes_and_locked_environment_unchanged') is not True
                or identity.get('checked_package_count_before') != 43
                or identity.get('checked_package_count_after') != 43):
            raise ValueError(label + ' complete source/environment binding required')
    if factory.get('pose') != reader.get('pose'):
        raise ValueError('same original posture required')
    if reader.get('native_STEP_readback_executed') is not True or reader.get('mismatches_to_factory'):
        raise ValueError('independent complete STEP agreement required')
    if reader.get('factory_report_sha256') != factory_hash:
        raise ValueError('independent reader is not bound to this original factory report')
    comparisons = reader.get('L1_whole_endpoint_material_comparisons', [])
    if len(comparisons) != 8 or not all(x.get('passed') is True for x in comparisons):
        raise ValueError('all eight historical L1 material-frame matches required')
    for side in 'LR':
        if factory.get('panel_KEY_direct_Common', {}).get(side, {}).get('common_mm3', 0.) <= TOL:
            raise ValueError('original actual panel/KEY positive must remain in baseline')
    return factory, reader


def design_contract():
    # Analytic separation applies only to the newly declared prisms and the
    # two source post prisms. It is not complete KEY/full-scene collision proof.
    K=12/79.75
    a=(.425-.4)*math.hypot(1,K);b=(.425-.4)*math.sqrt(2)
    domains={'defined_ContactProfile':(Fraction(0),Fraction(12)),
             'unclipped_nominal_slot_projection':(-Fraction(a)-Fraction(b),Fraction(K)*Fraction('79.75')+Fraction(a)+Fraction(b)),
             'unclipped_real_slot_comparison_TOL_model':(-Fraction(a+1e-7)-Fraction(b+1e-7),Fraction(K)*Fraction('79.75')+Fraction(a+1e-7)+Fraction(b+1e-7))}
    axis_gaps=[]
    for domain,(qlo,qhi) in domains.items():
        for name,(lo,hi) in ADDITIONS.items():
            swept_lo=(Fraction(lo[0]),Fraction(lo[1])+qlo,Fraction(lo[2]))
            swept_hi=(Fraction(hi[0]),Fraction(hi[1])+qhi,Fraction(hi[2]))
            for post,(pl,ph) in POSTS.items():
                gaps=[max(swept_lo[i]-Fraction(ph[i]),Fraction(pl[i])-swept_hi[i]) for i in range(3)]
                exact=max(gaps)
                if exact<=0:raise ValueError('new declared prism sweep intersects source post')
                lower=float(exact)
                if Fraction(lower)>exact:lower=math.nextafter(lower,-math.inf)
                axis_gaps.append({'source_projection':domain,'new_prism':name,'fixed_post':post,
                    'q_projection_exact_mm':[str(qlo),str(qhi)],'separating_axis':'XYZ'[gaps.index(exact)],
                    'exact_axis_gap_mm':str(exact),'axis_gap_float_rounded_down_mm':lower,
                    'applies_to_declared_source_prisms_only':True})
    return {'candidate_name': NAME, 'functional_baseline': S4,
        'cut_box_R_local_q0_mm': CUT, 'added_boxes_R_local_q0_mm': ADDITIONS,
        'defined_native_ContactProfile_q_mm': Q_DOMAIN,
        'source_slot_domain_clipped_by_this_candidate': False,
        'physical_stop_added_or_proved': False,
        'declared_new_prisms_vs_backing_posts_continuous_axis_certificates': axis_gaps,
        'axis_certificates_cover_only_three_new_prisms_and_two_source_posts':True,
        'unclipped_slot_projection_is_not_physical_motion_permission':True,
        'cam_profile_extended_outside_declared_q_domain':False,
        'floating_point_slot_acceptance_set_proved_equal_to_real_projection':False,
        'inboard_and_outboard_leg_cross_sections_mm': [.38, .36],
        'local_leg_section_area_mm2': .38 * .36,
        'original_transverse_bar_section_mm2': 1.5 * .36,
        'section_area_ratio_for_declared_sections_only': .38 / 1.5,
        'minimum_whole_KEY_section_or_strength_qualified': False,
        'protected_old_material_masks_R_mm': PROTECTED_MATERIAL,
        'old_panel_and_cover_contact_geometry_changed': False,
        'real_material_process_preload_tolerances_and_loads_known': False,
        'required_followon': ['native single-solid topology and exact material budget',
            'complete factory and independent STEP readback at both original witnesses',
            'STOW/OPEN and all real independent offset, STOP/SPRING and telescope domains',
            'actual wall and section measurements on resulting geometry',
            'original functional contact extraction and assembly/repair-path checks',
            'new current-geometry FE/tolerance qualification'],
        'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}


def _box(p, side, lo, hi):
    if side not in ('L', 'R'):
        raise ValueError('explicit side required')
    if side == 'L':
        lo, hi = (-hi[0], lo[1], lo[2]), (-lo[0], hi[1], hi[2])
    return p.box(lo, hi)


def apply(parts, factory_report, reader_report, p):
    """Apply to every complete imported baseline body; return evidence shapes.

    ``p`` is the immutable S4 product_assembly module, whose single(), volume()
    and strict_common() retain the original topology and signed-volume rules.
    Caller must save every returned original/cutter/removed/added/result shape,
    re-evaluate all 11,781 pairs, then execute an independent native STEP reader.
    """
    factory, reader = require_witness(factory_report, reader_report)
    if set(parts) != set(factory['participant_names']) or len(parts) != 154:
        raise ValueError('full original factory body inventory required')
    for name, body in parts.items():
        solids, volume = p.whole_material(body)
        expected = factory['body_exports'][name]['signature_before']
        if (not body.isValid() or len(solids) != expected['solid_count']
                or abs(volume - expected['signed_volume_mm3']) > TOL
                or max(abs(x-y) for x,y in zip(p.bounds(body), expected['bounds_mm'])) > TOL):
            raise ValueError('original whole body signature differs: ' + name)
    q = factory['pose_input']['native_q_from_K_times_slide_mm']
    if type(q) not in (int, float) or not math.isfinite(q) or not 0 <= q <= 12:
        raise ValueError('original total q required without clamping')
    updated = dict(parts); evidence = {}; accounts = {}
    for side in 'LR':
        key = side + '_KEY'; old = p.single(parts[key].translate((0, -q, 0)))
        cutter = _box(p, side, *CUT)
        new_prisms = {name: _box(p, side, *bounds) for name, bounds in ADDITIONS.items()}
        removed = old.intersect(cutter); kept = old.cut(cutter)
        removed_volume = p.volume(removed)
        # Exact original local web is 1.10 x 1.50 x .36 in this cut. A different
        # retained native material must fail this source-feature precondition.
        if abs(removed_volume - 1.10 * 1.50 * .36) > TOL:
            raise ValueError('actual original transverse web differs from frozen feature')
        native = kept
        for prism in new_prisms.values():
            native = native.fuse(prism)
        native = p.single(native.clean())
        actual_loss = old.cut(native); actual_add = native.cut(old)
        loss, gain = p.volume(actual_loss), p.volume(actual_add)
        retained_loss = p.volume(kept.cut(native))
        unintended_loss = p.volume(actual_loss.cut(cutter))
        cut_restored = p.volume(native.intersect(cutter))
        material_balance = p.volume(old) - loss + gain - p.volume(native)
        if max(retained_loss, unintended_loss, cut_restored, abs(material_balance)) > TOL:
            raise ValueError('complete retained material or balance failed')
        if abs(loss - removed_volume) > TOL:
            raise ValueError('removed material identity failed')
        protected = {}
        for label, bounds in PROTECTED_MATERIAL.items():
            mask = _box(p, side, *bounds)
            before, after = old.intersect(mask), native.intersect(mask)
            deltas = [p.volume(before.cut(after)), p.volume(after.cut(before))]
            if max(deltas) > TOL:
                raise ValueError('protected functional-region material changed: ' + label)
            protected[label] = {'before_minus_after_mm3': deltas[0],
                                'after_minus_before_mm3': deltas[1]}
        actual_global = p.single(native.translate((0, q, 0)))
        updated[key] = actual_global
        evidence[key] = {'original_q0': old, 'cutter_q0': cutter,
            'removed_q0': actual_loss, 'added_q0': actual_add,
            'candidate_q0': native, 'candidate_at_witness': actual_global,
            **{'new_prism_q0_' + name: value for name, value in new_prisms.items()}}
        accounts[key] = {'original_mm3': p.volume(old), 'removed_mm3': loss,
            'added_mm3': gain, 'new_mm3': p.volume(native),
            'signed_material_balance_error_mm3': material_balance,
            'retained_original_material_loss_mm3': retained_loss,
            'unintended_loss_outside_declared_cutter_mm3': unintended_loss,
            'material_restored_inside_clearance_cut_mm3': cut_restored,
            'single_positive_valid_solid_required': True,
            'protected_material_region_comparisons': protected,
            'panel_direct_Common_at_original_witness': p.strict_common(parts['A_BACK_PANEL'], actual_global)}
    return updated, evidence, {'schema': 'razr-key-forward-loop-v1-native-application-v1',
        'design_contract': design_contract(), 'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'baseline_factory_pose': factory['pose'], 'actual_total_q_mm': q,
        'unchanged_participants': sorted(set(parts) - {'L_KEY', 'R_KEY'}),
        'material_accounts': accounts, 'all_pairs_rerun_complete': False,
        'independent_native_readback_complete': False,
        'continuous_all_participants_clear': False, 'strength_qualified': False,
        'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}
