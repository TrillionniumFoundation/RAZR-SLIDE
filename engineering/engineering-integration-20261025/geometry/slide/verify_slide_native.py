"""Prepare or execute a bounded full-material nominal SLIDE diagnostic.

CAD is imported only by --native. The scratch implementation preserves the
complete 154-material/11,781-pair inventory even after a resource stop. Its
external-pair result cannot grant G2, flexible self-validity, or physical release.
Run native work through supervise_slide_native.py for hard wall/RSS/global
capacity interruption while an individual CAD operation is in progress.
"""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
from dataclasses import asdict
from fractions import Fraction as F
import hashlib
import itertools
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

import slide_domain as d
import slide_evidence as evidence
import slide_checkpoint as checkpoint
import owned_process

HERE, ROOT = evidence.HERE, evidence.ROOT
DEFAULT_HEAD = '042b768903cccbd7a0995317c8598401e0318e2a'
OWN_NAMES = ('slide_domain.py', 'slide_evidence.py', 'verify_slide_native.py',
             'supervise_slide_native.py', 'check_slide_report.py',
             'test_slide_domain.py', 'test_slide_native_contracts.py',
             'slide_checkpoint.py', 'check_slide_checkpoint.py',
             'test_slide_checkpoint.py', 'test_slide_supervisor_lifecycle.py',
             'owned_process.py', 'test_owned_process.py')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_identity():
    expected_executed = ((Path(__file__), HERE/'verify_slide_native.py'),
                         (Path(d.__file__), HERE/'slide_domain.py'),
                         (Path(evidence.__file__), HERE/'slide_evidence.py'),
                         (Path(checkpoint.__file__), HERE/'slide_checkpoint.py'),
                         (Path(owned_process.__file__), HERE/'owned_process.py'))
    for actual, expected in expected_executed:
        evidence.require(actual.resolve() == expected.resolve(),
                         'executed scratch entrypoint/module differs from its declared source path')
    expected_helpers = ((evidence.cages, evidence.HELPER_DIR/'slide_enclosures.py'),
                        (evidence.cages.shared, HERE.parent/'seating/seating_enclosures.py'),
                        (evidence.cages.shared_domain, HERE.parent/'seating/seating_domain.py'))
    for module, path in expected_helpers:
        evidence.require(Path(module.__file__).resolve() == path.resolve(),
                         'executed flexible helper is outside its explicit source-owned path')
    paths = [*(HERE/name for name in OWN_NAMES), evidence.INVENTORY,
             Path(evidence.cages.__file__).resolve(),
             Path(evidence.cages.shared.__file__).resolve(),
             Path(evidence.cages.shared_domain.__file__).resolve()]
    for path in paths:
        evidence.require(path.is_file() and not path.is_symlink(), 'missing or linked scratch source: '+str(path))
    return {str(path): sha(path) for path in sorted(set(paths))}


def resource_snapshot(folder='/tmp'):
    fields = {}
    for row in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines():
        key, value = row.split(); fields[key] = int(value)
    available = os.statvfs(folder)
    return {'f_bavail_bytes': available.f_bavail*available.f_frsize,
            'estimated_unreclaimable_bytes': fields.get('anon', 0)+fields.get('shmem', 0)
                +max(0, fields.get('kernel', 0)-fields.get('slab_reclaimable', 0))+fields.get('unevictable', 0),
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}


class BudgetExceeded(RuntimeError):
    def __init__(self, message, partial=None):
        super().__init__(message)
        self.partial = partial


