"""Read and register the frozen source/inputs and original local resource gates."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
SOURCE = ROOT / 'source-v9'
OLD = WORKSPACE / 'r7-recovery/v7/r5-local-v7/input-snapshot-v1'
HERE = ROOT / 'local-v9'


def ident(path):
    path = path.resolve()
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return {'path':str(path), 'bytes':path.stat().st_size, 'sha256':h.hexdigest()}


def same(a, b):
    return all(a[k] == b[k] for k in ('bytes', 'sha256'))


def main():
    started = time.monotonic()
    HERE.mkdir(exist_ok=False)
    source_lock = SOURCE / 'R7E_PORTABLE_SOURCE_LOCK_V9.json'
    lock = json.loads(source_lock.read_text())
    assert ident(source_lock)['sha256'] == 'a797041d09fab9a40ddbc474d9812c06b316e4fb5dcdacbc7947e02a3c4cc9f6'
    groups = {'source':[], 'r4':[], 'base_v5':[], 'base_v6':[]}
    for row in lock['r5_files']:
        actual = ident(SOURCE / row['path']); assert same(actual,row); groups['source'].append(actual)
    groups['source'].append(ident(source_lock))
    r4 = OLD / 'r4'; v5 = OLD / 'base-v5'; v6 = OLD / 'base-v6'
    for row in lock['r4_source_files']:
        actual = ident(r4 / row['path']); assert same(actual,row); groups['r4'].append(actual)
    bridge = json.loads((SOURCE / 'R5E_PUBLIC_INPUT_BRIDGE.json').read_text())
    assert len(bridge['files']) == 19
    for row in bridge['files']:
        actual = ident(r4 / row['path']); assert same(actual,row['public_identity'])
        assert row['decoded_json_equal'] is True and row['changed_strings'] == []
        groups['r4'].append(actual)
    for group, root, filename, count in [('base_v5',v5,'R5E_V6_BASE_V5_INPUT_BRIDGE.json',25),
                                         ('base_v6',v6,'R5E_V7_BASE_V6_INPUT_BRIDGE.json',53)]:
        old = json.loads((SOURCE / filename).read_text()); assert len(old['files']) == count
        for row in old['files']:
            actual = ident(root / row['path']); assert same(actual,row); groups[group].append(actual)
    assert {k:len(v) for k,v in groups.items()} == {'source':46, 'r4':22, 'base_v5':25, 'base_v6':53}
    identities = [r for group in groups.values() for r in group]
    assert len(identities) == len({r['path'] for r in identities}) == 146
    st = os.statvfs(ROOT)
    memory = {k:int(v) for k,v in (line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())}
    shared = memory['anon'] + memory['shmem'] + max(memory['kernel']-memory['slab_reclaimable'],0) + memory.get('unevictable',0)
    cwd = WORKSPACE / 'razr-current'
    repo = subprocess.run(['git','--no-lazy-fetch','-C',str(cwd),'rev-parse','HEAD'],capture_output=True,text=True,check=True)
    assert repo.stdout.strip() == '65f2a8fbb30d6310c1a69ef37204fa7fa8f32b3a'
    command = [sys.executable,'-I','-S','-B',str(SOURCE / 'run_portable_planar_r7e_v9.py'),
               '--r4-root',str(r4),'--base-v5-root',str(v5),'--base-v6-root',str(v6),'--output',str(HERE / 'attempt-1')]
    registration = {'schema':'razr-r7e-v9-local-execution-registration-v1',
        'registered_utc':datetime.now(timezone.utc).isoformat(), 'source':ident(Path(__file__)),
        'source_lock':ident(source_lock), 'groups':groups, 'complete_bound_input_count':146,
        'source_and_input_bytes':sum(r['bytes'] for r in identities),
        'command':command, 'working_directory':str(cwd), 'actual_worktree_HEAD':repo.stdout.strip(),
        'original_scientific_anchor':lock['source_commit'], 'github_run_claimed':False,
        'stdout_path':str(HERE / 'driver.stdout.log'), 'stderr_path':str(HERE / 'driver.stderr.log'),
        'actual_python':{'version':sys.version, 'executable':ident(Path(sys.executable))},
        'fixed_scientific_scope':{'case_id':'case-028','frame':1,'V6_root_index':76,'V6_node_index':47,
            'whole_original_D_retained':True,'original_float64_TOL_unchanged':True,
            'maximum_new_splits':4096,'maximum_depth':24,'maximum_combined_piece_tests':12000000,
            'maximum_combined_support_inequalities':12000000,'source_UV_census':4100,'source_plane_census':50},
        'original_worker_limits':{'wall_seconds':600,'RSS_limit_bytes':805306368,'shared_ceiling_bytes':7301444403,
            'disk_floor_bytes':104857600,'maximum_output_bytes':41943040,'metadata_margin_bytes':4194304},
        'maximum_owned_stages':5, 'sum_of_registered_worker_wall_limits_seconds':3000,
        'wall_limit_sum_excludes_orchestration_overhead':True,
        'registered_algorithm_basis':'Two exact original Plane domain maps add36UVsourcepieces; all original tree and proof functions unchanged. Original selected-leaf u/TOL and independent verification precede full16 preflight/refinement. No time estimate is substituted for original resource enforcement.',
        'actual_resource_observation':{'ordinary_available_bytes':st.f_bavail*st.f_frsize,
            'shared_unreclaimable_bytes':shared,'original_startup_disk_required_bytes':150994944,
            'original_startup_shared_plus_worker_bytes':shared+805306368,
            'original_startup_disk_gate_currently_satisfied':st.f_bavail*st.f_frsize>=150994944,
            'original_startup_shared_gate_currently_satisfied':shared+805306368<=7301444403},
        'bounded_diagnostic_already_completed':ident(ROOT / 'diagnostic-v1/attempt-2/R7E_ORIGINAL_LINE_PLANE_DOMAIN_DIAGNOSIS_V2.json'),
        'independent_checker_source_review':ident(ROOT / 'independent-checker-review/R7E_V9_CROSS_AUTHOR_CHECKER_STATIC_REVIEW_V2.json'),
        'registration_completed_seconds':time.monotonic()-started,
        'new_V9_worker_executed':False, 'final_root_package_review_pending':True,
        'native_qualification_claimed':False,'all_blockers_closed':False}
    path = HERE / 'R7E_V9_LOCAL_EXECUTION_REGISTRATION_V1.json'
    path.write_text(json.dumps(registration,indent=2)+'\n')
    print(json.dumps({'registration':ident(path),'input_count':146,
                      'input_bytes':registration['source_and_input_bytes'],
                      'resources':registration['actual_resource_observation'],'executed':False}))


if __name__ == '__main__':
    main()
