"""Hash declared original files and run the unchanged R3 V2 structural intake; never grant a pass."""
from __future__ import annotations
import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

CONTRACT_SHA = '876ca9a54ba94fe6be7695ab641435cdcd69709ff21bf093898f30a09fd36a5a'
VALIDATOR_SHA = '7ed1aa270bfb05f543d27f33b31b7ee0bd641b3d7d7d6217314f11d2391cc8d8'
KINDS = {'same_specimen_original', 'model_literature', 'supplier_original',
         'calibration_original', 'physical_gate_original', 'synthetic_fixture'}

def read_json(path):
    def pairs(rows):
        result = {}
        for k, v in rows:
            if k in result:
                raise ValueError('duplicate_JSON_key:' + k)
            result[k] = v
        return result
    def constant(x):
        raise ValueError('nonfinite_JSON_number:' + x)
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=constant)

def identity(path):
    h = hashlib.sha256()
    count = 0
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
            count += len(chunk)
    return {'bytes': count, 'sha256': h.hexdigest()}

def text_field(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('missing_text:' + label)
    return value

def time_field(value, label):
    value = text_field(value, label)
    t = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if t.tzinfo is None:
        raise ValueError('timezone_missing:' + label)

def receive(inventory, packet, evidence_root):
    if inventory.get('schema') != 'razr-r5-evidence-receipt-inventory-v1':
        raise ValueError('inventory_schema')
    if packet.get('schema') != 'razr-r3-intake-packet-v1':
        raise ValueError('original_packet_schema')
    if packet.get('evidence'):
        raise ValueError('input_packet_evidence_must_be_empty_to_prevent_silent_replacement')
    root = Path(evidence_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('regular_evidence_root_directory_required')
    root = root.resolve()
    rows = inventory.get('files')
    if not isinstance(rows, list):
        raise ValueError('declared_file_list_required')
    ids, paths, accepted, rejected = set(), set(), [], []
    for index, row in enumerate(rows):
        label = 'row:' + str(index)
        try:
            if not isinstance(row, dict):
                raise ValueError('file_metadata_object_required')
            eid = text_field(row.get('evidence_id'), 'evidence_id')
            label = eid
            if eid in ids:
                raise ValueError('duplicate_evidence_id')
            ids.add(eid)
            rel_text = text_field(row.get('path'), 'path')
            rel = Path(rel_text)
            if rel.is_absolute() or '..' in rel.parts or rel_text != rel.as_posix() or rel.as_posix() == '.':
                raise ValueError('canonical_relative_file_path_required')
            if rel.as_posix() in paths:
                raise ValueError('one_original_path_one_evidence_id')
            paths.add(rel.as_posix())
            target = root / rel
            current = root
            for component in rel.parts:
                current = current / component
                if current.is_symlink():
                    raise ValueError('symlink_original_rejected')
            if root not in target.resolve().parents or not target.is_file():
                raise ValueError('regular_original_missing_or_outside_root')
            kind = row.get('evidence_kind')
            if kind not in KINDS:
                raise ValueError('evidence_kind_not_explicit_or_unknown')
            for field in ('acquirer', 'method', 'source_locator'):
                text_field(row.get(field), field)
            time_field(row.get('acquired_at_utc'), 'acquired_at_utc')
            if kind in ('same_specimen_original', 'physical_gate_original'):
                if not packet.get('specimen_id') or row.get('specimen_id') != packet['specimen_id']:
                    raise ValueError('declared_same_specimen_id_missing_or_different')
            before = target.stat()
            actual = identity(target)
            after = target.stat()
            if not stat.S_ISREG(before.st_mode) or actual['bytes'] <= 0:
                raise ValueError('nonempty_regular_original_required')
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError('original_changed_during_reception')
            expected = row.get('expected_identity')
            if expected is not None and expected != actual:
                raise ValueError('provided_original_identity_mismatch')
            copied = {k: copy.deepcopy(v) for k, v in row.items() if k != 'expected_identity'}
            copied.update(actual)
            accepted.append(copied)
        except (ValueError, TypeError, OSError) as exc:
            rejected.append({'file': label, 'reason': str(exc)})
    output_packet = copy.deepcopy(packet)
    if not rejected:
        output_packet['evidence'] = accepted
    return {'received': accepted, 'rejected': rejected,
            'packet': output_packet,
            'input_claims_preserved_exactly': output_packet.get('claims') == packet.get('claims'),
            'input_gate_and_intervention_events_preserved_exactly': all(output_packet.get(k) == packet.get(k)
                for k in ('gate_events', 'repair_and_replacement_events'))}

def run(inventory_path, packet_path, evidence_root, contract_path, validator_path, output_dir):
    contract_id, validator_id = identity(contract_path), identity(validator_path)
    if contract_id['sha256'] != CONTRACT_SHA or validator_id['sha256'] != VALIDATOR_SHA:
        raise ValueError('original_contract_or_V2_validator_identity_changed')
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError('fresh output directory required')
    inventory, packet, contract = read_json(inventory_path), read_json(packet_path), read_json(contract_path)
    result = receive(inventory, packet, evidence_root)
    if result['rejected']:
        admission = None
    else:
        spec = importlib.util.spec_from_file_location('razr_original_intake_v2', validator_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        admission = module.validate(contract, result['packet'], evidence_root)
    if identity(contract_path) != contract_id or identity(validator_path) != validator_id:
        raise ValueError('original_contract_or_V2_validator_changed_during_run')
    receipt = {'schema': 'razr-r5-declared-original-reception-v1',
        'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'source_identity': identity(__file__),
        'inventory_identity': identity(inventory_path), 'input_packet_identity': identity(packet_path),
        'original_contract_identity': contract_id, 'original_V2_validator_identity': validator_id,
        'declared_files_count': len(inventory['files']), 'actual_received_files_count': len(result['received']),
        'rejected': result['rejected'],
        'all_declared_originals_received': bool(inventory['files']) and not result['rejected'],
        'input_claims_preserved_exactly': result['input_claims_preserved_exactly'],
        'input_gate_and_intervention_events_preserved_exactly': result['input_gate_and_intervention_events_preserved_exactly'],
        'original_V2_admission_executed': admission is not None,
        'review_ready_structure': bool(admission and admission['review_ready_structure']),
        'original_evidence_authenticity_verified': False,
        'new_physical_measurement_count': 0,
        'physical_gate_pass': {'G3': False, 'G4': False, 'G5': False},
        'scope': 'Byte receipt and original V2 structural review only. Caller-declared physical labels are not authenticated. Missing evidence, limits and facts remain missing.'}
    output.mkdir(parents=True)
    for name, data in [('R5_RECEPTION_RECEIPT.json', receipt),
                       ('packet_for_original_v2.json', result['packet']),
                       ('original_V2_admission.json', admission)]:
        if data is not None:
            (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: receipt[k] for k in ('actual_received_files_count', 'review_ready_structure', 'physical_gate_pass', 'rejected')}))
    return 2 if result['rejected'] else 0

def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ('inventory', 'packet', 'evidence-root', 'contract', 'validator', 'output-dir'):
        parser.add_argument('--' + name, required=True, type=Path)
    option_keys = [x.split('=', 1)[0] for x in sys.argv[1:] if x.startswith('--')]
    if len(option_keys) != len(set(option_keys)):
        parser.error('duplicate options rejected')
    a = parser.parse_args()
    return run(a.inventory, a.packet, a.evidence_root, a.contract, a.validator, a.output_dir)

if __name__ == '__main__':
    raise SystemExit(main())
