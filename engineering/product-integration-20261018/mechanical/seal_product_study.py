"""Package the independently read-back, frozen product study without builders."""
from pathlib import Path
import argparse
import gzip
import hashlib
import io
import json
import shutil
import tarfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args()
    source = args.input.resolve()
    run = json.loads((source / 'run-summary.json').read_text())
    for rel, expected in run['source_sha256'].items():
        if sha(ROOT / rel) != expected:
            raise ValueError('frozen source changed: ' + rel)
    for name in ('targeted-tests.txt', 'targeted-tests.json', 'product-motion-report.json',
                 'oled-motion-report.json', 'run-summary.json'):
        shutil.copy2(source / name, HERE / name)
    archives = {}
    elapsed_readback = 0.
    for pose, count in (('STOW', 99), ('PREDOCK', 99), ('OPEN', 106)):
        folder = source / pose
        manifest = json.loads((folder / 'manifest.json').read_text())
        reader_path = HERE / ('readback-' + pose + '.json')
        reader = json.loads(reader_path.read_text())
        if not reader['passed'] or reader['manifest_sha256'] != sha(folder / 'manifest.json'):
            raise ValueError('readback does not match exported bytes')
        if reader['reader_sha256'] != sha(HERE / 'verify_product_exports.py'):
            raise ValueError('reader source changed')
        if len(manifest['exports']) != count or reader['participant_count'] != count:
            raise ValueError('unexpected complete participant count')
        for rel, expected in manifest['generator_source_sha256'].items():
            if sha(ROOT / rel) != expected:
                raise ValueError('export generator/configuration changed')
        members = sorted(folder.iterdir())
        if any(not f.is_file() or f.is_symlink() for f in members):
            raise ValueError('only regular direct export files may be packaged')
        out = HERE / ('native-' + pose + '.tar.gz')
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
    motion = json.loads((HERE / 'product-motion-report.json').read_text())
    oled = json.loads((HERE / 'oled-motion-report.json').read_text())
    added = json.loads((HERE / 'added-material-motion-report.json').read_text())
    for rel, expected in added['source_sha256'].items():
        if sha(ROOT / rel) != expected:
            raise ValueError('added-material proof is not the frozen source')
    record = {'schema': 'razr-mechanical-product-delivery-v1',
              'created_utc': datetime.now(timezone.utc).isoformat(),
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
                                    'independent_processes_ran_partly_in_parallel': True},
              'geometry_parameter_vs_selected_module_fit': 'unselected trial OLED and four allocation boxes; no physical complete phone',
              'complete_OEM_phone_hardware_cycle': False,
              'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}
    report_paths = ('targeted-tests.json', 'targeted-tests.txt', 'product-motion-report.json',
                    'oled-motion-report.json', 'added-material-motion-report.json',
                    'source-downloads.json', 'export-cache-drift-negative.json', 'README.md',
                    'verify_product_exports.py', 'verify_added_material_motion.py',
                    'run_product_study.py', 'seal_product_study.py')
    record['evidence_sha256'] = {name: sha(HERE / name) for name in report_paths}
    (HERE / 'final-delivery.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
