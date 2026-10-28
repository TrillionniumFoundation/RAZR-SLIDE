"""Bind recovered bytes to the unchanged R3 projection builder/entry/validator."""
import argparse
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path


def identity(path):
    b = Path(path).read_bytes()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


def identified(path):
    return {'path': str(path.resolve()), **identity(path)}


def require(condition, message):
    if not condition: raise ValueError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--r3-root', type=Path, required=True)
    p.add_argument('--runtime-root', type=Path, required=True)
    a = p.parse_args(); r3 = a.r3_root.resolve(); out = a.runtime_root.resolve()
    recovery_result = out / 'recovery-worker-attempt2/R4_RUNTIME_PAYLOAD_RECOVERY_EXECUTED.json'
    recovered_plan = out / 'recovery-worker-attempt2/R4_RECOVERED_PROJECTION_PLAN.json'
    controller = json.loads((out / 'recovery-attempt2/controller.json').read_text())
    recovery = json.loads(recovery_result.read_text())
    require(controller['completed'] and controller['resource_stop'] is None and recovery['completed'],
            'Payload recovery did not complete under original gates')
    require(identity(recovered_plan) == recovery['new_plan_identity'], 'Recovered plan differs')
    plan = json.loads(recovered_plan.read_text())
    old_plan_path = r3 / 'campaign-source-and-controls/R3_READONLY_PROJECTION_PLAN_V1.json'
    old_plan = json.loads(old_plan_path.read_text())
    require([{k:r[k] for k in ('relative','identity','owner_names')} for r in plan['payload_files']] ==
            [{k:r[k] for k in ('relative','identity','owner_names')} for r in old_plan['payload_files']],
            'Exact original payload meaning differs')
    require(plan['original_43_version_map'] == old_plan['original_43_version_map'] and
            plan['new_RECORD_payload_members_by_distribution'] == old_plan['new_RECORD_payload_members_by_distribution'],
            'Original metadata or per-owner inventory differs')
    # Relocate historical references only after verifying the complete original bytes.
    for key, relative in [('attempt1_result', 'actual-original-runtime-attempt1/worker/R3_RUNTIME_PAYLOAD_EXECUTED.json'),
                          ('attempt1_contract', 'campaign-source-and-controls/R3_RUNTIME_PAYLOAD_FROZEN_CONTRACT.json')]:
        source = r3 / relative
        require(identity(source) == {k:old_plan[key][k] for k in ('bytes','sha256')}, 'Historical reference differs')
        plan[key] = identified(source)
    old_failure = json.loads(Path(plan['attempt1_result']['path']).read_text())
    forbidden = {row['path'] for row in old_failure['scope_inventory']['issues']}
    source_contract = json.loads((out / 'R4_RUNTIME_RECOVERY_CONTRACT_V2.json').read_text())
    replacements = []
    for row in plan['payload_files']:
        if row['source'] not in forbidden:
            continue
        choices = [Path(source_contract['new_payload_root']) / owner / row['relative']
                   for owner in row['owner_names']]
        verified = [path for path in choices if path.is_file() and not path.is_symlink()
                    and identity(path) == row['identity']]
        require(bool(verified), 'No verified fresh wheel member for forbidden historical source path')
        previous = row['source']
        row['r4_previous_matching_but_nonadmitted_source'] = previous
        row['source'] = str(verified[0])
        row['current_recovery_basis'] = 'fresh_locked_wheel_member_excluding_original117_source_paths'
        replacements.append({'relative':row['relative'], 'previous':previous,
                             'source':row['source'], 'identity':row['identity']})
    require(not any(row['source'] in forbidden for row in plan['payload_files']),
            'Original117 source path remains in new projection')
    plan['original117_equal_byte_sources_replaced'] = replacements
    plan['recovery_plan_source_identity'] = plan['source_identity']
    plan['source_identity'] = identity(__file__)
    plan['activation_preparation_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    plan['unmodified_recovery_plan'] = identified(recovered_plan)
    plan['candidate_root'] = str(out / 'candidate-v4')
    plan['new_candidate_name'] = 'r4-recovered-payload-projection-v4'
    activation = out / 'R4_ACTIVATION_PLAN_V3.json'
    activation.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    old_contract_path = r3 / 'campaign-source-and-controls/R3_PROJECTION_FROZEN_CONTRACT_V2.json'
    old_contract = json.loads(old_contract_path.read_text())
    rec_contract = json.loads((out / 'R4_RUNTIME_RECOVERY_CONTRACT_V2.json').read_text())
    source_root = r3 / 'campaign-source-and-controls'
    builder = source_root / 'build_runtime_projection_r3.py'
    entry = source_root / 'readonly_projection_entry_r3.py'
    validator = source_root / 'verify_runtime_projection_r3_v2.py'
    supervisor = source_root / 'supervise_runtime_payloads_r3.py'
    for source, key in [(builder,'builder_identity'), (entry,'entry_identity'), (validator,'validator_identity')]:
        require(identity(source) == old_contract[key], 'Frozen projection source differs')
    require(identity(supervisor)['sha256'] == old_contract['supervisor_sha256'], 'Frozen supervisor differs')
    contract = {'schema':'razr-r4-recovered-projection-frozen-contract-v3',
        'frozen_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'candidate_name':plan['new_candidate_name'], 'plan':identified(activation),
        'supervisor_sha256':identity(supervisor)['sha256'],
        'resource_limits':copy.deepcopy(old_contract['resource_limits']),
        'original_six_resource_limits_unchanged':True,
        'allowed_reference_prefixes':[rec_contract['existing_site'], rec_contract['new_payload_root'], str(Path(rec_contract['existing_prefix']) / 'share/man/man1')],
        'builder_source':str(builder), 'builder_identity':identity(builder),
        'entry_source':str(entry), 'entry_identity':identity(entry),
        'validator_source':str(validator), 'validator_identity':identity(validator),
        'actual_import_probes':old_contract['actual_import_probes'],
        'actual_negative_import_probe':old_contract['actual_negative_import_probe'],
        'frozen_R3_projection_contract':identified(old_contract_path),
        'actual_R4_payload_recovery':identified(recovery_result),
        'capacity_plan':{'new_filesystem_bytes_upper_bound':134217728,
            'builder_time_estimate_seconds':30, 'validation_time_estimate_seconds':60,
            'basis':'Same8112 references/43 RECORDs and unchanged builder/validator; prior actual4.26s/8.28s; current source paths and imports are independently checked again.',
            'downloads_during_build_and_validation':0, 'heavy_payload_copies_during_build_and_validation':0},
        'scope':'New R4 controlled runtime with original43 payload identities. Recovered historical records retain original failure/success scopes. Runtime code labels remain R3 because their original bytes are reused unchanged.',
        'OS_enforced_immutable_runtime_claimed':False, 'historical_execution_requalified':False,
        'compiled_kernel_formal_binding_verified':False, 'physical_qualification':False}
    contract['superseded_failed_build'] = identified(out / 'build-worker-attempt1/R3_PROJECTION_BUILD_EXECUTED.json')
    contract['superseded_rejected_validation'] = identified(out / 'validation-worker-attempt1/R3_PROJECTION_VALIDATION_EXECUTED.json')
    contract['v2_change_scope'] = 'Declare the exact verified current man1 source prefix for the original fonttools ttx.1 payload, use a distinct new candidate root, and retain failed8111-link build plus same-contract validation refusal. Original builder/entry/validator and payload hashes are unchanged.'
    contract['v3_change_scope'] = 'Preserve original117 exact-source-path exclusion:53 equal-byte global aliases are replaced with already verified fresh locked-wheel payloads. No additional download, original payload identity changes, or verifier gate changes.'
    contract['original117_source_replacement_count'] = len(replacements)
    contract['superseded_original117_rejection'] = identified(out / 'validation-worker-attempt2/R3_PROJECTION_VALIDATION_EXECUTED.json')
    target = out / 'R4_PROJECTION_CONTRACT_V3.json'
    target.write_text(json.dumps(contract, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'plan':identified(activation),'contract':identified(target),
                      'original_8112_payloads_and43_versions_unchanged':True,
                      'historical_source_paths_relocated_after_identity_check':True}))


if __name__ == '__main__': main()
