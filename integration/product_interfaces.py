"""Bind the selected donor-reuse architecture to real native terminal evidence.

The preserved BM28 and A-chain boards are research fixtures. Their owned net
identities must never be promoted to Motorola connector pin assignments.
"""
from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'design/product_interfaces.json'
POWER = Path('engineering/power-chain-pcba-20261013-r5')
ENDPOINT = Path('engineering/endpoint-pcba-design-20261013-r2')
STAGES = {
    'A1': ('A_PACK_P', 'A_MID_P', 'A_PACK_N'),
    'A2': ('A_MID_P', 'A_TX_P', 'A_PACK_N'),
    'B1': ('A_RX_P', 'A_RX_MID_P', 'B_SYS_N'),
    'B2': ('A_RX_MID_P', 'SYS_B_P', 'B_SYS_N'),
}
INTERFACES = {'MAIN_DISPLAY', 'MAIN_TOUCH', 'A_PROTECTED_PACK',
              'B_PROTECTED_PACK', 'A_CHARGE', 'B_CHARGE', 'USB_DATA_CROSS',
              'USB_POWER', 'CAMERAS', 'RF_ANTENNA', 'AUDIO_SENSORS', 'MOTION_STATE'}
# The required identity inventory belongs to this schema, not to a mutable
# configuration or import manifest. Unknown observations retain a null value;
# deleting their keys must never make an incomplete donor appear complete.
DONOR_FIELDS = ('model', 'region', 'mainboard_revision', 'runtime_panel_id',
                'display_module_part', 'display_module_revision',
                'touch_revision', 'pack_A_label', 'pack_B_label',
                'USB_roles', 'USB_version_rate')
PHYSICAL_DONOR_FIELDS = frozenset({'mainboard_revision', 'display_module_part',
    'display_module_revision', 'touch_revision', 'pack_A_label', 'pack_B_label'})


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_config(path=None):
    data = json.loads(Path(path or CONFIG).read_text())
    validate_config(data)
    return data


def positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(name + ' must be finite and positive')
    return float(value)


def validate_pinmap(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('a physical pin map must contain terminal rows')
    sources, sinks, terminal_nets = set(), set(), {}
    for row in rows:
        required = ('net', 'source_connector', 'source_pin', 'sink_connector', 'sink_pin', 'evidence')
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in required):
            raise ValueError('physical terminal map has an unknown identity or missing evidence')
        a = (row['source_connector'], row['source_pin'])
        b = (row['sink_connector'], row['sink_pin'])
        if a in sources or b in sinks:
            raise ValueError('a physical terminal is assigned more than once')
        if a == b:
            raise ValueError('a terminal map cannot connect a physical pin to itself')
        for terminal in (a, b):
            if terminal in terminal_nets and terminal_nets[terminal] != row['net']:
                raise ValueError('a physical terminal has contradictory net identities')
            terminal_nets[terminal] = row['net']
        if row.get('identity_kind') != 'observed_physical_terminal':
            raise ValueError('software configuration or owned coupon IDs are not OEM terminals')
        sources.add(a)
        sinks.add(b)


def evidence_record(reference,schema,root=ROOT):
    """Read and hash-bind an existing measurement record; declarations are not records."""
    if not isinstance(reference,dict):return None
    name,digest=reference.get('path'),reference.get('sha256')
    if not isinstance(name,str) or not isinstance(digest,str) or not re.fullmatch(r'[a-f0-9]{64}',digest):return None
    root=Path(root).resolve();path=(root/name).resolve()
    if root not in path.parents or not path.is_file() or sha(path)!=digest:return None
    try:record=json.loads(path.read_text())
    except (ValueError,OSError):return None
    if not isinstance(record,dict) or record.get('schema')!=schema:return None
    if any(not isinstance(record.get(k),str) or not record[k].strip() for k in ('recorded_at_utc','measurement_method','operator_or_instrument')):return None
    observations=record.get('observations')
    if not isinstance(observations,list) or not observations:return None
    for source in observations:
        if not isinstance(source,dict) or not isinstance(source.get('path'),str):return None
        observation=(root/source['path']).resolve()
        if root not in observation.parents or not observation.is_file() or sha(observation)!=source.get('sha256'):return None
    return record


