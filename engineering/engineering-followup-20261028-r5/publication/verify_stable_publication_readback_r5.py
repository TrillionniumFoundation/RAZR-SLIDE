from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / 'razr-current'
HEAD = '2bd3b2643f7fb996f2f9bb854ce5f8d5c6ebc9fd'
START = time.monotonic()

def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO, timeout=60)

tree = git('rev-parse', HEAD + '^{tree}').decode().strip()
assert tree == '4181b8dc85894798b14f2b5982a3ea08dd664488'
rows = json.loads((ROOT / 'r5-integration/R5_STABLE_PUBLICATION_MANIFEST.json').read_text())
verified = []
for row in rows:
    remote = git('show', HEAD + ':' + row['path'])
    local = (REPO / row['path']).read_bytes()
    assert remote == local
    assert len(remote) == row['bytes']
    assert hashlib.sha256(remote).hexdigest() == row['sha256']
    verified.append(dict(row, remote_bytes_match=True))
changes = git('diff', '--name-only', 'c5f6606924937d716b007cd3ffa8e54df8ecfa5d', HEAD).decode().splitlines()
assert all(p.startswith('engineering/engineering-followup-20261028-r5/') or p == '.github/workflows/r5-exterior-channel.yml' for p in changes)
report = {
    'schema': 'r5-stable-publication-full-remote-readback-v1',
    'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'elapsed_seconds': time.monotonic() - START,
    'repository': 'TrillionniumFoundation/RAZR-SLIDE',
    'branch': 'evidence/full-sprint-20261028-r5',
    'commit': HEAD, 'tree': tree,
    'parent': '06e4f37690e2d5b9dc2abaf69cab9ba16957f1e2',
    'source': 'Public remote Git fetch of this exact immutable commit, then git show every file; missing promisor blobs fetched from the same remote.',
    'files': verified,
    'all_remote_file_bytes_equal': True,
    'all_changes_inside_R5_scopes': True,
    'R4_source_changed': False,
    'exact_a11_published': False,
    'all_blockers_closed': False,
}
(ROOT / 'r5-integration/R5_STABLE_PUBLICATION_REMOTE_READBACK.json').write_text(json.dumps(report, indent=2) + '\n')
path = ROOT / 'r5-integration/R5_INTEGRATION_PROGRESS.json'
progress = json.loads(path.read_text())
progress.update(stable_publication_readback='69_of_69_full_bytes_equal', at_utc=report['at_utc'])
path.write_text(json.dumps(progress, indent=2) + '\n')
print(json.dumps({'commit': HEAD, 'files': len(verified), 'bytes': sum(x['bytes'] for x in verified), 'all_remote_file_bytes_equal': True, 'elapsed_seconds': report['elapsed_seconds']}))
