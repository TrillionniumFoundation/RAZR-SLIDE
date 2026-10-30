"""Independent synthetic original-donor admission controls, never hardware evidence.

The production _common/Evidence/prerequisite/_finish implementations are loaded
unchanged from --source.  Two external-world adapters are isolated explicitly:
verify_binding returns a declared synthetic complete binding, and product_inputs
reads a SHA-bound synthetic observed-donor file.  The actual JSON evidence reader,
all as-built comparisons, and all evidence SHA rechecks remain production code.
No production source, repository metadata, or physical input record is modified.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    raw = (json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    path.write_bytes(raw)
    return {'path': path.name, 'sha256': digest(raw)}


def identity(path):
    raw = path.read_bytes()
    return {'path': str(path.resolve()), 'bytes': len(raw), 'sha256': digest(raw)}


def semantic(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def load_source(path):
    spec = importlib.util.spec_from_file_location('donor_probe_exact_evaluator', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def probe(q, kind, folder, gate="G4", location="top"):
    folder.mkdir()
    label = b'SYNTHETIC DONOR BINDING TEST ONLY. No actual device or acquired observation.\n'
    (folder / 'synthetic-provenance.txt').write_bytes(label)
    source = {'path': 'synthetic-provenance.txt', 'sha256': digest(label)}
    specimen = 'SYNTHETIC-ASSEMBLY-1'
    observed_donor = 'SYNTHETIC-DONOR-B'
    binding = {'git_commit': '0' * 40, 'candidate_id': 'SYNTHETIC-CANDIDATE',
               'files_sha256': {}, 'native_payload_sha256': {}}
    roles = {role: {'identity': 'SYNTHETIC-' + role, 'source': source}
             for role in ('parts', 'material_lots', 'process', 'firmware', 'assembly')}
    original = {'schema': 'synthetic-as-built-record', 'specimen_id': specimen,
                'is_template': False, 'execution_kind': 'synthetic_fixture',
                'design_binding': binding, 'qualification_assembly': copy.deepcopy(roles),
                'synthetic_fixture': True}
    if kind == 'contradictory_original_donor':
        original['same_donor_specimen_id'] = 'SYNTHETIC-DONOR-A'
    elif kind == 'matching_original_donor':
        original['same_donor_specimen_id'] = observed_donor
    elif kind != 'missing_original_donor':
        raise ValueError(kind)
    if location in ('nested', 'top_null_nested', 'both'):
        donor = original.get('same_donor_specimen_id')
        if donor is not None:
            original['qualification_assembly']['same_donor_specimen_id'] = donor
        if location == 'nested':
            original.pop('same_donor_specimen_id', None)
        elif location == 'top_null_nested':
            original['same_donor_specimen_id'] = None
    original_ref = write_json(folder / 'original-as-built.json', original)
    observed = {'schema': 'synthetic-product-inputs-observation',
                'unknown_donor_identity_fields': [], 'physical_donor_identity_bound': True,
                'observed_donor_specimen_id': observed_donor,
                'missing_physical_interfaces': [], 'physically_bound_interfaces': [],
                'synthetic_fixture': True,
                'scope': 'Test adapter return only; does not prove physical interface completeness.'}
    observed_ref = write_json(folder / 'synthetic-observed-donor.json', observed)
    prior = {'schema': 'razr-unpowered-motion-qualification-decision-v1',
             'current_EP5_candidate_bound': True, 'execution_kind': 'physical',
             'specimen_id': specimen, 'design_binding': binding, 'status': 'pass',
             'sampled_criteria_status': 'pass',
             'criteria': [{'metric': 'synthetic_only', 'status': 'pass'}],
             'acquisition_started_at_utc': '2026-10-02T10:00:00Z',
             'acquisition_ended_at_utc': '2026-10-02T12:00:00Z',
             'qualification_reviewed_at_utc': '2026-10-02T13:00:00Z',
             'as_built_specimen_record': original_ref,
             'synthetic_fixture': True,
             'scope': 'Deliberately fabricated physical-schema parser fixture; no measured pass.'}
    prior_ref = write_json(folder / 'synthetic-g3-schema-record.json', prior)
    plan = {'schema': 'razr-product-qualification-plan-v1', 'gate': gate,
            'is_template': False, 'design_binding': binding, 'specimen_ids': [specimen],
            'same_donor_specimen_id': observed_donor,
            'declared_at_utc': '2026-10-02T14:00:00Z', 'approved_by': 'SYNTHETIC-REVIEWER',
            'approval_evidence': [source], 'prerequisites': {'G3': {specimen: prior_ref}}}
    if gate == 'G5':
        g4 = {'schema': 'razr-product-qualification-decision-v1', 'gate': 'G4',
              'execution_kind': 'physical', 'specimen_ids': [specimen],
              'design_binding': binding, 'status': 'pass', 'sampled_criteria_status': 'pass',
              'criteria': [], 'coverage': [{'complete': True}], 'observations': 1,
              'execution_binding': {'physical_commit_bytes_verified': True},
              'acquisition_started_at_utc': '2026-10-02T13:30:00Z',
              'acquisition_ended_at_utc': '2026-10-02T13:40:00Z',
              'qualification_reviewed_at_utc': '2026-10-02T13:50:00Z',
              'as_built_specimen_records': {specimen: original_ref},
              'synthetic_fixture': True,
              'scope': 'Fabricated physical-schema parser fixture only; not a measured G4 pass.'}
        plan['prerequisites']['G4'] = {specimen: write_json(folder / 'synthetic-g4-schema-record.json', g4)}
    record = {'schema': 'razr-product-qualification-acquisition-v1', 'gate': gate,
              'execution_kind': 'synthetic_fixture', 'specimen_ids': [specimen],
              'design_binding': binding,
              'started_at_utc': '2026-10-03T00:00:00Z',
              'ended_at_utc': '2026-10-03T00:10:00Z',
              'maintenance_or_replacement_events': [], 'failures': [],
              'as_built': {specimen: {'design_binding': binding,
                                    'same_donor_specimen_id': observed_donor,
                                    'specimen_record': original_ref, **copy.deepcopy(roles)}}}
    review = {'plan_semantic_sha256': semantic(plan),
              'acquisition_semantic_sha256': semantic(record),
              'specimen_ids': [specimen], 'gate': gate,
              'conclusion': 'verified_preregistered_exact_plan',
              'independent_of_acquisition': True, 'reviewed_by': 'SYNTHETIC-REVIEWER',
              'original_evidence': [source],
              'verified_registration_at_utc': '2026-10-02T15:00:00Z',
              'reviewed_at_utc': '2026-10-03T00:11:00Z'}
    write_json(folder / 'synthetic-plan.json', plan)
    write_json(folder / 'synthetic-acquisition.json', record)
    write_json(folder / 'synthetic-review.json', review)
    external_reader = q.Evidence(folder)
    design = q.Evidence(folder)
    design.binding_status = {'bound_commit': binding['git_commit'],
                            'current_HEAD': binding['git_commit'],
                            'bound_commit_is_current_HEAD': True,
                            'physical_commit_bytes_verified': False,
                            'unbound_current_source_paths': [],
                            'unbound_native_payload_paths': []}

    def synthetic_product_inputs(repository):
        return q.strict_json(external_reader.read(observed_ref))

    out = {'case': kind, 'gate': gate, 'original_donor_location': location,
           'original_nested_donor': original['qualification_assembly'].get('same_donor_specimen_id'),
           'synthetic_fixture': True,
           'execution_kind': record['execution_kind'],
           'original_record_sha256': original_ref['sha256'],
           'original_donor': original.get('same_donor_specimen_id'),
           'original_donor_field_present': 'same_donor_specimen_id' in original,
           'wrapper_donor': record['as_built'][specimen]['same_donor_specimen_id'],
           'plan_donor': plan['same_donor_specimen_id'],
           'synthetic_observed_donor': observed_donor,
           'same_qualification_assembly_roles': all(original['qualification_assembly'][k] == v for k, v in roles.items()),
           'physical_measurement_or_physical_pass_claimed': False}
    with patch.object(q, 'verify_binding', return_value=design), \
            patch.object(q, 'product_inputs', side_effect=synthetic_product_inputs):
        try:
            result, evidence, used_design, _ = q._common(plan, record, folder, folder, review)
            # Test admission finalization with no failing sampled criteria.  This is
            # not evaluate_g4's metric/protocol pipeline or a physical execution.
            result = q._finish(result, evidence, used_design, ['pass'])
            donor_blockers = [b for b in result['blockers'] if 'donor' in b]
            out.update(rejected=False, decision=result, donor_blockers=donor_blockers,
                       donor_identity_admitted=len(donor_blockers) == 0,
                       original_record_checked=any(p.name == 'original-as-built.json'
                                                   for p in evidence.checked))
            if kind == 'missing_original_donor':
                expected = result['status'] == 'unknown' and len(donor_blockers) > 0
            elif kind == 'contradictory_original_donor':
                expected = False
            else:
                expected = len(donor_blockers) == 0 and result['status'] == 'unknown'
        except ValueError as exc:
            out.update(rejected=True, exception_type='ValueError', message=str(exc),
                       donor_identity_admitted=False)
            expected = kind == 'contradictory_original_donor' and 'donor' in str(exc).lower()
    external_reader.recheck()
    out['expected_semantics_met'] = expected
    write_json(folder / 'OUTCOME.json', out)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--assert-fixed', action='store_true')
    args = parser.parse_args()
    source_id = identity(args.source)
    args.output_dir.mkdir()
    q = load_source(args.source)
    specifications = [(gate, kind, 'top') for gate in ('G4', 'G5') for kind in
                      ('missing_original_donor', 'contradictory_original_donor', 'matching_original_donor')]
    specifications += [(gate, 'matching_original_donor', location) for gate in ('G4', 'G5')
                       for location in ('nested', 'top_null_nested', 'both')]
    cases = [probe(q, kind, args.output_dir / (gate+'_'+location+'_'+kind), gate, location)
             for gate, kind, location in specifications]
    if identity(args.source) != source_id:
        raise ValueError('Evaluator source changed while probing')
    report = {'schema': 'r12.independent_original_donor_admission.v1',
              'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'source': source_id, 'probe': identity(Path(__file__)),
              'external_adapters_isolated': ['verify_binding', 'product_inputs'],
              'real_evaluator_path_tested': ['_common', 'Evidence.read', 'prerequisite_decisions', '_finish'],
              'full_G4_protocol_executed': False, 'full_G5_protocol_executed': False,
              'actual_physical_input_or_pass': False,
              'scope': 'Synthetic identity admission only; original bytes and refs are retained and SHA rechecked.',
              'all_expected_semantics_met': all(c['expected_semantics_met'] for c in cases),
              'cases': cases}
    write_json(args.output_dir / 'REPORT.json', report)
    inventory = [{'path': p.relative_to(args.output_dir).as_posix(),
                  'bytes': p.stat().st_size, 'sha256': digest(p.read_bytes())}
                 for p in sorted(args.output_dir.rglob('*')) if p.is_file()]
    write_json(args.output_dir / 'MANIFEST.json', {'schema': 'r12.probe_manifest.v1', 'files': inventory})
    print(json.dumps({'source_sha256': source_id['sha256'],
                      'all_expected_semantics_met': report['all_expected_semantics_met'],
                      'cases': [{k: c.get(k) for k in ('gate', 'case', 'original_donor_location', 'rejected', 'donor_blockers',
                                 'message', 'donor_identity_admitted', 'expected_semantics_met')}
                                for c in cases]}, indent=2))
    if args.assert_fixed and not report['all_expected_semantics_met']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