def interface_contract_sha256(data):
    """Hash design semantics without circular evidence pointers or observations.

    Exact source JSON is archived by the importer too. Donor values and terminal
    rows are compared directly to their records, not silently removed from checks.
    """
    value = copy.deepcopy(data)
    value.pop('donor_evidence', None)
    value.pop('donor', None)
    value.get('architecture_decision', {}).pop('actual_donor_selected', None)
    for row in value.get('interfaces', []):
        for key in ('actual_pinmap', 'terminal_measurement_record', 'extension_approved'):
            row.pop(key, None)
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def observed_record_compatible(record, data, root=ROOT):
    """A versioned physical record must identify this specimen and design inputs."""
    if record.get('is_template') is not False or record.get('physical_execution_occurred') is not True:
        return False
    if not isinstance(record.get('specimen_id'), str) or not record['specimen_id'].strip():
        return False
    try:
        stamp = dt.datetime.fromisoformat(record['recorded_at_utc'].replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            return False
        binding = record['design_binding']
        if not re.fullmatch(r'[a-f0-9]{40}', binding.get('git_commit', '')):
            return False
        files = binding['files_sha256']
        if any(not isinstance(files.get(name), str) or not re.fullmatch(r'[a-f0-9]{64}', files[name])
               for name in ('design/product_geometry.json', 'design/product_interfaces.json')):
            return False
        geometry = 'design/product_geometry.json'
        if files.get(geometry) != sha(Path(root)/geometry):
            return False
        if binding.get('interface_contract_sha256') != interface_contract_sha256(data):
            return False
        if any(row.get('kind') not in ('manufacturer_document', 'design_input')
               and row.get('specimen_id') != record['specimen_id'] for row in record['observations']):
            return False
        # The exact JSON used for each observation is retained, even if adding
        # evidence pointers later changes the current interface JSON bytes.
        inputs = {row.get('input_design_path'): row.get('sha256')
                  for row in record['observations'] if row.get('input_design_path')}
        if not all(inputs.get(name) == files.get(name)
                   for name in ('design/product_geometry.json', 'design/product_interfaces.json')):
            return False
        original = next(row for row in record['observations']
                        if row.get('input_design_path') == 'design/product_interfaces.json')
        archived = json.loads((Path(root)/original['path']).read_text())
        return interface_contract_sha256(archived) == binding['interface_contract_sha256']
    except (KeyError, TypeError, ValueError, OSError):
        return False


def observed_field_bound(field, observations, physical_only=False):
    """Require an observation of the specimen for a physical identity or row.

    OEM documents can supply specifications and corroborate a measured/labelled
    part. A document alone does not establish that this specimen contains it;
    regional service lists must not become an observed physical inventory.
    The importer/record validator separately checks physical-source specimen IDs.
    """
    if not isinstance(field, dict) or not identity_value_known(field.get('value')):
        return False
    if not isinstance(field.get('locator'), str) or not field['locator'].strip():
        return False
    ids = field.get('observation_ids')
    if not isinstance(ids, list) or not ids or not all(isinstance(key, str) for key in ids) or len(ids) != len(set(ids)):
        return False
    physical_kinds = {'physical_label', 'physical_measurement'}
    kinds = physical_kinds | {'manufacturer_document'}
    if not physical_only:
        kinds |= {'device_readback', 'instrument_log'}
    if not all(key in observations and observations[key].get('kind') in kinds for key in ids):
        return False
    return not physical_only or any(observations[key].get('kind') in physical_kinds for key in ids)


def readback_trace_consistent(readback):
    """Check that declared properties and final connection exist in the raw trace."""
    digest = readback.get('selected_serial_sha256', '')
    if not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest):
        return False
    collector = readback.get('collector_sha256')
    if not isinstance(collector, str) or not re.fullmatch(r'[a-f0-9]{64}', collector):
        return False
    records, properties = readback.get('command_records'), readback.get('properties')
    if not isinstance(records, list) or not records or not isinstance(properties, dict):
        return False
    selected = 'sha256:'+digest
    seen = {}
    for row in records:
        if not isinstance(row, dict) or not isinstance(row.get('stdout_text'), str):
            return False
        args = row.get('args', [])
        if not isinstance(args, list):
            return False
        if row.get('returncode') == 0 and len(args) == 5 and args[:4] == ['-s', selected, 'shell', 'getprop']:
            seen[args[4]] = row.get('stdout_text', '').strip() or None
    if not properties.get('ro.product.model') or not properties.get('ro.build.fingerprint'):
        return False
    if any(key not in seen or seen[key] != value for key, value in properties.items()):
        return False
    last = records[-1]
    inventory = [line.split() for line in last.get('stdout_text', '').splitlines()]
    return (last.get('args') == ['devices', '-l'] and last.get('returncode') == 0
            and any(len(row) >= 2 and row[:2] == [selected, 'device'] for row in inventory))


