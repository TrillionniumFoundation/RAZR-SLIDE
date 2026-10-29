"""Make a lossless reviewable native evidence checkpoint; do not mutate Git refs."""
import hashlib
import json
from pathlib import Path
import resource
import shutil
import signal
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'engineering/engineering-followup-20261028-r7/'
PARENT = '8bb6f52b624cd40a0570f8710f140bb5a0abf96f'
BASE_TREE = '5081698dbb0b73047270b389aec554575f35ba83'
OUT = ROOT / 'r7-publication/native-finite-checkpoint-v1'
ZIP_NAME = 'R7_NATIVE_FINITE_ORIGINAL_REPORTS_AND_BINDINGS_V1.zip'

def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def main():
    assert not OUT.exists(), 'New immutable checkpoint output required'
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('60-second publication preparation budget')))
    signal.alarm(60)
    selected = {}

    def add(p, destination):
        p = Path(p)
        assert p.is_file() and not p.is_symlink()
        assert p.resolve().is_relative_to(ROOT)
        assert '.private.' not in p.name and 'r7-private-helpers' not in p.parts
        assert '__pycache__' not in p.parts and p.suffix != '.pyc'
        destination = PREFIX + destination
        assert destination not in selected
        selected[destination] = p.resolve()

    def tree(local, destination):
        d = ROOT / local
        assert d.is_dir()
        for p in sorted(d.rglob('*')):
            if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and p.suffix != '.pyc':
                add(p, destination + '/' + p.relative_to(d).as_posix())

    for p in sorted((ROOT / 'r7-native').iterdir()):
        if p.is_file():
            add(p, 'native/' + p.name)
    for name in ('native80-attempt1', 'recovered-science-v1', 'setup-assess_only-v1',
                 'setup-assess_only-v2', 'setup-assess_only-v3', 'setup-install_only-v2',
                 'setup-install_only-v3'):
        tree('r7-native/' + name, 'native/' + name)
    for pose in ('near', 'far'):
        raw = ROOT / ('r7-native/full-' + pose + '-attempt1')
        dest = 'native/full-' + pose + '-attempt1'
        for p in sorted(raw.iterdir()):
            if p.is_file():
                add(p, dest + '/' + p.name)
        for name in ('factory', 'readback', 'verify-complete-owned', 'export-engineering-owned', 'source'):
            tree(str(raw.relative_to(ROOT) / name), dest + '/' + name)
    for name in ('native-review-v1', 'native-setup-v2-review', 'native-setup-v3-review',
                 'native-stage-v4-review', 'native80-archive', 'near-full-archive',
                 'far-full-archive', 'full-factory-review', 'runtime-cleanup-correspondence',
                 'uv-01010-primary-source', 'external-status'):
        tree('r7-audit/' + name, 'independent-review/' + name)
    for p in sorted((ROOT / 'r7-audit').glob('*.py')):
        if any(s in p.name for s in ('native', 'far', 'near', 'runtime', 'uv_', 'full_factory')):
            add(p, 'independent-review/source/' + p.name)
    for name in ('R7_NATIVE80_COMPLETE_PRESERVATION_V1.json', 'R7_NEAR_COMPLETE_PRESERVATION_V1.json',
                 'R7_FAR_COMPLETE_PRESERVATION_V1.json'):
        add(ROOT / 'r7-deliverables' / name, 'preservation/' + name)
    for name in ('R7_MAIN_CHECKOUT_CAPACITY_RECOVERY_V1.json', 'R7_MAIN_CHECKOUT_CAPACITY_RECOVERY_V2.json',
                 'R7_DURABLE_ORIGINAL_ZIP_DOWNLOAD_CACHE_RECLAIM_V1.json',
                 'reclaim_archived_near_engineering_copy_v1.py', 'R7_NEAR_ENGINEERING_ARCHIVE_MIGRATION_V1.json',
                 'reclaim_saved_native80_zip_cache_v1.py', 'R7_SAVED_NATIVE80_ZIP_CACHE_RECLAIM_V1.json'):
        add(ROOT / 'r7-publication' / name, 'preservation/' + name)
    add(ROOT / 'r7-publication/R7_NATIVE_FINITE_WITNESSES_README_V1.md', 'NATIVE_FINITE_WITNESSES.md')
    add(Path(__file__), 'publication/prepare_native_finite_publication_v1.py')

    rows = []
    for dest, p in sorted(selected.items()):
        data = p.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        try:
            text = data.decode('utf-8')
            textual = '\0' not in text
        except UnicodeDecodeError:
            textual = False
        archived = (len(data) > 98304 or not textual or p.suffix.lower() in ('.brep', '.step', '.stp', '.gz', '.zip'))
        rows.append({'repository_path': dest, 'local_path': str(p), 'bytes': len(data),
                     'sha256': hashlib.sha256(data).hexdigest(), 'original_git_blob_sha': blob,
                     'representation': 'lossless_member_in_public_checkpoint_zip' if archived else 'individual_original_file',
                     'zip_member': dest if archived else None})
    total = sum(r['bytes'] for r in rows)
    assert total <= 268435456
    assert shutil.disk_usage(ROOT).free >= 67108864 + 134217728
    OUT.mkdir()
    plan = {'schema': 'razr-r7-native-finite-checkpoint-plan-v1', 'parent_commit': PARENT,
            'base_tree': BASE_TREE, 'full_original_selected_bytes': total, 'selected_member_count': len(rows),
            'archive_output_cap_bytes': 67108864, 'ordinary_free_floor_bytes': 134217728,
            'wall_seconds': 60, 'address_space_bytes': 268435456,
            'all_selected_originals_preserved': True,
            'complete_raw_and_engineering_BREP_STEP_and_prerequisites_in_bound_saved_archives': True,
            'new_scientific_execution': False, 'exact_a11_push_fulfilled': False,
            'full_continuous_G2': False, 'all_blockers_closed': False, 'files': rows}
    (OUT / 'PLAN.json').write_text(json.dumps(plan, indent=2) + '\n')
    archive = OUT / ZIP_NAME
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for r in rows:
            if r['representation'].startswith('lossless'):
                info = zipfile.ZipInfo(r['zip_member'], date_time=(1980,1,1,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                z.writestr(info, selected[r['repository_path']].read_bytes(), compresslevel=6)
                assert archive.stat().st_size <= 67108864
                assert shutil.disk_usage(ROOT).free >= 134217728
        z.writestr('ORIGINAL_FILE_MANIFEST.json', json.dumps(plan, indent=2) + '\n')
    assert archive.stat().st_size <= 67108864
    with zipfile.ZipFile(archive) as z:
        wanted = {r['zip_member'] for r in rows if r['zip_member']} | {'ORIGINAL_FILE_MANIFEST.json'}
        assert set(z.namelist()) == wanted and len(z.infolist()) == len(wanted)
        for r in rows:
            if r['zip_member']:
                h = hashlib.sha256(); n = 0
                with z.open(r['zip_member']) as f:
                    while b := f.read(1048576):
                        h.update(b); n += len(b)
                assert n == r['bytes'] and h.hexdigest() == r['sha256']
        assert json.loads(z.read('ORIGINAL_FILE_MANIFEST.json')) == plan
    assert all(sha(selected[r['repository_path']]) == r['sha256'] and selected[r['repository_path']].stat().st_size == r['bytes'] for r in rows)
    data = archive.read_bytes()
    result = {'schema': 'razr-r7-native-finite-checkpoint-actual-v1', 'completed': True,
              'selected_original_count': len(rows), 'selected_original_bytes': total,
              'archived_original_count': sum(r['zip_member'] is not None for r in rows),
              'individually_readable_original_count': sum(r['zip_member'] is None for r in rows),
              'archive': {'path': str(archive), 'repository_path': PREFIX + 'native/' + ZIP_NAME,
                          'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                          'git_blob_sha': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()},
              'all_input_bytes_unchanged': True, 'full_archive_member_CRC_SHA_verified': True,
              'seconds': time.monotonic()-started,
              'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
              'ordinary_available_disk_after': shutil.disk_usage(ROOT).free,
              'scientific_qualification_reclassified': False, 'ref_mutated': False,
              'all_blockers_closed': False}
    (OUT / 'ACTUAL.json').write_text(json.dumps(result, indent=2) + '\n')
    signal.alarm(0)
    print(json.dumps(result))

if __name__ == '__main__':
    main()
