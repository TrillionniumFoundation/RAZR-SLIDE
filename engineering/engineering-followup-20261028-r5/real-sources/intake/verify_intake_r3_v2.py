"""V2 review-only intake: retain and enforce assembly intervention chronology."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re


def read_json(path):
    def pairs(rows):
        out = {}
        for key, value in rows:
            if key in out:
                raise ValueError('duplicate_JSON_key:' + key)
            out[key] = value
        return out
    def constant(value):
        raise ValueError('nonfinite_JSON_number:' + value)
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=constant)


def ident(path):
    raw = Path(path).read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('timestamp_missing')
    t = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if t.tzinfo is None:
        raise ValueError('timestamp_timezone_missing')
    return t


def numeric(value, name, nonnegative=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('finite_nonboolean_number_required:' + name)
    if nonnegative and value < 0:
        raise ValueError('negative_number:' + name)


def validate(contract, packet, evidence_root):
    if contract.get('schema') != 'razr-r3-intake-contract-v1':
        raise ValueError('contract_schema')
    if packet.get('schema') != 'razr-r3-intake-packet-v1':
        raise ValueError('packet_schema')
    if packet.get('execution_kind') not in ('unacquired', 'physical', 'synthetic_fixture'):
        raise ValueError('execution_kind')
    missing, invalid, verified = [], [], {}
    root = Path(evidence_root).resolve()
    specimen = packet.get('specimen_id')
    candidate = packet.get('candidate', {})
    if packet.get('is_template') is not False:
        missing.append('packet_is_template')
    if not nonempty(specimen):
        missing.append('specimen_id')
    for key in ('candidate_id', 'functional_commit', 'geometry_revision', 'assembly_revision'):
        if not nonempty(candidate.get(key)):
            missing.append('candidate:' + key)
    if candidate.get('functional_commit') is not None and not re.fullmatch(r'[0-9a-f]{40}', candidate['functional_commit']):
        invalid.append('candidate_commit_format')
    evidences = packet.get('evidence', [])
    if not isinstance(evidences, list):
        raise ValueError('evidence_list_required')
    by_id = {}
    for row in evidences:
        eid = row.get('evidence_id')
        if not nonempty(eid) or eid in by_id:
            raise ValueError('missing_or_duplicate_evidence_id')
        by_id[eid] = row
        try:
            rel = Path(row.get('path', ''))
            if rel.is_absolute() or not rel.parts or '..' in rel.parts:
                raise ValueError('relative_original_path_required')
            path = root/rel
            for ancestor in (path, *path.parents):
                if ancestor == root:
                    break
                if ancestor.is_symlink():
                    raise ValueError('evidence_symlink_not_accepted')
            if root not in path.resolve().parents or not path.is_file():
                raise ValueError('original_file_missing')
            if type(row.get('bytes')) is not int or row['bytes'] <= 0:
                raise ValueError('nonempty_original_bytes_required')
            actual = ident(path)
            if actual != {'sha256': row.get('sha256'), 'bytes': row.get('bytes')}:
                raise ValueError('original_size_or_hash_mismatch')
            if row.get('evidence_kind') not in ('same_specimen_original', 'model_literature',
                    'supplier_original', 'calibration_original', 'physical_gate_original', 'synthetic_fixture'):
                raise ValueError('evidence_kind')
            timestamp(row.get('acquired_at_utc'))
            for field in ('acquirer', 'method', 'source_locator'):
                if not nonempty(row.get(field)):
                    raise ValueError('evidence_metadata:' + field)
            if row['evidence_kind'] in ('same_specimen_original', 'physical_gate_original'):
                if not nonempty(specimen) or row.get('specimen_id') != specimen:
                    raise ValueError('evidence_specimen_mismatch')
            verified[eid] = {'path': path, 'identity': actual}
        except (ValueError, OSError) as exc:
            invalid.append('evidence:' + eid + ':' + str(exc))

    def refs(ids, label, require_specimen=False):
        if not isinstance(ids, list) or not ids:
            missing.append(label + ':evidence_ids')
            return False
        if len(ids) != len(set(ids)):
            invalid.append(label + ':duplicate_evidence_reference')
        good = True
        for eid in ids:
            if eid not in verified:
                invalid.append(label + ':unverified_evidence:' + str(eid))
                good = False
            elif require_specimen and (by_id[eid].get('evidence_kind') != 'same_specimen_original'
                                      or by_id[eid].get('specimen_id') != specimen):
                invalid.append(label + ':not_same_specimen_original:' + eid)
                good = False
        return good

    for kind in ('source_files', 'native_payloads'):
        refs(candidate.get(kind), 'candidate:' + kind)
    requirements = {r['id']: r for r in contract['requirements']}
    claims = packet.get('claims', [])
    claim_map = {}
    for row in claims:
        rid = row.get('requirement_id')
        if rid not in requirements or rid in claim_map:
            raise ValueError('unexpected_or_duplicate_requirement_id:' + str(rid))
        claim_map[rid] = row
    structurally_present = []
    for rid, requirement in requirements.items():
        row = claim_map.get(rid, {})
        if row.get('value') is None:
            missing.append(rid + ':value')
            continue
        before = (len(missing), len(invalid))
        same = requirement['scope'] == 'same_specimen'
        refs(row.get('evidence_ids'), rid, same)
        if same and (not nonempty(specimen) or row.get('specimen_id') != specimen):
            invalid.append(rid + ':claim_specimen_mismatch')
        for field in ('source_locator', 'source_revision'):
            if not nonempty(row.get(field)):
                missing.append(rid + ':' + field)
        if requirement['category'] == 'part':
            expected = packet.get('part_bindings', {}).get(requirement['role'])
            if not nonempty(expected) or row.get('part_id') != expected:
                invalid.append(rid + ':part_binding_missing_or_different')
        measurement = row.get('measurement')
        if 'dimension' in rid or rid.endswith(':measurement_uncertainty'):
            if not isinstance(measurement, dict):
                missing.append(rid + ':measurement_record')
        if measurement is not None:
            try:
                numeric(measurement.get('value'), 'measurement')
                numeric(measurement.get('uncertainty'), 'uncertainty', True)
                for f in ('unit', 'uncertainty_kind', 'coordinate_frame_and_datums', 'instrument_id'):
                    if not nonempty(measurement.get(f)):
                        raise ValueError('measurement_metadata:' + f)
                refs(measurement.get('calibration_evidence_ids'), rid + ':calibration')
                cal_ids = measurement.get('calibration_evidence_ids') or []
                if any(by_id.get(x, {}).get('evidence_kind') != 'calibration_original' for x in cal_ids):
                    raise ValueError('calibration_original_required')
                start = timestamp(measurement.get('calibration_valid_from_utc'))
                end = timestamp(measurement.get('calibration_valid_until_utc'))
                if start > end:
                    raise ValueError('calibration_window_reversed')
                for eid in row.get('evidence_ids', []):
                    if eid in verified and not start <= timestamp(by_id[eid]['acquired_at_utc']) <= end:
                        raise ValueError('acquisition_outside_calibration_window')
            except (ValueError, TypeError) as exc:
                invalid.append(rid + ':' + str(exc))
        if before == (len(missing), len(invalid)):
            structurally_present.append(rid)
    for role in contract['part_roles']:
        if not nonempty(packet.get('part_bindings', {}).get(role)):
            missing.append('part_binding:' + role)
    for interface in contract['interfaces']:
        rows = packet.get('interface_terminal_maps', {}).get(interface)
        if not isinstance(rows, list) or not rows:
            missing.append('terminal_map:' + interface)
            continue
        seen = set()
        for row in rows:
            endpoint = (row.get('source_connector_PN'), row.get('source_pin'))
            if endpoint in seen:
                invalid.append('terminal_map:' + interface + ':duplicate_source_terminal')
            seen.add(endpoint)
            for field in ('source_connector_PN', 'source_connector_revision', 'source_pin',
                          'sink_connector_PN', 'sink_connector_revision', 'sink_pin',
                          'signal_identity', 'direction', 'return_reference', 'source_locator'):
                if not nonempty(row.get(field)):
                    missing.append('terminal_map:' + interface + ':' + field)
            refs(row.get('evidence_ids'), 'terminal_map:' + interface, True)

    intervention_rows = packet.get('repair_and_replacement_events')
    if not isinstance(intervention_rows, list):
        raise ValueError('repair_and_replacement_event_list_required')
    intervention_ids, interventions, intervention_history = set(), [], []
    intervention_missing_start = len(missing)
    intervention_invalid_start = len(invalid)
    for event in intervention_rows:
        eid = event.get('event_id')
        if not nonempty(eid) or eid in intervention_ids:
            invalid.append('intervention:missing_or_duplicate_event_id')
        else:
            intervention_ids.add(eid)
        label = 'intervention:' + str(eid)
        if event.get('kind') not in ('repair', 'replacement'):
            invalid.append(label + ':repair_or_replacement_kind_required')
        if event.get('specimen_id') != specimen:
            invalid.append(label + ':specimen_mismatch')
        old, new = event.get('old_assembly_revision'), event.get('new_assembly_revision')
        if not nonempty(old) or not nonempty(new) or old == new:
            invalid.append(label + ':distinct_revision_required')
        refs(event.get('evidence_ids'), label)
        observed = {'event_id': eid, 'kind': event.get('kind'),
                    'old_assembly_revision': old, 'new_assembly_revision': new,
                    'started_at_utc': event.get('started_at_utc'),
                    'ended_at_utc': event.get('ended_at_utc')}
        intervention_history.append(observed)
        try:
            start = timestamp(event.get('started_at_utc'))
            end = timestamp(event.get('ended_at_utc'))
            if start >= end:
                raise ValueError('intervention_chronology_must_be_strict')
            interventions.append((start, end, event))
        except (ValueError, TypeError) as exc:
            invalid.append(label + ':time_unknown_or_invalid:' + str(exc))
    interventions.sort(key=lambda row: (row[0], row[1]))
    previous_end, previous_new = None, None
    seen_revisions = set()
    for start, end, event in interventions:
        eid = str(event.get('event_id'))
        old, new = event.get('old_assembly_revision'), event.get('new_assembly_revision')
        if previous_end is not None and start < previous_end:
            invalid.append('intervention:' + eid + ':overlapping_interventions')
        if previous_new is not None and old != previous_new:
            invalid.append('intervention:' + eid + ':revision_chain_discontinuous')
        if nonempty(old) and not seen_revisions:
            seen_revisions.add(old)
        if nonempty(new) and new in seen_revisions:
            invalid.append('intervention:' + eid + ':assembly_revision_reused')
        if nonempty(new):
            seen_revisions.add(new)
        previous_end, previous_new = end, new
    if interventions and candidate.get('assembly_revision') != previous_new:
        invalid.append('intervention:current_assembly_revision_differs_from_latest_recorded_revision')
    intervention_history_coherent = (len(missing) == intervention_missing_start
                                     and len(invalid) == intervention_invalid_start)

    events = packet.get('gate_events', [])
    event_ids, accepted, gate_history = set(), {}, []
    known_failure = False
    for event in events:
        eid, gate = event.get('event_id'), event.get('gate')
        if not nonempty(eid) or eid in event_ids or gate not in ('G3', 'G4', 'G5'):
            raise ValueError('gate_event_identity')
        event_ids.add(eid)
        status = event.get('reported_status')
        if status not in ('pass', 'fail', 'missing', 'invalid'):
            raise ValueError('gate_event_status')
        known_failure |= status == 'fail'
        before = len(invalid)
        if eid in intervention_ids:
            invalid.append('gate:' + eid + ':event_id_also_used_by_intervention')
        if not intervention_history_coherent:
            invalid.append('gate:' + eid + ':intervention_history_unknown_or_inconsistent')
        if event.get('specimen_id') != specimen or event.get('candidate') != candidate:
            invalid.append('gate:' + eid + ':binding_mismatch')
        decision_ids = event.get('original_decision_evidence_ids')
        decision_ok = refs(decision_ids, 'gate:' + eid + ':decision')
        raw_ok = refs(event.get('raw_acquisition_evidence_ids'), 'gate:' + eid + ':raw')
        for ref in (decision_ids or []) + (event.get('raw_acquisition_evidence_ids') or []):
            if by_id.get(ref, {}).get('evidence_kind') != 'physical_gate_original' or by_id.get(ref, {}).get('specimen_id') != specimen:
                invalid.append('gate:' + eid + ':physical_original_required:' + ref)
        if status == 'pass' and decision_ok:
            if len(decision_ids) != 1:
                invalid.append('gate:' + eid + ':one_original_decision_required')
            else:
                try:
                    decision = read_json(verified[decision_ids[0]]['path'])
                    expected_schema = ('razr-unpowered-motion-qualification-decision-v1' if gate == 'G3'
                                       else 'razr-product-qualification-decision-v1')
                    if decision.get('schema') != expected_schema or decision.get('status') != 'pass' or decision.get('execution_kind') != 'physical':
                        raise ValueError('original_physical_pass_decision_required')
                    if gate == 'G3':
                        if decision.get('current_EP5_candidate_bound') is not True or decision.get('specimen_id') != specimen:
                            raise ValueError('original_G3_candidate_specimen_mismatch')
                    elif decision.get('gate') != gate or specimen not in decision.get('specimen_ids', []):
                        raise ValueError('original_gate_or_specimen_mismatch')
                    binding = decision.get('design_binding', {})
                    if binding.get('git_commit') != candidate.get('functional_commit') or binding.get('candidate_id') != candidate.get('candidate_id'):
                        raise ValueError('original_decision_candidate_mismatch')
                except (ValueError, OSError) as exc:
                    invalid.append('gate:' + eid + ':' + str(exc))
        try:
            start, end = timestamp(event.get('started_at_utc')), timestamp(event.get('ended_at_utc'))
            if start >= end:
                raise ValueError('gate_event_chronology')
            if interventions and start < interventions[-1][1]:
                invalid.append('gate:' + eid + ':current_revision_gate_predates_latest_intervention_completion')
            for repair_start, repair_end, repair in interventions:
                if repair_start < end and repair_end > start:
                    invalid.append('gate:' + eid + ':intervention_overlaps_acquisition:' + str(repair.get('event_id')))
            if status == 'pass':
                if event.get('execution_kind') != 'physical':
                    invalid.append('gate:' + eid + ':not_reported_physical')
                prior_gate = {'G4': 'G3', 'G5': 'G4'}.get(gate)
                if prior_gate:
                    prior = accepted.get(event.get('predecessor_event_id'))
                    if prior is None or prior['gate'] != prior_gate:
                        invalid.append('gate:' + eid + ':prerequisite_pass_missing')
                    elif timestamp(prior['ended_at_utc']) >= start:
                        invalid.append('gate:' + eid + ':prerequisite_not_finished_before_start')
                    else:
                        prior_end = timestamp(prior['ended_at_utc'])
                        if any(prior_end <= repair_end and repair_start <= start
                               for repair_start, repair_end, _ in interventions):
                            invalid.append('gate:' + eid + ':intervention_invalidates_predecessor')
                if len(invalid) == before and decision_ok and raw_ok:
                    accepted[eid] = event
            gate_history.append({'event_id': eid, 'gate': gate, 'reported_status': status,
                                 'reported_pass_sequence_structurally_valid': eid in accepted})
        except ValueError as exc:
            invalid.append('gate:' + eid + ':' + str(exc))
    for eid, row in verified.items():
        if ident(row['path']) != row['identity']:
            invalid.append('evidence_changed_during_admission:' + eid)
    if packet['execution_kind'] != 'physical':
        missing.append('no_declared_physical_acquisition')
    return {
        'schema': 'razr-r3-intake-admission-v2',
        'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'review_ready_structure': not missing and not invalid,
        'verified_original_bytes_count': len(verified),
        'requirement_count': len(requirements),
        'structurally_present_requirement_count': len(structurally_present),
        'structurally_present_requirement_ids': structurally_present,
        'missing': sorted(set(missing)), 'invalid': sorted(set(invalid)),
        'reported_gate_history': gate_history,
        'reported_intervention_history': intervention_history,
        'intervention_history_structurally_coherent': intervention_history_coherent,
        'accepted_gate_history_scope': 'Current declared assembly revision only; historical reported outcomes remain in reported_gate_history.',
        'known_failure_retained': known_failure,
        'qualification_status': 'fail_report_retained' if known_failure else 'unqualified',
        'physical_gate_pass': {'G3': False, 'G4': False, 'G5': False},
        'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False,
        'original_evidence_authenticity_verified': False,
        'scope': contract['scope']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--packet', type=Path, required=True)
    p.add_argument('--evidence-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError('fresh output required')
    result = validate(read_json(a.contract), read_json(a.packet), a.evidence_root)
    result.update({'contract_identity': ident(a.contract), 'packet_identity': ident(a.packet),
                   'evaluator_identity': ident(Path(__file__))})
    a.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    print(json.dumps({k: result[k] for k in ('review_ready_structure', 'verified_original_bytes_count',
                                           'requirement_count', 'physical_gate_pass')}))


if __name__ == '__main__':
    main()