class Budget:
    def __init__(self, args):
        self.args, self.started, self.calls = args, time.monotonic(), 0

    def check(self, operator=False):
        now = resource_snapshot(self.args.output.parent)
        if time.monotonic()-self.started > 1800:
            raise BudgetExceeded('1800-second native diagnostic wall budget exhausted')
        if now['f_bavail_bytes'] < 100*2**20:
            raise BudgetExceeded('ordinary-user disk reserve fell below 100 MiB')
        if now['peak_RSS_bytes'] > 1536*2**20:
            raise BudgetExceeded('observed peak RSS exceeded 1536 MiB')
        if now['estimated_unreclaimable_bytes'] > 6.8*2**30:
            raise BudgetExceeded('shared estimated unreclaimable memory exceeded 6.8 GiB')
        if operator:
            self.calls += 1

    def record(self):
        return {'elapsed_seconds': time.monotonic()-self.started,
                'continuous_pair_calls': self.calls, **resource_snapshot(self.args.output.parent),
                'wall_limit_seconds': 1800, 'peak_RSS_limit_MiB': 1536,
                'shared_unreclaimable_limit_GiB': 6.8, 'runtime_ordinary_disk_reserve_MiB': 100,
                'internal_checks_between_operators_only': True,
                'external_supervisor_required_for_inflight_operator_limits': True}


