"""Frozen engineering-only F1a prerequisite; raw runtime reports are unavailable."""
from __future__ import annotations
import hashlib
import itertools
import json
from pathlib import Path

S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
F1A_RUN = 40273568199
F1A_COMMIT = '935d6adb5ceeb2995971cb32ba2a5f7694114237'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def prerequisite(base, binding_path, pose):
    """Verify a byte-frozen public engineering export and both complete reports.

    No raw report is fetched or synthesized. original.sha256 identifies the
    original ephemeral report that the published projection explicitly cites.
    """
    base = Path(base).resolve(); binding_path = Path(binding_path).resolve()
    binding = json.loads(binding_path.read_text())
    require(binding['run_id'] == F1A_RUN and binding['head_sha'] == F1A_COMMIT,
            'frozen F1a run/source identity required')
    entry = binding['poses'][pose]
    require(entry['artifact_name'] == f'S4-F1-{pose}-{F1A_RUN}-1-engineering',
            'frozen pose, run and attempt artifact name required')
    manifest_path = base/'ENGINEERING_MANIFEST.json'
    require(sha(manifest_path) == entry['engineering_manifest_sha256'],
            'frozen complete engineering manifest hash differs')
    manifest = json.loads(manifest_path.read_text())
    for rel, ref in manifest['members'].items():
        path = (base/rel).resolve()
        require(path.is_relative_to(base) and path.is_file() and not path.is_symlink(),
                'unsafe or absent engineering member')
        require(path.stat().st_size == ref['bytes'] and sha(path) == ref['sha256'],
                'engineering member byte identity differs: '+rel)
    results = {}
    for kind in ('factory', 'readback'):
        rp = base/kind/'worker/report.engineering.json'
        projection = json.loads(rp.read_text())
        require(projection.get('derived_projection_not_raw_original') is True,
                'explicit engineering projection required')
        original_hash = projection.get('original', {}).get('sha256')
        require(isinstance(original_hash, str) and len(original_hash) == 64,
                'projection original report hash required')
        r = projection['engineering_record']
        require(r.get('functional_source_commit') == S4 and r.get('pose') == pose,
                'original S4 pose identity differs')
        require(r.get('execution_completed') is True
                and r.get('all_unordered_pairs_present_once') is True
                and len(r.get('pairs', [])) == 11781
                and len(r.get('participant_names', [])) == 154
                and not r.get('evaluation_failures')
                and not r.get('mismatches_to_factory'),
                'complete original all-pairs result required')
        names=r['participant_names']
        actual=[(x['a'],x['b']) for x in r['pairs']]
        require(len(set(names))==154 and actual==list(itertools.combinations(sorted(names),2)),
                'original pair roles must exactly cover every unordered body pair once')
        ident = r.get('source_identity_projection', {})
        require(ident.get('source_commit_before') == ident.get('source_commit_after') == S4
                and ident.get('worktree_clean_before') is True
                and ident.get('source_bytes_and_locked_environment_unchanged') is True
                and ident.get('locked_environment_before_passed') is True
                and ident.get('locked_environment_after_passed') is True
                and ident.get('checked_package_count_before') == 43
                and ident.get('checked_package_count_after') == 43
                and not ident.get('changed_or_late_sources'),
                'complete unchanged source and 43-package prerequisite required')
        journal = base/kind/'worker/pairs.jsonl'
        rows = [json.loads(x) for x in journal.read_text().splitlines()]
        require(len(rows) == 23562 and
                [(x['a'],x['b']) for x in rows if x['event']=='selected']==actual and
                [x['row'] for x in rows if x['event'] == 'completed'] == r['pairs'],
                'original pair journal does not agree with complete report')
        results[kind] = projection
    factory = results['factory']['engineering_record']
    reader = results['readback']['engineering_record']
    require(factory.get('actual_complete_factory_called') is True
            and factory.get('fixed_pair_certificate_reused') is False
            and factory.get('geometry_repair_applied') is False,'original unmodified full factory must have executed')
    require(reader.get('factory_report_sha256') == results['factory']['original']['sha256'],
            'original reader report was bound to another producer')
    require(reader.get('native_STEP_readback_executed') is True
            and len(reader.get('body_readbacks', {})) == 154
            and all(x['passed'] for x in reader['body_readbacks'].values())
            and len(reader.get('L1_whole_endpoint_material_comparisons', [])) == 8
            and all(x['passed'] for x in reader['L1_whole_endpoint_material_comparisons']),
            'all original STEP bodies and eight L1 material-frame comparisons required')
    require(reader.get('L1_original_input_members_verified')==104
            and reader.get('L1_binding_sha256')=='cc4d09cf54d7b92cadd626051b11ebe7451f369bd0811f6c238717133f4178a2',
            'all 104 original L1 byte identities required')
    for side in 'LR':
        require(factory['panel_KEY_direct_Common'][side]['common_mm3'] > 1e-7,
                'original rejected witness must be retained')
    return results, {
        'run_id': F1A_RUN, 'head_sha': F1A_COMMIT, 'pose': pose,
        'artifact_name': entry['artifact_name'], 'artifact_id': entry['artifact_id'],
        'engineering_manifest_sha256': sha(manifest_path),
        'binding_sha256': sha(binding_path),
        'verified_engineering_member_count': len(manifest['members']),
        'original_raw_report_downloaded_or_reconstructed': False,
        'original_raw_runtime_durable_preservation_claimed': False,
        'factory_original_report_sha256': results['factory']['original']['sha256'],
        'reader_original_report_sha256': results['readback']['original']['sha256'],
        'factory_projection_sha256': sha(base/'factory/worker/report.engineering.json'),
        'reader_projection_sha256': sha(base/'readback/worker/report.engineering.json'),
        'source_and_environment_checks_observed_from_marked_projection': True,
        'current_S4_source_and_environment_require_independent_recheck': True,
    }
