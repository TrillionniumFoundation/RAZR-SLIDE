"""Append a storage-state clarification without changing the scientific scope."""
from pathlib import Path
import datetime as dt
import hashlib
import json

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
V1 = ROOT / 'R7_ACTUAL_NATIVE80_AND_TWO_FINITE_POSES_SCOPE_V1.json'
OBSERVATION = BASE / 'r7-audit/full-factory-review/R7_NEAR_ENGINEERING_MIGRATION_CURRENT_STATE_READBACK_V2.json'
FAILED_READ = BASE / 'r7-audit/full-factory-review/R7_NEAR_MIGRATION_CURRENT_READ_ATTEMPT1_ACTUAL_FAILURE.json'
MIGRATION = BASE / 'r7-publication/R7_NEAR_ENGINEERING_ARCHIVE_MIGRATION_V1.json'
OUT = ROOT / 'R7_NATIVE_SCOPE_STORAGE_OBSERVATION_ADDENDUM_V2.json'


def identity(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def bound(path):
    return {'path': str(path.relative_to(BASE)), **identity(path)}


def main():
    if OUT.exists():
        raise ValueError('Append-only fresh addendum required')
    paths = (V1, OBSERVATION, FAILED_READ, MIGRATION, Path(__file__).resolve())
    before = {str(p.relative_to(BASE)): identity(p) for p in paths}
    if identity(V1) != {'bytes': 21627, 'sha256': '8c88d441b9e3f311b95bac2bec17c543f5e1be376dc9030d2427f8442b9c8ae9'}:
        raise ValueError('Original V1 scope differs')
    if identity(OBSERVATION)['sha256'] != '0d42997dd6138dfce2d733bb84e2536e6027efd1f92d2068ed892c280e083282':
        raise ValueError('Bound independent V2 observation differs')
    observed = json.loads(OBSERVATION.read_text())
    if identity(FAILED_READ) != observed['prior_actual_failed_read'] or identity(MIGRATION) != observed['migration_receipt']:
        raise ValueError('Original observation bindings differ')
    record = {
        'schema': 'razr-r7-native-scope-storage-observation-append-only-addendum-v2',
        'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'original_V1_scope': bound(V1),
        'independent_storage_observation_V2': bound(OBSERVATION),
        'prior_actual_failed_current_read': bound(FAILED_READ),
        'historical_migration_receipt': bound(MIGRATION),
        'addendum_source': bound(Path(__file__).resolve()),
        'observation_time_utc': observed['recorded_utc'],
        'fresh_directory_census_performed_by_this_addendum': False,
        'temporal_scope': 'The following values describe the saved independent observation at observation_time_utc; this addendum does not assert a later filesystem state.',
        'observed_engineering_member_count': observed['current_member_count'],
        'observed_engineering_bytes': observed['current_bytes'],
        'observed_engineering_expansion_complete': observed['current_engineering_expansion_complete'],
        'observed_members_equal_historical_two_manifest_end_state': observed['current_members_match_reported_two_member_migration_end_state'],
        'historical_removed_but_current_observed_count': observed['historical_removed_but_current_observed_count'],
        'all_observed_member_hashes_match_original_seal': observed['all_current_observed_member_hashes_match_original_seal'],
        'observed_archive_identity': observed['actual_local_archive'],
        'observed_whole_archive_hash_matches_prior_complete_CRC_SHA_readback': observed['entire_archive_bytes_still_match_previously_completed_full_member_CRC_SHA_readback'],
        'historical_end_state_to_later_membership_correspondence_unresolved': observed['historical_migration_end_state_to_current_membership_correspondence_unresolved'],
        'physical_reappearance_or_platform_cause_proved': observed['physical_reappearance_or_platform_cause_proved'],
        'corrected_prior_chat_statement': 'The earlier statement that the current near engineering directory contained only two manifests cannot be retained as a current-state claim. The historical migration receipt recorded that end state; the later saved independent observation contains 2359 files / 210541721 bytes, including 2357 names from its removed list.',
        'scientific_scope_interpretation': 'V1 reports sealed execution and independent scientific readback. Its historical full engineering counts are not a claim that the presently expanded engineering directory is complete.',
        'original_V1_scope_modified': False,
        'historical_scientific_results_reclassified': False,
        'original_scientific_reports_or_seals_modified': False,
        'new_CAD_or_scientific_execution': False,
        'deletion_restoration_or_rearchive_performed': False,
        'full_continuous_G2': False,
        'physical_qualification': False,
        'all_blockers_closed': False,
        'bound_input_identities': before,
    }
    after = {str(p.relative_to(BASE)): identity(p) for p in paths}
    if before != after:
        raise ValueError('Addendum input bytes changed')
    record['all_bound_input_bytes_unchanged'] = True
    with OUT.open('x') as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'addendum': bound(OUT), 'V1_unchanged': identity(V1) == before[str(V1.relative_to(BASE))]}))


if __name__ == '__main__':
    main()