def identity_value_known(value):
    return (isinstance(value,str) and bool(value.strip())) or (isinstance(value,list) and bool(value) and all(isinstance(x,str) and bool(x.strip()) for x in value))


def validate_donor_fields(donor):
    if not isinstance(donor, dict) or set(donor) != set(DONOR_FIELDS):
        raise ValueError('donor identity must retain the complete schema-owned field inventory')
    if any(value is not None and not identity_value_known(value) for value in donor.values()):
        raise ValueError('donor identity values must be observed text or null for unknown')
    return donor


def donor_identity_bound(data,root=ROOT):
    try:
        donor = validate_donor_fields(data.get('donor'))
    except ValueError:
        return False
    if any(not identity_value_known(v) for v in donor.values()):return False
    evidence=data.get('donor_evidence')
    if not isinstance(evidence,dict):return False
    # v1 is still readable with evidence_record(..., v1), but has no specimen or
    # design binding and cannot establish a new physical selection.
    record=evidence_record(evidence.get('identity_record'),'razr-observed-donor-identity-v2',root)
    if record is None or record.get('donor') != data['donor'] or not observed_record_compatible(record, data, root):
        return False
    observations = {r.get('id'): r for r in record['observations']}
    if len(observations) != len(record['observations']):
        return False
    fields = record.get('field_evidence', {})
    if not isinstance(fields, dict):
        return False
    if any(not observed_field_bound(fields.get(key), observations, key in PHYSICAL_DONOR_FIELDS)
           or fields[key]['value'] != value for key, value in data['donor'].items()):
        return False
    capture = next((r for r in record['observations']
                    if r.get('id') == record.get('device_readback_observation')), None)
    if capture is None or capture.get('kind') != 'device_readback':
        return False
    try:
        readback = json.loads((Path(root)/capture['path']).read_text())
    except (ValueError, OSError):
        return False
    inventory = record.get('part_inventory')
    if not isinstance(inventory, list) or not inventory:
        return False
    part_ids, roles = set(), set()
    for part in inventory:
        if (not isinstance(part, dict) or not isinstance(part.get('part_id'), str) or not part['part_id'].strip()
            or part['part_id'] in part_ids or not observed_field_bound(part.get('label'), observations, True)):
            return False
        part_ids.add(part['part_id'])
        declared = part.get('roles', [part.get('role')])
        if not isinstance(declared, list) or not declared or not all(isinstance(r, str) and r for r in declared):
            return False
        roles.update(declared)
    if not {'mainboard', 'display', 'touch', 'COF', 'pack_A', 'pack_B', 'USB_port_board'} <= roles:
        return False
    return (readback.get('schema') == 'razr-donor-readback-v2'
            and readback_trace_consistent(readback)
            and readback.get('specimen_id') == record['specimen_id']
            and readback.get('selected_donor_connected') is True
            and readback.get('software_identity_complete') is True
            and readback.get('design_inputs_unchanged') is True
            and readback.get('selected_serial_sha256') == record.get('selected_serial_sha256')
            and readback.get('properties', {}).get('ro.product.model') == data['donor']['model']
            and readback.get('design_binding', {}).get('files_sha256') == record['design_binding']['files_sha256'])


