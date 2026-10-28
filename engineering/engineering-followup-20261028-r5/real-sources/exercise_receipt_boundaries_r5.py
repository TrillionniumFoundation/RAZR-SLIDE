"""Execute focused receipt controls using explicit synthetic fixtures, never physical evidence."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
WORKER = ROOT / 'receive_evidence_r5.py'

def main():
    start = time.monotonic()
    out = ROOT / 'actual' / 'receipt-controls'
    out.mkdir()
    files = out / 'synthetic-originals'
    files.mkdir()
    raw = files / 'synthetic.txt'
    raw.write_bytes(b'EXPLICIT SYNTHETIC RECEIPT CONTROL\n')
    (files / 'alias.txt').symlink_to('synthetic.txt')
    spec = importlib.util.spec_from_file_location('r5_receipt_under_review', WORKER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    packet = m.read_json(ROOT / 'intake' / 'R3_EMPTY_INTAKE_PACKET.json')
    packet['specimen_id'] = 'SYNTHETIC-CONTROL-ONLY'
    packet['execution_kind'] = 'synthetic_fixture'
    row = {'evidence_id': 'SYNTHETIC-ONE', 'path': 'synthetic.txt',
        'evidence_kind': 'synthetic_fixture', 'specimen_id': 'SYNTHETIC-CONTROL-ONLY',
        'acquired_at_utc': '2026-10-28T00:00:00Z', 'acquirer': 'synthetic-control-generator',
        'method': 'synthetic boundary control only', 'source_locator': 'synthetic fixture bytes',
        'expected_identity': m.identity(raw)}
    base = {'schema': 'razr-r5-evidence-receipt-inventory-v1', 'files': [row]}
    results = []
    def check(name, inventory, expected):
        result = m.receive(inventory, packet, files)
        valid = any(expected in x['reason'] for x in result['rejected']) if expected else not result['rejected']
        valid = valid and result['input_claims_preserved_exactly'] and result['input_gate_and_intervention_events_preserved_exactly']
        if expected:
            valid = valid and result['packet']['evidence'] == []
        results.append({'name': name, 'expected_rejection': expected, 'observed': result['rejected'], 'passed': valid})
        (out / (name + '.input.json')).write_text(json.dumps(inventory, indent=2) + '\n')
        (out / (name + '.result.json')).write_text(json.dumps(result, indent=2) + '\n')
    check('synthetic_byte_receipt_preserves_missing_facts', copy.deepcopy(base), None)
    mutations = [
        ('hash_mismatch', 'expected_identity', {'bytes': row['expected_identity']['bytes'], 'sha256': '0' * 64}, 'provided_original_identity_mismatch'),
        ('symlink', 'path', 'alias.txt', 'symlink_original_rejected'),
        ('parent_escape', 'path', '../synthetic.txt', 'canonical_relative_file_path_required'),
        ('absolute_path', 'path', str(raw), 'canonical_relative_file_path_required'),
        ('undeclared_kind', 'evidence_kind', None, 'evidence_kind_not_explicit_or_unknown'),
        ('missing_operator', 'acquirer', None, 'missing_text:acquirer'),
        ('timezone_missing', 'acquired_at_utc', '2026-10-28T00:00:00', 'timezone_missing')]
    for name, key, value, expected in mutations:
        item = copy.deepcopy(base)
        item['files'][0][key] = value
        check(name, item, expected)
    item = copy.deepcopy(base)
    item['files'][0].update(evidence_kind='same_specimen_original', specimen_id='OTHER-SYNTHETIC')
    check('cross_specimen', item, 'declared_same_specimen_id_missing_or_different')
    item = copy.deepcopy(base)
    item['files'].append(copy.deepcopy(row))
    check('duplicate_evidence_id', item, 'duplicate_evidence_id')
    item = copy.deepcopy(base)
    item['files'].append({**row, 'evidence_id': 'SYNTHETIC-TWO'})
    check('duplicate_original_path', item, 'one_original_path_one_evidence_id')
    for name, raw_json, expected in [('duplicate_JSON_key', '{"x":1,"x":2}', 'duplicate_JSON_key'),
                                     ('nonfinite_JSON', '{"x":NaN}', 'nonfinite_JSON_number')]:
        path = out / (name + '.json')
        path.write_text(raw_json)
        try:
            m.read_json(path)
            observed = 'unexpected_accept'
        except ValueError as e:
            observed = str(e)
        results.append({'name': name, 'expected_rejection': expected, 'observed': observed, 'passed': expected in observed})
    cmd = [sys.executable, '-B', str(WORKER), '--inventory', str(ROOT / 'intake' / 'R5_EMPTY_EVIDENCE_INVENTORY.json'),
        '--packet', str(ROOT / 'intake' / 'R3_EMPTY_INTAKE_PACKET.json'), '--evidence-root', str(files),
        '--contract', str(ROOT / 'intake' / 'R3_SAME_SPECIMEN_INTAKE_CONTRACT.json'),
        '--validator', str(ROOT / 'intake' / 'verify_intake_r3_v2.py'), '--output-dir', str(out / 'must_not_exist')]
    for name, extra, expected in [('duplicate_output_option', ['--output-dir', str(out / 'other')], 'duplicate options rejected'),
                                   ('abbreviated_output_option', ['--output', str(out / 'other')], 'unrecognized arguments')]:
        r = subprocess.run(cmd + extra, capture_output=True, text=True, timeout=15)
        results.append({'name': name, 'exit': r.returncode, 'stderr': r.stderr,
            'passed': r.returncode == 2 and expected in r.stderr and not (out / 'must_not_exist').exists() and not (out / 'other').exists()})
    report = {'schema': 'razr-r5-receipt-boundary-controls-v1', 'execution_kind': 'synthetic_fixture',
        'worker_identity': m.identity(WORKER), 'controller_identity': m.identity(__file__),
        'checks': results, 'total_checks': len(results), 'all_passed': all(x['passed'] for x in results),
        'seconds': time.monotonic() - start, 'physical_originals_created': 0,
        'physical_qualification_granted': False, 'old_R3_37_control_suite_rerun': False}
    (out / 'R5_RECEIPT_BOUNDARY_CONTROLS.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('total_checks', 'all_passed', 'seconds')}))
    if not report['all_passed']:
        raise SystemExit(2)

if __name__ == '__main__':
    main()
