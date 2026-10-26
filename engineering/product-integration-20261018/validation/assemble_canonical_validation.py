#!/usr/bin/env python3
"""Validate and combine disjoint suite selections; never declare one full run passed."""
import argparse, datetime, hashlib, json, math, re
from pathlib import Path

INITIAL = 'b6abcb6326439270ec137cdac00cd6dd7ade4ac7'
REPAIR = '3eae4e7258814c7f5454937535d6c642dd51662f'
MANIFEST = '832ddc5c1e2ac1659018c19c46ac11d65946c5306997e6205a66eb98973b3f1c'
REGISTRY = '7b7ebf0f48556f2feca175a35b882a9a48337de2bb5f54b1ba7a740f85e8ce6b'
REPAIRED = {'thin-mechanism', 'mounted-mechanism', 'cam-coupling', 'pawl-actuator',
            'serviceable-pawl', 'endpoint-joint', 'product-integration'}
ALLOWED = {'README.md', 'CURRENT_DESIGN.md', 'status.json', 'design/current_product.json',
           'tools/sync_current_design.py', 'integration/assembly_inputs.json',
           'integration/product_assembly.py', 'integration/product_motion.py',
           'integration/product-study-tests/test_product_geometry.py',
           'engineering/product-integration-20261018/mechanical/metadata-correction.json',
           'engineering/product-integration-20261018/mechanical/geometry-wide-B-negative-control.json',
           'engineering/product-integration-20261018/mechanical/seal_product_study.py',
           'engineering/product-integration-20261018/electrical/run_electrical_study.py'}
COUNTERS = ('failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes')

def require(condition, message):
    if not condition: raise ValueError(message)

def read(path):
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()

def snapshots(report, label):
    before, after = report['source_hashes_before'], report['source_hashes_after']
    require(isinstance(before, dict) and bool(before) and isinstance(after, dict), label + ': missing source maps')
    for path, digest in before.items():
        require(isinstance(path, str) and path and not Path(path).is_absolute() and '..' not in Path(path).parts,
                label + ': invalid source path')
        require(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), label + ': invalid source SHA')
    require(before == after and report['source_bytes_unchanged'] is True and report['changed_during_tests'] == [],
            label + ': source changed during execution')
    require(report['syntax_errors'] == [], label + ': syntax errors')
    require(type(report['python_files_parsed']) is int and report['python_files_parsed'] == sum(p.endswith('.py') for p in before),
            label + ': Python parse count mismatch')
    require(before.get('tools/test_suites.json') == MANIFEST, label + ': source manifest identity differs')
    return before