def atomic_json(path, record):
    temporary = path.with_name(path.name+'.partial')
    with temporary.open('w') as stream:
        json.dump(record, stream, separators=(',', ':'), allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    temporary.replace(path)


def profile_records(profiles):
    return [asdict(profile) for profile in profiles]


def execution_limits(maximum_subdivision_depth):
    evidence.require(type(maximum_subdivision_depth) is int and maximum_subdivision_depth in range(4),
                     'source-owned maximum subdivision depth must be an integer in [0,3]')
    return {'wall_limit_seconds': 1800, 'peak_RSS_limit_MiB': 1536,
            'shared_unreclaimable_limit_GiB': 6.8, 'runtime_ordinary_disk_reserve_MiB': 100,
            'supervisor_startup_ordinary_disk_reserve_MiB': 200,
            'supervisor_startup_incremental_memory_reserve_MiB': 1536,
            'maximum_subdivision_depth': maximum_subdivision_depth}


def pair_visit_order(rows):
    # Identical to the v2 native order: preserve every original raw report index.
    return sorted(range(len(rows)), key=lambda i: (evidence.pair_class(rows[i]['a'], rows[i]['b']).startswith('flex'), i))


probe_inputs = evidence.probe_inputs
validate_construction = evidence.validate_construction


class BoundedBodies:
    """Bounded native cache; no pair-count-sized retained geometry cache."""
    def __init__(self, base, contract, nominal, p, budget):
        self.base, self.contract = base, contract
        self.nominal, self.p, self.budget = nominal, p, budget
        self.cache = OrderedDict()
        self.maximum = 32

    def material(self, descriptor, low, high):
        kind, name = descriptor['kind'], descriptor['material']
        if kind == 'complete_rigid_material':
            return self.base[name]
        key = evidence.digest_json(descriptor)
        if key not in self.cache:
            self.budget.check()
            if kind == 'complete_growing_spring_cylinder':
                start, end = descriptor['axis_start_mm'], descriptor['axis_end_mm']
                body = self.p.single(self.p.cq.Solid.makeCylinder(descriptor['radius_mm'], end[0]-start[0],
                        self.p.cq.Vector(*start), self.p.cq.Vector(1., 0., 0.)))
            elif kind == 'finite_flexible_cage':
                rows = self.contract.cage_rows(name, low, high, descriptor['reference_frame'])
                row = next(r for r in rows if r['label'] == descriptor['cage_label'])
                evidence.require(evidence.digest_json(row) == descriptor['cage_sha256'], 'cage source changed')
                body = evidence.cages.native_cage(row)
            else:
                raise ValueError('unsupported whole material descriptor')
            self.p.whole_material(body)
            self.cache[key] = body
            while len(self.cache) > self.maximum:
                self.cache.popitem(last=False)
            self.budget.check()
        self.cache.move_to_end(key)
        return self.cache[key]


def complete_difference(actual, expected, p):
    p.whole_material(actual); p.whole_material(expected)
    if actual.isSame(expected):
        return [0., 0.]
    result = [p.volume(actual.cut(expected)), p.volume(expected.cut(actual))]
    evidence.require(all(evidence.postguard.finite(v) and v >= 0. for v in result),
                     'nonfinite/negative bidirectional complete material difference')
    return result


def verify_factory_laws(base, metadata, contract, nominal, p, identity, budget, bodies, record, checkpoint):
    evidence.validate_metadata(metadata)
    # Verify the full original spring cylinder before extending it. Bounding-box
    # equality alone is never accepted as a material identity argument.
    base_springs = record['original_complete_spring_identity']
    for name in sorted(d.SPRINGS):
        budget.check()
        desc = contract.springs[name].record(contract.profiles, 0, 0)
        difference = complete_difference(base[name], bodies.material(desc, F(0), F(0)), p)
        evidence.require(max(difference) <= evidence.TOL, 'base spring is not the complete original X cylinder')
        base_springs.append({'material': name, 'bidirectional_difference_mm3': difference,
                             'spring_descriptor': desc})
    probes = record['probes']
    for inputs in probe_inputs(contract.profiles):
        budget.check()
        q = F(inputs['q_exact']); left = tuple(map(F, inputs['joints_left_exact']))
        right = tuple(map(F, inputs['joints_right_exact'])); flanks = inputs['flanks']
        actual, meta = nominal.full_scene(float(d.SLIDE_PER_Q*q), 0., 3., 3., flanks=flanks,
                telescope_offsets={'L': list(map(float, left)), 'R': list(map(float, right))},
                key_offsets=(0., 0.), crosshead_offsets=(0., 0.), open_hold=False, open_support=False)
        evidence.cages.ep5.validate_factory_input_coverage(meta['scene'], identity['executed_source_sha256'])
        evidence.require(sorted(actual) == contract.names, 'factory law probe changed the complete material inventory')
        checked = []
        flexible = []
        probes.append({'inputs': inputs, 'complete_participant_names': sorted(actual),
                       'native_scene_metadata': meta, 'material_law_checks': checked,
                       'flexible_materials_retained': flexible,
                       'source_laws_not_inferred_from_samples': True})
        for name in sorted(set(contract.names)-d.FLEX):
            budget.check()
            if name in d.SPRINGS:
                desc = contract.springs[name].record(contract.profiles, q, q)
                expected = bodies.material(desc, q, q)
            else:
                shift = contract.laws[name].coordinates(q, left, right, flanks, contract.profiles)
                expected = base[name].translate(shift) if any(shift) else base[name]
            difference = complete_difference(actual[name], expected, p)
            checked.append({'material': name, 'bidirectional_difference_mm3': difference})
            evidence.require(max(difference) <= evidence.TOL, 'source law fails on actual complete factory material: '+name)
        for name in sorted(d.FLEX):
            solids, volume = p.whole_material(actual[name])
            flexible.append({'material': name, 'positive_solid_count': len(solids),
                             'whole_volume_mm3': volume, 'whole_material_validation_passed': True})
        checkpoint()
        print(json.dumps({'stage': 'factory_law_probe', 'q_exact': str(q), **budget.record()}), flush=True)
        del actual
        # full_scene keeps only fixed-pose route bodies; discard completed probe
        # entries so a long profile list cannot retain many finite flex solids.
        nominal.fixed_route_parts.cache_clear()
    return record


def evaluate_interval(a, b, low, high, contract, bodies, budget, depth=0, maximum_depth=2):
    row = {'q_interval_exact': [str(low), str(high)], 'attempts': [],
           'disposition': 'unresolved_enclosure_overlap', 'collision_proved': False}
    frames = ('A', 'B') if evidence.pair_class(a, b).startswith('flex') else ('A',)
    for frame in frames:
        attempt = {'reference_frame': frame, 'records': []}
        row['attempts'].append(attempt)
        try:
            specs = contract.specifications(a, b, low, high, frame)
            for spec in specs:
                budget.check(operator=True)
                moving = bodies.material(spec['moving'], low, high)
                fixed = bodies.material(spec['fixed'], low, high)
                raw = bodies.nominal.continuous_pair(moving, fixed, spec['coefficients'],
                        domain=tuple(map(tuple, spec['parameter_intervals'])), cache=None)
                attempt['records'].append({'specification': spec, 'raw': raw})
                budget.check()
            attempt.update(evidence.aggregate(attempt['records']))
        except BudgetExceeded as exc:
            attempt.update(disposition='unresolved_budget', resource_stop=str(exc))
            row.update(disposition='unresolved_budget', resource_stop=str(exc))
            exc.partial = row
            raise
        except Exception as exc:
            attempt.update(disposition='unresolved_evaluation', error=type(exc).__name__+': '+str(exc))
        if attempt['disposition'] == 'clear':
            row.update(disposition='clear', method='whole_material_relative_enclosure')
            return row
    if any(attempt['disposition'] == 'unresolved_evaluation' for attempt in row['attempts']):
        row['disposition'] = 'unresolved_evaluation'
        return row
    if depth <= maximum_depth and low < high:
        split = 'all_actual_profile_breakpoints' if depth == 0 else 'closed_midpoint_bisection'
        intervals = contract.child_intervals(low, high, split)
        row.update(split=split, children=[])
        for child_low, child_high in intervals:
            try:
                row['children'].append(evaluate_interval(a, b, child_low, child_high, contract, bodies,
                        budget, depth+1, maximum_depth))
            except BudgetExceeded as exc:
                if exc.partial is not None:
                    row['children'].append(exc.partial)
                row.update(disposition='unresolved_budget', resource_stop=str(exc))
                exc.partial = row
                raise
        if all(child['disposition'] == 'clear' for child in row['children']):
            row.update(disposition='clear', method='complete_closed_interval_partition')
    return row


def preparation(expected_head):
    before = source_identity()
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    evidence.require(expected_head == head and len(head) == 40, 'unexpected current repository HEAD')
    names = evidence.expected_names()
    classes = Counter(evidence.pair_class(a, b) for a, b in itertools.combinations(names, 2))
    evidence.require(dict(classes) == evidence.CLASS_COUNTS, 'incomplete full pair classification')
    report = {'schema': 'razr-slide-runner-preparation-v1', 'expected_head': expected_head,
              'domain': evidence.recorded_domain(), 'complete_participant_names': names,
              'pair_class_counts': dict(classes), 'expected_pair_count': 11781,
              'flexible_material_contract': evidence.cages.material_contract(),
              'scratch_source_sha256_before': before, 'scratch_source_sha256_after': source_identity(),
              'native_checks_executed': False, 'CAD_imported': any(n == 'cadquery' or n == 'OCP' or n.startswith('OCP.') for n in sys.modules),
              **{key: False for key in evidence.FALSE_FLAGS}}
    evidence.require(report['scratch_source_sha256_after'] == before and report['CAD_imported'] is False,
                     'preparation changed sources or imported CAD')
    return report


def run_native(args):
    # Nothing above this function imports CAD or constructs native material.
    names = evidence.expected_names()
    rows = [{'a': a, 'b': b, 'pair_class': evidence.pair_class(a, b), 'disposition': 'not_evaluated'}
            for a, b in itertools.combinations(names, 2)]
    report = {'schema': 'razr-full-nominal-slide-native-diagnostic-v1', 'expected_head': args.expected_head,
              'domain': evidence.recorded_domain(), 'complete_participant_names': names, 'participant_count': len(names),
              'expected_pair_count': len(rows), 'pair_count': len(rows), 'pairs': rows,
              'pair_class_counts': dict(evidence.CLASS_COUNTS), 'scratch_source_sha256_before': source_identity(),
              'execution_limits': execution_limits(args.maximum_subdivision_depth),
              'native_checks_executed': False, 'execution_completed': False,
              'construction_probes_complete': False, **{key: False for key in evidence.FALSE_FLAGS}}
    atomic_json(args.output, report)
    budget = Budget(args)
    before = after = contract = journal = None
    current_index = None
    try:
        budget.check()
        import product_nominal_motion as nominal
        import product_assembly as p
        before = nominal.execution_identity(args.expected_head)
        report['identity_before'] = before
        guard_path = ROOT/'tools/validate_product_nominal_report.py'
        evidence.require(Path(evidence.postguard.__file__).resolve() == guard_path
                         and before['head_bound_source_sha256'].get('tools/validate_product_nominal_report.py') == sha(guard_path),
                         'executed independent native raw validator is not HEAD-bound')
        report['domain'] = evidence.recorded_domain(evidence.original_profiles())
        order = pair_visit_order(rows)
        context = checkpoint.context_record(args.expected_head, report['domain'], names, order,
            report['scratch_source_sha256_before'], before, report['execution_limits'], args.output.name)
        journal = checkpoint.PairJournal(args.output.parent/'pairs.jsonl', context)
        reference = {side: [float(d.JOINT_NOMINAL)]*3 for side in 'LR'}
        base, metadata = nominal.full_scene(0., 0., 3., 3., flanks=(0., 0.), telescope_offsets=reference,
                key_offsets=(0., 0.), crosshead_offsets=(0., 0.), open_hold=False, open_support=False)
        evidence.cages.ep5.validate_factory_input_coverage(metadata['scene'], before['executed_source_sha256'])
        evidence.validate_metadata(metadata)
        report['native_scene_metadata'] = metadata
        inputs = p.native_inputs()
        profiles = tuple(profile for side in 'LR' for profile in inputs[4][side])
        evidence.require(profiles == evidence.original_profiles(), 'native factory profiles differ from frozen source')
        halfwidth = {side: inputs[5][side]['halfwidth'] for side in 'LR'}
        laws = d.rigid_laws(base, halfwidth, names)
        for body in base.values():
            p.whole_material(body)
        springs = {name: evidence.Spring(name, tuple(p.bounds(base[name]))) for name in d.SPRINGS}
        contract = evidence.Contract(names, laws, profiles, springs)
        report.update(domain=evidence.recorded_domain(profiles), profiles=profile_records(profiles),
                      native_slot_halfwidth_mm=halfwidth,
                      rigid_motion_laws={name: law.record() for name, law in sorted(laws.items())},
                      base_spring_records={name: spring.record(profiles, 0, 0) for name, spring in sorted(springs.items())})
        evidence.require(report['domain'] == context['domain'], 'actual native domain differs from the source-bound journal')
        bodies = BoundedBodies(base, contract, nominal, p, budget)
        report['construction'] = {'original_complete_spring_identity': [], 'probes': [],
                                  'source_laws_not_inferred_from_samples': True}
        verify_factory_laws(base, metadata, contract, nominal, p, before, budget, bodies,
                            report['construction'], lambda: atomic_json(args.output, report))
        report['construction_probes_complete'] = validate_construction(report['construction'], contract)
        report['native_checks_executed'] = True
        atomic_json(args.output, report)
        journal.record_construction(report)
        # Nonflex work first, but the report always retains all 11,781 pairs.
        evidence.require(order == pair_visit_order(rows), 'journal visit order differs from the native pair order')
        for number, current_index in enumerate(order, 1):
            budget.check()
            current = rows[current_index]
            journal.record_start(current_index, current)
            result = evaluate_interval(current['a'], current['b'], F(0), d.QMAX, contract, bodies, budget,
                                       maximum_depth=args.maximum_subdivision_depth)
            rows[current_index] = {**current, **result}
            journal.record_complete(current_index, rows[current_index])
            if number % 128 == 0:
                report.update(resource=budget.record(), completed_pair_count=number,
                              counts=dict(Counter(row['disposition'] for row in rows)))
                print(json.dumps({'stage': 'pairs', 'evaluated': number, **budget.record()}), flush=True)
        report['execution_completed'] = True
    except BudgetExceeded as exc:
        report['terminal_failure'] = 'BudgetExceeded: '+str(exc)
        if exc.partial is not None:
            report['interrupted_pair_partial_evidence'] = exc.partial
            if current_index is not None:
                rows[current_index] = {**rows[current_index], **exc.partial}
    except Exception as exc:
        report['terminal_failure'] = type(exc).__name__+': '+str(exc)
    finally:
        if journal is not None and report.get('terminal_failure') and not journal.broken:
            try:
                raw = rows[journal.active['raw_pair_index']] if journal.active is not None else None
                journal.record_interruption(report['terminal_failure'], raw)
            except Exception as exc:
                report['checkpoint_write_failure'] = type(exc).__name__+': '+str(exc)
        try:
            if before is not None:
                after = nominal.execution_identity(args.expected_head)
                report['identity_after'] = after
            own_after = source_identity()
            report['scratch_source_sha256_after'] = own_after
            if contract is not None:
                # Never trust the producer's construction boolean alone.
                report['construction_probes_complete'] = validate_construction(report.get('construction', {}), contract)
                report.update(evidence.complete_result(report, contract, after, own_after))
                # Validation itself reads source-owned profiles/configuration.
                # Bind the final bytes after the reader has completed as well.
                evidence.require(source_identity() == own_after
                                 and nominal.execution_identity(args.expected_head) == after,
                                 'source/runtime changed while independently checking the raw receipt')
            else:
                report.update(complete_native_diagnostic_executed=False,
                              whole_declared_slide_external_pair_domain_clear=False)
        except Exception as exc:
            report.update(postflight_failure=type(exc).__name__+': '+str(exc),
                          complete_native_diagnostic_executed=False,
                          whole_declared_slide_external_pair_domain_clear=False)
        try:
            report.update(resource=budget.record(), counts=dict(Counter(row['disposition'] for row in rows)))
        except Exception as exc:
            report.update(postflight_failure=type(exc).__name__+': '+str(exc),
                          complete_native_diagnostic_executed=False,
                          whole_declared_slide_external_pair_domain_clear=False)
        if journal is None or journal.broken or report.get('checkpoint_write_failure'):
            report.update(complete_native_diagnostic_executed=False,
                          whole_declared_slide_external_pair_domain_clear=False)
        try:
            if journal is not None and not journal.broken and not report.get('checkpoint_write_failure'):
                journal.record_postflight(report)
                journal.publish_report(args.output, report)
            else:
                atomic_json(args.output, report)
        except Exception as exc:
            # A valid prefix remains useful evidence, but a torn or unindexed
            # final publication cannot qualify as a complete diagnostic.
            report.update(checkpoint_write_failure=type(exc).__name__+': '+str(exc),
                          complete_native_diagnostic_executed=False,
                          whole_declared_slide_external_pair_domain_clear=False)
            atomic_json(args.output, report)
        finally:
            if journal is not None:
                journal.close()
    print(json.dumps({key: report.get(key) for key in ('counts', 'complete_native_diagnostic_executed',
          'whole_declared_slide_external_pair_domain_clear', 'terminal_failure', 'postflight_failure', 'resource')}), flush=True)
    return 0 if report.get('complete_native_diagnostic_executed') else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-head', default=DEFAULT_HEAD)
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--maximum-subdivision-depth', type=int, default=2, choices=range(4))
    args = parser.parse_args(argv)
    if args.native:
        # Only the supervising parent's validated nonce release permits CAD.
        owned_process.announce_worker_from_environment(Path(__file__))
    args.output = args.output.resolve()
    evidence.require(not args.output.exists() and not args.output.is_relative_to(ROOT.resolve()),
                     'new report outside frozen repository required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.native:
        return run_native(args)
    atomic_json(args.output, preparation(args.expected_head))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
