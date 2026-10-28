"""Read existing support certificates without rerunning the producer or native CAD."""
from pathlib import Path
from fractions import Fraction as F
import datetime as dt
import gzip
import hashlib
import json


def identity(path):
    with Path(path).open('rb') as stream:
        return {'bytes': Path(path).stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    root = Path(__file__).resolve().parents[1]
    out = Path(__file__).resolve().parent
    original = root.parent / 'recovered-inputs/RAZR-R3E-COMPLETE-SCIENTIFIC-EVIDENCE-20261027'
    binding_path = original / 'source-and-inputs/R3E_INPUT_BINDING.json'
    binding = json.loads(binding_path.read_text())
    original_frames = {(case['case_id'], row['frame']): row for case in binding['cases'] for row in case.get('tiny_frames', [])}
    materials = {(case['case_id'], item['material_id']): item for case in binding['cases'] for item in case['materials']}
    report_path = root / 'support-v2/report.json'
    report = json.loads(report_path.read_text())
    require(report['execution_completed'] and len(report['frames']) == 16, 'V2 not complete16')
    result = {'schema': 'razr-r4e-independent-actual-support-certificate-readback-v1',
              'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'source_identity': identity(__file__),
              'original_binding_identity': identity(binding_path), 'V2_report_identity': identity(report_path),
              'method': 'Read every existing V2 compressed proof and selected oriented topology; no producer, native geometry, or exhaustive source-support recomputation.',
              'frames': [], 'actual_command_bindings': [], 'original_resource_values': {},
              'native_boundary_semantics_verified': False, 'compiled_rounding_verified': False,
              'physical_qualification': False, 'full_continuous_G2': False, 'expensive_math_reruns': 0}
    TOL = F(1e-7)
    for row in report['frames']:
        key = row['case_id'], row['frame']; prior = original_frames[key]
        proof_path = root / 'support-v2' / row['proof']['path']
        require(identity(proof_path) == {k: row['proof'][k] for k in ('bytes', 'sha256')}, 'Compressed proof identity')
        proof = json.loads(gzip.decompress(proof_path.read_bytes()))
        require((proof['case_id'], proof['frame']) == key, 'Proof frame binding')
        require(proof['full_remaining_displacement_box_exact'] == row['full_remaining_displacement_box_exact'] == prior['full_remaining_displacement_box_exact'], 'Original full interval changed')
        for side, material_key in [('moving', 'moving_saved_material_id'), ('fixed', 'fixed_original_material_id')]:
            require(proof[side + '_input'] == materials[(key[0], prior[material_key])], 'Whole material binding')
        upper = F(row['conditional_complete_material_intersection_upper_exact_mm3'])
        selected = proof['selected_exact_representation_enclosure']
        require(upper == F(selected['exact_intersection_upper_mm3']) == min(F(x['exact_intersection_upper_mm3']) for x in proof['all_registered_candidate_enclosures']), 'Selected original raw upper')
        require(F(selected['original_clearance_threshold_exact_mm3']) == TOL and row['original_clearance_gate_passed'] == (upper <= TOL), 'Original float64 clearance gate')
        inflation = F(row['declared_tolerance_diagnostic_upper_exact_mm3'])
        require(inflation == F(proof['selected_declared_tolerance_diagnostic']['exact_intersection_upper_mm3']) == min(F(x['exact_intersection_upper_mm3']) for x in proof['all_declared_tolerance_candidate_diagnostics']), 'Selected diagnostic upper')
        require(row['declared_tolerance_diagnostic_gate_passed'] == (inflation <= TOL), 'Diagnostic original threshold')
        support_piece_observations = 0
        for direction in proof['complete_support_proofs']:
            for side in ('moving', 'fixed'):
                support = direction[side]; counts = support['counts']
                wanted = {(kind, i) for kind, plural in [('face', 'faces'), ('edge', 'edges'), ('vertex', 'vertices')] for i in range(counts[plural])}
                actual = [(p['kind'], p['index']) for p in support['pieces']]
                require(len(actual) == len(wanted) == support['complete_piece_count'] and set(actual) == wanted, 'Complete support piece set')
                require(support['input'] == proof[side + '_input'], 'Support material identity')
                ranges = [tuple(map(F, p['support_exact'])) for p in support['pieces']]
                require(all(lo <= hi for lo, hi in ranges), 'Unordered support interval')
                require(tuple(map(F, support['support_exact'])) == (min(x[0] for x in ranges), max(x[1] for x in ranges)), 'Whole support aggregation')
                support_piece_observations += len(actual)
        volumes = []
        for label, expected in [('exact_representation_enclosure_topology', upper), ('declared_tolerance_enclosure_topology', inflation)]:
            topology = proof[label]
            require(topology['valid_set'], 'Selected topology flagged invalid')
            if topology['kind'] == 'exact_rational_closed_parallelepiped':
                points = [tuple(map(F, p)) for p in topology['vertices_exact']]
                triangles = topology['outward_triangles']
                require(len(points) == 8 and len(triangles) == 12, 'Selected cell counts')
                directed_edges = {}
                total = F(0)
                for a, b, c in triangles:
                    u, v, w = points[a], points[b], points[c]
                    total += sum(u[i] * (v[(i+1)%3]*w[(i+2)%3] - v[(i+2)%3]*w[(i+1)%3]) for i in range(3)) / 6
                    for x, y in [(a,b), (b,c), (c,a)]:directed_edges[x,y] = directed_edges.get((x,y),0)+1
                require(all(n == 1 and directed_edges.get((b,a)) == 1 for (a,b), n in directed_edges.items()), 'Selected oriented incidence')
                require(8-len(directed_edges)//2+12 == 2 and total == expected > 0, 'Selected directed volume or Euler')
                volumes.append(str(total))
            else:
                require(expected == 0 and F(topology['oriented_volume_exact']) == 0, 'Degenerate topology volume')
                volumes.append('0')
        result['frames'].append({'case_id': key[0], 'frame': key[1], 'proof_identity': identity(proof_path),
            'full_original_displacement_and_material_binding': True, 'complete_piece_set_observations': support_piece_observations,
            'selected_topology_and_directed_volumes_exact': volumes, 'raw_upper_exact_mm3': str(upper),
            'original_gate_pass': upper <= TOL, 'diagnostic_gate_pass': inflation <= TOL,
            'native_boundary_semantics_remains_a_premise': row['native_boundary_semantics_remains_a_premise']})
    for version in (2,3):
        contract_path = root / f'R4E_SUPPORT_SUPERVISION_V{version}_OWNED.json'
        controller_path = root / f'support-v{version}-supervision/controller.json'
        supervision = json.loads(contract_path.read_text())
        controller_bytes = controller_path.read_bytes(); controller = json.loads(controller_bytes)
        argv = controller['command']
        def argument(option):
            locations = [i for i, x in enumerate(argv) if x == option]
            require(len(locations) == 1, 'Actual command option count')
            return Path(argv[locations[0]+1]).resolve()
        require(argument('--supervision-contract') == contract_path, 'Actual supervision contract path')
        require(identity(contract_path)['sha256'] == controller['contract_sha256'], 'Actual supervision SHA')
        require(identity(argument('--contract'))['sha256'] == supervision['registered_math_contract_sha256'], 'Actual mathematical contract SHA')
        require(argument('--output') == Path(supervision['worker_output_directory']).resolve(), 'Actual output binding')
        require(identity(supervision['worker']['path'])['sha256'] == supervision['worker']['sha256'], 'Actual mathematical worker identity')
        required = {'wall_seconds':600, 'RSS_limit_bytes':805306368, 'shared_ceiling_bytes':7301444403,
                    'disk_floor_bytes':104857600, 'maximum_output_bytes':41943040, 'metadata_margin_bytes':4194304}
        require(all(supervision[k] == value for k,value in required.items()), 'Original numeric gate changed')
        result['original_resource_values'] = required
        entry_path = root / f'support-v{version}-supervision/entry-receipt.json'
        entry = json.loads(entry_path.read_text()) if entry_path.exists() else None
        math_path = root / f'support-v{version}/report.json'
        math_bytes = math_path.read_bytes(); math = json.loads(math_bytes)
        row = {'version': version, 'command': argv, 'all_registered_paths_and_SHA_match': True,
               'controller_identity_as_read': {'bytes':len(controller_bytes), 'sha256':hashlib.sha256(controller_bytes).hexdigest()},
               'controller_completed_as_read': controller['completed'], 'worker_exit_code_as_read':controller['worker_exit_code'],
               'resource_stop_as_read':controller['resource_stop'], 'entry_receipt_as_read':entry,
               'mathematical_report_identity_as_read': {'bytes':len(math_bytes),'sha256':hashlib.sha256(math_bytes).hexdigest()},
               'mathematical_execution_completed_as_read': math['execution_completed'],
               'mathematical_frames_completed_as_read':len(math['frames']),
               'mathematical_progress_as_read':math.get('current_frame_progress'),
               'mathematical_failure_as_read':math.get('failure'),
               'actual_output_bytes_as_read':sum(p.stat().st_size for p in Path(supervision['worker_output_directory']).rglob('*') if p.is_file())}
        result['actual_command_bindings'].append(row)
        snapshots = out / 'receipt-snapshots'; snapshots.mkdir(exist_ok=True)
        (snapshots / f'support-v{version}-controller-as-read.json').write_bytes(controller_bytes)
        (snapshots / f'support-v{version}-report-as-read.json').write_bytes(math_bytes)
        if version == 2:
            require(controller['completed'] and controller['worker_exit_code'] == 0 and controller['resource_stop'] is None and entry['completed'], 'V2 supervised completion')
            require(entry['peak_RSS_bytes'] <= required['RSS_limit_bytes'] and not entry['native_geometry_imported'], 'V2 worker peak/native claim')
        for key in ('native_material_boundary_semantics_verified','compiled_curve_or_transform_rounding_verified','full_continuous_G2','all_blockers_closed'):
            require(math[key] is False, 'Qualification scope incorrectly promoted')
    result['V2_raw_conditional_passes'] = sum(x['original_gate_pass'] for x in result['frames'])
    result['V2_raw_conditional_failures'] = 16-result['V2_raw_conditional_passes']
    result['V2_declared_diagnostic_passes'] = sum(x['diagnostic_gate_pass'] for x in result['frames'])
    require((result['V2_raw_conditional_passes'],result['V2_raw_conditional_failures'],result['V2_declared_diagnostic_passes']) == (4,12,0), 'V2 exact result summary')
    result['completed'] = True
    destination = out / 'R4E_EXISTING_SUPPORT_CERTIFICATES_INDEPENDENT_READBACK.json'
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'report':str(destination),'identity':identity(destination),'completed':True,'frames_read':len(result['frames']),
                      'V2_pass_fail_diagnostic':[4,12,0], 'V3_completed_as_read':result['actual_command_bindings'][1]['controller_completed_as_read']}))


if __name__ == '__main__':
    main()