def validate(report, label, specs):
    initial = label == 'initial'; expected = list(specs) if initial else [x for x in specs if x in REPAIRED]
    require(report['base_commit'] == (INITIAL if initial else REPAIR), label + ': unexpected commit')
    require(report['scope'] == ('all_current_unit_suites' if initial else 'selected'), label + ': scope differs')
    require(report['suite_manifest_sha256'] == MANIFEST, label + ': manifest SHA differs')
    require(report['passed'] is (False if initial else True), label + ': aggregate pass flag differs')
    for flag in ('full_motion_reexecuted', 'native_KiCad_reexecuted', 'hardware_qualification', 'candidate_go', 'manufacturing_go'):
        require(report[flag] is False, label + ': forbidden qualification claim: ' + flag)
    rows = report['suite_results']; require(isinstance(rows, list), label + ': invalid suite list')
    require([r['id'] for r in rows] == expected, label + ': suite IDs/order/duplicates differ')
    for row in rows:
        sid = row['id']; failed = initial and sid in REPAIRED
        for key in ('tests_run', 'minimum_tests', *COUNTERS):
            require(type(row[key]) is int and row[key] >= 0, sid + ': invalid integer ' + key)
        count = 1 if initial and sid == 'serviceable-pawl' else specs[sid]['minimum_tests']
        require(row['tests_run'] == count and row['minimum_tests'] == specs[sid]['minimum_tests'], sid + ': count differs')
        ids = row['test_ids']; require(isinstance(ids, list) and len(ids) == count, sid + ': test ID count differs')
        require(all(isinstance(x, str) and x for x in ids) and len(set(ids)) == len(ids), sid + ': invalid/duplicate test ID')
        import_failure = initial and sid == 'serviceable-pawl'
        require(all(x.startswith('unittest.loader._FailedTest.') for x in ids) if import_failure else
                all('_FailedTest' not in x for x in ids), sid + ': import-failure identity differs')
        expected_errors = int(failed and sid in {'serviceable-pawl', 'product-integration'})
        require(row['errors'] == expected_errors and row['failures'] == int(failed and not expected_errors), sid + ': failure/error count differs')
        require(all(row[k] == 0 for k in COUNTERS[2:]), sid + ': skips or expected/unexpected failures')
        require(type(row['exit_code']) is int and row['exit_code'] == int(failed), sid + ': exit code differs')
        require(row['passed'] is (not failed) and row['manufacturing_go'] is False, sid + ': pass/go flag differs')
        require(type(row['seconds']) in (int, float) and math.isfinite(row['seconds']) and row['seconds'] >= 0, sid + ': invalid duration')
    require(type(report['tests_run']) is int and report['tests_run'] == sum(r['tests_run'] for r in rows)
            == (1220 if initial else 182), label + ': aggregate test count differs')
    return {r['id']: r for r in rows}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'initial', 'repair', 'output'): parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(); repo = args.repo.resolve(); output = args.output.resolve()
    require(args.initial.resolve() != args.repair.resolve(), 'Two distinct original reports required')
    require(not output.exists() and output not in {args.initial.resolve(), args.repair.resolve()}, 'Output must be a new file')
    config, manifest_sha = read(repo / 'tools/test_suites.json'); specs = {s['id']: s for s in config['suites']}
    require(manifest_sha == MANIFEST and len(config['suites']) == len(specs) == 32, 'Repository manifest differs')
    require(config['minimum_total_tests'] == sum(s['minimum_tests'] for s in specs.values()) == 1240, 'Manifest count differs')
    require(hashlib.sha256((repo / 'integration/assembly_inputs.json').read_bytes()).hexdigest() == REGISTRY, 'Repository registry not restored')
    initial, initial_sha = read(args.initial); repair, repair_sha = read(args.repair)
    old = snapshots(initial, 'initial'); new = snapshots(repair, 'repair')
    changes = [{'path': p, 'old_sha256': old.get(p), 'new_sha256': new.get(p)}
               for p in sorted(old.keys() | new.keys()) if old.get(p) != new.get(p)]
    require(all(c['path'] in ALLOWED and c['new_sha256'] is not None for c in changes), 'Unapproved source change/deletion: ' + repr(changes))
    require(new.get('integration/assembly_inputs.json') == REGISTRY and old.get('integration/assembly_inputs.json') != REGISTRY,
            'Registry restoration identity not demonstrated')
    first = validate(initial, 'initial', specs); second = validate(repair, 'repair', specs)
    id_changes = []
    for sid in sorted(REPAIRED):
        a, b = first[sid]['test_ids'], second[sid]['test_ids']
        require(sid == 'serviceable-pawl' or a == b, sid + ': test selection changed beyond import recovery')
        id_changes.append({'suite_id': sid, 'removed': sorted(set(a) - set(b)), 'added': sorted(set(b) - set(a))})
    accepted = []
    for sid in specs:
        source = 'repair' if sid in REPAIRED else 'initial'; row = (second if source == 'repair' else first)[sid]
        accepted.append({**row, 'adopted_report': source, 'adopted_report_sha256': repair_sha if source == 'repair' else initial_sha,
                         'adopted_source_commit': REPAIR if source == 'repair' else INITIAL})
    kept = [r for r in accepted if r['adopted_report'] == 'initial']
    require(len(kept) == 25 and sum(r['tests_run'] for r in kept) == 1058, 'Initial accepted selection differs')
    require(len(accepted) == 32 and sum(r['tests_run'] for r in accepted) == 1240 and all(r['passed'] for r in accepted), 'Invalid union')
    evidence = {label: {'path': str(path.resolve()), 'sha256': digest, 'base_commit': report['base_commit'],
                       'scope': report['scope'], 'started_utc': report['started_utc'], 'python': report['python'],
                       'versions': report['versions'], 'tests_run': report['tests_run'], 'passed': report['passed']}
                for label, path, digest, report in [('initial', args.initial, initial_sha, initial), ('repair', args.repair, repair_sha, repair)]}
    result = {'schema': 'razr-disjoint-canonical-unit-selection-v1', 'assembled_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'scope': '25 passing suites / 1058 tests from b6ab plus 7 repaired suites / 182 tests from 3eae; disjoint canonical selections, not one successful full run',
              'single_full_run_passed': False, 'accepted_unit_selection_passed': True, 'accepted_suites': 32, 'accepted_tests': 1240,
              'original_reports': evidence, 'suite_manifest_sha256': MANIFEST, 'source_changes': changes,
              'sources_are_identical_across_runs': old == new, 'unchanged_source_paths': len(old.keys() & new.keys()) - sum(c['path'] in old for c in changes),
              'test_id_changes_in_repaired_suites': id_changes, 'suite_results': accepted,
              'source_hashes_unchanged_within_each_run': True, 'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'full_motion_reexecuted': False, 'native_KiCad_reexecuted': False, 'hardware_qualification': False,
              'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False, 'physical_phone_verified': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream: json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'output': str(output), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'accepted_suites': 32, 'accepted_tests': 1240}))

if __name__ == '__main__': main()
