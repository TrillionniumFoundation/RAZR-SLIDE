"""Bounded read-only identity audit; no support/channel/native computation."""
from pathlib import Path
from datetime import datetime, timezone
from fractions import Fraction
import gc
import gzip
import hashlib
import json
import resource
import signal
import time
import traceback

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / 'R7I_EDGE189_SOURCE_READ_PLAN_V1.json'
OUT = ROOT / 'R7I_EDGE189_ORIGINAL_SOURCE_READBACK_V1.json'


def identity(path):
    p = Path(path)
    h = hashlib.sha256()
    with p.open('rb') as stream:
        for b in iter(lambda: stream.read(1048576), b''):
            h.update(b)
    return {'path': str(p.resolve()), 'bytes': p.stat().st_size,
            'sha256': h.hexdigest()}


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    started = time.monotonic()
    plan = json.loads(PLAN.read_text())
    result = {'schema': 'razr-r7i-edge189-original-read-only-readback-v1',
              'recorded_utc': datetime.now(timezone.utc).isoformat(),
              'plan': identity(PLAN), 'source': identity(__file__),
              'completed': False, 'new_support_channel_or_native_operations': 0}
    resource.setrlimit(resource.RLIMIT_AS, (plan['address_space_bytes'],) * 2)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('60 s read-only limit')))
    signal.alarm(plan['wall_seconds'])
    try:
        before = {k: identity(v['path']) for k, v in plan['inputs'].items()}
        for k, observed in before.items():
            expected = plan['inputs'][k]
            require(observed['bytes'] == expected['bytes'] and observed['sha256'] == expected['sha256'],
                    'Registered read-only source identity mismatch: ' + k)
        result['inputs_before'] = before
        metadata = json.loads(Path(plan['inputs']['metadata']['path']).read_text())
        selected = []
        runtimes = []
        source_maps = []
        for label in ('producer', 'reader'):
            with Path(plan['inputs'][label]['path']).open() as f:
                report = json.load(f)
            hits = [entry for entry in report['operands'] if
                    entry['input']['case_id'] == 'case-028' and entry['input']['material_id'] == 3]
            require(len(hits) == 1, 'Exactly one complete original operand required')
            entry = hits[0]
            edge = entry['boundary']['edges'][189]
            require(edge['index'] == 189, 'Original edge enumeration mismatch')
            record = {'input': entry['input'],
                      'complete_boundary_counts': entry['boundary']['counts'],
                      'complete_boundary_canonical_sha256': canonical(entry['boundary']),
                      'complete_original_edge': edge,
                      'complete_original_edge_canonical_sha256': canonical(edge)}
            require(record == metadata['selected_original_record'],
                    'Original selected source differs from metadata: ' + label)
            selected.append(record)
            runtimes.append(report['runtime'])
            source_maps.append(report.get('source_sha256'))
            del report, hits, entry, edge
            gc.collect()
        require(selected[0] == selected[1], 'Complete original selected records differ')
        result['complete_original_selected_record'] = selected[1]
        result['producer_reader_complete_selected_records_equal'] = True
        result['original_runtime_records'] = runtimes
        result['original_source_maps'] = source_maps
        edge = selected[1]['complete_original_edge']
        curve = edge['native_global_curve']
        require(edge['local_curve'] == curve, 'Local/global original Line differ')
        require(curve['type'] == 'GeomAbs_CurveType.GeomAbs_Line', 'Source is not original Line')
        require(edge['location']['identity'] is True and edge['location']['matrix_3x4_exact'] ==
                [['1','0','0','0'],['0','1','0','0'],['0','0','1','0']], 'Nonidentity placement')
        require(Fraction(curve['direction_exact'][2]) != 0, 'Original Vz must be retained')
        for scalar in (curve['first_parameter'], curve['last_parameter'], edge['tolerance']):
            require(float.fromhex(scalar['hex']) == scalar['float'] and
                    Fraction.from_float(scalar['float']) == Fraction(scalar['exact']),
                    'Original exact/float64/hex source encodings disagree')
        result['source_domain_checks'] = {
            'local_global_complete_records_equal': True, 'complete_identity_placement': True,
            'complete_parameter_interval_retained': True, 'nonzero_original_Vz_retained': True,
            'original_float64_hex_and_exact_tolerance_and_parameters_equal': True,
            'orientation': edge['orientation'], 'IsPeriodic': curve['IsPeriodic'],
            'period_field_not_used_as_wrapping_interval': True}
        brep = before['original_BREP']
        require(brep['bytes'] == selected[1]['input']['bytes'] and brep['sha256'] == selected[1]['input']['sha256'],
                'Original BREP does not match source report input')
        probe = json.loads(Path(plan['inputs']['prior_spatial_probe']['path']).read_text())
        full_D = probe['original_full_remaining_D']
        require(full_D == [['0','0'],['0','1/2251799813685248'],['0','0']], 'Full original D differs')
        result['original_full_remaining_D'] = full_D
        with gzip.open(plan['inputs']['original_V6']['path'], 'rt') as f:
            certificate = json.load(f)
        carrier = certificate['boundary']['sources'][0]['pieces'][332]
        require(carrier == metadata['complete_original_inherited_carrier'], 'Full original carrier differs')
        require(carrier['kind'] == 'edge' and carrier['index'] == 189 and carrier['additional_slabs'] == [],
                'Original unchanged empty-slab edge required')
        result['complete_original_carrier'] = carrier
        del certificate
        gc.collect()
        official = []
        for receipt_name, key in [('OFFICIAL_SOURCE_RECEIPT_V1.json','sources'),
                                  ('OFFICIAL_SOURCE_EXTENSION_RECEIPT_V2.json','additional_sources')]:
            receipt = json.loads((ROOT/'official-occt-7.8.1'/receipt_name).read_text())
            for item in receipt[key]:
                data = Path(item['local_path']).read_bytes()
                git_sha = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
                require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
                        and git_sha == item['git_blob_sha'], 'Official source original bytes differ')
                official.append({'path': item['local_path'], 'bytes': len(data),
                                 'sha256': item['sha256'], 'git_blob_sha': git_sha})
        require(len(official) == 11, 'Official primary source count differs')
        result['official_11_files_independently_hash_checked'] = official
        result['official_source_bytes'] = sum(x['bytes'] for x in official)
        after = {k: identity(v['path']) for k, v in plan['inputs'].items()}
        require(before == after, 'Read-only input bytes changed')
        result['all_bound_inputs_unchanged'] = True
        result['geometric_support_values_computed'] = False
        result['native_binary_equivalence_or_error_bound_certified'] = False
        result['completed'] = True
    except BaseException as exc:
        result['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        signal.alarm(0)
        result['wall_seconds'] = time.monotonic() - started
        result['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        with OUT.open('x') as f:
            json.dump(result, f, indent=2, allow_nan=False)
            f.write('\n')
        print(json.dumps({'result': identity(OUT), 'completed': result['completed'],
                          'wall_seconds': result['wall_seconds'], 'peak_RSS_bytes': result['peak_RSS_bytes'],
                          'failure': result.get('failure')}))
    if not result['completed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
