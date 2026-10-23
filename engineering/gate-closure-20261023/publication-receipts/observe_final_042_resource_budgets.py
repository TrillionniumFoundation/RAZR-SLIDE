"""Read each frozen supervisor's actual resource formula without spawning workers."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import os
import resource

WORK = Path('/workspace/scratch/95cd2986fdf2')
OUT = WORK / 'final042-resource-observation.json'


def function(filename, name, extra=None):
    path = WORK / filename
    text = path.read_text()
    original = ast.parse(text, filename=str(path))
    selected = next(node for node in original.body
                    if isinstance(node, ast.FunctionDef) and node.name == name)
    tree = ast.Module(body=[selected], type_ignores=[])
    namespace = {'Path': Path, 'os': os, 'resource': resource}
    namespace.update(extra or {})
    exec(compile(tree, str(path), 'exec'), namespace)
    return namespace[name], {
        'source': str(path), 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'function': name, 'execution_scope': 'only the original pure resource-reading function; no module entrypoint or native import',
    }


def main():
    assert not OUT.exists(), 'one new observation, no polling loop'
    sources = []
    slide_fn, identity = function('g2_slide_r3/verify_slide_native.py', 'resource_snapshot')
    sources.append(identity)
    slide = slide_fn('/tmp')
    seat_fn, identity = function('input_recovery/g2_seating_v3/supervise_seating_native.py', 'snapshot')
    sources.append(identity)
    seat = seat_fn(Path('/tmp'))
    key_fn, identity = function('gates_audit/dev/key-endpoint-v4/run_key_endpoint_trials.py', 'resources')
    sources.append(identity)
    key = key_fn(WORK)
    fe_fn, identity = function(
        'input_recovery/fe_probe_prepared-v1/prepared-source-bytes/02-supervise_probe_diagnosis.py',
        'memory', {'CGROUP': Path('/sys/fs/cgroup')})
    sources.append(identity)
    fe = fe_fn()
    fs = os.statvfs('/tmp/razr-fe-20261023')
    fe['f_bavail_bytes'] = fs.f_bavail * fs.f_frsize
    limit = int(6.8 * 2**30)
    evaluations = {
        'SLIDE_r3': {'snapshot': slide, 'startup_disk_requirement_bytes': 200 * 2**20,
                     'startup_memory_increment_bytes': 1536 * 2**20,
                     'disk_pass': slide['f_bavail_bytes'] >= 200 * 2**20,
                     'memory_pass': slide['estimated_unreclaimable_bytes'] + 1536 * 2**20 <= limit},
        'SEATING_r3': {'snapshot': seat, 'startup_disk_requirement_bytes': 400 * 2**20,
                       'startup_memory_increment_bytes': 1536 * 2**20,
                       'disk_pass': seat['f_bavail_bytes'] >= 400 * 2**20,
                       'memory_pass': seat['estimated_unreclaimable_bytes'] + 1536 * 2**20 <= limit},
        'KEY_v4': {'snapshot': key, 'startup_disk_requirement_bytes': 256 * 2**20,
                   'startup_effective_headroom_requirement_bytes': 2 * 2**30,
                   'disk_pass': key['writeable_disk_bytes'] >= 256 * 2**20,
                   'memory_pass': key['effective_memory_headroom_bytes'] >= 2 * 2**30,
                   'runtime_shared_memory_below_original_limit': key['shared_unreclaimable_memory_bytes'] <= limit},
        'panel_probe_only': {'snapshot': fe, 'startup_disk_requirement_bytes': 600 * 2**20,
                             'startup_memory_increment_bytes': int(2.9 * 2**30),
                             'disk_pass': fe['f_bavail_bytes'] >= 600 * 2**20,
                             'memory_pass': fe['estimated_unreclaimable_bytes'] + int(2.9 * 2**30) <= limit},
    }
    for entry in evaluations.values():
        entry['startup_resource_conditions_satisfied_at_observation'] = entry['disk_pass'] and entry['memory_pass']
    receipt = {
        'schema': 'razr-fresh-frozen-formula-resource-observation-v1',
        'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_functional_commit': '042b768903cccbd7a0995317c8598401e0318e2a',
        'observer_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_functions': sources, 'evaluations': evaluations,
        'original_resource_thresholds_changed': False,
        'uses_ordinary_available_disk_blocks': True,
        'workers_started_by_this_observation': 0,
        'native_or_FE_executed': False,
        'is_a_supervisor_invocation_or_source_environment_preflight': False,
        'scope': 'One read-only observation of exact frozen resource formulas, not permission to bypass a later supervisor gate. If any task starts later its original supervisor must recheck all original source/environment/resource conditions.',
    }
    OUT.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'observed_at_utc': receipt['observed_at_utc'], 'evaluations': evaluations}))


if __name__ == '__main__':
    main()
