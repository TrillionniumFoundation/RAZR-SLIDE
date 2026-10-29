"""Preserve source-only v2 and close independently identified census/budget gaps."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parent

def ident(p):
    b = p.read_bytes(); return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

def main():
    old = ROOT / 'register_and_run_native_local_r7_v2.py'
    src = old.read_text().replace('import shutil\n','import shutil\nimport stat\n',1)
    helper = '''def strict_inventory(root):
    require(stat.S_ISDIR(root.lstat().st_mode), 'Inventory root is not a real directory')
    result = {}
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        for name in dirs:
            require(stat.S_ISDIR((Path(base) / name).lstat().st_mode), 'Symlink or special directory in complete census')
        for name in files:
            p = Path(base) / name
            require(stat.S_ISREG(p.lstat().st_mode), 'Special or symlink file in complete census')
            result[str(p.relative_to(root))] = identity(p)
    return result


def seal_phase(phase, actual_stage_completed):
    # Same original scope: all case raw outputs, all161 scientific inputs,
    # every published source asset. New local runtimefixture remains separate.
    target = CASE / (phase + '-seal.json')
    require(not target.exists(), 'New immutable per-phase scientific seal required')
    rows = strict_inventory(CASE)
    science = strict_inventory(SCIENCE)
    published = strict_inventory(ASSETS)
    local = {}
    for p in sorted(ROOT.iterdir()):
        if p.is_file() and p.suffix in ('.py', '.json'):
            require(stat.S_ISREG(p.lstat().st_mode), 'Local source metadata is not regular')
            local[p.name] = identity(p)
    for parent in ('setup-assess_only-v2', 'setup-install_only-v2'):
        p = ROOT / parent / 'R7_FRESH_LOCAL_RUNTIME_SETUP_ACTUAL_V1.json'
        if p.is_file():
            local[parent + '/' + p.name] = identity(p)
    total = sum(v['bytes'] for group in (rows, science, published, local) for v in group.values())
    record = {'schema': 'razr-r7-complete-finite-scientific-phase-seal-v1', 'phase': phase,
              'raw_case_members': rows, 'all_original_scientific_inputs': science,
              'all_original_published_assets': published, 'new_local_source_and_bound_setup_receipts': local,
              'scientific_raw_bytes_including_current_inputs': total, 'registered_scientific_output_budget_bytes': 67108864,
              'within_registered_64MiB_budget': total <= 67108864,
              'actual_native_stage_completed': actual_stage_completed,
              'completed_scientific_stage': actual_stage_completed and total <= 67108864,
              'new_venv_uv_installation_and_transient_setup_fixture_separate': True,
              'historical_failed_stages_not_reclassified': True, 'full_continuous_G2': False,
              'manufacturing_go': False, 'physical_qualification': False}
    save(target, record)
    return record


def require_sealed_phase(phase):
    record = json.loads((CASE / (phase + '-seal.json')).read_text())
    require(record['completed_scientific_stage'] and record['within_registered_64MiB_budget'],
            'Original aggregate scientific budget or prior phase completion failed')
    for rel, expected in record['raw_case_members'].items():
        require(identity(CASE / rel) == expected, 'Prior raw evidence changed after phase seal')
    return record


'''
    src = src.replace('def verify_sources():\n',helper+'def verify_sources():\n',1)
    old_census="    actual = {str(p.relative_to(SCIENCE)) for p in SCIENCE.rglob('*') if p.is_file()}\n    require(actual == set(manifest), 'Complete scientific input member set differs')"
    new_census="    actual = strict_inventory(SCIENCE)\n    require(set(actual) == set(manifest) and actual == manifest, 'Complete scientific input member set or bytes differ')"
    assert src.count(old_census)==1;src=src.replace(old_census,new_census)
    src=src.replace('def check_qualification():\n','def check_qualification():\n    require_sealed_phase(\'qualify\')\n',1)
    marker="            require(phase == 'core-reader', 'Unsupported stage')\n"
    assert src.count(marker)==1;src=src.replace(marker,marker+"            require_sealed_phase('core-producer')\n",1)
    old_return="    save(target, report); print(json.dumps(report))\n    return 0 if report['completed'] else result.returncode or 2\n"
    new_return="    save(target, report)\n    seal = seal_phase(c['phase'], report['completed'])\n    print(json.dumps({**report, 'scientific_aggregate_seal_passed': seal['completed_scientific_stage'], 'scientific_total_bytes': seal['scientific_raw_bytes_including_current_inputs']}))\n    return 0 if report['completed'] and seal['completed_scientific_stage'] else result.returncode or 2\n"
    assert src.count(old_return)==1;src=src.replace(old_return,new_return,1)
    ast.parse(src);new=ROOT/'register_and_run_native_local_r7_v3.py';assert not new.exists();new.write_text(src)
    fullold=ROOT/'register_full_factory_local_r7_v1.py';full=fullold.read_text().replace('register_and_run_native_local_r7_v2.py','register_and_run_native_local_r7_v3.py')
    full=full.replace("    reader_actual = core.CASE / 'core-reader-command-actual.json'\n","    core.require_sealed_phase('core-reader')\n    reader_actual = core.CASE / 'core-reader-command-actual.json'\n",1)
    full=full.replace("{str(p.relative_to(DRIVERS)) for p in DRIVERS.rglob('*') if p.is_file()}","set(core.strict_inventory(DRIVERS))")
    full=full.replace("{str(p.relative_to(src)) for p in src.rglob('*') if p.is_file()}","set(core.strict_inventory(src))")
    ast.parse(full);fullnew=ROOT/'register_full_factory_local_r7_v2.py';assert not fullnew.exists();fullnew.write_text(full)
    report={'schema':'RAZR_R7_NATIVE_REGISTRAR_V2_STATIC_GAPS_AND_V3_REVISION',
            'earlier_versions_executed_native_or_installer':False,
            'gaps':['Science census must reject all special/symlink entries','Original64MiB aggregate case+science+publishedassets seal must remain a gate'],
            'fixes':['strictlstat complete161source census with no pruning','immutableper-phase fullaggregate seal including originalscope plusnewlocalboundsource receipts; nextstage requires prior completedseal'],
            'sources':{p.name:ident(p) for p in (old,new,fullold,fullnew)},'science_worker_or_threshold_changed':False}
    (ROOT/'R7_NATIVE_REGISTRAR_V2_STATIC_GAPS_AND_V3_REVISION.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
