"""Independent persisted-pair and complete STEP reader; no product factory rebuild.

Run structural checks without --native. Native readback must be launched by
supervise_key.py. This uses the same CAD kernel, independently of the builder.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent/'slide')]
import execution_identity as identity
import owned_process
import stow_two_layer_face_relief as relief_v2

FALSE_FLAGS = ('original_v4_execution_claimed', 'continuous_backlash_domain_proved',
               'complete_product_motion_proved', 'physical_qualification',
               'candidate_go', 'fixture_fabrication_go', 'manufacturing_go')
TOL = 1e-7


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_report(report, *, allow_partial=False):
    require(report.get('schema') == 'razr-complete-finite-KEY-trial-20261025-v1', 'unexpected report schema')
    require(all(report.get(key) is False for key in FALSE_FLAGS), 'unearned qualification flag')
    names = report['complete_participant_names']
    require(type(names) is list and names == sorted(set(names)), 'unique ordered complete participant names required')
    expected_count = 161 if report['trial']['pose'] == 'OPEN' else 154
    require(len(names) == report['participant_count'] == expected_count, 'complete finite inventory required')
    require(set(report['nominal_parts']) == set(report['current_parts']) == set(names), 'nominal or trial material omitted')
    for phase in ('nominal_parts', 'current_parts'):
        for item in report[phase].values():
            require(finite(item['volume_mm3']) and item['volume_mm3'] > 0, 'positive complete body volume required')
            require(type(item['solid_count']) is int and item['solid_count'] >= 1, 'complete positive solid inventory required')
            bounds = item['bounds_mm']
            require(type(bounds) is list and len(bounds) == 6 and all(finite(v) for v in bounds)
                    and all(bounds[i+1] > bounds[i] for i in (0, 2, 4)), 'invalid complete body bounds')
            require(item['material_assignment_present'] is False and item['old_PR34_structural_result_applicable'] is False,
                    'geometry inventory cannot qualify a material or reuse old structure')
    expected = set(itertools.combinations(names, 2))
    require(report['expected_pair_count'] == len(expected), 'pair inventory count differs')
    pairs = report['pairs']
    actual = [(r['a'], r['b']) for r in pairs]
    require(len(actual) == len(set(actual)) and set(actual) <= expected, 'duplicate, reversed or foreign pairs')
    positive = {}
    rejected = []
    failures = []
    for row in pairs:
        pair = (row['a'], row['b'])
        if row.get('evaluation_failed'):
            failures.append(pair)
            continue
        value = row['common_mm3']
        require(finite(value) and value >= 0, 'finite nonnegative Common required')
        require(row.get('rejected') is (value > TOL), 'Common rejection threshold changed')
        require(row['method'] in ('positive_axis_gap', 'native_common'), 'unknown finite-pair method')
        if row['method'] == 'positive_axis_gap':
            require(value == 0 and finite(row['axis_gap_lower_mm']) and row['axis_gap_lower_mm'] > 0,
                    'axis gap shortcut requires a strictly positive native gap')
        else:
            require(row['axis_gap_lower_mm'] == 0, 'native Common metadata differs')
        if value > 0:
            positive[pair] = value
        if row['rejected']:
            rejected.append(pair)
    saved = report['positive_actual_Common']
    require(len(saved) == len(positive) and len({(r['a'], r['b']) for r in saved}) == len(saved),
            'all positive numeric pairs must be preserved once')
    for row in saved:
        require(positive.get((row['a'], row['b'])) == row['common_mm3'], 'positive pair volume differs')
    all_pairs = set(actual) == expected
    complete = all_pairs and not failures and not report['evaluation_failures']
    after = report.get('identity_after', {})
    identity_ok = (after.get('source_bytes_and_locked_environment_unchanged') is True
                   and not after.get('changed_or_late_sources')
                   and after.get('exact_commit_execution_claimed') is False)
    if not allow_partial:
        require(complete and identity_ok and report.get('execution_completed') is True,
                'complete executed pair inventory and source/environment identity required')
    if report.get('execution_completed'):
        require(complete and identity_ok, 'unsupported completion claim')
        require(report.get('finite_trial_clear') is (not rejected), 'finite clearance claim contradicts raw Common')
    require(report.get('all_unordered_pairs_present_once', False) is all_pairs, 'unsupported inventory completion claim')
    crosscheck = report['in_domain_factory_crosscheck']
    differences = crosscheck['bidirectional_material_difference_mm3']
    require(crosscheck['all_participants_compared'] == len(names) and set(differences) == set(names)
            and all(finite(v) and 0 <= v <= TOL for v in differences.values()), 'in-domain complete material crosscheck failed')
    require(len(report['production_profile_rejections']) == 4, 'original outside-profile rejection must remain explicit')
    return {'all_unordered_pairs_present_once': all_pairs, 'completed_pair_count': len(pairs),
            'expected_pair_count': len(expected), 'positive_pair_count': len(positive),
            'rejected_pairs': [list(pair) for pair in rejected], 'rejected_pair_count': len(rejected),
            'finite_trial_clear': bool(complete and identity_ok and not rejected),
            'execution_completed': bool(complete and identity_ok),
            'original_v4_execution_claimed': False, 'geometry_generator_imported': False}


def validate_journal(path, report):
    events = [json.loads(line) for line in Path(path).read_text().splitlines()]
    require(len(events) == 2*len(report['pairs']), 'truncated or extra pair journal events')
    for index, row in enumerate(report['pairs']):
        first, second = events[2*index:2*index+2]
        require(first == {'event': 'selected', 'a': row['a'], 'b': row['b']}, 'selected pair journal order differs')
        require(second == {'event': 'completed', 'row': row}, 'completed raw pair differs from report')
    return {'all_selected_pairs_have_matching_completed_raw_record': True, 'journal_event_count': len(events),
            'sha256': identity.sha(path)}


def read_step(path):
    import cadquery as cq
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    leaves = []
    solid_bounds = []
    def visit(node):
        require(node.isValid(), 'invalid STEP topology')
        if node.ShapeType() == 'Solid':
            value = float(node.Volume())
            require(finite(value) and value > 0, 'nonpositive signed STEP solid')
            leaves.append(value)
            bound = Bnd_Box()
            BRepBndLib.AddOptimal_s(node.wrapped, bound, False, False)
            x0, y0, z0, x1, y1, z1 = bound.Get()
            solid_bounds.append([x0, x1, y0, y1, z0, z1])
        elif node.ShapeType() in ('Compound', 'CompSolid'):
            children = list(node)
            require(bool(children), 'empty STEP topology')
            for child in children:
                visit(child)
        else:
            raise ValueError('free non-solid STEP topology')
    roots = cq.importers.importStep(str(path)).vals()
    require(bool(roots), 'missing STEP roots')
    for root in roots:
        visit(root)
    raw = sum(float(root.Volume()) for root in roots)
    require(finite(raw) and raw > 0 and abs(raw-sum(leaves)) <= TOL, 'complete signed STEP volume mismatch')
    return {'root_count': len(roots), 'positive_solid_count': len(leaves), 'volume_mm3': raw,
            'individual_positive_solid_volume_mm3': leaves, 'individual_positive_solid_bounds_mm': solid_bounds}


def complete_boolean_volume(body):
    """Retain every Boolean solid; an empty result is allowed, free wires are not."""
    values = []
    def visit(node):
        require(node.isValid(), 'invalid material-accounting Boolean topology')
        if node.ShapeType() == 'Solid':
            value = float(node.Volume())
            require(finite(value) and value > 0, 'nonpositive material-accounting solid')
            values.append(value)
        elif node.ShapeType() in ('Compound', 'CompSolid'):
            for child in node:
                visit(child)
        else:
            raise ValueError('non-solid material-accounting topology')
    visit(body)
    raw = float(body.Volume())
    require(finite(raw) and raw >= 0 and abs(raw-sum(values)) <= TOL, 'whole material-accounting volume differs')
    return raw


def validate_relief_definition(candidate):
    """Bind the v2 construction contract before reading any persisted STEP."""
    if candidate.get('schema') == 'razr-STOW-local-face-relief-research-20261025-v1':
        return None  # Keep the historical v1 reader scope unchanged.
    expected = relief_v2.definition()
    require(candidate.get('schema') == expected['schema'], 'unknown finite relief schema')
    require(set(expected) <= set(candidate), 'incomplete v2 relief construction contract')
    require(set(candidate)-set(expected) <= {'material_changes', 'unchanged_participant_names'},
            'unknown v2 relief claim or parameter')
    require(all(candidate[key] == value for key, value in expected.items()),
            'v2 relief cut, motion, domain, or qualification differs from frozen definition')
    return {row['part']: row['cut_boxes'] for row in expected['parts']}


def read_relief(candidate, directory, *, native):
    expected = {side+'_'+role for side in 'LR' for role in ('CAP_0', 'ROOT_INNER')}
    definition_boxes = validate_relief_definition(candidate)
    changes = candidate['material_changes']
    require(candidate['schema'] in ('razr-STOW-local-face-relief-research-20261025-v1',
                                   'razr-STOW-local-two-layer-face-relief-research-20261025-v2')
            and len(changes) == 4 and {row['part'] for row in changes} == expected,
            'complete four-body finite relief required')
    require(candidate['q_or_other_control_domain_removed'] is False
            and candidate['contact_law_changed'] is False
            and candidate['production_default_changed'] is False
            and candidate['strength_or_tolerance_qualified'] is False
            and candidate['manufacturing_go'] is False, 'unsupported relief scope')
    checked = []
    for row in changes:
        exports = row['exports']
        require(set(exports) == {'before', 'after', 'cut_envelope'}, 'complete before/after/cut STEP set required')
        shapes = {}
        item = {'part': row['part'], 'exports': {}}
        for kind, record in exports.items():
            path = (directory/record['path']).resolve(strict=True)
            require(path.is_relative_to(directory.resolve()) and path.is_file() and not path.is_symlink()
                    and identity.sha(path) == record['sha256'], 'candidate STEP path or bytes differ')
            item['exports'][kind] = {'path': record['path'], 'sha256': record['sha256']}
            if native:
                import cadquery as cq
                signature = read_step(path)
                require(signature['positive_solid_count'] == record['solid_count']
                        and abs(signature['volume_mm3']-record['volume_mm3']) <= TOL,
                        'complete candidate STEP signature differs')
                if kind != 'cut_envelope':
                    require(signature['positive_solid_count'] == 1, 'relief disconnected a required body')
                roots = cq.importers.importStep(str(path)).vals()
                shapes[kind] = roots[0] if len(roots) == 1 else cq.Compound.makeCompound(roots)
                item['exports'][kind].update(signature)
        require(finite(row['removed_mm3']) and row['removed_mm3'] > 0
                and finite(row['added_mm3']) and 0 <= row['added_mm3'] <= TOL
                and abs(row['balance_error_mm3']) <= TOL, 'invalid reported relief material balance')
        if native:
            before, after, tool = (shapes[name] for name in ('before', 'after', 'cut_envelope'))
            if definition_boxes is not None:
                expected_tools = []
                for box in definition_boxes[row['part']]:
                    lo, hi = box['lo_mm'], box['hi_mm']
                    expected_tools.append(cq.Solid.makeBox(*(hi[i]-lo[i] for i in range(3)),
                                                         cq.Vector(*lo)))
                expected_tool = (expected_tools[0] if len(expected_tools) == 1
                                 else cq.Compound.makeCompound(expected_tools))
                cut_definition_differences = [
                    complete_boolean_volume(tool.cut(expected_tool)),
                    complete_boolean_volume(expected_tool.cut(tool))]
                require(max(cut_definition_differences) <= TOL,
                        'persisted v2 cut envelope differs from frozen construction boxes')
                item['cut_envelope_to_frozen_definition_difference_mm3'] = cut_definition_differences
            removed = complete_boolean_volume(before.cut(after))
            added = complete_boolean_volume(after.cut(before))
            tool_removed = complete_boolean_volume(before.intersect(tool))
            reconstructed = before.cut(tool)
            differences = [complete_boolean_volume(reconstructed.cut(after)),
                           complete_boolean_volume(after.cut(reconstructed))]
            balance = complete_boolean_volume(before)-removed+added-complete_boolean_volume(after)
            require(removed > 0 and added <= TOL and abs(balance) <= TOL
                    and abs(removed-tool_removed) <= TOL and max(differences) <= TOL
                    and abs(removed-row['removed_mm3']) <= TOL,
                    'independent complete relief accounting or reconstruction failed')
            item.update(removed_mm3=removed, added_mm3=added, balance_error_mm3=balance,
                        tool_intersection_mm3=tool_removed, bidirectional_reconstruction_difference_mm3=differences)
        checked.append(item)
    return {'parts': checked, 'native_material_accounting_executed': native,
            'production_default_changed': False, 'strength_or_tolerance_qualified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native', action='store_true')
    args = parser.parse_args(argv)
    if args.native:
        owned_process.announce_worker_from_environment(Path(__file__))
    require(not args.output.exists(), 'new reader output required')
    source_before = {str(Path(path).resolve()): identity.sha(path)
                     for path in (__file__, identity.__file__, owned_process.__file__, relief_v2.__file__)}
    report_path = args.report.resolve(strict=True)
    before = identity.sha(report_path)
    report = json.loads(report_path.read_text())
    result = {'schema': 'razr-complete-finite-KEY-readback-20261025-v1', 'passed': False,
              'source_sha256': source_before, 'report_sha256': before,
              'native_readback_executed': False, 'independent_CAD_kernel': False,
              **{key: False for key in FALSE_FLAGS}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result['pair_readback'] = validate_report(report)
        result['journal_readback'] = validate_journal(report_path.parent/'pairs.jsonl', report)
        if report.get('candidate') is not None:
            result['candidate_material_readback'] = read_relief(report['candidate'], report_path.parent, native=args.native)
        result['positive_STEP_readbacks'] = []
        for row in report['positive_actual_Common']:
            record = row['actual_Common_STEP']
            filename = record['path']
            require(type(filename) is str and Path(filename).name == filename, 'STEP must be a direct regular member')
            path = report_path.parent/filename
            require(path.is_file() and not path.is_symlink() and identity.sha(path) == record['sha256'],
                    'STEP bytes differ from numeric export record')
            item = {'a': row['a'], 'b': row['b'], 'path': filename, 'sha256': record['sha256']}
            if args.native:
                item.update(read_step(path))
                error = abs(item['volume_mm3']-row['common_mm3'])
                require(error <= max(1e-9, row['common_mm3']*1e-8), 'independent STEP volume differs')
                item['volume_readback_error_mm3'] = error
            result['positive_STEP_readbacks'].append(item)
        require(identity.sha(report_path) == before, 'report changed during independent readback')
        require(all(identity.sha(path) == digest for path, digest in source_before.items()), 'reader source changed')
        require(not any(name in sys.modules for name in ('product_assembly', 'product_nominal_motion',
                    'product_routing_ep5', 'cam_coupling', 'probe_key_endpoint_extension')),
                'independent reader imported a geometry builder')
        result.update(passed=True, native_readback_executed=args.native)
    except Exception as exc:
        result['failure'] = type(exc).__name__+': '+str(exc)
    identity.atomic_json(args.output, result)
    print(json.dumps({key: result.get(key) for key in ('passed', 'native_readback_executed', 'failure')}), flush=True)
    return 0 if result['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
