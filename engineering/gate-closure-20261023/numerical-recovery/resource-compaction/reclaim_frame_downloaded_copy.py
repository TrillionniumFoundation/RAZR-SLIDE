"""Authorized local-only unlink of the already saved and verified frame archive."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import stat

BASE = Path('/workspace/scratch/95cd2986fdf2')
EVIDENCE = BASE / 'input_recovery/resource_compaction'
ARCHIVE = BASE / 'frame-compute-archive-20261023/frame-full-L2-rebuild-20261023.tar.xz'
SIZE = 243162164
SHA = '1c41ae773f93e7259293e3e09db78099f4dce574c05cdc2c5d46b093ad36d90b'
LIBRARY_ID = 'libfile_230ac19968c0819185599859f6a89f8f'
FILE_ID = 'file_00000000cd74820db92f9d091f5692e2'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def data(path):
    return json.loads(Path(path).read_text())


def results(value):
    while isinstance(value, dict) and 'results' not in value:
        value = value['structuredContent']
    return value['results']


def snapshot():
    s = os.statvfs(BASE)
    return {'f_bavail': s.f_bavail, 'f_frsize': s.f_frsize,
            'f_bavail_bytes': s.f_bavail * s.f_frsize}


def signature(s):
    return [s.st_dev, s.st_ino, s.st_size, s.st_nlink, s.st_mtime_ns, s.st_ctime_ns]


def exclusive_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def main():
    prior_path = EVIDENCE / 'frame-downloaded-archive-readback.json'
    prior = data(prior_path)
    require(prior['archive_sha256'] == SHA and prior['archive_bytes'] == SIZE
            and prior['all_original_members_verified'] is True
            and prior['original_member_count'] == 22 and prior['total_archive_file_members'] == 23,
            'prior complete exact member readback is missing')
    current_paths = [EVIDENCE / 'frame-local-archive-current-search.json',
                     EVIDENCE / 'frame-local-archive-current-read-metadata.json']
    current = []
    for path in current_paths:
        selected = [r for r in results(data(path)) if r.get('library_file_id') == LIBRARY_ID]
        require(len(selected) == 1 and selected[0]['file_id'] == FILE_ID
                and selected[0]['size_bytes'] == SIZE, 'current persistent file metadata identity differs')
        current.append(selected[0])
    old = data(EVIDENCE / 'frame-raw-archive-preflight.json')['persisted_file_receipt']
    require(old['status'] == 'succeeded' and old['library_file_id'] == LIBRARY_ID
            and old['file_id'] == FILE_ID and old['bytes'] == SIZE and old['sha256'] == SHA,
            'original successful persistent save identity differs')
    require(not ARCHIVE.is_symlink(), 'archive cannot be a symbolic link')
    before = ARCHIVE.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size == SIZE and before.st_nlink == 1,
            'one exact regular local archive link required')
    require(sha(ARCHIVE) == SHA, 'local archive no longer matches the fully verified saved bytes')
    after_hash = ARCHIVE.stat()
    require(signature(before) == signature(after_hash), 'file identity changed while hashing')
    previous_identity = data(EVIDENCE / 'frame-local-archive-readonly-audit.json')
    require((after_hash.st_dev, after_hash.st_ino) ==
            (previous_identity['device'], previous_identity['inode']), 'approved archive inode changed')
    process_evidence = data(EVIDENCE / 'frame-local-archive-process-visibility.json')
    require(process_evidence['open_refs'] == [] and process_evidence['numeric_workers'] == [],
            'an observed frame/archive numeric reader prevents this local reclamation')
    numerical_now = []
    for process in Path('/proc').iterdir():
        if not process.name.isdecimal():
            continue
        try:
            argv = (process / 'cmdline').read_bytes().decode(errors='replace').split('\0')
        except (OSError, ProcessLookupError):
            continue
        scripts = [a for a in argv if a.endswith('.py')]
        if any('/input_recovery/fe_preflight/' in a or '/tmp/razr-fe-20261023/' in a for a in scripts):
            numerical_now.append({'pid': int(process.name), 'scripts': scripts})
    require(not numerical_now, 'an active numerical script appeared before unlink')
    restore_script = EVIDENCE / 'restore_frame_raw.py'
    record = {
        'schema': 'razr-frame-saved-local-downloaded-copy-reclamation-v1',
        'utc_before_unlink': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'only_authorized_unlink_path': str(ARCHIVE), 'archive_bytes': SIZE,
        'archive_sha256_before_unlink': SHA, 'allocated_bytes_before': before.st_blocks * 512,
        'exact_stat_signature_before_unlink': signature(after_hash),
        'original_successful_save_receipt': old,
        'current_persistent_metadata': [{k: r.get(k) for k in ('library_file_id', 'file_id', 'name',
            'size_bytes', 'version_id', 'created_at', 'modified_at')} for r in current],
        'current_version_id_is_null_not_a_fresh_version_zero_assertion': all(r.get('version_id') is None for r in current),
        'historical_saved_version_number': old['current_version_number'],
        'remote_payload_downloaded_for_this_reclamation': False,
        'fresh_current_remote_metadata_is_not_new_remote_byte_verification': True,
        'prior_full_download_readback_receipt': str(prior_path), 'prior_readback_receipt_sha256': sha(prior_path),
        'prior_original_members_verified': 22, 'prior_additional_manifest_verified': 1,
        'local_full_archive_SHA_binds_the_same_previously_verified_members': True,
        'process_visibility_receipt': str(EVIDENCE / 'frame-local-archive-process-visibility.json'),
        'process_visibility_receipt_sha256': sha(EVIDENCE / 'frame-local-archive-process-visibility.json'),
        'observed_FD_or_mapping_references': [], 'observed_numeric_scripts_immediately_before_unlink': numerical_now,
        'global_FD_and_mapping_absence_not_claimed': True,
        'root_and_owning_agents_confirm_no_frame_reader_or_near_term_frame_run': True,
        'authorization': 'Root explicitly authorized reversible reclamation of this one local downloaded copy after same-SHA/stat recheck.',
        'persistent_file_deleted_or_changed': False, 'panel_or_H_or_inputs_modified': False,
        'restore_route': {
            'fresh_library_search': {'search_query': [{'q': '"frame-full-L2-rebuild-20261023.tar.xz"', 'search_title_only': True}], 'top_k': 5},
            'required_library_file_id': LIBRARY_ID, 'required_file_id': FILE_ID,
            'helper_source': 'skill://plugin_connector_1p_1b8ff8edfc1481918b252c8277e23125/library/scripts/library_download.py',
            'transfer_method': 'Use the current Library skill download helper and companions unchanged, with the complete fresh search result and the exact matching selection; no raw URL transfer.',
            'destination_relative_to_workspace': 'frame-compute-archive-20261023',
            'required_result_path': str(ARCHIVE), 'required_archive_bytes': SIZE, 'required_archive_sha256': SHA,
            'prior_member_manifest': str(EVIDENCE / 'frame-original-artifact-manifest.json'),
            'prior_member_manifest_sha256': sha(EVIDENCE / 'frame-original-artifact-manifest.json'),
            'verify_after_future_download': 'Stream-check the full archive SHA and size before accepting it; exact SHA binds the preserved 22-member-plus-manifest byte inventory. Preserve a new retrieval receipt without overwriting the historical readback.',
            'optional_exact_raw_K_restore_argv': [str(BASE / 'RAZR-SLIDE/.venv/bin/python'), '-B', str(restore_script), '--restore', '--archive', str(ARCHIVE)],
            'raw_restore_script_sha256': sha(restore_script),
            'raw_K_sha256': 'e077f8d0176c041041b984b5dbb016e140219b34223d235ac739978b1dddd95d',
            'raw_restore_additional_required_available_disk_bytes': 394530277 + 500 * 2**20,
            'no_solver_is_started_by_restoration': True,
        },
        'reclamation_source_sha256': sha(__file__), 'unlink_completed': False,
    }
    record['metadata_evidence_sha256'] = {str(p): sha(p) for p in current_paths}
    exclusive_json(EVIDENCE / 'frame-local-downloaded-archive-unlink-preflight.json', record)
    require(signature(ARCHIVE.stat()) == signature(after_hash), 'archive changed before authorized unlink')
    record['available_disk_immediately_before_unlink'] = snapshot()
    ARCHIVE.unlink()
    record['available_disk_immediately_after_unlink'] = snapshot()
    record['f_bavail_delta_bytes'] = (record['available_disk_immediately_after_unlink']['f_bavail_bytes']
                                     - record['available_disk_immediately_before_unlink']['f_bavail_bytes'])
    record['unlink_completed'] = True
    record['archive_raw_path_materialized_after'] = ARCHIVE.exists()
    record['frame_raw_K_materialized_after'] = Path('/tmp/razr-fe-20261023/volume-rebuild/frame/level-2/K.npz').exists()
    record['frame_exact_numeric_input_requires_future_archive_retrieval'] = True
    record['utc_after_unlink'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record['no_native_or_numerical_worker_started'] = True
    receipt = EVIDENCE / 'frame-local-downloaded-archive-reclaimed.json'
    exclusive_json(receipt, record)
    print(json.dumps({'receipt': str(receipt), 'receipt_sha256': sha(receipt),
        'unlinked': str(ARCHIVE), 'before_available_bytes': record['available_disk_immediately_before_unlink']['f_bavail_bytes'],
        'after_available_bytes': record['available_disk_immediately_after_unlink']['f_bavail_bytes'],
        'delta_bytes': record['f_bavail_delta_bytes'], 'raw_frame_archive_requires_retrieval': True}))


if __name__ == '__main__':
    main()
