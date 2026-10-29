"""Derive a compact scope from already sealed and independently read evidence.

This performs no CAD or new scientific acceptance test.  It reads the final
independent audit records and binds their original reports, keeping every scope
restriction and the external cleanup discrepancy.  The full audit inventories
remain the authority for the complete raw and engineering byte sets.
"""
from pathlib import Path
import datetime as dt
import hashlib
import json
import stat


ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
AUDIT = BASE / 'r7-audit'
OUTPUT = ROOT / 'R7_ACTUAL_NATIVE80_AND_TWO_FINITE_POSES_SCOPE_V1.json'


def identity(path):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Scope input must be a regular file: ' + str(path))
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(data)
    return {'bytes': info.st_size, 'sha256': digest.hexdigest()}


def bind(path):
    path = Path(path)
    return {'path': str(path.relative_to(BASE)), **identity(path)}


def read(path):
    return json.loads(Path(path).read_text())


def native80_scope():
    original_path = ROOT / 'R7_NATIVE80_ACTUAL_SCOPE_V1.json'
    scope = read(original_path)
    for name in ('qualification', 'producer', 'independent_reader'):
        original = scope[name]['report']
        source = Path(original['path'])
        if identity(source) != {k: original[k] for k in ('bytes', 'sha256')}:
            raise ValueError('Native80 original report differs')
        scope[name]['report'] = bind(source)
    external = scope['later_external_scratch_state_unresolved']
    source = Path(external['path'])
    if identity(source) != {k: external[k] for k in ('bytes', 'sha256')}:
        raise ValueError('Original scratch reobservation differs')
    scope['later_external_scratch_state_unresolved'] = bind(source)
    scope['original_scope_record'] = bind(original_path)
    return scope


def pose_scope(pose):
    case = ROOT / ('full-' + pose + '-attempt1')
    seal_path = ROOT / ('R7_' + pose.upper() + '_COMPLETE_FINITE_POSE_FINAL_SEAL_V1.json')
    audit_path = AUDIT / 'full-factory-review' / ('R7_' + pose.upper() + '_ACTUAL_FULL_FACTORY_INDEPENDENT_EVIDENCE_READBACK.json')
    audit = read(audit_path)
    seal = read(seal_path)
    if not audit['evidence_readback_pass'] or audit['final_seal'] != identity(seal_path):
        raise ValueError('Final independent audit does not bind this seal')
    if not seal['completed'] or not seal['complete_full_pair_execution']:
        raise ValueError('Complete finite execution is absent')
    workers = audit['original_factory_and_independent_reader']
    reports = {}
    for mode in ('factory', 'readback'):
        report_path = case / mode / 'worker/report.json'
        observed = identity(report_path)
        if observed != workers[mode]['raw_report'] or observed != seal['raw_members'][mode + '/worker/report.json']:
            raise ValueError('Original finite report differs from audit/seal')
        reports[mode] = read(report_path)
    phases = {}
    for phase in ('factory', 'readback', 'verify-complete', 'export-engineering'):
        actual_path = case / (phase + '-command-actual.json')
        if identity(actual_path) != seal['raw_members'][actual_path.name]:
            raise ValueError('Original phase receipt differs from seal')
        actual = read(actual_path)
        if not actual['completed']:
            raise ValueError('Original phase did not complete')
        phases[phase] = {'actual_receipt': bind(actual_path), 'seconds': actual['seconds'],
                         'exit_code': actual['exit_code'], 'completed': actual['completed']}
    factory, reader = reports['factory'], reports['readback']
    return {
        'pose': pose,
        'slide_mm': factory['pose_input']['slide'],
        'actual_q_by_side_mm': factory['actual_q_by_side_mm'],
        'candidate': audit['candidate'],
        'functional_source_commit': audit['functional_source_commit'],
        'final_seal': bind(seal_path),
        'independent_full_evidence_readback': bind(audit_path),
        'raw_member_count': audit['actual_raw_member_count'],
        'raw_bytes': audit['actual_raw_bytes'],
        'engineering_member_count': audit['actual_engineering_member_count'],
        'engineering_bytes': audit['actual_engineering_bytes'],
        'factory_and_reader': workers,
        'method_count_interpretation': 'All-pair records include both native_common and positive_axis_gap. The pair count is not a count of direct Common calls. Explicit two-side panel/KEY direct Common records are listed separately inside each worker.',
        'complete_full_pair_execution': audit['original_complete_pair_execution'],
        'finite_state_clear': audit['finite_state_clear'],
        'maximum_factory_reader_all_pair_volume_difference_mm3': audit['maximum_factory_reader_all_pair_volume_difference_mm3'],
        'independent_STEP_body_readback_count': len(reader['body_readbacks']),
        'independent_early_gate_count': len(reader['independent_early_gate_records']),
        'all_original_STEP_signature_criteria_passed': audit['all_154_complete_STEP_readbacks_passed_original_signature_criteria'],
        'same_kernel_separate_process_reader': audit['same_kernel_separate_process_reader'],
        'phases': phases,
        'remaining_unproved_domains': audit['remaining_unproved_domains'],
        'full_continuous_G2': audit['full_continuous_G2'],
        'physical_qualification': audit['physical_qualification'],
        'manufacturing_go': audit['manufacturing_go'],
    }


