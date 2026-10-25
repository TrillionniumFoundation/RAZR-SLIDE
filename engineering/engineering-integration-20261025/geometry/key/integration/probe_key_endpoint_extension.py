"""Finite slot-admissible KEY endpoint-outside diagnostics on complete material.

The current factory deliberately rejects q outside [0,12]. This study does not
clamp q or pretend that the factory accepted it. It translates actual complete
KEY/crosshead/telescope material according to the existing rigid motion law,
retaining each STOP at the existing endpoint plateau/lower-stop height. Native
floor extents are inspected before claiming a STOW plateau continuation.
Positive Common proves a penetrating trial placement, not a usable state or a
global hard-stop theorem. Finite clear trials do not discharge a continuous
backlash domain or restoring-force/physical qualification.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import signal
import sys
import tempfile
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clearance_constants():
    radial = .425-.4
    cam = radial*math.hypot(1., 12./79.75)
    yoke = radial*math.sqrt(2.)
    return cam, yoke, cam+yoke


def endpoint_trials(pose):
    if pose not in ('STOW', 'OPEN'):
        raise ValueError('one declared endpoint required')
    cam, _, half = clearance_constants()
    direction = -1. if pose == 'STOW' else 1.
    return [{'label': pose+'_OUTSIDE_'+label, 'KEY_offset_mm': direction*half*factor,
             'crosshead_offset_mm': direction*cam*factor, 'nominal_q_mm': 0. if pose == 'STOW' else 12.}
            for label, factor in (('0p001mm', .001/half), ('HALF_BAND', .5), ('FULL_BAND', 1.))]


def moving_inventory(names):
    names = set(names)
    result = {side+'_'+role for side in 'LR' for role in (
        'KEY', 'CROSSHEAD', 'CROSSHEAD_TUBE_BOTTOM_CAP', 'KEY_FOLLOWER_LOWER_FLANGE',
        'TELESCOPE_1', 'TELESCOPE_1_BOTTOM_CAP', 'TELESCOPE_2', 'TELESCOPE_2_BOTTOM_CAP',
        'TELESCOPE_3', 'TELESCOPE_3_CORE_BOTTOM_SHOULDER', 'TELESCOPE_3_CAM_LOWER_FLANGE',
        'TELESCOPE_3_CAM_UPPER_FLANGE')}
    if not result <= names:
        raise ValueError('complete moving KEY/crosshead/telescope material is missing')
    return result


def pair_partition(names):
    """Every changed pair is recomputed; only unchanged pairs may be reused."""
    names = list(names)
    if len(names) != len(set(names)):
        raise ValueError('duplicate material participant')
    moving = moving_inventory(names)
    pairs = list(itertools.combinations(sorted(names), 2))
    changed = [(a, b) for a, b in pairs if a in moving or b in moving]
    fixed = [(a, b) for a, b in pairs if a not in moving and b not in moving]
    if len(changed)+len(fixed) != len(names)*(len(names)-1)//2 or set(changed) & set(fixed):
        raise ValueError('changed and unchanged pair partition is incomplete')
    return changed, fixed


def rigid_trial(parts, dq, dx):
    cam, yoke, _ = clearance_constants()
    if not all(type(v) in (int, float) and math.isfinite(v) for v in (dq, dx)):
        raise ValueError('finite offsets required')
    if abs(dx) > cam+1e-12 or abs(dx-dq) > yoke+1e-12:
        raise ValueError('trial is outside the two coupled native groove constraints')
    moving = moving_inventory(parts)
    result = dict(parts)
    for name in sorted(moving):
        sign = -1. if name.startswith('L_') else 1.
        vector = (0., dq, 0.) if name.endswith('_KEY') else (sign*dx, 0., 0.)
        result[name] = parts[name].translate(vector)
    return result


def contact_coordinates(side, point, nominal_q=0.):
    """Inverse of the audited native placement plus the 6 mm mounted shift."""
    x, y, z = point.toTuple() if hasattr(point, 'toTuple') else point
    sign = -1. if side == 'L' else 1.
    return z-4.2, y-14.8-nominal_q, sign*x-23.85


def retain_positive(row, positives, export=None, checkpoint=None):
    """Preserve a real numeric rejection even if witness export later fails."""
    common = row.get('common_mm3')
    if (type(common) not in (int, float) or not math.isfinite(common)
            or common <= 1e-7 or row.get('rejected') is not True):
        raise ValueError('an actual positive Common row is required')
    positive = dict(row)
    positives.append(positive)
    if checkpoint is not None:
        checkpoint()
    if export is None:
        return None
    try:
        positive['actual_Common_STEP'] = export()
    except Exception as exc:
        error = type(exc).__name__+': '+str(exc)
        positive['STEP_export_failure'] = error
        return {'a': row['a'], 'b': row['b'], 'evaluation_failed': True,
                'failure_stage': 'positive_Common_STEP_export', 'error': error,
                'actual_common_mm3_preserved': common}
    return None


def native_plateau_extent(parts, profiles, p):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    import cadquery as cq
    _, _, outside = clearance_constants()
    records = []
    for side in 'LR':
        sign = -1. if side == 'L' else 1.
        for index, profile in enumerate(profiles[side]):
            key, stop = parts[side+'_KEY'], parts[f'{side}_STOP_{index}']
            floors = []
            for face_index, face in enumerate(key.Faces()):
                if face.geomType() != 'PLANE':
                    continue
                normal = face.normalAt(); center = contact_coordinates(side, face.Center())
                if (abs(sign*normal.x-1.) > 1e-9 or abs(center[2]-profile.floor_height) > 1e-7
                        or not -.61 < center[0] < -.19):
                    continue
                vertices = [contact_coordinates(side, vertex.Center()) for vertex in face.Vertices()]
                e = [min(v[0] for v in vertices), max(v[0] for v in vertices)]
                q = [min(v[1] for v in vertices), max(v[1] for v in vertices)]
                corners = {(round(v[0], 9), round(v[1], 9)) for v in vertices}
                rectangular = (len(face.Wires()) == 1 and len(vertices) == 4 and len(face.Edges()) == 4
                    and all(edge.geomType() == 'LINE' for edge in face.Edges())
                    and corners == set(itertools.product(map(lambda x: round(x, 9), e), map(lambda x: round(x, 9), q)))
                    and abs(face.Area()-(e[1]-e[0])*(q[1]-q[0])) <= 1e-7)
                floors.append({'face': face_index, 'e_extent_mm': e, 'q_extent_mm': q,
                    'area_mm2': face.Area(), 'complete_trimmed_face_is_rectangle': rectangular,
                    'vertices_eqr_mm': vertices, 'wire_count': len(face.Wires()),
                    'edge_geometry_types': [edge.geomType() for edge in face.Edges()],
                    'normal_xyz': normal.toTuple(), 'center_eqr_mm': center})
            pins = []
            for face_index, face in enumerate(stop.Faces()):
                if face.geomType() != 'CYLINDER':
                    continue
                cylinder = BRepAdaptor_Surface(face.wrapped).Cylinder(); axis = cylinder.Axis().Direction()
                if abs(abs(axis.Z())-1.) > 1e-9 or abs(cylinder.Radius()-profile.pin_radius) > 1e-7:
                    continue
                location = cylinder.Location(); point = (location.X(), location.Y(), location.Z())
                e0, q0, r0 = contact_coordinates(side, point)
                pin_vertices = [contact_coordinates(side, vertex.Center()) for vertex in face.Vertices()]
                extents = [vertex[0] for vertex in pin_vertices]
                e = [min(extents), max(extents)]
                pin = cq.Solid.makeCylinder(cylinder.Radius(), e[1]-e[0],
                    cq.Vector(sign*(23.85+r0), 14.8+q0, 4.2+e[0]), cq.Vector(0, 0, 1))
                pins.append({'face': face_index, 'pin_q_mm': q0, 'pin_r_mm': r0, 'e_extent_mm': e,
                             'radius_mm': cylinder.Radius(), 'axis_direction_xyz': (axis.X(), axis.Y(), axis.Z()),
                             'cylinder_location_xyz': point, 'vertices_eqr_mm': pin_vertices,
                             'full_pin_outside_STOP_mm3': p.volume(pin.cut(stop))})
            record = {'side': side, 'STOP': index, 'floor_candidates': floors, 'pin_candidates': pins,
                      'negative_KEY_interval_mm': [-outside, 0.], 'native_plateau_extension_supported': False}
            if len(floors) == len(pins) == 1:
                floor, pin = floors[0], pins[0]
                q_range = [pin['pin_q_mm'], pin['pin_q_mm']+outside]
                overlap = min(floor['e_extent_mm'][1], pin['e_extent_mm'][1])-max(floor['e_extent_mm'][0], pin['e_extent_mm'][0])
                margins = [q_range[0]-floor['q_extent_mm'][0], floor['q_extent_mm'][1]-q_range[1]]
                supported = (floor['complete_trimmed_face_is_rectangle'] and min(margins) >= 0. and overlap > 0.
                    and pin['full_pin_outside_STOP_mm3'] <= 1e-7
                    and abs(pin['pin_r_mm']-profile.floor_height-profile.pin_radius) <= 1e-7
                    and abs(pin['pin_q_mm']-profile.pin_q) <= 1e-7)
                record.update(native_plateau_extension_supported=supported, contact_q_interval_mm=q_range,
                              finite_floor_q_edge_margins_mm=margins, contact_e_overlap_mm=overlap)
            records.append(record)
    return {'schema': 'razr-native-finite-plateau-extension-v1', 'rows': records,
            'all_four_current_native_floors_support_the_declared_negative_q_contact': len(records) == 4 and all(
                row['native_plateau_extension_supported'] for row in records),
            'restoring_force_and_physical_contact_qualified': False, 'formal_directed_rounding_certificate': False}


STUDY_SOURCE_PATHS = (
    'integration/probe_key_endpoint_extension.py',
    'tools/key_endpoint_resume.py',
    'run_key_endpoint_trials.py',
    'tests/test_key_endpoint_extension.py',
    'tests/test_key_endpoint_resume.py',
)
TRIAL_LABELS = tuple(row['label'] for pose in ('STOW', 'OPEN') for row in endpoint_trials(pose))
FALSE_FLAGS = (
    'execution_checks_passed', 'canonical_execution_claimed',
    'continuous_backlash_domain_proved', 'global_KEY_hard_stop_proved',
    'complete_product_motion_proved', 'physical_qualification', 'candidate_go',
    'fixture_fabrication_go', 'manufacturing_go', 'formal_directed_rounding_certificate',
    'whole_current_factory_acceptance_claimed', 'all_trial_states_accepted_by_existing_factory',
)


def study_source_snapshot(folder):
    folder = Path(folder).resolve()
    result = {}
    for name in STUDY_SOURCE_PATHS:
        path = folder/name
        if not path.is_file() or path.is_symlink() or path.resolve() != path:
            raise ValueError('missing or linked reviewed study source: '+name)
        result[name] = sha(path)
    return result


def selected_trials(labels):
    labels = list(labels)
    if (not labels or any(label not in TRIAL_LABELS for label in labels)
            or labels != sorted(set(labels), key=TRIAL_LABELS.index)):
        raise ValueError('select each declared finite trial once in canonical order')
    return labels


def trial_input(label):
    selected_trials([label])
    pose = label.split('_', 1)[0]
    trial = next(row for row in endpoint_trials(pose) if row['label'] == label)
    return {**trial, 'pose': pose, 'q_mm': trial['nominal_q_mm']+trial['KEY_offset_mm']}


def scope_for_pose(pose):
    if pose not in ('STOW', 'OPEN'):
        raise ValueError('one declared endpoint required')
    opened = pose == 'OPEN'
    joint = .1 if opened else .1+8.2/3
    return {'pose': pose, 'slide_mm': 79.75 if opened else 0., 'descent_mm': 8.2 if opened else 0.,
            'tabs_mm': [3., 3.], 'slot_flanks': [0., 0.],
            'telescope_offsets_each_mm': [joint]*3,
            'independent_left_right_offsets_explored': False}


def atomic_json(path, value):
    """The previous complete JSON survives serialization or replacement failure."""
    path = Path(path)
    data = (json.dumps(value, indent=2, allow_nan=False)+'\n').encode()
    temporary = None
    try:
        descriptor, name = tempfile.mkstemp(prefix='.'+path.name+'.', suffix='.tmp', dir=path.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class Checkpoint:
    def __init__(self, report, path, started=None):
        self.report, self.path = report, Path(path)
        self.started = time.perf_counter() if started is None else started

    def save(self):
        report = self.report
        expected, rows = report['expected_changed_pairs'], report['actual_native_changed_pairs']
        actual = [[row['a'], row['b']] for row in rows]
        if len(rows) > len(expected) or actual != expected[:len(rows)]:
            raise ValueError('checkpoint raw rows are not the complete ordered processed prefix')
        report['processed_pair_count'] = len(rows)
        report['pending_changed_pairs'] = expected[len(rows):]
        report['checkpoint_generation'] += 1
        report['seconds'] = time.perf_counter()-self.started
        atomic_json(self.path, report)


class TrialInterrupted(BaseException):
    pass


def interrupted(signum, frame):
    raise TrialInterrupted('received signal '+str(signum))


def initial_report(label, expected_head, own):
    trial = trial_input(label)
    return {'schema': 'razr-KEY-endpoint-single-trial-v2', 'source_commit': expected_head,
            'trial_label': label, 'trial_inputs': trial, 'scope': scope_for_pose(trial['pose']),
            **dict.fromkeys(FALSE_FLAGS, False),
            'status': 'pending', 'execution_completed': False,
            'diagnostic_execution_checks_passed': False, 'source_bytes_unchanged': False,
            'scratch_study_source': True, 'geometry_generator_imported': False, 'same_CAD_kernel': True,
            'executed_study_source': {'path': str(own), 'sha256': sha(own)},
            'complete_participant_names': [], 'moving_participants': [],
            'expected_changed_pairs': [], 'reused_unchanged_pairs': [],
            'actual_native_changed_pairs': [], 'pending_changed_pairs': [],
            'processed_pair_count': 0, 'positive_actual_Common': [], 'evaluation_failures': [],
            'existing_profile_rejections': [], 'finite_trial_material_clear': False,
            'positive_Common_STEP_export_limit_per_trial': 8,
            'all_positive_pair_numeric_records_retained_even_when_STEP_export_limit_reached': True,
            'positive_Common_means_penetrating_trial_not_usable_state': True,
            'checkpoint_generation': 0, 'seconds': 0.}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--trial', choices=TRIAL_LABELS, required=True)
    parser.add_argument('--control-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    root, output = args.root.resolve(), args.output.resolve()
    own, folder = Path(__file__).resolve(), Path(__file__).resolve().parents[1]
    if (output.exists() or output.is_relative_to(root) or own.is_relative_to(root)
            or len(args.expected_head) != 40
            or any(c not in '0123456789abcdef' for c in args.expected_head)):
        raise ValueError('new scratch output and full expected HEAD required')
    output.mkdir(parents=True)
    started = time.perf_counter()
    report = initial_report(args.trial, args.expected_head, own)
    checkpoint = Checkpoint(report, output/'report.json', started)
    checkpoint.save()
    previous_signal = signal.signal(signal.SIGTERM, interrupted)
    try:
        # These modules are stdlib-only. The full expected inventory is durable
        # before any CAD import or native construction can consume resources.
        sys.path[:0] = [str(folder/'tools'), str(root/'tools'), str(root/'integration')]
        import validate_product_nominal_report as postguard
        before = postguard.current_identity(root, args.expected_head)
        source_before = study_source_snapshot(folder)
        report.update(identity_before=before, study_source_sha256_before=source_before)
        baseline_path = args.control_report.resolve(strict=True)
        baseline_digest = sha(baseline_path)
        baseline = json.loads(baseline_path.read_text())
        pose = report['trial_inputs']['pose']
        receipt = postguard.validate_report(baseline, pose, args.expected_head, before)
        names = baseline['complete_participant_names']
        changed, fixed = pair_partition(names)
        report.update(complete_participant_names=names, moving_participants=sorted(moving_inventory(names)),
            expected_changed_pairs=[list(pair) for pair in changed],
            reused_unchanged_pairs=[list(pair) for pair in fixed],
            baseline_report={'pose': pose, 'path': str(baseline_path), 'sha256': baseline_digest},
            baseline_receipt_postcheck=receipt, status='constructing')
        checkpoint.save()
        import product_nominal_motion as nominal
        import product_routing_ep5 as ep5
        import cadquery as cq
        report['geometry_generator_imported'] = True
        p = nominal.p
        s, d = report['scope']['slide_mm'], report['scope']['descent_mm']
        accessory = pose == 'OPEN'
        parts, metadata = nominal.full_scene(s, d, 3., 3., open_hold=accessory, open_support=accessory)
        ep5.validate_factory_input_coverage(metadata['scene'], before['executed_source_sha256'])
        if sorted(parts) != names:
            raise ValueError('fresh complete endpoint inventory differs from the checked control receipt')
        profiles = p.native_inputs()[4]
        pose_record = {'pose': pose, 'participants': len(parts), 'complete_participant_names': sorted(parts),
            'native_scene_metadata': metadata, 'moving_participants': sorted(moving_inventory(parts)),
            'tabs_mm': [3., 3.], 'slot_flanks': [0., 0.],
            'telescope_allocation': metadata['scene']['telescope_offsets_by_side_mm']}
        report['pose_record'] = pose_record
        checkpoint.save()
        # This crosscheck covers every retained participant, including explicit
        # zero differences for identical topology; no omitted-body inference.
        cam, _, half = clearance_constants()
        inward = (min(profile.breakpoints[0] for side in 'LR' for profile in profiles[side])/4
                  if pose == 'STOW' else -.001)
        dx = inward*cam/half
        actual, _ = nominal.full_scene(s, d, 3., 3., key_offsets=(inward, inward), crosshead_offsets=(dx, dx),
                                        open_hold=accessory, open_support=accessory)
        expected = rigid_trial(parts, inward, dx)
        if set(actual) != set(parts):
            raise ValueError('accepted factory crosscheck omitted actual material')
        differences = {name: 0. if actual[name].isSame(expected[name]) else
                       max(p.volume(actual[name].cut(expected[name])), p.volume(expected[name].cut(actual[name])))
                       for name in sorted(parts)}
        if any(type(value) not in (int, float) or not math.isfinite(value) or not 0. <= value <= 1e-7
               for value in differences.values()):
            raise ValueError('rigid branch placement changed actual factory material')
        pose_record['in_domain_factory_crosscheck'] = {
            'KEY_offset_mm': inward, 'crosshead_offset_mm': dx,
            'all_participants_compared': len(parts), 'bidirectional_material_difference_mm3': differences}
        del actual, expected
        gc.collect()
        checkpoint.save()
        if pose == 'STOW':
            pose_record['native_plateau_contact_extension'] = native_plateau_extent(parts, profiles, p)
        else:
            pose_record['selected_lower_stop_positions_retained'] = True
            pose_record['new_lower_stop_force_or_retention_proof'] = False
        trial = report['trial_inputs']
        current = rigid_trial(parts, trial['KEY_offset_mm'], trial['crosshead_offset_mm'])
        for side in 'LR':
            for index, profile in enumerate(profiles[side]):
                try:
                    profile.evaluate(trial['q_mm'])
                except ValueError as exc:
                    report['existing_profile_rejections'].append({'side': side, 'STOP': index, 'error': str(exc)})
        if len(report['existing_profile_rejections']) != 4:
            raise ValueError('trial is not the declared missing software endpoint branch')
        report['status'] = 'evaluating'
        checkpoint.save()
        rows, positives, failures = (report[key] for key in
                                    ('actual_native_changed_pairs', 'positive_actual_Common', 'evaluation_failures'))
        for a, b in changed:
            try:
                result = p.strict_common(current[a], current[b])
                value = result['common_mm3']
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0.:
                    raise ValueError('invalid actual Common value')
            except Exception as exc:
                row = {'a': a, 'b': b, 'evaluation_failed': True, 'error': type(exc).__name__+': '+str(exc)}
                rows.append(row)
                failures.append(row)
                checkpoint.save()
            else:
                row = {'a': a, 'b': b, **result, 'rejected': value > 1e-7}
                rows.append(row)
                if row['rejected']:
                    export = None
                    if len(positives) < 8:
                        path = output/(trial['label']+'-positive-%02d.step' % (len(positives)+1))
                        def export():
                            cq.exporters.export(current[a].intersect(current[b]), str(path))
                            return {'path': path.name, 'sha256': sha(path)}
                    # The actual pair/volume is durable BEFORE exporting STEP.
                    failure = retain_positive(row, positives, export, checkpoint.save)
                    if failure is not None:
                        failures.append(failure)
                    checkpoint.save()
            if len(rows) % 128 == 0:
                checkpoint.save()
                print(json.dumps({'trial': trial['label'], 'completed_pairs': len(rows),
                                  'expected_pairs': len(changed), 'positive_pairs': len(positives),
                                  'errors': len(failures), 'seconds': time.perf_counter()-started}), flush=True)
        checkpoint.save()
        after = postguard.current_identity(root, args.expected_head)
        source_after = study_source_snapshot(folder)
        unchanged = before == after and source_before == source_after and sha(baseline_path) == baseline_digest
        report.update(identity_after=after, study_source_sha256_after=source_after,
                      source_bytes_unchanged=unchanged,
                      finite_trial_material_clear=not positives and not failures)
        if not unchanged or failures:
            raise ValueError('source changed or actual evaluation/export failed; partial data retained')
        report.update(status='complete', execution_completed=True, diagnostic_execution_checks_passed=True)
        report['seconds'] = time.perf_counter()-started
        import key_endpoint_resume as resume
        report['independent_trial_postcheck'] = resume.validate_completed_trial(
            report, expected_head=args.expected_head, expected_label=args.trial,
            current_identity=after, expected_study_sources=source_after,
            baseline_report=baseline, baseline_path=baseline_path, report_directory=output)
        if (postguard.current_identity(root, args.expected_head) != after
                or study_source_snapshot(folder) != source_after or sha(baseline_path) != baseline_digest):
            raise ValueError('source/baseline changed during completed-trial postcheck')
        checkpoint.save()
    except BaseException as exc:
        report.update(status='interrupted' if isinstance(exc, (TrialInterrupted, KeyboardInterrupt, SystemExit)) else 'failed',
            execution_completed=False, diagnostic_execution_checks_passed=False,
            finite_trial_material_clear=False, execution_failure=type(exc).__name__+': '+str(exc))
        try:
            checkpoint.save()
        except BaseException as save_error:
            print('checkpoint write failed; last atomic checkpoint retained: '+repr(save_error), file=sys.stderr, flush=True)
    finally:
        signal.signal(signal.SIGTERM, previous_signal)
    print(json.dumps({key: report.get(key) for key in (
        'trial_label', 'status', 'execution_completed', 'diagnostic_execution_checks_passed',
        'processed_pair_count', 'finite_trial_material_clear', 'execution_failure', 'seconds')}), flush=True)
    return 0 if report['execution_completed'] and report['diagnostic_execution_checks_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())

