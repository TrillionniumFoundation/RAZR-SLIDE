#!/usr/bin/env python3
"""Retain real GitHub Actions attempts, steps and failure annotations.

Read-only. Uses GITHUB_TOKEN or the selected repository's existing git
credential helper. Credentials are never emitted, saved, or sent on redirects.
Exit 0 requires the requested head, a successful run and executed successful
steps in every job. A queued request or an empty job is not execution evidence.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPO_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")


def summarize(run: dict, jobs: list[dict], annotations: dict, expected_head: str) -> dict:
    if not SHA_PATTERN.fullmatch(expected_head):
        raise ValueError("a complete expected head SHA is required")
    if len({j['id'] for j in jobs}) != len(jobs):
        raise ValueError('duplicate job identities')
    rows = []
    for job in jobs:
        steps = job.get('steps') or []
        executed = [s for s in steps if s.get('started_at') and s.get('conclusion') not in ('skipped', None)]
        notices = annotations.get(str(job['id']), [])
        billing = any('recent account payments have failed' in n.get('message', '').lower()
                      or 'spending limit needs to be increased' in n.get('message', '').lower()
                      for n in notices)
        inherited = bool(job.get('created_at') and job.get('completed_at')
                         and job['completed_at'] < job['created_at'])
        rows.append({'id': job['id'], 'name': job['name'], 'head_sha': job.get('head_sha'),
                     'run_attempt': job.get('run_attempt'), 'status': job.get('status'),
                     'conclusion': job.get('conclusion'), 'runner_id': job.get('runner_id'),
                     'step_records': len(steps), 'executed_step_records': len(executed),
                     'inherited_completion_precedes_attempt_creation': inherited,
                     'billing_or_spend_block_annotation': billing,
                     'annotation_count': len(notices), 'html_url': job.get('html_url')})
    identity_ok = (run.get('head_sha') == expected_head
                   and all(j.get('head_sha') == expected_head for j in jobs))
    actual = bool(rows) and all(r['executed_step_records'] > 0 for r in rows)
    successful = (run.get('status') == 'completed' and run.get('conclusion') == 'success'
                  and all(r['status'] == 'completed' and r['conclusion'] == 'success' for r in rows))
    inherited = [r['id'] for r in rows if r['inherited_completion_precedes_attempt_creation']]
    return {'expected_head': expected_head, 'run_id': run.get('id'),
            'run_attempt': run.get('run_attempt'), 'actual_run_head': run.get('head_sha'),
            'head_identity_matches': identity_ok, 'run_status': run.get('status'),
            'run_conclusion': run.get('conclusion'), 'jobs': rows,
            'jobs_without_executed_steps': [r['id'] for r in rows if not r['executed_step_records']],
            'billing_block_job_ids': [r['id'] for r in rows if r['billing_or_spend_block_annotation']],
            'inherited_job_result_ids': inherited,
            'all_jobs_have_executed_steps': actual,
            'successful_hosted_report': identity_ok and actual and successful,
            'one_fresh_attempt_executed_all_jobs': actual and not inherited,
            'scope': 'provider execution records; no test-count or hardware result inferred'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def repository_credential(repository: str) -> str:
    if os.environ.get('GITHUB_TOKEN'):
        return os.environ['GITHUB_TOKEN']
    env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_ASKPASS': '/bin/false', 'SSH_ASKPASS': '/bin/false'}
    proc = subprocess.run(['git', 'credential', 'fill'], cwd=ROOT, env=env,
                          input=f'protocol=https\nhost=github.com\npath={repository}.git\n\n',
                          text=True, capture_output=True, timeout=20)
    fields = dict(line.split('=', 1) for line in proc.stdout.splitlines() if '=' in line)
    if proc.returncode or not fields.get('password'):
        raise RuntimeError('selected repository has no usable noninteractive HTTPS credential')
    return fields['password']


def collect(repository: str, run_id: int, expected_head: str, output: Path) -> dict:
    if not REPO_PATTERN.fullmatch(repository) or not SHA_PATTERN.fullmatch(expected_head) or run_id <= 0:
        raise ValueError('valid repository, positive run ID and full expected head SHA required')
    output = output.resolve()
    if output.exists():
        raise ValueError('use a new output directory to preserve earlier attempts')
    output.mkdir(parents=True)
    record = {'schema': 'razr-actions-inspection-v1', 'repository': repository,
              'observed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'collector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'read_only': True, 'expected_head': expected_head, 'requested_run_id': run_id,
              'responses': []}
    path = output / 'report.json'
    def persist():
        path.write_text(json.dumps(record, indent=2) + '\n')
    try:
        token = repository_credential(repository)
        opener = urllib.request.build_opener(NoRedirect)
        prefix = f'https://api.github.com/repos/{repository}/'
        def get(suffix):
            url = prefix + suffix
            req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token,
                'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
                'User-Agent': 'RAZR-SLIDE-read-only-actions-inspector'})
            try:
                with opener.open(req, timeout=20) as response:
                    status, data = response.status, json.load(response)
            except urllib.error.HTTPError as exc:
                status = exc.code
                try:
                    data = json.loads(exc.read())
                except (ValueError, UnicodeError):
                    data = {'message': 'non-JSON provider response'}
            record['responses'].append({'url': url, 'status': status, 'data': data})
            persist()
            if status != 200:
                raise RuntimeError(f'GitHub returned HTTP {status} for repository API read')
            return data
        run = get(f'actions/runs/{run_id}')
        if run.get('id') != run_id or run.get('repository', {}).get('full_name', '').lower() != repository.lower():
            raise ValueError('provider returned a different repository/run identity')
        attempt = run['run_attempt']
        jobs = []
        for page in range(1, 21):
            data = get(f'actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100&page={page}')
            jobs.extend(data['jobs'])
            if len(jobs) >= data['total_count']:
                break
        else:
            raise ValueError('job pagination bound reached; report is incomplete')
        annotations = {}
        for job in jobs:
            check = job.get('check_run_url', '')
            if not check.startswith(prefix + 'check-runs/'):
                raise ValueError('unexpected check URL outside the selected repository')
            suffix = check[len(prefix):]
            annotations[str(job['id'])] = []
            for page in range(1, 21):
                data = get(suffix + f'/annotations?per_page=100&page={page}')
                annotations[str(job['id'])].extend(data)
                if len(data) < 100:
                    break
            else:
                raise ValueError('annotation pagination bound reached; report is incomplete')
        record['summary'] = summarize(run, jobs, annotations, expected_head)
        record['completed_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    except Exception as exc:
        # Never include subprocess credential output, request headers or tokens.
        record['inspection_error'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        persist()
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default='TrillionniumFoundation/RAZR-SLIDE')
    parser.add_argument('--run-id', type=int, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = collect(args.repository, args.run_id, args.expected_head, args.output)
    print(json.dumps({'report': str(args.output / 'report.json'),
                      'summary': result.get('summary'), 'inspection_error': result.get('inspection_error')}))
    raise SystemExit(0 if result.get('summary', {}).get('successful_hosted_report') else 2)


if __name__ == '__main__':
    main()
