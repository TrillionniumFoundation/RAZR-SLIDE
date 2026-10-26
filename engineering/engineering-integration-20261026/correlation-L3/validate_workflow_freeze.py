"""Check workflow syntax, immutable S4 bytes and actual embedded heredoc bytes.

This is a static preparation check, not a native geometry result.  It reads the
named Git object and never checks out or edits the repository.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re
import subprocess
import yaml


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workflow', type=Path, required=True)
    ap.add_argument('--source-dir', type=Path, required=True)
    ap.add_argument('--baseline-repo', type=Path, required=True)
    ap.add_argument('--label', choices=['L2', 'L3'], required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    wf = yaml.safe_load(args.workflow.read_text())
    revision = wf['env']['S4']
    assert revision == 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
    actual_tree = subprocess.check_output(
        ['git', 'rev-parse', revision + '^{tree}'],
        cwd=args.baseline_repo, text=True).strip()
    assert actual_tree == 'cdd9e2c41216201b6cd04dd610d45fde80499045'
    steps = wf['jobs']['replay']['steps']
    bash_checks, system_python, embedded = [], [], {}
    for i, step in enumerate(steps):
        if 'run' not in step:
            continue
        script = step['run']
        subprocess.run(['bash', '-n'], input=script, text=True, check=True)
        bash_checks.append(i)
        for match in re.finditer(r"(?m)^python3 -B - <<'([A-Z_0-9]+)'\n(.*?)\n\1(?:\n|$)", script, re.S):
            delimiter, body = match.groups()
            tree = ast.parse(body, feature_version=(3, 10))
            calls = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == 'file_digest']
            assert not calls, (i, delimiter, 'Python 3.10 lacks hashlib.file_digest')
            system_python.append({'step': i, 'delimiter': delimiter, 'python310_AST': True, 'file_digest_calls': 0})
        for match in re.finditer(r"(?m)^cat > \"(\$HOST_ROOT/[^\"]+)\" <<'([A-Z_0-9]+)'\n(.*?)\n\2(?:\n|$)", script, re.S):
            destination, delimiter, body = match.groups()
            data = (body + '\n').encode()
            assert destination not in embedded
            embedded[destination] = data
            if destination.endswith('.py'):
                ast.parse(body)
    prep = steps[2]['run']
    body = prep.split("<<'S4_SOURCE'\n", 1)[1].split('\nS4_SOURCE\n', 1)[0]
    tree = ast.parse(body)
    expected = ast.literal_eval(next(n.value for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'expected' for t in n.targets)))
    assert len(expected) == 13
    source_checks = {}
    for rel, expected_hash in expected.items():
        data = subprocess.check_output(['git', 'show', revision + ':' + rel], cwd=args.baseline_repo)
        actual_hash = digest(data)
        assert actual_hash == expected_hash, rel
        source_checks[rel] = actual_hash
    assert "strip()=='" + actual_tree + "'" in body
    assert "'source_tree':'" + actual_tree + "'" in body
    launcher = digest(embedded['$HOST_ROOT/service-launch.py'])
    cap = digest(embedded['$HOST_ROOT/host-cap.py'])
    assert "assert record['service_launcher_sha256']=='" + launcher + "' and record['hostcap_sha256']=='" + cap + "'" in body
    for name in ['service-launch.py', 'host-cap.py']:
        code = embedded['$HOST_ROOT/' + name].decode()
        ast.parse(code, feature_version=(3, 10))
        assert 'file_digest' not in code
    assert wf['jobs']['replay']['timeout-minutes'] == 40
    assert "'platform_maximum_job_seconds': 2400" in prep
    assert "'external_command_deadline_seconds_after_first_step': 2220" in prep
    assert "float(os.environ['HOST_JOB_START']) + 2220" in prep
    assert "float(state['environment']['HOST_JOB_START'])+2250" in prep
    label = args.label
    check = prep.split("<<'" + label + "_SOURCE_CHECK'\n", 1)[1].split('\n' + label + '_SOURCE_CHECK\n', 1)[0]
    tree = ast.parse(check)
    expected = ast.literal_eval(next(n.value for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'expected' for t in n.targets)))
    driver_checks = {}
    for name, row in expected.items():
        data = embedded['$HOST_ROOT/' + label.lower() + '/' + name]
        assert data == (args.source_dir / name).read_bytes(), name
        assert len(data) == row['bytes'] and digest(data) == row['sha256'], name
        driver_checks[name] = row
    report = {'schema': 'razr-workflow-static-identity-check-v2',
        'workflow_sha256': digest(args.workflow.read_bytes()),
        'source_commit': revision, 'actual_immutable_S4_tree': actual_tree,
        'S4_assertion_and_record_match_actual_tree': True,
        'thirteen_source_hashes_match_immutable_git_object': source_checks,
        'bash_blocks_passed': bash_checks,
        'system_python_heredoc_checks': system_python,
        'system_launcher_sha256': launcher, 'system_hostcap_sha256': cap,
        'launcher_and_hostcap_heredoc_hashes_match_actual_assertion': True,
        'embedded_driver_files_match_source_byte_for_byte': driver_checks,
        'named_host_time_fields_checked': True,
        'native_executed': False,
        'static_preparation_check_is_not_geometry_qualification': True}
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'out': str(args.out), 'workflow_sha256': report['workflow_sha256'],
                      'source_files': len(driver_checks), 'passed': True}))


if __name__ == '__main__':
    main()
