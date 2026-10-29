#!/usr/bin/env python3
"""Append a bounded source-only review of the additive V2 scope correction."""
import argparse
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import resource
import signal
import time

ROOT = Path('/workspace/scratch/34f8fcac2ab1')
OUT = ROOT / 'r7-audit/method-publication-v2-review'
SELF = Path(__file__).resolve()
PLAN = OUT / 'R7_METHOD_SCOPE_WORDING_INDEPENDENT_ADDENDUM_PLAN_V1.json'
REPORT = OUT / 'R7_METHOD_SCOPE_WORDING_INDEPENDENT_ADDENDUM_V1.json'
LIMITS = {'wall_seconds': 10, 'address_space_bytes': 67108864,
          'total_read_bytes': 4194304, 'maximum_report_bytes': 65536}
INPUTS = {
    'frozen_main_review': OUT / 'R7_METHOD_CHECKPOINT_INDEPENDENT_REVIEW_V1.json',
    'frozen_payload_manifest': ROOT / 'r7-publication/method-checkpoint-v2/MANIFEST.json',
    'frozen_preparation_seal': ROOT / 'r7-publication/method-checkpoint-v2/PREPARATION_SEAL.json',
    'original_scope_V1': ROOT / 'r7-publication/R7_METHOD_DIAGNOSTICS_AND_CURRENT_BLOCKERS_V1.md',
    'additive_scope_V2': ROOT / 'r7-publication/R7_METHOD_DIAGNOSTICS_AND_CURRENT_BLOCKERS_V2.md',
    'root_exact_correction_record': ROOT / 'r7-publication/R7_METHOD_SCOPE_WORDING_CORRECTION_V2.json',
}
EXPECTED = {
    'frozen_main_review': '8893bb0c69bd3dadc9cd2bb85eeb0c432f1658f2a92f35923cff1d484cc208a9',
    'frozen_payload_manifest': '19c591f3f48af446215a79852149e75be14d9e0a73bfebc3f4db10f5a68f5872',
    'frozen_preparation_seal': '350ad67e35e0941504e843a5cb7658bb8f8c7c418483f11b128267ae21edccc6',
    'original_scope_V1': '73a86792746a332b647213e7de5d06dac823109e33b29a91548cd0ecb1d7366d',
    'additive_scope_V2': '0d5cf29aa9ee7f6e9c3f1a42e5de5ddae5688e0b1cfdce4ccee8e413a077eee0',
}
READ = 0


def read_blob(path):
    global READ
    blob = path.read_bytes()
    READ += len(blob)
    assert READ <= LIMITS['total_read_bytes']
    return blob


def identity(path, blob=None):
    if blob is None:
        blob = read_blob(path)
    assert READ <= LIMITS['total_read_bytes']
    return {'path': str(path), 'bytes': len(blob),
            'sha256': hashlib.sha256(blob).hexdigest(),
            'git_blob_sha': hashlib.sha1(b'blob ' + str(len(blob)).encode() + b'\0' + blob).hexdigest()}


def snapshot():
    out = {key: identity(path) for key, path in INPUTS.items()}
    for key, expected in EXPECTED.items():
        assert out[key]['sha256'] == expected, key
    return out


