#!/usr/bin/env python3
"""Independent exact-commit byte and lock-source review; no native worker import."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import resource
import time

ROOT = Path(__file__).resolve().parent
COMMIT = '8c730aaad652bf0c4bda1f94ce6506ecf0b68fbd'


def main():
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024**2, 128 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    out_path = ROOT / 'R7_OFFICIAL_UV_01010_LOCK_SOURCE_REVIEW_V1.json'
    if out_path.exists():
        raise FileExistsError(out_path)
    receipt_path = ROOT / 'OFFICIAL_RETRIEVAL_RECEIPT_V1.json'
    tree_path = ROOT / 'EXACT_COMMIT_RECURSIVE_TREE_ORIGINAL.json'
    receipt = json.loads(receipt_path.read_bytes())
    tree = json.loads(tree_path.read_bytes())
    assert receipt['tag_original']['object'] == {
        'sha': COMMIT, 'type': 'commit',
        'url': 'https://api.github.com/repos/astral-sh/uv/git/commits/' + COMMIT}
    assert tree['truncated'] is False
    assert len(tree['tree']) == 1594
    entries = {x['path']: x for x in tree['tree']}
    assert len(entries) == len(tree['tree'])
    assert len(receipt['selected_blob_entries']) == 6
    checks = []
    text = {}
    watched = {}
    for entry in receipt['selected_blob_entries']:
        assert entries[entry['path']] == entry
        assert entry['type'] == 'blob' and entry['mode'] == '100644'
        p = ROOT / 'originals' / entry['path']
        raw = p.read_bytes()
        assert len(raw) == entry['size']
        blob = hashlib.sha1(('blob ' + str(len(raw)) + '\0').encode() + raw).hexdigest()
        assert blob == entry['sha']
        sha256 = hashlib.sha256(raw).hexdigest()
        checks.append({'path': str(p.relative_to(ROOT)), 'bytes': len(raw),
            'sha256': sha256, 'git_blob_sha1': blob, 'full_byte_identity_pass': True,
            'official_url': 'https://github.com/astral-sh/uv/blob/' + COMMIT + '/' + entry['path']})
        watched[p] = sha256
        text[entry['path']] = raw.decode('utf-8')
    assert 'let _lock = environment\n        .lock()\n        .await' in text['crates/uv/src/commands/project/sync.rs']
    assert '.inspect_err(|err| {' in text['crates/uv/src/commands/project/sync.rs']
    assert 'self.0.interpreter.lock().await' in text['crates/uv-python/src/environment.rs']
    interpreter = text['crates/uv-python/src/interpreter.rs']
    assert '} else if self.is_virtualenv() {' in interpreter
    assert 'self.sys_prefix.join(".lock")' in interpreter
    lock = text['crates/uv-fs/src/locked_file.rs']
    assert 'let file = Self::create(&path)?;' in lock
    assert 'NamedTempFile::new_in(parent)' in lock
    assert 'file.persist_noclobber(path.as_ref())' in lock
    assert '// If path already exists, return it.' in lock
    assert '.create(true)' in lock
    assert '.truncate(' not in lock
    assert '.write_all(' not in lock and '.write_fmt(' not in lock
    assert 'self.0.unlock()' in lock
    for p, sha in watched.items():
        assert hashlib.sha256(p.read_bytes()).hexdigest() == sha
    report = {
        'schema': 'razr-r7-official-uv-01010-lock-source-review-v1',
        'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'official_repository': 'astral-sh/uv', 'tag': '0.10.10', 'commit': COMMIT,
        'review_kind': 'Cross-author source-provenance and semantic review. No producer code imported or scientific/native worker executed.',
        'source_identity_checks': checks,
        'read_sources_unchanged': True,
        'source_findings': [
            {'path': 'crates/uv/src/commands/project/sync.rs', 'lines': [193, 199],
             'finding': 'Sync requests the environment lock; lock errors are warned and converted to an optional lock, so a successful sync alone does not prove lock acquisition.'},
            {'path': 'crates/uv-python/src/environment.rs', 'lines': [314, 317],
             'finding': 'Environment lock delegates to interpreter lock.'},
            {'path': 'crates/uv-python/src/interpreter.rs', 'lines': [671, 705],
             'finding': 'A normal virtual environment uses exactly sys_prefix/.lock. Target and prefix installs use their own roots; non-venv fallback uses a temporary global file.'},
            {'path': 'crates/uv-fs/src/locked_file.rs', 'lines': [209, 337],
             'finding': 'A missing Unix lock is normally created as a fresh temporary file and persisted without clobbering. Existing files are opened unchanged. Creation fallback and non-Unix branch use create(true) without truncation. None of these paths establish that every pre-existing lock is empty.'},
            {'path': 'crates/uv-fs/src/locked_file.rs', 'lines': [340, 353],
             'finding': 'Dropping the lock unlocks its file; the path is not removed by this Drop implementation.'},
        ],
        'supported_qualifier_scope': 'For a registered fresh uv 0.10.10 virtual environment, an actually observed empty regular nonsymlink file at the exact environment root/.lock may be classified as uv runtime metadata. All other files, nonempty locks, symlinks and nested lock names remain subject to original ownership rejection.',
        'required_actual_followup': ['actual pinned uv binary/version and wheel identity',
            'fresh-environment installation receipt', 'lstat and byte identity of the actual root .lock',
            'unchanged original wheel/RECORD/import and scientific gates'],
        'not_proven_by_this_review': ['actual runtime qualification', 'actual CAD or Common result',
            'presence of a lock after every successful uv invocation', 'empty content of any pre-existing .lock'],
        'actual_native_worker_executed': False, 'G2': False,
        'execution': {'elapsed_seconds': time.monotonic() - started,
            'max_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            'source_bytes_read_twice': sum(x['bytes'] for x in checks) * 2,
            'cpu_cap_seconds': 30, 'address_cap_bytes': 128 * 1024**2},
    }
    encoded = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode()
    out_path.write_bytes(encoded)
    print(json.dumps({'report': str(out_path), 'bytes': len(encoded),
        'sha256': hashlib.sha256(encoded).hexdigest(), 'source_count': len(checks),
        'all_source_identity_checks_pass': True, 'native_executed': False}))


if __name__ == '__main__':
    main()
