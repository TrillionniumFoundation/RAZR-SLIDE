"""A bound, predeclared decision for sampled unpowered-motion evidence.

This module never authorizes fabrication, powering or whole-phone release.
Missing observations and unidentified specimen revisions remain UNKNOWN.
A PASS applies only to the supplied, identified sampled protocol; original
attachments and declared timestamps are checked, not externally authenticated.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

PLAN_SCHEMA = 'razr-unpowered-motion-qualification-plan-v1'
SPECIMEN_SCHEMA = 'razr-as-built-qualification-specimen-v1'
REVIEW_SCHEMA = 'razr-preregistration-review-v1'
REQUIRED_ROLES = ('cad', 'ep4', 'bom', 'drawings', 'material', 'process', 'firmware')
# Units and required comparison directions are code-owned. A plan may not omit
# a failed/missing channel or silently choose a different comparison direction.
METRICS = {
    'operator_force_max_N': ('N', 'maximum'),
    'left_right_y_max_mm': ('mm', 'maximum'),
    'left_right_z_max_mm': ('mm', 'maximum'),
    'return_y_max_mm': ('mm', 'maximum'),
    'return_z_max_mm': ('mm', 'maximum'),
    'stroke_y_mm': ('mm', 'range'),
    'stroke_z_mm': ('mm', 'range'),
    'hands_off_y_drift_max_mm': ('mm', 'maximum'),
    'hands_off_z_drift_max_mm': ('mm', 'maximum'),
    'oled_tail_travel_mm': ('mm', 'range'),
    'oled_pull_force_max_N': ('N', 'maximum'),
    'oled_radius_min_mm': ('mm', 'minimum'),
    'fpc_radius_min_mm': ('mm', 'minimum'),
    'fpc_resistance_max_ohm': ('ohm', 'maximum'),
}


def finite(value, name, *, positive=False, integer=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(name + ': finite non-boolean number required')
    if value < 0 or (positive and value <= 0):
        raise ValueError(name + ': invalid sign')
    if integer and (type(value) is not int or value < 1):
        raise ValueError(name + ': positive integer required')
    return value


def real(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(name + ': finite non-boolean result required')
    return value


def checked_interval(bounds):
    if not isinstance(bounds, list) or len(bounds) != 2:
        raise ValueError('measurement interval requires two finite bounds')
    lo, hi = (real(v, 'measurement interval') for v in bounds)
    if lo > hi:
        raise ValueError('measurement interval bounds are reversed')
    return lo, hi


def interval(value, error, *, nonnegative=True):
    value = real(value, 'interval value')
    error = finite(error, 'interval error')
    low, high = real(value - error, 'interval lower bound'), real(value + error, 'interval upper bound')
    bounds = [max(0., low) if nonnegative else low, high]
    checked_interval(bounds)
    return bounds


def combine(states):
    return 'fail' if 'fail' in states else 'unknown' if 'unknown' in states else 'pass'


def decide(bounds, limits):
    """Interval wholly outside fails; straddling a limit remains unknown."""
    if bounds is None or limits is None:
        return 'unknown'
    lo, hi = checked_interval(bounds)
    minimum, maximum = limits.get('minimum'), limits.get('maximum')
    if (minimum is not None and hi < minimum) or (maximum is not None and lo > maximum):
        return 'fail'
    if (minimum is not None and lo < minimum) or (maximum is not None and hi > maximum):
        return 'unknown'
    return 'pass'


def metric_observations(rows, calibrations, analysis):
    """Keep valid observations and coverage separately; never erase a known failure."""
    out, coverage = {}, {}
    yerr = finite(calibrations['left_y_mm']['error'] + calibrations['right_y_mm']['error'], 'summed y error')
    zerr = finite(calibrations['left_z_mm']['error'] + calibrations['right_z_mm']['error'], 'summed z error')

    def maximum(key, error):
        return interval(max(abs(r[key]) for r in rows), error)

    out['operator_force_max_N'] = maximum('operator_force_N', calibrations['operator_force_N']['error'])
    out['left_right_y_max_mm'] = maximum('left_minus_right_y_mm', yerr)
    out['left_right_z_max_mm'] = maximum('left_minus_right_z_mm', zerr)
    cycles = analysis['cycles']
    out['return_y_max_mm'] = interval(max(abs(c['return_offset_mean_y_mm']) for c in cycles), yerr)
    out['return_z_max_mm'] = interval(max(abs(c['return_offset_mean_z_mm']) for c in cycles), zerr)
    # A range criterion must be met by EVERY cycle; one complete cycle cannot
    # hide an incomplete stroke in another cycle.
    out['stroke_y_mm'] = [interval(c['sampled_mean_y_range_mm'], yerr) for c in cycles]
    out['stroke_z_mm'] = [interval(real(
        max(r['mean_z_mm'] for r in rows if r['cycle'] == c['cycle'])
        - min(r['mean_z_mm'] for r in rows if r['cycle'] == c['cycle']), 'cycle z range'), zerr)
        for c in cycles]
    holds = [h for c in cycles for h in c['hands_off_segments']]
    for axis, error in [('y', yerr), ('z', zerr)]:
        out['hands_off_' + axis + '_drift_max_mm'] = (
            interval(max(h['maximum_mean_' + axis + '_drift_from_first_sample_mm'] for h in holds), error)
            if holds else None)

    def optional(metric, key, mode):
        has_calibration = key in calibrations
        valid = [r for r in rows if has_calibration and r.get(key) is not None]
        missing = len(rows) - len(valid)
        info = {'complete': missing == 0, 'missing_observations': missing}
        coverage[metric] = info
        if mode == 'range':
            spans, complete = [], []
            for cycle in sorted({r['cycle'] for r in rows}):
                members = [r for r in rows if r['cycle'] == cycle]
                values = [r[key] for r in members if has_calibration and r.get(key) is not None]
                complete.append(len(values) == len(members))
                spans.append(interval(real(max(values) - min(values), 'optional cycle range'),
                                      finite(2 * calibrations[key]['error'], 'optional range error'))
                             if values else None)
            info['intervals_complete'] = complete
            return spans
        info['intervals_complete'] = [missing == 0]
        if not valid:
            return None
        values = [r[key] for r in valid]
        return interval(min(values) if mode == 'minimum' else max(abs(v) for v in values),
                        calibrations[key]['error'])

    out['oled_tail_travel_mm'] = optional('oled_tail_travel_mm', 'oled_tail_y_mm', 'range')
    out['oled_pull_force_max_N'] = optional('oled_pull_force_max_N', 'oled_pull_force_N', 'maximum')
    out['oled_radius_min_mm'] = optional('oled_radius_min_mm', 'oled_min_radius_mm', 'minimum')
    out['fpc_radius_min_mm'] = optional('fpc_radius_min_mm', 'fpc_min_radius_mm', 'minimum')
    wire_names = ['fpc_c%02d_ohm' % i for i in range(1, 27)]
    valid = [(r[name], calibrations[name]['error']) for r in rows for name in wire_names
             if name in calibrations and r.get(name) is not None]
    missing = len(rows) * len(wire_names) - len(valid)
    coverage['fpc_resistance_max_ohm'] = {
        'complete': missing == 0, 'missing_observations': missing, 'intervals_complete': [missing == 0]}
    if valid:
        observed_intervals = [interval(value, error) for value, error in valid]
        out['fpc_resistance_max_ohm'] = [
            max(bounds[0] for bounds in observed_intervals), max(bounds[1] for bounds in observed_intervals)]
    else:
        out['fpc_resistance_max_ohm'] = None
    return out, coverage


def evaluate(manifest, analysis, rows, calibrations, evidence_root, repository,
             *, read_file, stamp, verify_commit, preregistration_review=None):
    root, repository = Path(evidence_root), Path(repository)
    checked_refs = []

    def retained(ref):
        data = read_file(root, ref)
        checked_refs.append(ref)
        return data

    def record(ref, schema):
        item = json.loads(retained(ref))
        if not isinstance(item, dict) or item.get('schema') != schema:
            raise ValueError('unrecognized qualification record schema')
        return item

    result = {
        'schema': 'razr-unpowered-motion-qualification-decision-v1',
        'status': 'unknown',
        'scope': 'identified sampled unpowered motion only',
        'criteria': [],
        'blockers': [],
        'qualification_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'physical_phone_verified': False,
        'fixture_fabrication_go': False,
        'manufacturing_go': False,
        'attachment_authenticity_independently_proved': False,
        'absence_of_unsampled_dropout_proved': False,
    }
    ref = manifest.get('qualification_plan')
    if ref is None:
        result['blockers'].append('predeclared_qualification_plan_missing')
        return result
    plan = record(ref, PLAN_SCHEMA)
    result['plan_reference'] = ref
    if plan.get('is_template') is not False:
        result['blockers'].append('qualification_plan_is_template_or_undeclared')
        return result
    if plan.get('scope') != 'unpowered_motion':
        raise ValueError('this evaluator only accepts unpowered_motion scope')
    planned_phases = plan.get('planned_phase_order')
    if planned_phases is None:
        result['blockers'].append('predeclared_phase_order_missing')
    elif planned_phases != manifest['planned_phase_order']:
        raise ValueError('acquisition phase order differs from the predeclared protocol')
    binding = manifest['design_binding']
    if plan.get('design_binding') != binding:
        raise ValueError('qualification plan design identity differs from acquisition')
    result['design_binding'] = binding
    roles = binding.get('artifact_roles', {})
    if not isinstance(roles, dict) or set(roles) - set(REQUIRED_ROLES):
        raise ValueError('unsupported artifact role')
    files = binding['files_sha256']
    missing_roles = []
    for role in REQUIRED_ROLES:
        paths = roles.get(role)
        if not isinstance(paths, list) or not paths:
            missing_roles.append(role)
            continue
        if any(not isinstance(p, str) for p in paths) or len(paths) != len(set(paths)):
            raise ValueError('artifact role needs distinct relative file identities')
        if any(p not in files for p in paths):
            raise ValueError('artifact role is not bound to the design file digest map')
    if missing_roles:
        result['blockers'].append('unbound_artifact_roles:' + ','.join(missing_roles))
    result['missing_artifact_roles'] = missing_roles
    for path, digest in files.items():
        read_file(repository, {'path': path, 'sha256': digest})
    if manifest['execution_kind'] == 'physical':
        verify_commit(repository, binding['git_commit'], files)
    else:
        result['blockers'].append('synthetic_fixture_is_not_physical_qualification')

    # Missing dates produce UNKNOWN. Dates contradicting a predeclaration
    # claim reject the record instead of retrospectively accepting limits.
    started, ended = manifest.get('acquisition_started_at_utc'), manifest.get('acquisition_ended_at_utc')
    declared = plan.get('declared_at_utc')
    if None in (started, ended, declared):
        result['blockers'].append('predeclaration_or_acquisition_time_missing')
        start_time = end_time = None
    else:
        start_time, end_time, declared_time = stamp(started), stamp(ended), stamp(declared)
        if stamp(manifest['recorded_at_utc']) < end_time:
            raise ValueError('record timestamp predates acquisition end')
        if declared_time >= start_time or end_time <= start_time:
            raise ValueError('plan must precede acquisition and acquisition times must be ordered')
        if rows[-1]['t_s'] - rows[0]['t_s'] > (end_time - start_time).total_seconds():
            raise ValueError('CSV duration exceeds the declared acquisition interval')
    # Git fixes content identity, not trustworthy chronology: local commit dates
    # can be set by the committer. A later import of an independently preregistered
    # paper protocol is allowed. Git versions are optional unless the reviewer
    # specifically uses the controlled-version verification method.
    version = manifest.get('qualification_plan_version')
    if version is not None:
        if (not isinstance(version, dict) or set(version) != {'git_commit', 'path', 'sha256'}
                or not isinstance(version['git_commit'], str)
                or not re.fullmatch(r'[0-9a-f]{40}', version['git_commit'])
                or not isinstance(version['path'], str) or not version['path']
                or version['sha256'] != ref['sha256']):
            raise ValueError('invalid immutable qualification plan version')
        path = Path(version['path'])
        if path.is_absolute() or '..' in path.parts or not path.parts:
            raise ValueError('qualification plan repository path must be relative')
        verify_commit(repository, version['git_commit'], {version['path']: version['sha256']})
        result['qualification_plan_version'] = version

    # Only the assessor's explicit argument selects the review. A field supplied
    # by the acquisition manifest cannot approve its own preregistration claim.
    # This records a human verification boundary; it does not authenticate the
    # reviewer or turn local Git timestamps into a trusted timestamp service.
    review_path = review_bytes = None
    reviewed_originals = []
    result['caller_supplied_review_attestation'] = False
    result['reviewer_identity_or_independence_authenticated_by_program'] = False
    if preregistration_review is None:
        result['blockers'].append('independent_preregistration_review_missing')
    else:
        review_path = Path(preregistration_review).resolve()
        review_bytes = review_path.read_bytes()
        review = json.loads(review_bytes)
        if not isinstance(review, dict) or review.get('schema') != REVIEW_SCHEMA:
            raise ValueError('unrecognized preregistration review schema')
        result['preregistration_review_sha256'] = hashlib.sha256(review_bytes).hexdigest()
        if review.get('is_template') is not False:
            result['blockers'].append('preregistration_review_is_template')
        elif review.get('conclusion') != 'verified_preregistered_exact_plan':
            result['blockers'].append('preregistration_not_verified_by_reviewer')
        else:
            if (review.get('scope') != 'unpowered_motion'
                    or review.get('plan_sha256') != ref['sha256']
                    or review.get('specimen_id') != manifest['specimen_id']
                    or review.get('acquisition_manifest_sha256') != analysis['manifest_sha256']
                    or review.get('design_binding_sha256') != hashlib.sha256(
                        json.dumps(binding, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()):
                raise ValueError('preregistration review does not bind the exact plan, acquisition and specimen')
            method = review.get('verification_method')
            if method not in ('observed_controlled_version_time', 'independently_reviewed_preregistration_document'):
                raise ValueError('unsupported preregistration verification method')
            if method == 'observed_controlled_version_time' and (version is None or review.get('controlled_version') != version):
                raise ValueError('review does not identify the controlled plan version')
            originals = review.get('original_evidence')
            if (not isinstance(review.get('reviewed_by'), str) or not review['reviewed_by'].strip()
                    or review.get('reviewer_independent_of_acquisition') is not True
                    or not isinstance(review.get('verification_note'), str) or not review['verification_note'].strip()
                    or not isinstance(originals, list) or not originals):
                result['blockers'].append('independent_review_identity_or_original_evidence_missing')
            elif start_time is None:
                result['blockers'].append('cannot_compare_reviewed_preregistration_with_missing_acquisition_time')
            else:
                registered = stamp(review.get('verified_registration_at_utc'))
                reviewed = stamp(review.get('reviewed_at_utc'))
                if (registered >= start_time or registered < stamp(declared)
                        or reviewed < registered or reviewed < end_time):
                    raise ValueError('reviewed preregistration and acquisition chronology is inconsistent')
                for original in originals:
                    read_file(review_path.parent, original)
                    reviewed_originals.append(original)
                result['caller_supplied_review_attestation'] = True
                result['preregistration_verification'] = {
                    'method': method, 'reviewed_by': review['reviewed_by'],
                    'verified_registration_at_utc': registered.isoformat(),
                    'reviewed_at_utc': reviewed.isoformat(),
                    'trust_boundary': 'caller-supplied review attestation selected by assessor; reviewer identity, independence and attachments are not authenticated by this program'}
    approval = plan.get('approval_evidence')
    if not isinstance(plan.get('approved_by'), str) or not plan['approved_by'].strip() or not isinstance(approval, list) or not approval:
        result['blockers'].append('predeclaration_approval_evidence_missing')
    else:
        for item in approval:
            retained(item)

    specimen_ref = manifest.get('as_built_specimen_record')
    if specimen_ref is None:
        result['blockers'].append('as_built_specimen_record_missing')
    else:
        specimen = record(specimen_ref, SPECIMEN_SCHEMA)
        if specimen.get('is_template') is not False:
            result['blockers'].append('as_built_specimen_record_is_template')
        elif specimen.get('specimen_id') != manifest['specimen_id']:
            raise ValueError('as-built record names a different specimen')
        elif specimen.get('execution_kind') != manifest['execution_kind']:
            raise ValueError('as-built and acquisition execution kinds differ')
        elif specimen.get('design_binding') != binding:
            raise ValueError('as-built specimen differs from the tested design identity')
        else:
            observed = specimen.get('role_observations', {})
            if not isinstance(observed, dict) or set(observed) - set(REQUIRED_ROLES):
                raise ValueError('invalid as-built role inventory')
            for role in REQUIRED_ROLES:
                item = observed.get(role, {})
                if not isinstance(item, dict):
                    raise ValueError('invalid as-built role observation')
                required_text = ('part_or_lot_id', 'method', 'locator', 'observed_at_utc')
                originals = item.get('original_evidence')
                if (not all(isinstance(item.get(k), str) and item[k].strip() for k in required_text)
                        or not isinstance(originals, list) or not originals):
                    result['blockers'].append('as_built_observation_missing:' + role)
                    continue
                if item.get('design_paths') != roles.get(role):
                    raise ValueError('as-built role does not cover the exact assigned design artifacts')
                observed_time = stamp(item['observed_at_utc'])
                if start_time is not None and observed_time > start_time:
                    raise ValueError('as-built observation postdates the acquisition start')
                for original in originals:
                    retained(original)
    if start_time is not None:
        for name, cal in calibrations.items():
            recorded = cal.get('recorded_at_utc')
            if recorded is None:
                result['blockers'].append('calibration_time_missing:' + name)
            elif stamp(recorded) > start_time:
                raise ValueError('calibration postdates acquisition: ' + name)

    requirements = plan.get('measurement_requirements', {})
    if not isinstance(requirements, dict):
        raise ValueError('measurement requirements must be an object')
    validated = {}
    for name in ('minimum_cycles', 'minimum_samples_per_phase', 'minimum_hands_off_duration_s',
                 'maximum_sampling_gap_s', 'maximum_alignment_error_s'):
        value = requirements.get(name)
        if value is None:
            result['blockers'].append('measurement_requirement_missing:' + name)
        else:
            validated[name] = finite(value, name, positive=name != 'maximum_alignment_error_s',
                                     integer=name in ('minimum_cycles', 'minimum_samples_per_phase'))
    cycles = analysis['cycles']
    if rows[0]['cycle'] != 1 or any(not c['matches_declared_phase_labels'] for c in cycles):
        result['blockers'].append('incomplete_or_misordered_cycle_observations')
    if 'minimum_cycles' in validated and len(cycles) < validated['minimum_cycles']:
        result['blockers'].append('fewer_than_predeclared_cycles')
    if 'minimum_samples_per_phase' in validated and any(
            phase['sample_count'] < validated['minimum_samples_per_phase']
            for c in cycles for phase in c['phase_results']):
        result['blockers'].append('insufficient_samples_in_phase')
    alignment = finite(manifest['timebase']['alignment_error_bound_s'], 'alignment_error_bound_s')
    alignment_span = finite(2 * alignment, 'two-sample alignment error')
    if 'maximum_alignment_error_s' in validated and alignment > validated['maximum_alignment_error_s']:
        result['blockers'].append('time_alignment_exceeds_predeclared_limit')
    if 'maximum_sampling_gap_s' in validated and (
            finite(analysis['sampling']['maximum_observed_gap_s'] + alignment_span, 'gap including alignment error') > validated['maximum_sampling_gap_s']):
        result['blockers'].append('sampling_gap_exceeds_predeclared_limit')
    if 'minimum_hands_off_duration_s' in validated and any(
            not c['hands_off_segments'] or any(
                h['sample_count'] < 2 or real(h['observed_duration_s'] - alignment_span, 'hands-off duration lower bound') < validated['minimum_hands_off_duration_s']
                for h in c['hands_off_segments'])
            for c in cycles):
        result['blockers'].append('insufficient_contiguous_hands_off_duration')

    observed, coverage = metric_observations(rows, calibrations, analysis)
    declarations = plan.get('criteria', {})
    if not isinstance(declarations, dict) or set(declarations) - set(METRICS):
        raise ValueError('unsupported qualification metric')
    for metric, (unit, direction) in METRICS.items():
        item = declarations.get(metric)
        limits = None
        reason = None
        if item is None:
            reason = 'predeclared_threshold_missing'
        elif not isinstance(item, dict) or item.get('unit') != unit:
            raise ValueError('qualification criterion has wrong unit: ' + metric)
        else:
            keys = ('minimum', 'maximum') if direction == 'range' else (direction,)
            if set(item) - {'unit', *keys}:
                raise ValueError('unsupported criterion comparison: ' + metric)
            if any(item.get(k) is None for k in keys):
                reason = 'predeclared_threshold_missing'
            else:
                limits = {k: finite(item[k], metric + '.' + k) for k in keys}
                if direction == 'range' and limits['minimum'] > limits['maximum']:
                    raise ValueError('reversed criterion bounds: ' + metric)
        bounds = observed[metric]
        # Range metrics always carry one element per cycle, including None
        # for an entirely missing cycle. Extrema carry one interval.
        intervals = bounds if direction == 'range' else [bounds]
        info = coverage.get(metric, {
            'complete': bounds is not None, 'missing_observations': 0,
            'intervals_complete': [bounds is not None] * len(intervals)})
        complete = info['intervals_complete']
        states = []
        for bound, covered in zip(intervals, complete):
            state = decide(bound, limits)
            if not covered:
                # An incomplete observed range can only prove an upper-limit
                # violation. Missing points could enlarge it to the minimum.
                if direction == 'range':
                    state = ('fail' if bound is not None and limits is not None
                             and checked_interval(bound)[0] > limits['maximum'] else 'unknown')
                elif state != 'fail':
                    state = 'unknown'
            states.append(state)
        status = combine(states)
        if not info['complete']:
            reason = ('measured_limit_exceedance_with_incomplete_channel_coverage' if status == 'fail'
                      else 'required_channel_missing_incomplete_or_overrange')
        elif status == 'unknown' and reason is None:
            reason = 'measurement_uncertainty_straddles_acceptance_limit'
        result['criteria'].append({'metric': metric, 'unit': unit, 'sampled_intervals': intervals,
                                   'limits': limits, 'status': status, 'reason': reason,
                                   'observation_coverage': info})
    result['sampled_criteria_status'] = combine([x['status'] for x in result['criteria']])
    result['thresholds_applied'] = all(x['limits'] is not None for x in result['criteria'])
    result['status'] = combine([result['sampled_criteria_status']] + (['unknown'] if result['blockers'] else []))
    if manifest['execution_kind'] != 'physical':
        result['status'] = 'unknown'
    # Re-read every linked attachment and all assigned design bytes after evaluation.
    if review_path is not None:
        if review_path.read_bytes() != review_bytes:
            raise ValueError('preregistration review changed during analysis')
        for original in reviewed_originals:
            read_file(review_path.parent, original)
    for item in checked_refs:
        read_file(root, item)
    for path, digest in files.items():
        read_file(repository, {'path': path, 'sha256': digest})
    return result

