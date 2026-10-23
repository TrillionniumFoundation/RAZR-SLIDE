"""Collect byte-preserved numerical source and small receipts; exclude payloads."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import os
import shutil

WORK = Path('/workspace/scratch/95cd2986fdf2')
ROOT = WORK / 'RAZR-SLIDE'
BASE = Path(__file__).resolve().parent
PRIVATE = Path('/tmp/razr-fe-20261023')
OUT = WORK / 'input_recovery/numerical-delivery-20261023'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    OUT.mkdir(exist_ok=False)
    entries = []
    def copy(path, relative, kind, status=None):
        path = Path(path)
        assert path.is_file()
        assert path.suffix in ('.py', '.json', '.log', '.md')
        target = OUT / relative
        assert not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        assert sha(target) == sha(path)
        row = {'path': relative, 'original_path': str(path),
               'bytes': target.stat().st_size, 'sha256': sha(target), 'kind': kind}
        if status:
            row['execution_status'] = status
        entries.append(row)
    statuses = {
        'restore_exact_historical_metadata.py': 'executed; exact original metadata restored',
        'real_mesh_bounded_probe.py': 'executed; real mesh and 128-cell energy contracts only',
        'rebuild_l2_only.py': 'executed; complete panel L2 K, original executed source preserved',
        'rebuild_l2_tmp.py': 'executed; complete frame L2 K, publication EXDEV retained separately',
        'finalize_frame_matrix.py': 'executed; verified existing frame matrix publication, no FE rerun',
        'package_l2_matrices.py': 'executed; both archives verified, payload excluded from this delivery',
        'rebuild_base_response.py': 'executed; panel factor MemoryError under 3 GiB AS, no H completed',
        'rebuild_base_response_limited.py': 'executed; panel 2560/3885 columns, shared-memory resource stop',
        'supervise_base_response.py': 'executed; original 600-second and 6.8-GiB whole-cgroup guard',
        'freeze_partial_response.py': 'executed; stopped-worker 2560-column prefix hash closure',
        'rebuild_base_response_resumable.py': 'prepared; not executed',
        'supervise_response_chunks.py': 'prepared; not executed',
        'rebuild_base_response_mapped.py': 'prepared and reviewed; worker never launched',
        'supervise_response_mapped.py': 'executed preflight only; refused insufficient memory margin',
        'wait_for_panel_window.py': 'executed observer only; interrupted before any worker launch for disk coordination',
        'rebuild_base_response_budgeted.py': 'prepared; not executed; newest f_bavail storage-only variant',
        'supervise_response_budgeted.py': 'prepared; not executed; newest explicit disk and memory preflight',
        'combine_base_responses.py': 'prepared and reviewed; not executed; requires both complete body responses',
        'preflight_trace_interfaces.py': 'executed; all 86 original exterior interfaces mapped and locally verified',
        'rebuild_trace_response.py': 'prepared and independently small-contract reviewed; no large Schur or inverse run',
        'build_geometric_nd.py': 'executed for both bodies; exact graph and separator proofs, no factor',
        'build_geometric_nd_v2.py': 'executed for both bodies; minimum-cover axis selection, no factor',
        'predict_nd_fill.py': 'executed; symbolic fill and 100 small explicit-elimination checks, no numeric factor',
        'predict_nd_fill_fixed.py': 'executed for frame; original fully fixed scalar nodes removed, no numeric factor',
        'correct_symbolic_storage_accounting.py': 'executed; arithmetic label correction, old reports preserved',
        'prepare_numerical_delivery.py': 'executed; this metadata-only collector',
    }
    for name, status in statuses.items():
        source = BASE / name
        ast.parse(source.read_text())
        copy(source, 'sources/new/' + name, 'byte-preserved new source', status)
    pinned = json.loads((BASE / 'source-preflight.json').read_text())['file_sha256']
    originals = dict(pinned)
    for name in ('engineering/volume-convergence-20261017/frozen_load_response.py',
                 'engineering/volume-convergence-20261017/solve_enriched_contact.py',
                 'engineering/bearing-continuation-20261022/run_continuation.py',
                 'engineering/bearing-continuation-20261022/continued_rigid_bearing_probe.py'):
        p = ROOT / name
        if p.is_file():
            originals[str(p)] = sha(p)
    for name, expected in originals.items():
        p = Path(name)
        assert sha(p) == expected
        copy(p, 'sources/original/' + str(p.relative_to(ROOT)), 'original pinned numerical source',
             'original implementation source; inclusion does not mean its driver was executed')
    small_base = [
        'source-preflight.json', 'frozen-elastic-recovery.json', 'exact-PR35-input-recovery.json',
        'real-mesh-bounded-probe.json', 'panel-L2-artifact-receipt.json', 'frame-L2-artifact-receipt.json',
        'frame-saved-archive-local-cleanup.json', 'K-private-relocation.json',
        'owned-K-sync-cleanup.json', 'owned-partial-cleanup.json',
        'panel-partial-response-receipt.json', 'symbolic-storage-accounting-correction.json',
        'original-response-library-search.json',
        'l2-rebuild/panel/progress.json', 'l2-rebuild/frame/progress.json',
        'l2-rebuild/frame/delivery-finalization.json',
        'base-response/panel/progress.json',
        'real-projection-seed-diagnostic/report.json',
        'historical-original/volume/panel/level-2/report.json',
        'historical-original/volume/frame/level-2/report.json',
        'historical-original/legacy-seed/manifest.json',
        'trace-interface-delivery/manifest.json',
    ]
    for relative in small_base:
        copy(BASE / relative, 'evidence/local/' + relative, 'small receipt; may reference excluded payloads')
    private_paths = [
        'volume-rebuild/panel/level-2/report.json', 'volume-rebuild/frame/level-2/report.json',
        'base-response-425/panel/progress.json',
        'base-response-425/panel/partial-linear-response-manifest.json',
        'supervision/panel/progress.json', 'supervision/panel/report.json', 'supervision/panel/worker.log',
        'supervision/panel-mapped-resume1/report.json', 'supervision/panel-memory-window.json',
        'supervision/panel-memory-window-interruption.json',
        'trace-interface-preflight/report.json', 'trace-interface-preflight/panel/selection.json',
        'trace-interface-preflight/frame/selection.json',
    ]
    for directory in ('ordering-panel', 'ordering-frame', 'ordering-panel-v2',
                      'ordering-panel-v2-attempt2', 'ordering-frame-v2',
                      'symbolic-panel-v2', 'symbolic-frame-v2', 'symbolic-frame-v2-fixed'):
        for name in ('progress.json', 'report.json'):
            if (PRIVATE / directory / name).is_file():
                private_paths.append(directory + '/' + name)
    for relative in private_paths:
        copy(PRIVATE / relative, 'evidence/private/' + relative, 'small receipt; numeric payload intentionally excluded')
    copy(WORK / 'numeric_artifacts_saved.json', 'evidence/persistence-status.json', 'existing saved/blocked status only; no upload executed')
    copy(WORK / 'ci_audit/fe-adapter-independent-small-contracts.json',
         'evidence/independent-small-contract-review.json', 'independent small-contract evidence; not a large FE validation')
    current = dict(line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())
    kernel = max(int(current.get('kernel', 0)) - int(current.get('slab_reclaimable', 0)), 0)
    nonreclaimable = int(current['anon']) + int(current.get('shmem', 0)) + kernel + int(current.get('unevictable', 0))
    disk = os.statvfs(PRIVATE)
    state = {
        'schema': 'razr-numerical-delivery-state-v1',
        'captured_utc': datetime.now(timezone.utc).isoformat(),
        'original_inputs_exactly_restored': 8, 'original_input_manifest_entries': 11,
        'still_missing_original_bytes': ['panel K.npz', 'frame K.npz', 'legacy-seed response.npz'],
        'new_full_L2_K_completed_bodies': ['panel', 'frame'],
        'original_material_normalization': {'E': 1.0, 'nu': 0.3},
        'panel_original_vector_DOFs': 344103, 'frame_original_vector_DOFs': 474726,
        'panel_completed_base_H_columns': 2560, 'required_base_H_columns': 3885,
        'panel_remaining_base_H_columns': 1325, 'frame_base_H_columns_completed': 0,
        'panel_recorded_full_DOF_residual_max': 2.7066562324762344e-9,
        'panel_recorded_MMD_factor_nnz': 176412608,
        'panel_recorded_factor_seconds': 14.838245134000317,
        'panel_recorded_peak_RSS_KiB': 2684440,
        'original_five_full_inverse_probes_completed': False,
        'complete_base_H_available': False, 'complete_trace_H_available': False,
        'trace_interfaces_locally_verified': {'panel': 46, 'frame': 40},
        'original_trace_skfem_driver_executed': False,
        'new_explicit_Schur_adapter_prepared_not_executed': True,
        'new_bearing_QP_executed': False, 'bearing_restart_checkpoint_created': False,
        'whole_contact_or_mesh_convergence_qualified': False,
        'physical_or_current_EP5_structural_qualification': False,
        'resource_stop_is_not_mathematical_failure': True,
        'numeric_worker_running': False,
        'memory_snapshot': {'anon': int(current['anon']), 'shmem': int(current.get('shmem', 0)),
                            'kernel_excluding_reclaimable_slab': kernel,
                            'estimated_unreclaimable_bytes': nonreclaimable,
                            'approved_whole_cgroup_stop_bytes': int(6.8 * 1024**3),
                            'panel_incremental_reserve_bytes': int(2.4 * 1024**3)},
        'disk_snapshot': {'nonprivileged_available_bytes': disk.f_bavail * disk.f_frsize,
                          'root_free_bytes_not_used_for_new_task_budget': disk.f_bfree * disk.f_frsize,
                          'panel_start_floor_bytes': 1024 * 1024**2,
                          'frame_start_floor_bytes': 1152 * 1024**2,
                          'runtime_reserve_bytes': 500 * 1024**2},
        'next_worker_decision': 'do not start until parent coordinates disk and memory window; no background observer remains',
        'ND_decision': 'do not numeric-factor these geometric permutations; exact symbolic storage is worse than measured panel MMD and too large for frame',
        'matrix_payloads_excluded_from_this_delivery': True,
    }
    write(OUT / 'STATUS.json', state)
    runtime = json.loads((PRIVATE / 'volume-rebuild/panel/level-2/report.json').read_text())['runtime']
    deps = {
        'runtime_actually_recorded_during_full_assembly': runtime,
        'locked_project_file': str(ROOT / 'uv.lock'), 'uv_lock_sha256': sha(ROOT / 'uv.lock'),
        'pyproject_toml_sha256': sha(ROOT / 'pyproject.toml'),
        'new_solver_dependencies_installed': False,
        'scikit_fem_installed_in_locked_environment': False,
        'thread_environment': {'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'PYTHONDONTWRITEBYTECODE': '1'},
        'numerical_identity_binds_individual_sources_and_inputs_not_moving_repo_HEAD': True,
        'all_13_PR35_pinned_sources_reverified_exact': True,
        'execution_absolute_roots': {'repo': str(ROOT), 'new_sources': str(BASE), 'large_private_artifacts': str(PRIVATE)},
        'relocation_rule': 'Preserve recorded executed sources. Changing hard-coded roots or adapters creates a new source identity and requires an explicit new run receipt.',
    }
    write(OUT / 'DEPENDENCIES.json', deps)
    environment = {'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    interpreter = str(ROOT / '.venv/bin/python')
    prefix = [interpreter, '-B']
    commands = []
    def cmd(name, args, status, note):
        commands.append({'id': name, 'cwd': str(WORK), 'environment': environment,
                         'argv': prefix + [str(BASE / args[0])] + args[1:],
                         'status': status, 'scope_or_prerequisites': note})
    cmd('panel_full_L2_K', ['rebuild_l2_only.py', '--body', 'panel', '--output', str(BASE / 'l2-rebuild/panel')],
        'executed', 'Original executed panel source preserved; old output already exists; do not rerun in place.')
    cmd('frame_full_L2_K', ['rebuild_l2_tmp.py', '--body', 'frame', '--output', str(BASE / 'l2-rebuild/frame')],
        'executed', 'Numerical assembly completed; final publication EXDEV separately repaired from exact finished bytes.')
    cmd('frame_delivery_finalization', ['finalize_frame_matrix.py'], 'executed', 'Publication only; no duplicate FE assembly.')
    old_supervision = json.loads((PRIVATE / 'supervision/panel/report.json').read_text())
    commands.append({'id': 'panel_original_2560_column_worker', 'cwd': str(BASE), 'environment': environment,
                     'argv': old_supervision['command'], 'status': 'executed and resource-stopped',
                     'exact_command_source': 'evidence/private/supervision/panel/report.json'})
    cmd('freeze_panel_partial', ['freeze_partial_response.py', '--supervisor-report', str(PRIVATE / 'supervision/panel/report.json')],
        'executed', 'Hash-binds the supervisor final progress, stopped producer, all inputs/sources/C/points and completed H prefix.')
    cmd('trace_interface_preflight', ['preflight_trace_interfaces.py', '--output', str(PRIVATE / 'trace-interface-preflight')],
        'executed', 'Exact original 46+40 interfaces and local energy blocks; no full inverse or QP.')
    for body, out in [('panel', 'ordering-panel-v2-attempt2'), ('frame', 'ordering-frame-v2')]:
        cmd(body + '_ND_v2', ['build_geometric_nd_v2.py', '--body', body, '--output', str(PRIVATE / out)],
            'executed', 'Actual K graph, exact minimum vertex cover and absence of cross-child edges; no numeric factor.')
        cmd(body + '_ND_symbolic_fill', ['predict_nd_fill.py', '--body', body, '--ordering-report', str(PRIVATE / out / 'report.json'),
                                        '--output', str(PRIVATE / ('symbolic-' + body + '-v2'))],
            'executed', 'Pure symbolic elimination; read separate accounting correction for the old L/U union labels.')
    cmd('frame_ND_symbolic_original_fixed_DOFs', ['predict_nd_fill_fixed.py', '--body', 'frame',
           '--ordering-report', str(PRIVATE / 'ordering-frame-v2/report.json'), '--output', str(PRIVATE / 'symbolic-frame-v2-fixed')],
        'executed', 'Original 777 vector constraints are 259 complete scalar nodes; no partially fixed scalar nodes.')
    cmd('panel_next_budgeted_resume', ['supervise_response_budgeted.py', '--body', 'panel',
           '--attempt-label', 'panel-budgeted-resume1', '--resume-manifest',
           str(PRIVATE / 'base-response-425/panel/partial-linear-response-manifest.json'), '--resume-sha256',
           'e64d3102eff7239a11d1e512c8711c78e4637e2af851fd7efee0aefe2a7a6520'],
        'prepared; not executed', 'Needs >=1 GiB f_bavail and <=4.4 GiB baseline nonreclaimable memory, plus parent resource coordination. Guard: AS4.25 GiB, wall600s, whole-cgroup6.8 GiB, disk500 MiB. Original MMD, precision, D and tolerances unchanged.')
    write(OUT / 'COMMANDS.json', {'schema': 'razr-exact-command-ledger-v1', 'commands': commands,
                                'commands_are_not_an_automatic_execution_script': True})
    readme = '''# PR35 numerical recovery: source and evidence delivery

This directory contains byte-preserved Python sources, JSON metadata and small logs. It intentionally excludes every K, H, C, mesh, load, trace-block, permutation and field payload. An inventory of a payload is not the payload itself. The larger numerical artifacts remain separately identified by SHA-256 and original/private paths.

## Executed results

Eight of the eleven named historical input files were recovered with their original SHA-256 identities: two meshes, two load files, two original volume reports, legacy points and legacy manifest. The original two K files and original response.npz have not been recovered. The recovered old reports must not be paired with the newly reconstructed matrices.

Both complete L2 stiffness matrices were newly assembled using the recovered original meshes/DOF order/constraints and the existing locked primitive tetrahedral formulas, with normalized E=1 and nu=0.3. Panel has 344,103 original vector DOFs; frame has 474,726. All original surface P2 traces remain unchanged and the added volume DOFs are internally condensed. Full assembly energy and six rigid-mode checks passed. These are five assembly-energy checks, not the five inverse-operator probes.

The first panel inverse attempt hit its explicit 3 GiB address-space limit. The subsequent 4.25 GiB MMD attempt completed 2,560 of 3,885 whole-operator response columns, with maximum full free-DOF residual 2.7066562324762344e-9, before a 6.8 GiB shared-memory guard stopped the worker. The stopped prefix and exact producer/source/input/C/point/progress hashes are frozen. It is a partial linear-response checkpoint, not an accepted finite-QP state or bearing restart. No complete H or original five-probe inverse validation has yet completed, and frame H has not started.

The explicit trace preflight verified the original 46 panel and 40 frame exterior faces, exact parent/local-face order, original trace coefficient order, original DOF coordinates, old energy blocks and zero interaction with the original fixed coordinates. It is a new, named adapter using the existing trace primitives. The original scikit-fem driver was not executed; scikit-fem is absent from the locked environment. The full Schur worker is prepared and its formulas were independently checked on small SPD contracts, but no full trace inverse or QP was run.

Both real sparse graphs were ordered by geometric nested dissection with exact minimum vertex covers and independent no-cross-edge checks. Symbolic elimination shows these permutations are not a justified memory improvement: the frame free system would use 415,297,008 separate L/U entries, about 4,987,355,696 bytes for the simple float64/int32 CSC arrays before factorization overhead. No ND numeric factor was attempted. Older symbolic reports mislabeled the L/U structural union as separate factor storage; the independent correction receipt preserves those reports and gives the corrected two-diagonal counts. These counts are not SuperLU peak-RSS predictions.

## Current resource decision and next executable step

No numerical worker or background observer remains running. The previous observer was stopped before any worker launch when disk margin changed. New task budgets use statvfs.f_bavail; root-reserved filesystem blocks are excluded. The newest prepared budgeted panel supervisor requires 1 GiB available disk at startup, retains 500 MiB during execution, keeps the 4.25 GiB AS and 6.8 GiB shared-memory bounds, and reserves 2.4 GiB incremental memory before launch. The concrete command is in COMMANDS.json. It has not been executed.

This storage-only worker maps the exact original Kff arrays read-only, keeps the original MMD ordering and numerical thresholds, resumes only a hash-verified prefix, and computes all remaining columns. It then genuinely solves the original five deterministic complete-K RHS actions, saves the full fields and RHS hashes, releases LU, and invokes the original restore interface with a callback limited to those five exact RHS values. That callback is not a general solver. The newest prepared version also rehashes derived Kff before deletion and uses chunked H extrema to avoid an unnecessary full-sized temporary array.

After panel completion, frame needs its own bounded measured factor/response run. Only two complete body responses and their full-field checks can be combined and validated by the original five-probe contract. Then the explicit trace Schur adapter may produce a separately identified response and be used to construct a genuine initial bearing state under the unchanged mathematical criteria. A finite QP, all-domain gap audit, force/moment/complementarity checks and independent audit are still required before any research closure. No current EP5 structural, physical, service, fixture or manufacturing qualification is implied.

## Evidence and reproduction

STATUS.json is the snapshot of achieved and pending work. COMMANDS.json separates executed commands from prepared commands. DEPENDENCIES.json records the actual runtime and uv.lock SHA. MANIFEST.json maps each delivered byte to its original source path and SHA. Executed sources are preserved without refactoring, including their original absolute path constants; relocating them is a new source identity and requires a new receipt. Do not overwrite an existing output or a historical receipt.

The frame archive was successfully saved before its redundant local compressed copy was removed; its raw K and inputs remain. The panel archive remains local because automatic approval review blocked its external save. This metadata delivery performs no external upload and provides no alternate upload route. Large payload retention and authorization are separate from this source/metadata submission.
'''
    (OUT / 'README.md').write_text(readme)
    for relative in ('STATUS.json', 'DEPENDENCIES.json', 'COMMANDS.json', 'README.md'):
        target = OUT / relative
        entries.append({'path': relative, 'bytes': target.stat().st_size, 'sha256': sha(target),
                        'kind': 'new delivery metadata'})
    manifest = {'schema': 'razr-numerical-source-evidence-delivery-v1',
                'created_utc': state['captured_utc'], 'collector_source_sha256': sha(__file__),
                'excluded_payload_extensions': ['.npz', '.npy', '.tar', '.xz', '.gz', '.step', '.brep'],
                'executed_results_are_not_reclassified_by_packaging': True,
                'files': entries, 'file_count_excluding_this_manifest': len(entries),
                'total_bytes_excluding_this_manifest': sum(row['bytes'] for row in entries)}
    write(OUT / 'MANIFEST.json', manifest)
    for row in entries:
        assert sha(OUT / row['path']) == row['sha256']
    assert all(p.suffix in ('.py', '.json', '.log', '.md') for p in OUT.rglob('*') if p.is_file())
    print(json.dumps({'directory': str(OUT), 'files_including_manifest': len(entries) + 1,
                      'payload_bytes': manifest['total_bytes_excluding_this_manifest'],
                      'manifest_sha256': sha(OUT / 'MANIFEST.json')}))


if __name__ == '__main__':
    main()