def terminal_evidence_bound(row,data,root=ROOT):
    if row.get('actual_pinmap') is None or not donor_identity_bound(data,root):return False
    record=evidence_record(row.get('terminal_measurement_record'),'razr-physical-terminal-measurement-v2',root)
    identity=evidence_record(data['donor_evidence']['identity_record'],'razr-observed-donor-identity-v2',root)
    if (record is None or record.get('interface_id')!=row['id'] or record.get('donor')!=data['donor']
        or not observed_record_compatible(record, data, root)
        or record.get('specimen_id') != identity.get('specimen_id')
        or record.get('donor_identity_record') != data['donor_evidence']['identity_record']):return False
    fields=('net','source_connector','source_pin','sink_connector','sink_pin')
    expected=[{k:r[k] for k in fields} for r in row['actual_pinmap']]
    observed = record.get('terminal_rows', [])
    if not isinstance(observed, list) or [{k:r.get(k) for k in fields} for r in observed] != expected:
        return False
    observations = {r.get('id'): r for r in record['observations']}
    connectors = record.get('connectors', {})
    if not isinstance(connectors, dict) or not connectors:
        return False
    parts = {part['part_id'] for part in identity['part_inventory']}
    used = {name: set() for name in connectors}
    for terminal in observed:
        if not observed_field_bound({'value': terminal.get('net'),
                                     'locator': terminal.get('locator'),
                                     'observation_ids': terminal.get('observation_ids')}, observations, True):
            return False
        for end in ('source', 'sink'):
            connector = connectors.get(terminal[end+'_connector'], {})
            if (connector.get('part_id') not in parts
                or terminal[end+'_pin'] not in connector.get('observed_pins', [])
                or not observed_field_bound(connector.get('label'), observations, True)):
                return False
            used[terminal[end+'_connector']].add(terminal[end+'_pin'])
    if any(set(connector.get('observed_pins', [])) != used[name]
           for name, connector in connectors.items()):
        return False
    return True


def validate_config(data, root=ROOT):
    if data.get('schema') != 'razr-product-interfaces-v1':
        raise ValueError('unknown product interface schema')
    validate_donor_fields(data.get('donor'))
    mode = data.get('architecture_decision', {}).get('mode')
    if mode != 'retain_donor_electronics_first':
        raise ValueError('this implementation implements the donor-reuse architecture')
    constraints = data['constraints']
    expected = {'equal_finished_cabins': True, 'single_flexible_display': True,
                'independent_rear_display': False, 'planar_display_storage': True,
                'B_slide_mm': 79.75, 'B_descent_mm': 8.2,
                'A_larger_battery_priority': True, 'system_capacity_target_mAh': 4700,
                'USB_continuous_copper_through_motion': True}
    if constraints != expected:
        raise ValueError('fixed product constraints changed')
    ids = [x.get('id') for x in data['interfaces']]
    if len(ids) != len(set(ids)) or set(ids) != INTERFACES:
        raise ValueError('missing or repeated complete product interface')
    for row in data['interfaces']:
        if row['id'] == 'USB_DATA_CROSS' and row['cabin_or_route'] != 'cross':
            raise ValueError('the required cross-cabin copper USB path cannot disappear')
        if row.get('actual_pinmap') is not None:
            validate_pinmap(row['actual_pinmap'])
        if row.get('extension_approved') and not terminal_evidence_bound(row,data,root):
            raise ValueError('extension approval cannot precede a physical terminal map')
    donor = data['donor']
    if data['architecture_decision'].get('actual_donor_selected'):
        if not donor_identity_bound(data,root):
            raise ValueError('selected donor needs an actual identified device and evidence')
    coupon = data['coupon']
    if coupon.get('product_signal_or_power_assignment') is not None:
        raise ValueError('C01-C26 research coupon cannot acquire inferred OEM assignments')
    for key in ('width_mm', 'length_mm', 'free_length_mm', 'trace_width_mm', 'trace_pitch_mm'):
        positive(coupon[key], 'coupon.' + key)
    if coupon['trace_count'] != 26:
        raise ValueError('the frozen BM28 fixture has 26 independent continuity identities')
    return data


def sexp(text):
    stack = [[]]
    for token in re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', text):
        if token == '(':
            child = []
            stack[-1].append(child)
            stack.append(child)
        elif token == ')':
            if len(stack) == 1:
                raise ValueError('unmatched S-expression close')
            stack.pop()
        else:
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    if len(stack) != 1 or len(stack[0]) != 1:
        raise ValueError('invalid S-expression root')
    return stack[0][0]


def children(node, kind):
    return [v for v in node if isinstance(v, list) and v and v[0] == kind]


def pcb_pins(payload):
    board = sexp(payload.decode())
    if board[0] != 'kicad_pcb':
        raise ValueError('not a native KiCad PCB')
    pins = {}
    pad_count = 0
    for footprint in children(board, 'footprint'):
        ref = next(x[2] for x in children(footprint, 'fp_text') if x[1] == 'reference')
        for pad in children(footprint, 'pad'):
            # Mechanical NPTH has no electrical pin identity.
            if pad[1] == '':
                continue
            pad_count += 1
            n = children(pad, 'net')
            name = n[0][2].removeprefix('/') if n else None
            key = (ref, pad[1])
            if key in pins and pins[key] != name:
                raise ValueError('split copper lands disagree on their terminal net')
            pins[key] = name
    return pins, {'copper_pad_objects': pad_count,
                  'track_segments': len(children(board, 'segment')),
                  'vias': len(children(board, 'via'))}