def main():
    if OUTPUT.exists():
        raise ValueError('Fresh immutable consolidated scope output required')
    qa_path = AUDIT / 'native-stage-v4-review/R7_ACTUAL_RUNTIME_QUALIFICATION_INDEPENDENT_FULL_READBACK_V2.json'
    na_path = AUDIT / 'native-stage-v4-review/R7_NATIVE80_ACTUAL_PRODUCER_READER_INDEPENDENT_EVIDENCE_READBACK.json'
    qa, na = read(qa_path), read(na_path)
    if not qa['runtime_payload_readback_pass'] or not na['evidence_readback_pass']:
        raise ValueError('Actual finite runtime/native80 review is incomplete')
    poses = {pose: pose_scope(pose) for pose in ('near', 'far')}
    record = {
        'schema': 'RAZR_R7_ACTUAL_NATIVE80_AND_TWO_FINITE_POSES_SCOPE_V1',
        'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'derived_scope_only_original_reports_unchanged': True,
        'new_CAD_arithmetic_performed_by_this_consolidation': False,
        'scope_writer': bind(Path(__file__)),
        'native80': native80_scope(),
        'runtime_independent_review': {
            'report': bind(qa_path),
            'runtime_payload_readback_pass': qa['runtime_payload_readback_pass'],
            'review_pass_with_no_unresolved_discrepancies': qa['review_pass_with_no_unresolved_discrepancies'],
            'complete_actual_venv_member_count': qa['independent_complete_actual_venv_member_count'],
            'locked_payload_count': qa['independent_locked_payload_count'],
            'locked_payload_bytes': qa['independent_locked_payload_bytes'],
            'external_scratch_cleanup_absence_verified': qa['current_external_scratch_cleanup_absence_verified'],
            'historical_cleanup_to_current_state_correspondence_proved': qa['historical_cleanup_to_current_state_correspondence_proved'],
            'cleanup_discrepancy_cause': qa['cleanup_discrepancy_cause'],
        },
        'native80_independent_review': {
            'report': bind(na_path),
            'evidence_readback_pass': na['evidence_readback_pass'],
            'saved_BREP_readbacks': na['independent_native_saved_BREP_readback_count'],
            'comparison_count': na['reader_comparison_count'],
            'native_area_bit_inequality_count': na['native_area_bit_inequality_count'],
            'maximum_native_area_difference_mm2': na['maximum_observed_native_area_difference_mm2'],
            'all_native_areas_binary64_equal': na['all_native_areas_binary64_equal'],
            'new_physical_area_threshold_introduced': na['new_physical_area_threshold_introduced'],
            'aggregate_scientific_bytes': na['aggregate_scientific_bytes'],
        },
        'finite_poses': poses,
        'finite_pose_count': len(poses),
        'original_source_and_scientific_criteria_preserved': True,
        'new_runtime_revision_changes_candidate_geometry': False,
        'historical_F1_and_V5_failures_reclassified': False,
        'whole_current_exact_native_trim_model_membership_verified': False,
        'full_continuous_G2': False,
        'physical_allowed_domain_proved': False,
        'structural_strength_qualified': False,
        'OEM_electrical_identity_qualified': False,
        'G3_G4_G5_qualified': False,
        'all_blockers_closed': False,
        'capacity_basis_for_this_read_only_derivation': {
            'algorithm': 'Read small sealed reports and audit records; no re-import, CAD, solver or geometry computation',
            'maximum_output_bytes': 131072,
        },
    }
    data = (json.dumps(record, indent=2, allow_nan=False) + '\n').encode()
    if len(data) > 131072:
        raise ValueError('Consolidated scope output cap exceeded')
    with OUTPUT.open('xb') as stream:
        stream.write(data)
    print(json.dumps({'scope': bind(OUTPUT), 'all_blockers_closed': False}))


if __name__ == '__main__':
    main()
