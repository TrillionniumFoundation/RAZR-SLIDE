"""Analyse identified physical acquisition bytes without inventing observations.

Required motion/force channels share one explicitly documented monotonic time
base. Every channel has a hash-bound calibration record and original evidence.
The output distinguishes observed sampling, missing optional channels, declared
phase labels, uncertain threshold crossings and external operating force from
unknown internal KEY loads. Synthetic fixtures remain synthetic in the output.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re
import subprocess

HEX = re.compile(r'^[0-9a-f]{64}$')
COMMIT = re.compile(r'^[0-9a-f]{40}$')
MANDATORY = {'left_y_mm': 'mm', 'right_y_mm': 'mm', 'left_z_mm': 'mm',
             'right_z_mm': 'mm', 'operator_force_N': 'N'}
OPTIONAL = {'oled_tail_y_mm': 'mm', 'oled_pull_force_N': 'N',
            'oled_min_radius_mm': 'mm', 'fpc_min_radius_mm': 'mm',
            **{f'fpc_c{i:02d}_ohm': 'ohm' for i in range(1, 27)}}
PHASES = {'LOCKED_BASELINE', 'UNLOCK_LEFT', 'UNLOCK_RIGHT', 'SLIDE_OUT', 'SEAT',
    'HOLD_LEFT_INSTALL', 'HOLD_RIGHT_INSTALL', 'SUPPORT_INSTALL', 'HANDS_OFF_OPEN',
    'SUPPORT_REMOVE', 'HOLD_LEFT_REMOVE', 'HOLD_RIGHT_REMOVE', 'UNSEAT',
    'SLIDE_IN', 'RELOCK_LEFT', 'RELOCK_RIGHT', 'LOCKED_FINAL'}


def number(value, label, minimum=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(label+': finite number required')
    if minimum is not None and value < minimum:
        raise ValueError(label+': value below minimum')
    return float(value)


def stamp(value):
    if not isinstance(value, str):
        raise ValueError('timestamp must be an explicit timezone-aware ISO string')
    try:
        time = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('invalid recorded_at_utc') from exc
    if time.tzinfo is None or time.utcoffset().total_seconds() != 0:
        raise ValueError('recorded_at_utc must have an explicit UTC offset')
    return time


def relative_file(root, ref):
    if not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}:
        raise ValueError('file reference must contain exactly path and sha256')
    if not isinstance(ref['path'], str) or not isinstance(ref['sha256'], str) or not HEX.fullmatch(ref['sha256']):
        raise ValueError('invalid path or SHA256')
    rel = Path(ref['path'])
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:
        raise ValueError('evidence must be a relative descendant file')
    target = (root/rel).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError('evidence file missing or leaves its declared root')
    data = target.read_bytes()
    if hashlib.sha256(data).hexdigest() != ref['sha256']:
        raise ValueError('evidence bytes changed: '+ref['path'])
    return data


def calibration(root, ref, unit, execution_kind):
    data = json.loads(relative_file(root, ref))
    if data.get('schema') != 'razr-linear-sensor-calibration-v1':
        raise ValueError('unrecognized calibration record')
    if data.get('execution_kind') != execution_kind:
        raise ValueError('synthetic and physical calibration identities cannot be interchanged')
    if not isinstance(data.get('instrument_id'), str) or not data['instrument_id'].strip():
        raise ValueError('calibration requires its actual instrument identity')
    stamp(data.get('recorded_at_utc'))
    if data.get('output_unit') != unit:
        raise ValueError('calibration output unit does not match the channel')
    gain = number(data.get('gain'), 'gain')
    if gain == 0:
        raise ValueError('zero gain suppresses real variation')
    offset = number(data.get('offset'), 'offset')
    error = number(data.get('absolute_error_bound'), 'absolute error bound', 0.)
    if execution_kind == 'physical' and error == 0:
        raise ValueError('physical calibration needs a nonzero stated error bound')
    span = data.get('valid_raw_range')
    if not isinstance(span, list) or len(span) != 2:
        raise ValueError('two calibrated raw range limits required')
    lo, hi = (number(v, 'calibrated range') for v in span)
    if hi <= lo:
        raise ValueError('calibrated range is empty')
    evidence = data.get('original_evidence')
    if not isinstance(evidence, list) or not evidence:
        raise ValueError('calibration must retain original evidence')
    for item in evidence:
        relative_file(root, item)
    if not isinstance(data.get('calibration_method'), str) or not data['calibration_method'].strip():
        raise ValueError('calibration method required')
    return {'gain': gain, 'offset': offset, 'error': error, 'lo': lo, 'hi': hi,
            'instrument_id': data['instrument_id'], 'reference': ref}


def extent(rows, key, error):
    values = [(r['t_s'], r[key]) for r in rows if r.get(key) is not None]
    if not values:
        return None
    low = min(values, key=lambda v: v[1]); high = max(values, key=lambda v: v[1])
    peak = max(values, key=lambda v: abs(v[1]))
    return {'minimum': low[1], 'minimum_time_s': low[0], 'maximum': high[1],
        'maximum_time_s': high[0], 'maximum_absolute': abs(peak[1]),
        'maximum_absolute_time_s': peak[0], 'observed_samples': len(values),
        'missing_samples': len(rows)-len(values), 'absolute_error_bound': error}


def verify_physical_design_commit(repository, commit, files):
    """Read the exact local Git objects; matching dirty-workspace bytes alone is insufficient."""
    try:
        kind = subprocess.run(['git', '-C', str(repository), 'cat-file', '-t', commit],
                              capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError('cannot verify the physical record design commit with local Git') from exc
    if kind.returncode or kind.stdout.strip() != b'commit':
        raise ValueError('physical record design commit is not an available Git commit')
    for path, digest in files.items():
        try:
            blob = subprocess.run(['git', '-C', str(repository), 'cat-file', 'blob', commit+':'+path],
                                  capture_output=True, timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError('cannot read committed design bytes: '+path) from exc
        if blob.returncode or hashlib.sha256(blob.stdout).hexdigest() != digest:
            raise ValueError('committed design bytes differ from the physical record: '+path)
    return True


def analyse(manifest_path, repository):
    manifest_path, repository = Path(manifest_path).resolve(), Path(repository).resolve()
    root = manifest_path.parent
    manifest_bytes = manifest_path.read_bytes()
    m = json.loads(manifest_bytes)
    if m.get('schema') != 'razr-unpowered-motion-acquisition-v1':
        raise ValueError('unrecognized acquisition schema')
    kind = m.get('execution_kind')
    if kind not in ('physical', 'synthetic_fixture'):
        raise ValueError('explicit physical or synthetic_fixture identity required')
    if not isinstance(m.get('specimen_id'), str) or not m['specimen_id'].strip():
        raise ValueError('specimen identity required')
    recorded = stamp(m.get('recorded_at_utc'))
    binding = m.get('design_binding', {})
    if not COMMIT.fullmatch(str(binding.get('git_commit', ''))):
        raise ValueError('exact declared design commit required')
    files = binding.get('files_sha256', {})
    required_design = {'design/product_geometry.json', 'design/product_interfaces.json'}
    if not required_design <= set(files):
        raise ValueError('bind both geometry and electrical interface bytes')
    for path, digest in files.items():
        relative_file(repository, {'path': path, 'sha256': digest})
    original_log = relative_file(root, m['raw_csv'])
    # Both stage labels and observation of hands-off status must be supported
    # by a synchronized source, not inferred from near-zero force alone.
    relative_file(root, m['phase_and_hand_contact_evidence'])
    relative_file(root, m['coordinate_frame_evidence'])
    timebase = m.get('timebase', {})
    if timebase.get('kind') != 'monotonic' or timebase.get('unit') != 's':
        raise ValueError('one monotonic timebase in seconds is required')
    if not isinstance(timebase.get('source'), str) or not timebase['source'].strip():
        raise ValueError('timebase source required')
    max_gap = number(timebase.get('maximum_gap_s'), 'maximum allowed sampling gap', 0.)
    if max_gap == 0:
        raise ValueError('sampling-gap threshold must be positive')
    number(timebase.get('alignment_error_bound_s'), 'alignment error bound', 0.)
    relative_file(root, timebase['synchronization_evidence'])
    expected = m.get('planned_phase_order')
    if not isinstance(expected, list) or len(expected) != len(set(expected)) or not expected:
        raise ValueError('nonempty distinct planned phase order required')
    if any(x not in PHASES for x in expected):
        raise ValueError('unknown planned phase')
    if set(expected) != PHASES:
        raise ValueError('full declared program must retain every mechanical and hands-off observation phase')
    if expected[0] != 'LOCKED_BASELINE' or expected[-1] != 'LOCKED_FINAL':
        raise ValueError('cycle definition must include locked baseline and final observations')
    channels = m.get('channels', {})
    units = {**MANDATORY, **OPTIONAL}
    if not set(MANDATORY) <= set(channels) or not set(channels) <= set(units):
        raise ValueError('required motion channels missing or unsupported channel present')
    calibrations = {name: calibration(root, ref, units[name], kind) for name, ref in channels.items()}
    commit_verified = verify_physical_design_commit(repository, binding['git_commit'], files) if kind == 'physical' else False
    reader = csv.DictReader(io.StringIO(original_log.decode('utf-8-sig')))
    expected_columns = {'t_s', 'cycle', 'phase', 'hand_contact'} | set(channels)
    if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)) or set(reader.fieldnames) != expected_columns:
        raise ValueError('CSV columns must exactly match the declared channel map')
    rows, overrange = [], []
    last_t, last_cycle = None, None
    for ordinal, raw in enumerate(reader, 2):
        if None in raw or any(v is None for v in raw.values()):
            raise ValueError('malformed CSV row '+str(ordinal))
        try:
            t = number(float(raw['t_s']), 't_s', 0.)
            cycle = int(raw['cycle'])
        except (ValueError, TypeError) as exc:
            raise ValueError('invalid timestamp or cycle at row '+str(ordinal)) from exc
        if str(cycle) != raw['cycle'] or cycle < 1 or (last_cycle is not None and cycle not in (last_cycle, last_cycle+1)):
            raise ValueError('cycle identifiers must be positive consecutive integers')
        if last_t is not None and t <= last_t:
            raise ValueError('timestamps must be strictly increasing across the entire log')
        last_t, last_cycle = t, cycle
        phase = raw['phase']
        if phase not in expected or raw['hand_contact'] not in ('0', '1'):
            raise ValueError('unknown phase or nonbinary hand-contact record')
        hand = bool(int(raw['hand_contact']))
        if phase == 'HANDS_OFF_OPEN' and hand:
            raise ValueError('hands-off phase contradicts observed hand contact')
        row = {'t_s': t, 'cycle': cycle, 'phase': phase, 'hand_contact': hand}
        for name, cal in calibrations.items():
            value = raw[name]
            if value == '' and name in OPTIONAL:
                row[name] = None
                continue
            if value == 'OVER_RANGE' and name.startswith('fpc_c'):
                row[name] = None
                overrange.append({'channel': name, 'time_s': t, 'csv_line': ordinal,
                                  'meaning': 'instrument over-range report, not independently localized open circuit'})
                continue
            try:
                v = number(float(value), name)
            except (ValueError, TypeError) as exc:
                raise ValueError('invalid value '+name+' at row '+str(ordinal)) from exc
            if not cal['lo'] <= v <= cal['hi']:
                raise ValueError('value outside calibrated range: '+name+' at row '+str(ordinal))
            row[name] = v*cal['gain']+cal['offset']
            if units[name] == 'ohm' and row[name] < 0:
                raise ValueError('negative calibrated resistance')
        row['mean_y_mm'] = (row['left_y_mm']+row['right_y_mm'])/2
        row['mean_z_mm'] = (row['left_z_mm']+row['right_z_mm'])/2
        row['left_minus_right_y_mm'] = row['left_y_mm']-row['right_y_mm']
        row['left_minus_right_z_mm'] = row['left_z_mm']-row['right_z_mm']
        rows.append(row)
    if len(rows) < 2:
        raise ValueError('at least two actual acquisition rows are required')
    yerr = calibrations['left_y_mm']['error']+calibrations['right_y_mm']['error']
    zerr = calibrations['left_z_mm']['error']+calibrations['right_z_mm']['error']
    gaps = [{'from_time_s': a['t_s'], 'to_time_s': b['t_s'], 'gap_s': b['t_s']-a['t_s']}
            for a, b in zip(rows, rows[1:]) if b['t_s']-a['t_s'] > max_gap]
    cycles = []
    for cycle in sorted({r['cycle'] for r in rows}):
        selected = [r for r in rows if r['cycle'] == cycle]
        seen = [r['phase'] for i, r in enumerate(selected) if i == 0 or r['phase'] != selected[i-1]['phase']]
        first, last = selected[0], selected[-1]
        measured_stroke = max(r['mean_y_mm'] for r in selected)-min(r['mean_y_mm'] for r in selected)
        phase_summary = []
        for phase in dict.fromkeys(seen):
            phase_rows = [r for r in selected if r['phase'] == phase]
            phase_summary.append({'phase': phase, 'sample_count': len(phase_rows),
                'operator_force_N': extent(phase_rows, 'operator_force_N', calibrations['operator_force_N']['error']),
                'left_minus_right_y_mm': extent(phase_rows, 'left_minus_right_y_mm', yerr),
                'left_minus_right_z_mm': extent(phase_rows, 'left_minus_right_z_mm', zerr)})
        # Do not bridge separate releases or include manually supported rows.
        holds, segment = [], []
        for row in selected+[None]:
            if row is not None and row['phase'] == 'HANDS_OFF_OPEN' and not row['hand_contact']:
                if segment and row['t_s']-segment[-1]['t_s'] > max_gap:
                    holds.append(segment); segment = []
                segment.append(row)
            elif segment:
                holds.append(segment); segment = []
        hold_summary = []
        for segment in holds:
            h0 = segment[0]
            hold_summary.append({'first_time_s': h0['t_s'], 'last_time_s': segment[-1]['t_s'],
                'observed_duration_s': segment[-1]['t_s']-h0['t_s'], 'sample_count': len(segment),
                'maximum_mean_y_drift_from_first_sample_mm': max(abs(r['mean_y_mm']-h0['mean_y_mm']) for r in segment),
                'maximum_mean_z_drift_from_first_sample_mm': max(abs(r['mean_z_mm']-h0['mean_z_mm']) for r in segment),
                'conservative_displacement_error_bound_mm': {'y': yerr, 'z': zerr},
                'retention_capacity_or_lifetime_qualified': False})
        cycles.append({'cycle': cycle, 'observed_phase_order': seen,
            'matches_declared_phase_labels': seen == expected,
            'observed_sample_count': len(selected),
            'sampled_mean_y_range_mm': measured_stroke,
            'conservative_range_error_bound_mm': yerr,
            'return_offset_mean_y_mm': last['mean_y_mm']-first['mean_y_mm'],
            'return_offset_mean_z_mm': last['mean_z_mm']-first['mean_z_mm'],
            'first_and_last_positions_are_measured_not_assumed_locked': True,
            'phase_results': phase_summary, 'hands_off_segments': hold_summary})
    optionals = {name: None for name in OPTIONAL}
    for name in set(channels) & set(OPTIONAL):
        optionals[name] = extent(rows, name, calibrations[name]['error'])
    thresholds = m.get('continuity_threshold_ohm')
    crossings = None
    if thresholds is not None:
        threshold = number(thresholds, 'continuity threshold', 0.)
        if threshold == 0:
            raise ValueError('continuity threshold must be positive')
        relative_file(root, m['continuity_threshold_evidence'])
        crossings = []
        for row in rows:
            for name in channels:
                if name.startswith('fpc_c') and row.get(name) is not None:
                    value, err = row[name], calibrations[name]['error']
                    if value+err > threshold:
                        crossings.append({'time_s': row['t_s'], 'channel': name, 'value_ohm': value,
                            'absolute_error_bound_ohm': err, 'threshold_ohm': threshold,
                            'classification': 'above_even_with_error' if value-err > threshold else 'uncertain_at_error_bound'})
    result = {'schema': 'razr-unpowered-motion-analysis-v1',
        'analysis_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(), 'raw_csv': m['raw_csv'],
        'execution_kind': kind, 'specimen_id': m['specimen_id'], 'recorded_at_utc': recorded.isoformat(),
        'design_binding': binding, 'design_file_bytes_verified': True,
        'declared_commit_itself_independently_verified': commit_verified,
        'physical_execution_declared_by_record': kind == 'physical',
        'synthetic_values_are_not_hardware_evidence': kind == 'synthetic_fixture',
        'instrument_calibrations': {k: {'instrument_id': v['instrument_id'], 'reference': v['reference'],
            'absolute_error_bound': v['error'], 'unit': units[k]} for k, v in calibrations.items()},
        'sampling': {'rows': len(rows), 'start_time_s': rows[0]['t_s'], 'end_time_s': rows[-1]['t_s'],
            'maximum_observed_gap_s': max(b['t_s']-a['t_s'] for a, b in zip(rows, rows[1:])),
            'declared_maximum_gap_s': max_gap, 'gap_exceedances': gaps,
            'timebase': timebase, 'absence_of_unsampled_dropout_proved': False},
        'cycles': cycles, 'phase_label_complete_cycles': sum(x['matches_declared_phase_labels'] for x in cycles),
        'optional_sampled_observations': optionals, 'FPC_overrange_events': overrange,
        'FPC_threshold_crossings': crossings,
        'external_operator_force_N': extent(rows, 'operator_force_N', calibrations['operator_force_N']['error']),
        'structural_interpretation': {'force_scope': 'external operator sensor at its declared test setup',
            'internal_KEY_force_inferred': False, 'actual_KEY_material': None,
            'actual_KEY_unsupported_span_mm': None, 'actual_KEY_axial_and_lateral_load_N': None,
            'FE_force_points_or_boundary_conditions_generated': False,
            'reason': 'external operating force is not the internal load path; identify force transfer and real supports first'},
        'physical_cycle_acceptance_thresholds_applied': False,
        'manufacturing_go': False, 'physical_phone_verified': False}
    # Recheck every source byte against its identity after analysis.
    if manifest_path.read_bytes() != manifest_bytes or relative_file(root, m['raw_csv']) != original_log:
        raise ValueError('input changed during analysis')
    for path, digest in files.items():
        relative_file(repository, {'path': path, 'sha256': digest})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = analyse(args.manifest, args.repository)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, 'acquisition rejected: '+str(exc)+'\n')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'output': str(args.output), 'rows': result['sampling']['rows'],
                      'execution_kind': result['execution_kind'], 'physical_phone_verified': False}))
