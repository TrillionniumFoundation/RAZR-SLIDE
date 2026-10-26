"""New complete finite KEY trial; no reuse of a 042 fixed-pair certificate.

Every unordered pair of the actual 154/161 finite solids is evaluated. The
original v4 rigid-trial and finite-floor helpers are reused without modifying
the production profile. This is a new research execution, not original v4 or
continuous-domain qualification. Launch through supervise_key.py.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gc
import itertools
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE/'integration'), str(HERE.parent/'slide')]
import execution_identity as identity
import probe_key_endpoint_extension as original
import owned_process
import body_inventory

FALSE_FLAGS = ('original_v4_execution_claimed', 'continuous_backlash_domain_proved',
               'complete_product_motion_proved', 'physical_qualification',
               'candidate_go', 'fixture_fabrication_go', 'manufacturing_go')
TRIAL_LABELS = (*original.TRIAL_LABELS, 'STOW_OUTSIDE_ORTHOGONAL')


def trial_input(label):
    if label != 'STOW_OUTSIDE_ORTHOGONAL':
        return original.trial_input(label)
    cam, yoke, _ = original.clearance_constants()
    return {'label': label, 'pose': 'STOW', 'KEY_offset_mm': cam-yoke,
            'crosshead_offset_mm': cam, 'nominal_q_mm': 0., 'q_mm': cam-yoke,
            'orthogonal_slot_vertex': 'dx=+cam, dx-dq=+yoke'}


def resources(path):
    stats = dict((key, int(value)) for key, value in
                 (line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines()))
    disk = os.statvfs(path)
    return {'available_disk_bytes': disk.f_bavail*disk.f_frsize,
            'shared_unreclaimable_bytes': stats.get('anon', 0)+stats.get('shmem', 0)
                + max(0, stats.get('kernel', 0)-stats.get('slab_reclaimable', 0))+stats.get('unevictable', 0),
            'worker_peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}


def check_budget(output, started):
    r = resources(output)
    if (time.monotonic()-started > 1200 or r['available_disk_bytes'] < 100*2**20
            or r['shared_unreclaimable_bytes'] > 6.8*2**30 or r['worker_peak_RSS_bytes'] > 1536*2**20):
        raise RuntimeError('original KEY wall/disk/shared-memory or stronger 1536MiB RSS guard reached')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial', choices=TRIAL_LABELS, required=True)
    parser.add_argument('--candidate', choices=('none', 'stow_face_relief', 'stow_two_layer_face_relief'), default='none')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    owned_process.announce_worker_from_environment(Path(__file__))
    out = args.output.resolve()
    if out.exists() or out.is_relative_to(identity.ROOT):
        raise ValueError('new output outside the repository required')
    out.mkdir(parents=True)
    started = time.monotonic()
    report = {'schema': 'razr-complete-finite-KEY-trial-20261025-v1', 'trial': trial_input(args.trial),
              'status': 'preparing', 'execution_completed': False,
              'pairs': [], 'positive_actual_Common': [], 'evaluation_failures': [],
              'actual_geometry_generated': False, **{key: False for key in FALSE_FLAGS}}
    target = out/'report.json'
    def save():
        report['seconds'] = time.monotonic()-started
        report['persisted_completed_pair_count'] = len(report['pairs'])
        identity.atomic_json(target, report)
    def interrupted(signum, frame):
        raise InterruptedError('owned supervisor sent signal '+str(signum))
    previous = signal.signal(signal.SIGTERM, interrupted)
    before = None
    save()
    try:
        before = identity.snapshot()
        executed_project_files = identity.record_executed_project_files()
        report['identity_before'] = before
        save()
        sys.path[:0] = [str(identity.ROOT/'integration'), str(identity.ROOT/'tools')]
        import product_nominal_motion as nominal
        import product_routing_ep5 as ep5
        import cadquery as cq
        p = nominal.p
        trial = report['trial']
        opened = trial['pose'] == 'OPEN'
        s, d = (79.75, 8.2) if opened else (0., 0.)
        parts, metadata = nominal.full_scene(s, d, 3., 3., open_hold=opened, open_support=opened)
        ep5.validate_factory_input_coverage(metadata['scene'], before['available_source_sha256'])
        expected_count = 161 if opened else 154
        if len(parts) != expected_count:
            raise ValueError('complete nominal material inventory differs')
        names = sorted(parts)
        changed, fixed = original.pair_partition(names)
        report.update(actual_geometry_generated=True, native_scene_metadata=metadata,
                      complete_participant_names=names, participant_count=len(names),
                      expected_pair_count=len(names)*(len(names)-1)//2,
                      expected_changed_pair_count=len(changed), expected_fixed_pair_count=len(fixed),
                      original_control_baseline_reused=False,
                      scope={'tabs_mm': [3., 3.], 'flanks': [0., 0.], 'slide_mm': s, 'descent_mm': d,
                             'telescope_allocation': metadata['scene']['telescope_offsets_by_side_mm']})
        report['nominal_parts'] = body_inventory.measure(parts, metadata, p)
        report['structural_model_handoff'] = {
            'input_roles': before['native_input_roles'],
            'actual_scene_inventory_preserved': True,
            'all_body_names_have_actual_native_volume_and_bounds': True,
            'material_or_constitutive_assignment_inferred_from_geometry': False,
            'current_complete_EP5_finite_element_model_built': False,
            'old_PR34_structural_result_applicable': False}
        save()
        profiles = p.native_inputs()[4]
        cam, _, half = original.clearance_constants()
        inward = (min(profile.breakpoints[0] for side in 'LR' for profile in profiles[side])/4
                  if not opened else -.001)
        inward_dx = inward*cam/half
        actual, _ = nominal.full_scene(s, d, 3., 3., key_offsets=(inward, inward),
                                     crosshead_offsets=(inward_dx, inward_dx),
                                     open_hold=opened, open_support=opened)
        expected = original.rigid_trial(parts, inward, inward_dx)
        if set(actual) != set(parts):
            raise ValueError('in-domain production crosscheck omitted complete material')
        differences = {name: 0. if actual[name].isSame(expected[name]) else
                       max(p.volume(actual[name].cut(expected[name])), p.volume(expected[name].cut(actual[name])))
                       for name in names}
        if any(type(value) not in (int, float) or not math.isfinite(value) or not 0. <= value <= 1e-7
               for value in differences.values()):
            raise ValueError('rigid trial law differs from accepted full-scene native material')
        report['in_domain_factory_crosscheck'] = {
            'KEY_offset_mm': inward, 'crosshead_offset_mm': inward_dx,
            'all_participants_compared': len(parts), 'bidirectional_material_difference_mm3': differences}
        del actual, expected
        gc.collect()
        save()
        if args.candidate != 'none':
            if opened:
                raise ValueError('this finite relief candidate is explicitly a STOW study')
            if args.candidate == 'stow_two_layer_face_relief':
                import stow_two_layer_face_relief as selected_relief
            else:
                import stow_face_relief as selected_relief
            report['baseline_nominal_parts'] = report['nominal_parts']
            parts, candidate = selected_relief.apply(parts, p, out/'relief', identity.sha)
            report['candidate'] = candidate
            report['nominal_parts'] = body_inventory.measure(parts, metadata, p)
            save()
        if not opened:
            report['native_plateau_extent'] = original.native_plateau_extent(parts, profiles, p)
        current = original.rigid_trial(parts, trial['KEY_offset_mm'], trial['crosshead_offset_mm'])
        if set(current) != set(parts):
            raise ValueError('finite trial omitted complete material')
        report['current_parts'] = body_inventory.measure(current, metadata, p)
        if report.get('candidate') is not None:
            for row in report['candidate']['material_changes']:
                for phase in ('nominal_parts', 'current_parts'):
                    report[phase][row['part']]['additional_research_candidate_relief'] = row
        report['production_profile_rejections'] = []
        for side in 'LR':
            for index, profile in enumerate(profiles[side]):
                try:
                    profile.evaluate(trial['q_mm'])
                except ValueError as exc:
                    report['production_profile_rejections'].append({'side': side, 'stop': index, 'error': str(exc)})
        if len(report['production_profile_rejections']) != 4:
            raise ValueError('all original production profiles must still reject the outside trial')
        report['status'] = 'evaluating_complete_finite_pairs'
        save()
        with (out/'pairs.jsonl').open('x') as journal:
            for count, (a, b) in enumerate(changed+fixed, 1):
                check_budget(out, started)
                journal.write(json.dumps({'event': 'selected', 'a': a, 'b': b})+'\n')
                journal.flush()
                try:
                    measured = p.strict_common(current[a], current[b])
                    value = measured['common_mm3']
                    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                        raise ValueError('nonfinite or negative complete Common')
                    row = {'a': a, 'b': b, **measured, 'rejected': value > 1e-7}
                    report['pairs'].append(row)
                    if value > 0:
                        positive = dict(row)
                        report['positive_actual_Common'].append(positive)
                        save()  # Keep the numeric pair before an export can fail.
                        path = out/('positive-%04d.step' % len(report['positive_actual_Common']))
                        common = current[a].intersect(current[b])
                        cq.exporters.export(common, str(path))
                        positive['actual_Common_STEP'] = {'path': path.name, 'sha256': identity.sha(path)}
                        del common
                        save()
                except Exception as exc:
                    failure = {'a': a, 'b': b, 'evaluation_failed': True,
                               'error': type(exc).__name__+': '+str(exc)}
                    if not report['pairs'] or (report['pairs'][-1].get('a'), report['pairs'][-1].get('b')) != (a, b):
                        report['pairs'].append(failure)
                    report['evaluation_failures'].append(failure)
                    save()
                journal.write(json.dumps({'event': 'completed', 'row': report['pairs'][-1]}, allow_nan=False)+'\n')
                journal.flush()
                if count % 16 == 0:
                    os.fsync(journal.fileno())
                if count % 256 == 0:
                    save()
                    print(json.dumps({'pairs': count, 'expected': report['expected_pair_count'],
                                      'positive': len(report['positive_actual_Common']),
                                      'seconds': time.monotonic()-started}), flush=True)
            os.fsync(journal.fileno())
        after = identity.finish(before, [__file__, original.__file__, owned_process.__file__,
                                         identity.__file__, body_inventory.__file__, *executed_project_files,
                                         identity.ROOT/metadata['research_relief']['KEY_source']['reference_geometry_source']])
        report['identity_after'] = after
        actual_pairs = [(row['a'], row['b']) for row in report['pairs']]
        inventory_complete = len(actual_pairs) == len(set(actual_pairs)) == report['expected_pair_count']
        inventory_complete &= set(actual_pairs) == set(itertools.combinations(names, 2))
        complete = inventory_complete
        complete &= not report['evaluation_failures'] and after['source_bytes_and_locked_environment_unchanged']
        report.update(status='complete' if complete else 'failed_validation', execution_completed=bool(complete),
                      all_unordered_pairs_present_once=bool(inventory_complete),
                      finite_trial_clear=bool(complete and not any(row['rejected'] for row in report['pairs'])),
                      method_counts=dict(Counter(row.get('method', 'error') for row in report['pairs'])))
        save()
    except BaseException as exc:
        report.update(status='interrupted_or_failed', execution_completed=False,
                      failure=type(exc).__name__+': '+str(exc))
        save()
    finally:
        signal.signal(signal.SIGTERM, previous)
    print(json.dumps({key: report.get(key) for key in ('status', 'execution_completed', 'finite_trial_clear',
                                                    'persisted_completed_pair_count', 'failure', 'seconds')}), flush=True)
    return 0 if report['execution_completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
