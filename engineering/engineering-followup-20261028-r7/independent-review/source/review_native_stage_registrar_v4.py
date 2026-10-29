#!/usr/bin/env python3
"""Review original worker/qualifier preservation and actual finite-stage seal gates."""
from pathlib import Path
import ast
import datetime as dt
import hashlib
import importlib.util
import json
import os
import resource
import tempfile
import time

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
NATIVE = BASE / 'r7-native'
ASSETS = BASE / 'razr-current/engineering/engineering-followup-20261028-r5/cloud-native-v1'
SCIENCE = NATIVE / 'recovered-science-v1'
OUTPUT = ROOT / 'native-stage-v4-review/R7_NATIVE_STAGE_V4_INDEPENDENT_SOURCE_REVIEW.json'


def ident(p):
    raw = Path(p).read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    assert not OUTPUT.exists()
    registrar = NATIVE / 'register_and_run_native_local_r7_v4.py'
    qualifier = NATIVE / 'qualify_fresh_runtime_r7_v1.py'
    old_qualifier = ASSETS / 'qualify_fresh_runtime_r5.py'
    template_path = ASSETS / 'R5_CLOUD_NATIVE_SCIENCE_TEMPLATE.json'
    manifest_path = ASSETS / 'SCIENTIFIC_INPUT_MANIFEST.json'
    watched = {p: ident(p) for p in (registrar, qualifier, old_qualifier, template_path, manifest_path)}
    assert watched[registrar]['sha256'] == 'ac15965cdc05045b1f1a01662d046d5d48014e5197c7cfd5c6d0699390465120'
    assert watched[old_qualifier]['sha256'] == '9787944e893339831661542775ade149695137def6215dacdf878a6af36786c7'
    assert watched[qualifier]['sha256'] == 'a1b14b6586893339f245ba04363ea0dd210c2fea8c86fdfeaa82ed10eb19d1fb'
    tree = ast.parse(qualifier.read_text())
    stripped = []
    for node in tree.body:
        if isinstance(node, ast.Import) and len(node.names) == 1 and node.names[0].name == 'stat':
            continue
        if isinstance(node, ast.FunctionDef) and node.name == 'verified_uv_root_lock':
            continue
        stripped.append(node)
    tree.body = stripped
    main_function = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'main')
    additions = {ast.dump(ast.parse(x).body[0], include_attributes=False) for x in (
        "root_lock = verified_uv_root_lock(venv)",
        "scaffolds.update(root_lock['allowed_relative_files'])",
        "report['verified_uv_root_lock'] = root_lock")}
    removed = []
    for node in ast.walk(main_function):
        if isinstance(node, ast.Try):
            old = node.body
            removed += [x for x in old if ast.dump(x, include_attributes=False) in additions]
            node.body = [x for x in old if ast.dump(x, include_attributes=False) not in additions]
    assert len(removed) == 3
    assert ast.dump(tree, include_attributes=False) == ast.dump(ast.parse(old_qualifier.read_text()), include_attributes=False)
    lock_controls = json.loads((NATIVE / 'R7_UV_ROOT_LOCK_ACTUAL_CONTROLS_V1.json').read_bytes())
    assert lock_controls['count'] == 12 and lock_controls['completed']
    assert lock_controls['source']['sha256'] == watched[qualifier]['sha256']
    assert all(x['actual_accept'] == x['expected_accept'] for x in lock_controls['controls'])

    spec = importlib.util.spec_from_file_location('reviewed_local_native_registration_helpers', registrar)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = json.loads(manifest_path.read_bytes())['members']
    actual = module.strict_inventory(SCIENCE)
    assert len(manifest) == 161 and actual == manifest
    science_bytes = sum(x['bytes'] for x in actual.values())
    template = json.loads(template_path.read_bytes())
    original = template['science_contract']
    producer = SCIENCE / template['science_worker_paths']['producer']
    reader = SCIENCE / template['science_worker_paths']['reader']
    assert ident(producer) == original['worker_identity']
    assert ident(reader) == original['independent_reader_source_identity']
    watched[producer] = ident(producer)
    watched[reader] = ident(reader)
    for row in original['bound_records'] + original['bound_sources']:
        rel = Path(row['path']).relative_to(template['original_workspace_root'])
        assert ident(SCIENCE / rel) == row['identity']
    assert len(original['expected_43_package_versions']) == 43
    assert original['maximum_worker_output_bytes'] == 20971520
    assert original['maximum_new_campaign_bytes'] == 67108864
    assert original['original_3D_material_tolerance_mm3'] == 1e-7
    assert original['new_physical_area_threshold'] is None
    code = registrar.read_text()
    for text in ("c = copy.deepcopy(original)", "require_sealed_phase('qualify')",
                 "require_sealed_phase('core-producer')", "c['command'][7:] == c['worker_command']",
                 "shutil.disk_usage(ROOT).free >= 4 * 2**30", "set(actual) == set(manifest) and actual == manifest",
                 "report['completed'] and seal['completed_scientific_stage']"):
        assert text in code, text
    assert "'maximum_single_wheel_bytes': 268435456" in code
    assert "'maximum_report_bytes': 6291456, 'maximum_output_bytes': 8388608" in code
    assert 'GITHUB_' not in code
    controls = []
    with tempfile.TemporaryDirectory(prefix='explicit-synthetic-native-seal-', dir=ROOT) as tmp:
        base = Path(tmp)
        original_globals = {k: getattr(module, k) for k in ('ROOT', 'CASE', 'SCIENCE', 'ASSETS')}
        def fixture(name):
            local = base / name
            local.mkdir()
            module.ROOT = local
            module.CASE = local / 'case'
            module.SCIENCE = local / 'science'
            module.ASSETS = local / 'assets'
            for p in (module.CASE, module.SCIENCE, module.ASSETS): p.mkdir()
            (module.SCIENCE / 'one.bin').write_bytes(b'1')
            (module.ASSETS / 'one.bin').write_bytes(b'2')
        def expect_rejection(name, action):
            rejected, err = False, None
            try: action()
            except (ValueError, OSError) as exc: rejected, err = True, str(exc)
            assert rejected, name
            controls.append({'name': name, 'actual_rejected': rejected, 'error': err})
        fixture('census')
        x = module.SCIENCE / 'extra-fifo'; os.mkfifo(x)
        expect_rejection('complete-science-census-rejects-FIFO', lambda: module.strict_inventory(module.SCIENCE)); x.unlink()
        x = module.SCIENCE / 'extra-linkdir'; x.symlink_to(module.ASSETS, target_is_directory=True)
        expect_rejection('complete-science-census-rejects-symlink-directory', lambda: module.strict_inventory(module.SCIENCE)); x.unlink()
        x = module.SCIENCE / '.venv'; x.mkdir(); (x / 'extra.bin').write_bytes(b'x')
        files = module.strict_inventory(module.SCIENCE)
        assert '.venv/extra.bin' in files
        controls.append({'name': 'science-census-does-not-prune-runtime-name', 'actual_file_present': True})
        fixture('exact-cap')
        payload = module.CASE / 'raw.bin'
        with payload.open('wb') as f: f.truncate(67108864 - 2)
        exact = module.seal_phase('qualify', True)
        assert exact['scientific_raw_bytes_including_current_inputs'] == 67108864
        assert exact['completed_scientific_stage']
        module.require_sealed_phase('qualify')
        controls.append({'name': 'exact-original-64MiB-boundary', 'actual_accepted': True, 'bytes': 67108864})
        with payload.open('r+b') as f: f.write(b'tamper')
        expect_rejection('prior-sealed-raw-byte-change', lambda: module.require_sealed_phase('qualify'))
        fixture('above-cap')
        with (module.CASE / 'raw.bin').open('wb') as f: f.truncate(67108864 - 1)
        over = module.seal_phase('qualify', True)
        assert over['scientific_raw_bytes_including_current_inputs'] == 67108865
        assert not over['completed_scientific_stage'] and (module.CASE / 'qualify-seal.json').exists()
        expect_rejection('64MiB-plus-one-retained-failure-blocks-next-stage', lambda: module.require_sealed_phase('qualify'))
        fixture('failed-stage')
        (module.CASE / 'raw.bin').write_bytes(b'failure')
        failed = module.seal_phase('qualify', False)
        assert failed['within_registered_64MiB_budget'] and not failed['completed_scientific_stage']
        expect_rejection('failed-native-stage-cannot-pass-via-budget-only', lambda: module.require_sealed_phase('qualify'))
        for k,v in original_globals.items(): setattr(module, k, v)
    assert module.strict_inventory(SCIENCE) == manifest
    assert all(ident(p) == v for p,v in watched.items())
    report = {'schema': 'razr-r7-native-stage-v4-independent-source-review-v1',
        'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'source_review_pass': True,
        'reviewed_sources': [{'path': str(p.relative_to(BASE)), **v} for p,v in watched.items()],
        'all_watched_sources_and_original_inputs_unchanged': True,
        'complete_original_science_members': 161, 'complete_original_science_bytes': science_bytes,
        'all_original_scientific_bytes_preserved': True,
        'qualifier_original_AST_identical_except_single_root_lock_ownership_addition': True,
        'same_author_12_root_lock_controls_independently_read_back': True,
        'independent_synthetic_seal_and_census_controls': controls,
        'native_producer_and_reader_exact_original_bytes': True,
        'original_1e_minus7_tolerance_and_null_new_area_threshold_preserved': True,
        'original_six_native_limits': template['original_resource_limits'],
        'original_64MiB_aggregate_seal_preserved': True,
        'seal_budget_scope': 'Case raw files + complete161 original science files + all original published assets, extended with new local source/metadata/setup receipts; newly generated seal itself is not self-hashed, matching original seal treatment. Runtime fixture excluded as in original.',
        'actual_runtime_installation_or_qualification_executed_by_this_reviewer': False,
        'actual_native_geometry_or_physical_gate_executed_by_this_reviewer': False,
        'generated_command_contract_review_still_required_before_launch': True,
        'execution': {'seconds': time.monotonic() - started,
            'max_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            'address_cap_bytes': 256 * 1024**2, 'CPU_cap_seconds': 60},
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(report, indent=2) + '\n').encode(); OUTPUT.write_bytes(encoded)
    print(json.dumps({'report': str(OUTPUT), 'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest(),
        'source_review_pass': True, 'actual_controls': len(controls), 'science_members': len(manifest)}))


if __name__ == '__main__': main()
