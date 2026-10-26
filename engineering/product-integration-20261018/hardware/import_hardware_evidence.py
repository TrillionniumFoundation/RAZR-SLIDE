#!/usr/bin/env python3
"""Import original physical observations without editing the product configuration.

The operator supplies a manifest and original files. This tool checks identity,
hashes, units, provenance and version consistency; it does not authenticate the
contents of a photograph or turn a reported outcome into hardware qualification.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'integration'))
import product_interfaces as interfaces
sys.path.insert(0, str(ROOT/'tools'))
import read_donor

INPUTS = ('design/product_geometry.json', 'design/product_interfaces.json')
KINDS = {'physical_label', 'physical_measurement', 'manufacturer_document',
         'device_readback', 'instrument_log', 'operator_observation'}
SCHEMAS = {
    'donor_identity': 'razr-observed-donor-identity-v2',
    'terminal_map': 'razr-physical-terminal-measurement-v2',
    'dimensions': 'razr-part-measurements-v2',
    'phone_function': 'razr-phone-function-observations-v2',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def utc(value):
    require(nonempty(value), 'missing recorded_at_utc')
    stamp = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(stamp.tzinfo is not None, 'recorded_at_utc needs an explicit timezone')
    return stamp.isoformat()


def finite(value, label, nonnegative=False):
    require(not isinstance(value, bool), label+' is not a boolean')
    result = float(value)
    require(math.isfinite(result) and (not nonnegative or result >= 0), label+' must be finite')
    return result


def within(base, name):
    require(nonempty(name) and not Path(name).is_absolute(), 'source paths must be relative')
    path = (base/name).resolve()
    require(base.resolve() in path.parents and path.is_file(), 'source escaped its root or is missing: '+name)
    return path


def binding(root, data):
    value = read_donor.design_identity(root)
    require(value['complete'] and re.fullmatch(r'[a-f0-9]{40}', value.get('git_commit', '')),
            'a real Git checkout is required to bind physical observations')
    require(value['interface_contract_sha256'] == interfaces.interface_contract_sha256(data),
            'interface configuration changed during binding')
    return value


def source_rows(manifest, folder):
    result = {}
    for row in manifest.get('observations', []):
        require(isinstance(row, dict), 'observation must be an object')
        key = row.get('id')
        require(nonempty(key) and re.fullmatch(r'[A-Za-z0-9_.-]+', key) and key not in result,
                'observation IDs must be unique, nonempty and path-safe')
        require(row.get('kind') in KINDS, 'unsupported observation kind')
        if row['kind'] != 'manufacturer_document':
            require(row.get('specimen_id') == manifest['specimen_id'], 'original observation names a different or missing specimen')
        require(re.fullmatch(r'[a-f0-9]{64}', row.get('sha256', '')) is not None,
                'each original observation needs its supplied SHA256')
        path = within(folder, row.get('path'))
        payload = path.read_bytes()
        require(hashlib.sha256(payload).hexdigest() == row['sha256'], 'original evidence hash mismatch: '+key)
        result[key] = {**row, '_payload': payload, '_suffix': path.suffix}
    require(result, 'no original observations supplied')
    return result


def linked(ids, locator, sources, physical=False):
    probe = {'value': 'observed', 'locator': locator, 'observation_ids': ids}
    if physical:
        require(interfaces.observed_field_bound(probe, sources, True), 'physical row needs original evidence and a locator')
    else:
        require(isinstance(ids, list) and ids and len(ids) == len(set(ids))
                and all(key in sources for key in ids) and nonempty(locator),
                'row needs original evidence IDs and a locator')


def csv_rows(sources, source_id, fields):
    require(source_id in sources, 'missing original CSV observation')
    table = csv.DictReader(io.StringIO(sources[source_id]['_payload'].decode('utf-8-sig')))
    require(table.fieldnames is not None and len(table.fieldnames) == len(set(table.fieldnames)),
            'CSV header missing or repeated')
    require(set(fields) <= set(table.fieldnames), 'CSV missing columns: '+','.join(fields))
    rows = list(table)
    require(rows and all(None not in row for row in rows), 'CSV is empty or has excess columns')
    return rows


def readback(sources, source_id, specimen, expected_binding):
    require(source_id in sources and sources[source_id]['kind'] == 'device_readback',
            'a donor readback observation is required')
    value = json.loads(sources[source_id]['_payload'])
    require(value.get('schema') == 'razr-donor-readback-v2'
            and interfaces.readback_trace_consistent(value)
            and value.get('specimen_id') == specimen
            and value.get('selected_donor_connected') is True
            and value.get('software_identity_complete') is True
            and value.get('design_inputs_unchanged') is True,
            'readback did not identify a connected specimen with stable design inputs')
    require(value.get('design_binding', {}).get('files_sha256') == expected_binding['files_sha256'],
            'donor readback belongs to different design inputs')
    require(value.get('design_binding', {}).get('git_commit') == expected_binding['git_commit'],
            'readback and manifest name different source commits')
    digest = value.get('selected_serial_sha256', '')
    require(re.fullmatch(r'[a-f0-9]{64}', digest), 'selected donor hash is missing')
    return value


def import_identity(manifest, record, sources, data):
    interfaces.validate_donor_fields(data.get('donor'))
    fields = manifest.get('field_evidence', {})
    require(isinstance(fields, dict) and set(fields) <= set(interfaces.DONOR_FIELDS), 'unknown donor identity field')
    donor = {key: None for key in interfaces.DONOR_FIELDS}
    for key, field in fields.items():
        require(interfaces.observed_field_bound(field, sources, key in interfaces.PHYSICAL_DONOR_FIELDS), 'unsupported identity evidence: '+key)
        donor[key] = field['value']
    capture_id = manifest.get('device_readback_observation')
    capture = readback(sources, capture_id, record['specimen_id'], record['design_binding'])
    require(donor['model'] is None or donor['model'] == capture['properties']['ro.product.model'],
            'declared donor model differs from the original ADB observation')
    inventory = manifest.get('part_inventory', [])
    ids = set()
    for part in inventory:
        roles = part.get('roles', [part.get('role')])
        require(isinstance(roles, list) and roles and all(nonempty(role) for role in roles), 'physical parts need named roles')
        require(nonempty(part.get('part_id')) and part['part_id'] not in ids,
                'physical parts need unique IDs and roles')
        require(interfaces.observed_field_bound(part.get('label'), sources, True), 'part label has no original evidence')
        ids.add(part['part_id'])
    record.update(donor=donor, field_evidence=fields, part_inventory=inventory,
                  device_readback_observation=capture_id,
                  selected_serial_sha256=capture['selected_serial_sha256'])
    return {'known_identity_fields': sum(value is not None for value in donor.values()),
            'unknown_identity_fields': [key for key, value in donor.items() if value is None],
            'physical_parts_with_original_labels': len(inventory),
            'missing_inventory_roles': sorted({'mainboard', 'display', 'touch', 'COF', 'pack_A', 'pack_B', 'USB_port_board'}
                                              - {role for part in inventory for role in part.get('roles', [part.get('role')])}),
            'platform_frozen': False}


def selected_identity(manifest, data, root):
    reference = manifest.get('donor_identity_record')
    require(reference == data.get('donor_evidence', {}).get('identity_record'),
            'measurement must reference the same identity record as the current configuration')
    require(interfaces.donor_identity_bound(data, root), 'current donor identity is not physically bound')
    return interfaces.evidence_record(reference, 'razr-observed-donor-identity-v2', root)


def import_terminals(manifest, record, sources, data, root):
    identity = selected_identity(manifest, data, root)
    require(identity['specimen_id'] == record['specimen_id'], 'terminal map belongs to another specimen')
    interface_id = manifest.get('interface_id')
    require(interface_id in interfaces.INTERFACES, 'unknown product interface')
    fields = ('net', 'source_connector', 'source_pin', 'sink_connector', 'sink_pin')
    source_id = manifest.get('terminal_csv_observation')
    rows = csv_rows(sources, source_id, (*fields, 'observation_ids', 'locator'))
    terminals, pinmap = [], []
    connectors = manifest.get('connectors', {})
    require(isinstance(connectors, dict) and connectors, 'observed connectors are required')
    part_ids = {part['part_id'] for part in identity.get('part_inventory', [])}
    for name, connector in connectors.items():
        require(nonempty(name) and connector.get('part_id') in part_ids, 'connector is not attached to an observed donor part')
        pins = connector.get('observed_pins')
        require(isinstance(pins, list) and pins and len(pins) == len(set(pins)) and all(nonempty(p) for p in pins),
                'connector needs its unique physically observed pin inventory')
        require(interfaces.observed_field_bound(connector.get('label'), sources, True), 'connector label has no original evidence')
    used = {key: set() for key in connectors}
    for row in rows:
        ids = row['observation_ids'].split(';')
        linked(ids, row['locator'], sources, True)
        for end in ('source', 'sink'):
            name, pin = row[end+'_connector'], row[end+'_pin']
            require(name in connectors and pin in connectors[name]['observed_pins'], 'terminal is absent from observed connector inventory')
            used[name].add(pin)
        terminals.append({**{key: row[key] for key in fields}, 'observation_ids': ids,
                          'locator': row['locator'], 'csv_observation': source_id})
        pinmap.append({**{key: row[key] for key in fields}, 'evidence': source_id+':'+row['locator'],
                       'identity_kind': 'observed_physical_terminal'})
    interfaces.validate_pinmap(pinmap)
    record.update(donor=data['donor'], donor_identity_record=manifest['donor_identity_record'],
                  interface_id=interface_id, connectors=connectors, terminal_rows=terminals,
                  proposed_actual_pinmap=pinmap)
    return {'observed_terminal_rows': len(terminals),
            'unmapped_observed_pins': {key: sorted(set(value['observed_pins'])-used[key])
                                     for key, value in connectors.items()},
            'extension_approved': False, 'product_power_or_display_connected': False}


def import_dimensions(manifest, record, sources):
    require(nonempty(manifest.get('coordinate_frame')), 'measurements need a stated coordinate frame')
    source_id = manifest.get('measurement_csv_observation')
    fields = ('part_id', 'quantity', 'value', 'unit', 'uncertainty', 'observation_ids', 'locator')
    rows = csv_rows(sources, source_id, fields)
    measured = []
    for row in rows:
        require(nonempty(row['part_id']) and nonempty(row['quantity']), 'dimension has no physical part or quantity')
        require(row['unit'] in ('mm', 'g', 'deg', 'mm2', 'mm3'), 'dimension units must be explicit supported SI-derived units')
        ids = row['observation_ids'].split(';')
        linked(ids, row['locator'], sources, True)
        measured.append({**row, 'value': finite(row['value'], 'measurement'),
                         'uncertainty': finite(row['uncertainty'], 'uncertainty', True),
                         'observation_ids': ids, 'csv_observation': source_id})
    record.update(coordinate_frame=manifest['coordinate_frame'], measurements=measured)
    return {'measurement_rows': len(measured), 'part_ids': sorted({row['part_id'] for row in measured}),
            'CAD_replaced_or_packing_verified': False}


def import_phone(manifest, record, sources, data, root):
    identity = selected_identity(manifest, data, root)
    require(identity['specimen_id'] == record['specimen_id'], 'phone log belongs to another specimen')
    capture_id = manifest.get('device_readback_observation')
    capture = readback(sources, capture_id, record['specimen_id'], record['design_binding'])
    require(capture['selected_serial_sha256'] == identity['selected_serial_sha256'], 'phone log names another donor')
    require(nonempty(manifest.get('timebase_id')), 'phone observations need a named timebase')
    source_id = manifest.get('function_csv_observation')
    fields = ('time_s', 'phase', 'function', 'reported_outcome', 'metric', 'value', 'unit', 'observation_ids', 'locator')
    rows = csv_rows(sources, source_id, fields)
    observations, last = [], -math.inf
    for row in rows:
        stamp = finite(row['time_s'], 'time_s', True)
        require(stamp >= last, 'phone observation timestamps must be monotonic')
        last = stamp
        require(row['function'] in ('display', 'touch', 'power', 'usb', 'camera', 'rf', 'audio_sensors'), 'unknown phone function')
        require(nonempty(row['phase']), 'phone observation needs its actual pose or baseline phase')
        require(row['reported_outcome'] in ('observed_ok', 'observed_failure', 'not_observed'), 'use observed outcomes, not an inferred certification')
        ids = row['observation_ids'].split(';')
        linked(ids, row['locator'], sources)
        value = None if row['value'] == '' else finite(row['value'], 'phone metric')
        require(value is None or (nonempty(row['metric']) and nonempty(row['unit'])), 'numeric metrics require names and units')
        observations.append({**row, 'time_s': stamp, 'value': value, 'observation_ids': ids,
                             'csv_observation': source_id})
    record.update(donor=data['donor'], donor_identity_record=manifest['donor_identity_record'],
                  selected_serial_sha256=capture['selected_serial_sha256'],
                  device_readback_observation=capture_id, timebase_id=manifest['timebase_id'],
                  function_observations=observations)
    return {'observations': len(observations), 'functions_recorded': sorted({row['function'] for row in observations}),
            'phases_recorded': sorted({row['phase'] for row in observations}),
            'reported_failures': sum(row['reported_outcome'] == 'observed_failure' for row in observations),
            'observed_time_span_s': observations[-1]['time_s']-observations[0]['time_s'],
            'motion_continuity_verified': False, 'phone_function_verified': False,
            'scope': 'operator/instrument observations at logged times; interval coverage is not inferred'}


def import_manifest(manifest_path, output, root=ROOT):
    root, manifest_path, output = Path(root).resolve(), Path(manifest_path).resolve(), Path(output).resolve()
    require(root in output.parents and not output.exists(), 'output must be a new directory inside the repository')
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    require(manifest.get('schema') == 'razr-hardware-import-v1', 'unknown import manifest schema')
    require(manifest.get('is_template') is False and manifest.get('physical_execution_occurred') is True,
            'a template or planned observation is not physical evidence')
    for key in ('specimen_id', 'measurement_method', 'operator_or_instrument'):
        require(nonempty(manifest.get(key)), 'missing '+key)
    kind = manifest.get('record_type')
    require(kind in SCHEMAS, 'unknown hardware record type')
    data = json.loads((root/'design/product_interfaces.json').read_text())
    interfaces.validate_config(data, root)
    current = binding(root, data)
    supplied = manifest.get('design_binding', {})
    # Commit may precede a documentation-only followup. The retained exact source
    # input bytes, not an assumed same branch name, decide compatibility.
    require(re.fullmatch(r'[a-f0-9]{40}', supplied.get('git_commit', '')) is not None
            and supplied.get('files_sha256') == current['files_sha256']
            and supplied.get('interface_contract_sha256') == current['interface_contract_sha256'],
            'manifest source identity does not match current design bytes')
    committed = read_donor.commit_design_sha256(root, supplied['git_commit'])
    require(all(committed.values()) and supplied.get('commit_files_sha256') == committed
            and supplied.get('inputs_match_commit') is (supplied['files_sha256'] == committed),
            'source commit is missing or its committed-versus-working-input identity is incorrect')
    sources = source_rows(manifest, manifest_path.parent)
    record = {'schema': SCHEMAS[kind], 'is_template': False, 'physical_execution_occurred': True,
              'specimen_id': manifest['specimen_id'], 'recorded_at_utc': utc(manifest['recorded_at_utc']),
              'measurement_method': manifest['measurement_method'], 'operator_or_instrument': manifest['operator_or_instrument'],
              'design_binding': supplied, 'importer_sha256': interfaces.sha(__file__),
              'import_manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
              'candidate_go': False, 'fixture_fabrication_go': False,
              'manufacturing_go': False, 'physical_phone_verified': False}
    if kind == 'donor_identity':
        summary = import_identity(manifest, record, sources, data)
    elif kind == 'terminal_map':
        summary = import_terminals(manifest, record, sources, data, root)
    elif kind == 'dimensions':
        summary = import_dimensions(manifest, record, sources)
    else:
        summary = import_phone(manifest, record, sources, data, root)
    # Preserve source bytes once; every derived row points back to these files.
    payloads = {}
    indexed = []
    for key, source in sources.items():
        name = 'raw/'+key+source['_suffix']
        payloads[name] = source['_payload']
        indexed.append({key: value for key, value in source.items() if not key.startswith('_')})
        indexed[-1]['original_path'] = indexed[-1]['path']
        indexed[-1]['path'] = (output/name).relative_to(root).as_posix()
    for index, name in enumerate(INPUTS):
        key = 'archived_design_'+str(index)
        require(key not in sources, 'reserved design observation ID reused')
        payloads['inputs/'+Path(name).name] = (root/name).read_bytes()
        indexed.append({'id': key, 'kind': 'design_input', 'input_design_path': name,
                        'path': (output/'inputs'/Path(name).name).relative_to(root).as_posix(),
                        'sha256': current['files_sha256'][name]})
    require('archived_import_manifest' not in sources, 'reserved manifest observation ID reused')
    indexed.append({'id': 'archived_import_manifest', 'kind': 'import_manifest',
                    'specimen_id': record['specimen_id'],
                    'path': (output/'import-manifest.json').relative_to(root).as_posix(),
                    'sha256': hashlib.sha256(manifest_bytes).hexdigest()})
    record['observations'], record['summary'] = indexed, summary
    payloads['import-manifest.json'] = manifest_bytes
    payloads['record.json'] = (json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False)+'\n').encode()
    reference = {'path': (output/'record.json').relative_to(root).as_posix(),
                 'sha256': hashlib.sha256(payloads['record.json']).hexdigest()}
    proposed = {'record': reference, 'configuration_edited': False}
    if kind == 'donor_identity':
        proposed.update(donor=record['donor'], donor_evidence={'identity_record': reference},
                        architecture_decision={'actual_donor_selected': False})
    elif kind == 'terminal_map':
        proposed.update(interface_id=record['interface_id'], actual_pinmap=record['proposed_actual_pinmap'],
                        terminal_measurement_record=reference, extension_approved=False)
    payloads['proposed-config-update.json'] = (json.dumps(proposed, indent=2, ensure_ascii=False)+'\n').encode()
    require(binding(root, data) == current, 'design changed during import')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.hardware-import-', dir=output.parent))
    try:
        for name, payload in payloads.items():
            path = staging/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        require(not output.exists(), 'output appeared during import')
        staging.rename(output)
    except BaseException:
        shutil.rmtree(staging)
        raise
    return {'output': str(output), 'record': reference, 'summary': summary,
            'original_observation_files': len(sources), 'configuration_edited': False,
            'physical_phone_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=ROOT)
    parser.add_argument('--print-binding', action='store_true')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.print_binding:
            data = json.loads((args.repo_root/'design/product_interfaces.json').read_text())
            result = binding(args.repo_root, data)
        else:
            require(args.manifest is not None and args.output is not None, '--manifest and --output are required')
            result = import_manifest(args.manifest, args.output, args.repo_root)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