def native_xml_pins(payload):
    root = ET.fromstring(payload)
    pins = {}
    components = [x.get('ref') for x in root.findall('./components/comp')]
    if len(components) != len(set(components)):
        raise ValueError('duplicate native component')
    for net in root.findall('./nets/net'):
        nodes = net.findall('node')
        for node in nodes:
            key = (node.get('ref'), node.get('pin'))
            if key in pins:
                raise ValueError('duplicate native pin')
            value = net.get('name').removeprefix('/')
            if 'no_connect' in node.get('pintype', ''):
                if len(nodes) != 1 or not value.startswith('unconnected-'):
                    raise ValueError('a marked no-connect is actually connected')
                value = None
            pins[key] = value
    return pins, components


def verified_sources(config, root=ROOT):
    result = {}
    root = Path(root).resolve()
    for name, expected in config['frozen_native_sources'].items():
        path = (root / name).resolve()
        if root not in path.parents:
            raise ValueError('native source escaped repository')
        got = sha(path)
        if got != expected:
            raise ValueError('frozen native input changed: ' + name)
        result[name] = got
    return result


def bind_power_chain(root=ROOT):
    root = Path(root)
    boards = {}
    for stage, (vin, vout, ret) in STAGES.items():
        folder = root / POWER
        native, refs = native_xml_pins((folder/'native_pocket_v2/modules'/stage/'native.xml').read_bytes())
        copper, geometry = pcb_pins((folder/'modules'/stage/'cut_reference.kicad_pcb').read_bytes())
        if native != copper:
            raise ValueError('complete PCB/XML net mismatch at ' + stage)
        if (native.get(('J1', '1')), native.get(('J2', '1')),
            native.get(('J1', '2')), native.get(('J2', '2'))) != (vin, vout, ret, ret):
            raise ValueError('stage role changed')
        boards[stage] = {'role': 'A_source_cut' if stage.startswith('A') else 'A_chain_receiver_cut',
                         'components': len(refs), 'unique_pins': len(native),
                         'input': vin, 'output': vout, 'return': ret, **geometry}
    from harness_interface import check_harness, parse_native
    checked = {stage: parse_native((root/POWER/'native_pocket_v2/modules'/stage/'native.xml').read_bytes(), stage)
               for stage in STAGES}
    with (root/POWER/'harness_terminal_schedule.csv').open(newline='') as stream:
        harness = list(csv.DictReader(stream))
    binding = check_harness(harness, checked)
    return {'boards': boards, 'complete_native_pin_comparison': True,
            'native_unique_pins': sum(v['unique_pins'] for v in boards.values()),
            'harness': binding, 'B_battery_or_charger_implemented': False,
            'new_product_power_circuit': False}


def bind_endpoint(root=ROOT):
    folder = Path(root) / ENDPOINT
    mapping = json.loads((folder/'mating_site_map.json').read_text())
    if mapping.get('supplier_pin1') is not None or not mapping.get('coordinate_IDs_owned'):
        raise ValueError('owned endpoint identities were promoted to vendor pin numbers')
    pins = {side: pcb_pins((folder/f'endpoint_{side}.kicad_pcb').read_bytes())[0] for side in ('DP', 'DS')}
    rows = mapping['mapping']
    if len(rows) != 26 or {x['net'] for x in rows} != {f'C{i:02}' for i in range(1, 27)}:
        raise ValueError('incomplete BM28 mating map')
    for row in rows:
        for side in ('DP', 'DS'):
            if pins[side].get(('J1', row[side+'_site'])) != row['net']:
                raise ValueError('native connector copper contradicts mating map')
            # TP hole pins use the owned site name in the frozen PCB.
            tp = [(key, net) for key, net in pins[side].items() if key[0] == row[side+'_testpoint']]
            if len(tp) != 1 or tp[0][1] != row['net']:
                raise ValueError('native probe copper contradicts mating map')
    return {'connector_DP': 'BM28B0.6-24DP/2-0.35V(53)',
            'connector_DS': 'BM28B0.6-24DS/2-0.35V(53)',
            'mapping': rows, 'electrical_net_count': 26,
            'OEM_terminal_map': None, 'mating_verified_on_physical_sample': False,
            'orientation': mapping['chosen_transform_DP_local_to_DS_global']}


