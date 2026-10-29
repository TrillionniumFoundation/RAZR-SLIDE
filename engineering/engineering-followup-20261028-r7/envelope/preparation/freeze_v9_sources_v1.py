"""Freeze the complete new V9 package after both source authors finish.

This script hashes and checks source bytes only. It performs no geometry or
channel search and does not turn any source review into a qualification.
"""
from datetime import datetime, timezone
import ast
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'source-v9'
WORKSPACE = ROOT.parent
OLD = WORKSPACE / 'r7-recovery/v7/r5-local-v7/input-snapshot-v1/source'
R4 = WORKSPACE / 'r7-recovery/v7/r5-local-v7/input-snapshot-v1/r4'


def ident(path):
    data = path.read_bytes()
    return {'path': path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    started = time.monotonic()
    original = json.loads((OLD / 'R5E_PORTABLE_SOURCE_LOCK_V7.json').read_text())
    old_names = [r['path'] for r in original['r5_files']] + ['R5E_PORTABLE_SOURCE_LOCK_V7.json']
    new_names = ['planar_exterior_model_r7e_v9.py', 'planar_exterior_refinement_r7e_v9.py',
                 'verify_planar_exterior_r7e_v9.py', 'run_portable_planar_r7e_v9.py',
                 'R7E_ORIGINAL_LINE_PLANE_V9_BASIS.md', 'R7E_V9_STATIC_SOURCE_CAPACITY.json',
                 'R7E_V9_ORIGINAL_LINE_PLANE_PROJECTION.json']
    destination = SOURCE / 'R7E_PORTABLE_SOURCE_LOCK_V9.json'
    receipt_path = ROOT / 'R7E_V9_SOURCE_FREEZE_RECEIPT_V1.json'
    assert not destination.exists() and not receipt_path.exists(), 'preserve every frozen package and receipt'
    assert len(old_names) == len(set(old_names)) == 38
    expected = set(old_names + new_names)
    actual = {p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*') if p.is_file()}
    assert actual == expected, {'missing': sorted(expected - actual), 'extra': sorted(actual - expected)}
    assert not any(p.is_symlink() for p in SOURCE.rglob('*'))
    for name in old_names:
        assert (SOURCE / name).read_bytes() == (OLD / name).read_bytes(), name
    for name in expected:
        path = SOURCE / name
        if name.endswith('.py'):
            ast.parse(path.read_text())
    rows = [ident(SOURCE / name) for name in old_names + new_names]
    r4 = []
    for row in original['r4_source_files']:
        actual = ident(R4 / row['path'])
        assert all(actual[k] == row[k] for k in ('bytes', 'sha256'))
        r4.append(row)
    lock = dict(original)
    lock.update(schema='razr-r7e-portable-source-lock-v9-original-Line-plane-hulls',
                r5_files=rows, r4_source_files=r4,
                recovered_repository_commit='65f2a8fbb30d6310c1a69ef37204fa7fa8f32b3a',
                original_V7_source_lock=ident(SOURCE / 'R5E_PORTABLE_SOURCE_LOCK_V7.json'),
                new_revision_based_on_recovered_V7=True, missing_V8_bytes_reconstructed=False,
                actual_original_domain_diagnosis=ident(ROOT / 'diagnostic-v1/attempt-2/R7E_ORIGINAL_LINE_PLANE_DOMAIN_DIAGNOSIS_V2.json'),
                additional_source_planes=2, additional_original_Line_occurrences=18,
                additional_UV_boundary_pieces=36,
                original_computational_budgets_changed=False,
                source_capacity={'original_plane_models': 48, 'additional_plane_models': 2,
                                 'total_plane_models': 50, 'original_UV_boundary_pieces': 4064,
                                 'additional_UV_boundary_pieces': 36, 'total_UV_boundary_pieces': 4100},
                new_worker_execution_claimed=False)
    destination.write_text(json.dumps(lock, indent=2) + '\n')
    receipt = {'schema': 'razr-r7e-v9-complete-source-freeze-receipt-v1',
               'created_utc': datetime.now(timezone.utc).isoformat(),
               'source': ident(Path(__file__)), 'source_lock': ident(destination),
               'original_source_files_unchanged': 38, 'new_named_source_files': 7,
               'complete_source_member_count_including_lock': len(expected) + 1,
               'original_R4_source_files_verified': 3,
               'source_files': rows, 'new_worker_executions': 0,
               'new_mathematical_qualification': False, 'full_continuous_G2': False,
               'elapsed_seconds': time.monotonic() - started}
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'source_lock': ident(destination), 'receipt': ident(receipt_path),
                      'source_files': len(expected), 'executed': False}))


if __name__ == '__main__':
    main()
