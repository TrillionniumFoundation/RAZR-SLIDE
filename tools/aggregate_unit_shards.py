#!/usr/bin/env python3
"""Require every declared unit suite once, at one source/run/lock identity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.check_environment import normalized_name, python_matches
from tools.verify import sha, snapshot, validate_manifest


def matrix(config: dict) -> dict:
    validate_manifest(config)
    ids = [suite['id'] for suite in config['suites']]
    if any(not re.fullmatch(r'[a-z0-9][a-z0-9-]*', name) for name in ids):
        raise ValueError('suite ID is unsafe for an artifact or workflow matrix')
    return {'include': [{'id': name} for name in ids]}


def aggregate(config: dict, reports: list[dict], *, expected_head: str,
              manifest_sha256: str, lock_sha256: str, project_sha256: str,
              locked_packages: dict[str, str], python_constraint: str,
              expected_sources: dict[str, str], run_id: str, run_attempt: str) -> dict:
    matrix(config)
    if not re.fullmatch(r'[0-9a-f]{40}', expected_head):
        raise ValueError('full expected source commit required')
    if not run_id.isdigit() or not run_attempt.isdigit() or int(run_id) <= 0 or int(run_attempt) <= 0:
        raise ValueError('positive GitHub run and attempt identities required')
    if not expected_sources or not locked_packages:
        raise ValueError('nonempty current source and locked-package inventories required')
    wanted = {suite['id']: suite for suite in config['suites']}
    errors, seen, rows = [], set(), []
    for ordinal, report in enumerate(reports):
        prefix = 'report ' + str(ordinal + 1) + ': '
        issues = []
        selected = report.get('selected_suite_ids')
        suite_id = selected[0] if isinstance(selected, list) and len(selected) == 1 else None
        if not isinstance(suite_id, str) or suite_id not in wanted:
            errors.append(prefix + 'missing, multiple or unknown selected suite identities')
            continue
        prefix = suite_id + ': '
        if suite_id in seen:
            issues.append('duplicate suite report')
        seen.add(suite_id)
        suite = wanted[suite_id]
        if report.get('schema') != 'razr-unit-execution-v2' or report.get('scope') != 'selected':
            issues.append('unsupported report schema or scope')
        if any(report.get(key) != expected_head for key in ('expected_head', 'base_commit', 'source_head_after')):
            issues.append('source commit identity mismatch')
        if report.get('github_run_id') != run_id or report.get('github_run_attempt') != run_attempt:
            issues.append('report belongs to another workflow run or attempt')
        if not report.get('runner_name') or not report.get('github_job'):
            issues.append('hosted runner/job identity absent')
        for key in ('passed', 'execution_completed', 'environment_verified',
                    'source_identity_verified', 'source_bytes_unchanged', 'present_tracked_bytes_match_head'):
            if report.get(key) is not True:
                issues.append(key + ' is not true')
        for key in ('candidate_go', 'manufacturing_go', 'hardware_qualification',
                    'full_motion_reexecuted', 'native_KiCad_reexecuted'):
            if report.get(key) is not False:
                issues.append('unit scope overclaims ' + key)
        if report.get('diagnostic_unlocked') is not False:
            issues.append('diagnostic execution cannot satisfy canonical aggregate')
        for key, expected in (('suite_manifest_sha256', manifest_sha256),
                              ('uv_lock_sha256', lock_sha256), ('pyproject_sha256', project_sha256)):
            if report.get(key) != expected:
                issues.append(key + ' mismatch')
        if (report.get('source_hashes_before') != expected_sources or
                report.get('source_hashes_after') != expected_sources):
            issues.append('executed source snapshot differs from this checkout')
        environment = report.get('environment', {})
        if (not isinstance(environment, dict) or environment.get('passed') is not True or
                environment.get('uv_lock_sha256') != lock_sha256 or
                environment.get('pyproject_sha256') != project_sha256 or environment.get('errors') != []):
            issues.append('invalid environment verification receipt')
            environment = {}
        packages = environment.get('checked_packages', {})
        if type(environment.get('checked_package_count')) is not int or environment.get('checked_package_count') != len(locked_packages):
            issues.append('locked package count differs')
        if not isinstance(packages, dict) or set(packages) != set(locked_packages):
            issues.append('locked package coverage differs')
        else:
            for name, version in locked_packages.items():
                package = packages[name]
                if not isinstance(package, dict) or package != {'expected': version, 'observed': version, 'matches': True}:
                    issues.append('locked package version mismatch: ' + name)
        try:
            python = tuple(int(value) for value in environment.get('python_version', '').split('.'))
            if len(python) != 3 or not python_matches(python_constraint, python):
                issues.append('interpreter differs from locked Python constraint')
        except (ValueError, TypeError):
            issues.append('missing or invalid Python version')
        results = report.get('suite_results')
        row = results[0] if isinstance(results, list) and len(results) == 1 and isinstance(results[0], dict) else {}
        try:
            root_path, output_path, python_path = (report.get(key) for key in
                                                   ('repository_root', 'output_directory', 'python_executable'))
            paths = [root_path, output_path, python_path]
            if any(not isinstance(value, str) or not PurePosixPath(value).is_absolute()
                   or '..' in PurePosixPath(value).parts or str(PurePosixPath(value)) != value for value in paths):
                raise ValueError('absolute normalized execution paths are required')
            directory = suite.get('directory')
            extra_paths = suite.get('extra_paths', [])
            if not isinstance(extra_paths, list):
                raise ValueError('extra paths must be a list')
            for relative in [directory, *extra_paths]:
                if (not isinstance(relative, str) or not relative or PurePosixPath(relative).is_absolute()
                        or '..' in PurePosixPath(relative).parts or str(PurePosixPath(relative)) != relative):
                    raise ValueError('manifest paths must be normalized repository-relative paths')
            expected_command = [python_path, '-B', str(PurePosixPath(root_path) / 'tools/run_suite.py'),
                                '--directory', str(PurePosixPath(root_path) / directory),
                                '--minimum', str(suite['minimum_tests']),
                                '--report', str(PurePosixPath(output_path) / (suite_id + '.json'))]
            for relative in extra_paths:
                expected_command += ['--extra-path', str(PurePosixPath(root_path) / relative)]
            if row.get('command') != expected_command:
                issues.append('executed worker command differs from manifest suite/path/minimum/report binding')
        except (TypeError, ValueError) as exc:
            issues.append('invalid execution command binding: ' + str(exc))
        if row.get('id') != suite_id or row.get('passed') is not True or type(row.get('exit_code')) is not int or row.get('exit_code') != 0:
            issues.append('suite did not finish with a successful result')
        for key in ('minimum_tests',):
            if type(row.get(key)) is not int or row.get(key) != suite['minimum_tests']:
                issues.append('suite minimum differs from current manifest')
        if type(report.get('configured_minimum_tests')) is not int or report.get('configured_minimum_tests') != suite['minimum_tests']:
            issues.append('configured report minimum differs from current manifest')
        count = row.get('tests_run')
        ids = row.get('test_ids')
        valid_ids = isinstance(ids, list) and all(isinstance(value, str) and value for value in ids)
        if (type(count) is not int or count < suite['minimum_tests'] or
                type(report.get('tests_run')) is not int or report.get('tests_run') != count or
                not valid_ids or len(ids) != count or len(set(ids)) != count):
            issues.append('actual test identity/count/minimum validation failed')
        for key in ('failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes'):
            if type(row.get(key)) is not int or row.get(key) != 0:
                issues.append('suite has absent or nonzero ' + key)
        if report.get('syntax_errors') != [] or report.get('changed_during_tests') != []:
            issues.append('syntax or source-mutation diagnostics are not empty')
        errors.extend(prefix + issue for issue in issues)
        rows.append({'id': suite_id, 'tests_run': count if type(count) is int else 0,
                     'minimum_tests': suite['minimum_tests'], 'passed': not issues})
    missing = sorted(set(wanted) - seen)
    if missing:
        errors.append('missing suite reports: ' + ', '.join(missing))
    if len(reports) != len(wanted):
        errors.append('report count differs from complete manifest')
    return {'schema': 'razr-all-unit-shards-v1', 'scope': 'all_current_unit_suites',
            'expected_head': expected_head, 'github_run_id': run_id, 'github_run_attempt': run_attempt,
            'suite_manifest_sha256': manifest_sha256, 'uv_lock_sha256': lock_sha256,
            'pyproject_sha256': project_sha256, 'expected_suite_count': len(wanted),
            'observed_report_count': len(reports), 'missing_suite_ids': missing,
            'minimum_total_tests': config['minimum_total_tests'],
            'tests_run': sum(row['tests_run'] for row in rows), 'suite_results': rows,
            'errors': errors, 'passed': not errors,
            'hardware_qualification': False, 'full_motion_reexecuted': False,
            'native_KiCad_reexecuted': False, 'candidate_go': False, 'manufacturing_go': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--print-matrix', action='store_true')
    parser.add_argument('--artifacts', type=Path)
    parser.add_argument('--expected-head')
    parser.add_argument('--run-id')
    parser.add_argument('--run-attempt')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = root / 'tools/test_suites.json'
    config = json.loads(config_path.read_text())
    if args.print_matrix:
        print(json.dumps(matrix(config), separators=(',', ':')))
        return 0
    if not all((args.artifacts, args.expected_head, args.run_id, args.run_attempt, args.output)):
        parser.error('artifacts, expected-head, run-id, run-attempt and new output are required')
    lock = tomllib.loads((root / 'uv.lock').read_text())
    packages = {normalized_name(package['name']): package['version'] for package in lock['package'] if 'registry' in package.get('source', {})}
    reports, receipts, read_errors = [], [], []
    for path in sorted(args.artifacts.glob('*/report.json')):
        try:
            report = json.loads(path.read_text())
            if not isinstance(report, dict):
                raise ValueError('report is not an object')
            reports.append(report)
            receipts.append({'file': str(path.relative_to(args.artifacts)), 'sha256': sha(path)})
        except (OSError, ValueError) as exc:
            read_errors.append(str(path) + ': ' + str(exc))
    result = aggregate(config, reports, expected_head=args.expected_head,
                       manifest_sha256=sha(config_path), lock_sha256=sha(root / 'uv.lock'),
                       project_sha256=sha(root / 'pyproject.toml'), locked_packages=packages,
                       python_constraint=lock['requires-python'], expected_sources=snapshot(root),
                       run_id=args.run_id, run_attempt=args.run_attempt)
    result['reports'] = receipts
    result['errors'].extend(read_errors)
    result['passed'] = result['passed'] and not read_errors
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('passed', 'tests_run', 'expected_suite_count', 'errors')}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
