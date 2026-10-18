"""Bind the selected donor-reuse architecture to real native terminal evidence.

The preserved BM28 and A-chain boards are research fixtures. Their owned net
identities must never be promoted to Motorola connector pin assignments.
"""
from __future__ import annotations

import argparse
import csv
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
    sources, sinks = set(), set()
    for row in rows:
        required = ('net', 'source_connector', 'source_pin', 'sink_connector', 'sink_pin', 'evidence')
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in required):
            raise ValueError('physical terminal map has an unknown identity or missing evidence')
        a = (row['source_connector'], row['source_pin'])
        b = (row['sink_connector'], row['sink_pin'])
        if a in sources or b in sinks:
            raise ValueError('a physical terminal is assigned more than once')
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


def identity_value_known(value):
    return (isinstance(value,str) and bool(value.strip())) or (isinstance(value,list) and bool(value) and all(isinstance(x,str) and bool(x.strip()) for x in value))


def donor_identity_bound(data,root=ROOT):
    if any(not identity_value_known(v) for v in data['donor'].values()):return False
    evidence=data.get('donor_evidence')
    if not isinstance(evidence,dict):return False
    record=evidence_record(evidence.get('identity_record'),'razr-observed-donor-identity-v1',root)
    return record is not None and record.get('donor')==data['donor']


def terminal_evidence_bound(row,data,root=ROOT):
    if row.get('actual_pinmap') is None or not donor_identity_bound(data,root):return False
    record=evidence_record(row.get('terminal_measurement_record'),'razr-physical-terminal-measurement-v1',root)
    if record is None or record.get('interface_id')!=row['id'] or record.get('donor')!=data['donor']:return False
    fields=('net','source_connector','source_pin','sink_connector','sink_pin')
    expected=[{k:r[k] for k in fields} for r in row['actual_pinmap']]
    return record.get('terminal_rows')==expected


def validate_config(data):
    if data.get('schema') != 'razr-product-interfaces-v1':
        raise ValueError('unknown product interface schema')
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
        if row.get('extension_approved') and not terminal_evidence_bound(row,data):
            raise ValueError('extension approval cannot precede a physical terminal map')
    donor = data['donor']
    if data['architecture_decision'].get('actual_donor_selected'):
        if not donor_identity_bound(data):
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
    validate_config(config)
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