def write_new(path, value):
    blob = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    assert len(blob) <= LIMITS['maximum_report_bytes']
    with path.open('xb') as f:
        f.write(blob)
    return identity(path, blob)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def execute():
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('addendum wall budget')))
    signal.alarm(LIMITS['wall_seconds'])
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['address_space_bytes'], LIMITS['address_space_bytes']))
    assert not REPORT.exists()
    plan = json.loads(read_blob(PLAN))
    assert plan['source'] == identity(SELF)
    before = snapshot()
    assert before == plan['inputs']
    old = read_blob(INPUTS['original_scope_V1']).decode()
    new = read_blob(INPUTS['additive_scope_V2']).decode()
    correction = json.loads(read_blob(INPUTS['root_exact_correction_record']))
    main = json.loads(read_blob(INPUTS['frozen_main_review']))
    expected_new = old.replace(
        '# R7: finite witnesses, exact-source diagnostics and remaining blockers\n',
        '# R7: finite witnesses, exact-source diagnostics and remaining blockers — current scope V2\n', 1)
    expected_new = expected_new.replace(
        'The original OCP tolerance accessor has a Confusion floor; its reported scalar is not a certified native point-error bound or a measured uncertainty.',
        'The fixed official OCCT source for the tolerance accessor has a Confusion floor; equivalence to the installed OCP binary has not been proved. The original reported scalar is not a certified native point-error bound or a measured uncertainty.', 1)
    expected_new = expected_new.replace(
        'Subsequent archive creation succeeded after verified redundant copies were recovered.',
        'Subsequent archive creation succeeded after capacity was reclaimed from verified redundant local copies.', 1)
    expected_new = expected_new.replace(
        '\nThe next original-depth Cylinder source preparation is outside this completed checkpoint.',
        '\nThis V2 scope note corrects two wording ambiguities in the preserved V1 note: source-level OCCT semantics do not prove compiled binary equivalence, and redundant copies were reclaimed to free capacity. The original V1 note remains unchanged.\n\nThe next original-depth Cylinder source preparation is outside this completed checkpoint.', 1)
    assert new == expected_new, 'additive scope contains changes outside the stated two corrections and version/provenance text'
    diff = ''.join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                     fromfile=INPUTS['original_scope_V1'].name,
                                     tofile=INPUTS['additive_scope_V2'].name))
    assert correction['unified_diff'] == diff
    for name, key in [('previous', 'original_scope_V1'), ('current', 'additive_scope_V2')]:
        assert correction[name]['path'] == str(INPUTS[key].relative_to(ROOT))
        assert correction[name]['bytes'] == before[key]['bytes']
        assert correction[name]['sha256'] == before[key]['sha256']
    assert correction['original_manifest_and_all151_payloads_unchanged'] is True
    assert correction['new_geometry_or_acceptance_change'] is False
    assert main['prepublication_payload_review_pass_with_stated_scope_clarifications'] is True
    assert main['all_selected_bytes_unchanged_before_after'] is True
    assert main['all_blockers_closed'] is False and main['full_continuous_G2'] is False
    assert main['reviewed_payload_count'] == 151
    assert main['original_preparation_failure_and_all_four_partial_gzips_preserved'] is True
    after = snapshot()
    assert before == after
    assert identity(SELF) == plan['source']
    elapsed = time.monotonic() - started
    assert elapsed <= LIMITS['wall_seconds']
    report = {
        'schema': 'razr-r7-method-scope-wording-independent-addendum-v1',
        'recorded_utc': utc(), 'plan': identity(PLAN), 'source': identity(SELF),
        'limits': LIMITS, 'inputs_before_and_after_unchanged': before,
        'actual_unified_diff_matches_root_correction_record': True,
        'exact_allowed_change_reconstruction_equals_complete_V2_bytes': True,
        'resolved_wording_points': [
            {'original_point': 'The V1 phrase "redundant copies were recovered" was ambiguous.',
             'V2_resolution': 'Explicitly says capacity was reclaimed from verified redundant local copies; it does not claim restoration or recreation of deleted scientific originals.',
             'resolved': True},
            {'original_point': 'The V1 tolerance-accessor wording did not explicitly limit the claim to the reviewed official source.',
             'V2_resolution': 'Explicitly attributes the Confusion floor to the fixed official OCCT source and retains that equivalence to the installed OCP binary is unproved.',
             'resolved': True}],
        'original_main_audit_and_V1_note_unchanged': True,
        'frozen_151_payload_manifest_and_preparation_seal_unchanged': True,
        '151_payload_bytes_rechecked_in_this_addendum': False,
        'previous_complete151_double_readback_remains_the_bound_evidence': True,
        'new_acceptance_qualification_or_geometry_execution': False,
        'remote_ref_updated_or_final_remote_tree_checked_by_this_addendum': False,
        'main_payload_only_projected_tree_excludes_later_audit_or_scope_additions': True,
        'new_V2_scope_resolves_both_nonblocking_main_review_clarifications': True,
        'full_continuous_G2': False, 'all_blockers_closed': False,
        'elapsed_seconds': elapsed, 'total_read_bytes': READ,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
    }
    result = write_new(REPORT, report)
    signal.alarm(0)
    print(json.dumps(result, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--plan', action='store_true')
    p.add_argument('--execute', action='store_true')
    args = p.parse_args()
    assert args.plan != args.execute
    if args.plan:
        result = write_new(PLAN, {
            'schema': 'razr-r7-method-scope-wording-independent-addendum-plan-v1',
            'registered_utc': utc(), 'source': identity(SELF), 'limits': LIMITS,
            'inputs': snapshot(),
            'scope': 'Only six named small records and this source. Compare complete V1/V2 bytes, exact unified diff and unchanged frozen main review/manifest/seal. No full payload rerun, ZIP access, workspace scan, remote operation or source mutation.',
        })
        print(json.dumps(result, ensure_ascii=False))
    else:
        execute()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        failure = OUT / 'WORDING_ADDENDUM_ACTUAL_FAILURE_V1.json'
        if not failure.exists():
            write_new(failure, {'recorded_utc': utc(), 'type': type(error).__name__, 'error': str(error),
                                'original_inputs_modified': False, 'source': identity(SELF)})
        raise
