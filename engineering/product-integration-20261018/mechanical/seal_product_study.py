"""Package the independently read-back, frozen product study without builders."""
from pathlib import Path
import argparse
import gzip
import hashlib
import importlib.metadata
import io
import json
import platform
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def runtime_provenance():
    """Observe this process; never substitute it for another job's runtime."""
    packages = {}
    for name in ('cadquery', 'cadquery-ocp', 'numpy', 'scipy', 'ezdxf'):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    try:
        commit = subprocess.run(
            ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
            capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        commit = None
    return {'schema': 'razr-observed-python-runtime-v1',
            'observed_utc': datetime.now(timezone.utc).isoformat(),
            'scope': 'this process only; other jobs need their own execution receipt',
            'executable': sys.executable,
            'resolved_executable': str(Path(sys.executable).resolve()),
            'python_version': sys.version,
            'implementation': platform.python_implementation(),
            'platform': platform.platform(),
            'installed_distribution_versions': packages,
            'distribution_RECORD_integrity_verified_by_this_helper': False,
            'source_checkout_commit_at_observation': commit,
            'source_root': str(ROOT),
            'recorder_sha256': sha(__file__)}


def copy_evidence(source, destination):
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--evidence-dir', type=Path, default=HERE,
                        help='directory containing added-material and readback receipts; also receives final artifacts')
    parser.add_argument('--runtime-report', type=Path,
                        help='write an observation of this Python process and exit without packaging')
    parser.add_argument('--execution-record', type=Path,
                        help='optional external record of the actual generation and readback commands')
    parser.add_argument('--reconstruction', action='store_true',
                        help='label this package as a new execution replacing lost local artifacts')
    args = parser.parse_args()
    if args.runtime_report:
        args.runtime_report.write_text(json.dumps(runtime_provenance(), indent=2) + '\n')
        print(json.dumps({'runtime_report': str(args.runtime_report),
                          'sha256': sha(args.runtime_report)}), flush=True)
        return
    if args.input is None:
        parser.error('--input is required unless --runtime-report is used')
    source = args.input.resolve()
    evidence = args.evidence_dir.resolve()
    if evidence == source or source in evidence.parents or evidence == ROOT:
        raise ValueError('evidence directory must not be the primary output, inside it, or the repository root')
    evidence.mkdir(parents=True, exist_ok=True)
    run = json.loads((source / 'run-summary.json').read_text())
    for rel, expected in run['source_sha256'].items():
        if sha(ROOT / rel) != expected:
            raise ValueError('frozen source changed: ' + rel)
    for name in ('targeted-tests.txt', 'targeted-tests.json', 'product-motion-report.json',
                 'oled-motion-report.json', 'run-summary.json'):
        copy_evidence(source / name, evidence / name)
    for name in ('README.md', 'verify_product_exports.py', 'verify_added_material_motion.py',
                 'run_product_study.py', 'seal_product_study.py',
                 'geometry-wide-B-negative-control.json', 'metadata-correction.json'):
        if (HERE / name).is_file():
            copy_evidence(HERE / name, evidence / name)
    archives = {}
    elapsed_readback = 0.
    for pose, count in (('STOW', 99), ('PREDOCK', 99), ('OPEN', 106)):
        folder = source / pose
        manifest = json.loads((folder / 'manifest.json').read_text())
        reader_path = evidence / ('readback-' + pose + '.json')
        reader = json.loads(reader_path.read_text())
        if not reader['passed'] or reader['manifest_sha256'] != sha(folder / 'manifest.json'):
            raise ValueError('readback does not match exported bytes')
        if reader['reader_sha256'] != sha(HERE / 'verify_product_exports.py'):
            raise ValueError('reader source changed')
        if len(manifest['exports']) != count or reader['participant_count'] != count:
            raise ValueError('unexpected complete participant count')
        mechanical = manifest['mechanical']
        if (mechanical.get('installed_mechanical_parts') != count - 5 or
                mechanical.get('expected_scene_participants') != count - 5 or
                mechanical.get('material_geometry_changed') is not True or
                mechanical.get('native_baseline_expected_scene_participants') != 83 or
                mechanical.get('native_baseline_material_geometry_changed') is not False):
            raise ValueError('current candidate metadata does not match its mechanical payload')
        for rel, expected in manifest['generator_source_sha256'].items():
            if sha(ROOT / rel) != expected:
                raise ValueError('export generator/configuration changed')
        members = sorted(folder.iterdir())
        if any(not f.is_file() or f.is_symlink() for f in members):
            raise ValueError('only regular direct export files may be packaged')
        out = evidence / ('native-' + pose + '.tar.gz')
        with out.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as archive:
                for path in members:
                    data = path.read_bytes()
                    member = tarfile.TarInfo(path.name)
                    member.mode = 0o644
                    member.mtime = 0
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
        # Validate every packaged member byte against the exact completed
        # export directory. No unsafe extraction or first-file-only check.
        with tarfile.open(out, 'r:gz') as archive:
            infos = archive.getmembers()
            if len(infos) != len(members) or len({m.name for m in infos}) != len(infos):
                raise ValueError('archive count or duplicate member mismatch')
            for member in infos:
                if not member.isfile() or Path(member.name).name != member.name:
                    raise ValueError('unsafe archive member')
                payload = archive.extractfile(member).read()
                if hashlib.sha256(payload).hexdigest() != sha(folder / member.name):
                    raise ValueError('packaged byte mismatch')
        archives[pose] = {'path': out.name, 'sha256': sha(out), 'bytes': out.stat().st_size,
                          'archive_members': len(members), 'STEP_participants': count,
                          'manifest_sha256': sha(folder / 'manifest.json'),
                          'readback_receipt': reader_path.name,
                          'readback_sha256': sha(reader_path),
                          'all_member_bytes_rechecked': True,
                          'finite_added_M1_tool_access_clear': reader['added_nominal_M1_driver_access_clear']}
        elapsed_readback += reader['elapsed_seconds']
    motion = json.loads((evidence / 'product-motion-report.json').read_text())
    oled = json.loads((evidence / 'oled-motion-report.json').read_text())
    added = json.loads((evidence / 'added-material-motion-report.json').read_text())
    for rel, expected in added['source_sha256'].items():
        if sha(ROOT / rel) != expected:
            raise ValueError('added-material proof is not the frozen source')
    runtime_path = evidence / 'sealing-runtime.json'
    runtime_path.write_text(json.dumps(runtime_provenance(), indent=2) + '\n')
    external_execution = None
    if args.execution_record:
        # Preserve the supplied bytes. The sealer does not invent start/end
        # times or claim that its own interpreter produced earlier exports.
        json.loads(args.execution_record.read_text())
        execution_path = evidence / 'execution-record.json'
        copy_evidence(args.execution_record, execution_path)
        external_execution = {'path': execution_path.name, 'sha256': sha(execution_path),
                              'contents_are_external_job_observations': True}
    historical = {}
    for name in ('source-downloads.json', 'export-cache-drift-negative.json',
                 'geometry-trial-r0.json', 'geometry-trial-r1.json', 'geometry-trial-r2.json',
                 'packing-report.json', 'rejected-r2-product-motion-report.json'):
        path = HERE / name
        if path.is_file():
            copy_evidence(path, evidence / name)
            historical[name] = {'status': 'present_historical_record_not_rerun_by_sealer',
                                'sha256': sha(path)}
        else:
            historical[name] = {'status': 'not_available; no exact-byte restoration claimed'}
    record = {'schema': 'razr-mechanical-product-delivery-v1',
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'artifact_execution': 'new reconstruction after local artifact loss' if args.reconstruction else 'current input run',
              'historical_archive_bytes_reused_or_hashes_assumed': False,
              'primary_output_directory': str(source),
              'evidence_directory': str(evidence),
              'sealing_runtime': {'path': runtime_path.name, 'sha256': sha(runtime_path),
                                  'not_a_substitute_for_generation_runtime': True},
              'external_execution_record': external_execution,
              'historical_evidence_availability': historical,
              'base_commit': 'a1b3cc1e0773446f2e36d0a607edf61211dd9919',
              'product_source_sha256': run['source_sha256'],
              'targeted_tests': {'tests': run['targeted_tests']['tests'], 'passed': run['targeted_tests']['passed']},
              'four_state_changed_part_pairs': sum(r['checked_pairs'] for r in motion['four_state_checks']),
              'nominal_motion_checks_nonpenetrating': motion['all_requested_geometry_checks_nonpenetrating'],
              'OLED_complete_enclosure_checks': len(oled['checks']),
              'OLED_enclosures_clear': oled['all_declared_enclosures_clear'],
              'added_material_regions': added['positive_material_regions'],
              'added_material_scene_participants': added['full_scene_participants_excluding_separately_verified_OLED'],
              'added_material_three_stage_pair_count': added['positive_material_regions'] *
                  (added['full_scene_participants_excluding_separately_verified_OLED'] - 1) * 3,
              'added_material_enclosures_clear': added['all_added_material_nominal_motion_enclosures_clear'],
              'native_archives': archives,
              'durations_seconds': {'primary_checks_and_three_exports': run['elapsed_seconds'],
                                    'added_material_proof': added['elapsed_seconds'],
                                    'independent_readbacks_sum': elapsed_readback,
                                    'readback_durations_are_sum_not_wall_time': True},
              'independent_STEP_readback_still_required': False,
              'geometry_parameter_vs_selected_module_fit': 'unselected trial OLED and four allocation boxes; no physical complete phone',
              'complete_OEM_phone_hardware_cycle': False,
              'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}
    report_paths = ('targeted-tests.json', 'targeted-tests.txt', 'product-motion-report.json',
                    'oled-motion-report.json', 'added-material-motion-report.json',
                    'README.md', 'sealing-runtime.json',
                    'verify_product_exports.py', 'verify_added_material_motion.py',
                    'run_product_study.py', 'seal_product_study.py')
    record['evidence_sha256'] = {name: sha(evidence / name) for name in report_paths}
    for name in ('geometry-wide-B-negative-control.json', 'metadata-correction.json'):
        if (evidence / name).is_file():
            record['evidence_sha256'][name] = sha(evidence / name)
    (evidence / 'final-delivery.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