def cell_budget(data):
    keys = ('A_mAh', 'B_mAh', 'A_nominal_V', 'B_nominal_V')
    missing = [k for k in keys if data[k] is None]
    if missing:
        return {'known': False, 'missing': missing, 'sum_of_cell_label_mAh': None, 'same_reference_voltage_equivalent_mAh': None, 'energy_Wh': None, 'actual_system_terminal_capacity_verified': False, 'actual_pack_topology': None}
    v = {k: positive(data[k], k) for k in keys}
    energy = (v['A_mAh']*v['A_nominal_V'] + v['B_mAh']*v['B_nominal_V'])/1000
    same_voltage = math.isclose(v['A_nominal_V'], v['B_nominal_V'], rel_tol=1e-9, abs_tol=0)
    total = v['A_mAh'] + v['B_mAh'] if same_voltage else None
    return {'known': True, 'same_nominal_voltage': same_voltage, 'sum_of_cell_label_mAh': v['A_mAh']+v['B_mAh'], 'same_reference_voltage_equivalent_mAh': total,
            'energy_Wh': energy, 'A_larger_capacity': v['A_mAh'] > v['B_mAh'],
            'label_sum_target_comparison_at_common_voltage': total >= 4700 if total is not None else None, 'actual_system_terminal_capacity_verified': False, 'actual_pack_topology': None, 'system_terminal_capacity_mAh': None}


def inspect(config=None, root=ROOT):
    config = config or load_config()
    validate_config(config, root)
    before = verified_sources(config, root)
    power, endpoint = bind_power_chain(root), bind_endpoint(root)
    interfaces = []
    for row in config['interfaces']:
        interfaces.append({**row, 'declared_terminal_map': row['actual_pinmap'] is not None, 'physical_terminals_bound': terminal_evidence_bound(row,config,root)})
    if verified_sources(config, root) != before:
        raise ValueError('native sources changed during inspection')
    return {'schema': 'razr-product-interface-binding-v1',
            'architecture_decision': config['architecture_decision'],
            'source_sha256': sha(Path(__file__)), 'native_source_sha256': before,
            'donor': config['donor'], 'donor_evidence': config['donor_evidence'],
            'interfaces': interfaces, 'cell_budget': cell_budget(config['cell_budget']),
            'actual_A_chain': power, 'static_endpoint_fixture': endpoint,
            'product_interface_count': len(interfaces),
            'declared_terminal_maps': sum(x['declared_terminal_map'] for x in interfaces),
            'product_interfaces_physically_bound': sum(x['physical_terminals_bound'] for x in interfaces),
            'product_power_or_display_connected': False,
            'physical_qualification': False,
            'candidate_go': False, 'manufacturing_go': False}


def export(config_path, output, root=ROOT):
    data = load_config(config_path)
    report = inspect(data, root)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output/'interface-binding.json').write_text(json.dumps(report, indent=2)+'\n')
    fields = ('id', 'source', 'sink', 'decision', 'function', 'cabin_or_route', 'proposed_source_location', 'proposed_sink_location', 'design_routing_decision', 'physical_terminals_bound')
    with (output/'product-interface-schedule.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: row[k] for k in fields} for row in report['interfaces'])
    rows = []
    for row in report['static_endpoint_fixture']['mapping']:
        for end in ('A', 'B'):
            rows.append({'end': end, 'coupon_pad': row['net'],
                         'mini_DS_probe': 'TP'+row['net'][1:], 'frozen_R2_DS_probe': row['DS_testpoint'],
                         'static_DS_connector_site': row['DS_site'],
                         'mated_DP_connector_site': row['DP_site'],
                         'mini_DP_probe': 'TP'+row['net'][1:], 'frozen_R2_DP_probe': row['DP_testpoint'],
                         'identity': 'owned continuity only', 'OEM_signal': ''})
    with (output/'coupon-static-terminal-schedule.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=CONFIG)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = export(args.config, args.output)
    print(json.dumps({'native_pins_compared': result['actual_A_chain']['native_unique_pins'],
                      'BM28_continuity_nets': result['static_endpoint_fixture']['electrical_net_count'],
                      'product_interfaces_bound': result['product_interfaces_physically_bound'],
                      'candidate_go': result['candidate_go']}))
