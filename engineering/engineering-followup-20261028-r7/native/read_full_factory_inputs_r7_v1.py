"""Read complete historical K3 prerequisites and exact driver identities; no CAD."""
from pathlib import Path
import hashlib
import json
import os
import stat
import time

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
K3 = BASE / 'r7-recovery/k3'

def ident(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(2**20), b''): h.update(b)
    return {'bytes': p.stat().st_size, 'sha256': h.hexdigest()}

def regular_files(root):
    out = {}
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        for n in dirs:
            assert stat.S_ISDIR((Path(base) / n).lstat().st_mode)
        for n in files:
            p = Path(base) / n
            assert stat.S_ISREG(p.lstat().st_mode)
            out[str(p.relative_to(root))] = ident(p)
    return out

def main():
    started = time.monotonic()
    binding = json.loads((K3 / 'source/k3full/K3FULL_K3_BINDING.json').read_text())
    assert binding['actual_two_complete_pilots_reviewed_clear'] is True
    drivers = json.loads((K3 / 'K3FULL-driver-source.json').read_text())
    actual_drivers = regular_files(K3 / 'source/k3full')
    assert actual_drivers == {k: {'bytes':v['bytes'],'sha256':v['sha256']} for k,v in drivers.items()}
    report = {'schema':'RAZR_R7_FULL_FACTORY_INPUTS_ACTUAL_READBACK_V1','completed':False,
              'native_execution_claimed':False,'original_drivers':actual_drivers,'poses':{}}
    for pose in ('stow_tabs_3','predock'):
        src = K3 / ('prerequisite-' + pose)
        manifest = src / 'ENGINEERING_MANIFEST.json'
        assert ident(manifest)['sha256'] == binding['poses'][pose]['engineering_manifest_sha256']
        obj = json.loads(manifest.read_text()); assert obj['schema'] == 'razr-K3-engineering-export-manifest-v1'
        actual = regular_files(src)
        assert set(actual) == set(obj['members']) | {'ENGINEERING_MANIFEST.json'}
        assert {k: v for k, v in actual.items() if k != 'ENGINEERING_MANIFEST.json'} == {k: {'bytes':v['bytes'],'sha256':v['sha256']} for k,v in obj['members'].items()}
        for mode in ('factory','readback'):
            wrapper = json.loads((src / mode / 'worker/report.engineering.json').read_text())
            assert wrapper['derived_projection_not_raw_original'] is True
            r = wrapper['engineering_record']
            assert r['execution_completed'] and r['pilot_clear'] and r['pilot_preconditions_passed']
            assert len(r['participant_names']) == 154 and len(r['pairs']) == 153 and not r['evaluation_failures'] and not r['mismatches_to_factory']
            assert wrapper['original']['sha256'] == binding['poses'][pose]['original_report_sha256'][mode]
            if mode == 'readback':
                assert len(r['independent_early_gate_records']) == 18 and all(x['evaluated'] and x['passed'] for x in r['independent_early_gate_records'].values())
                assert not r['independent_native_evaluation_failures'] and r['producer_reader_precondition_classification_consistent']
        report['poses'][pose] = {'actual_regular_files':len(actual),'actual_bytes':sum(v['bytes'] for v in actual.values()),
                                'manifest_identity':ident(manifest),'actual_complete_member_set_equal':True,
                                'all_bytes_SHA256_equal':True,'historical_complete_clear_pilot_verified':True,
                                'original_source_binding_count_claim':binding['poses'][pose]['exact_ZIP_regular_file_count'],
                                'members':actual}
    report['completed'] = True
    report['seconds'] = time.monotonic() - started
    report['total_prerequisite_regular_files'] = sum(x['actual_regular_files'] for x in report['poses'].values())
    report['total_prerequisite_bytes'] = sum(x['actual_bytes'] for x in report['poses'].values())
    p = ROOT / 'R7_FULL_FACTORY_INPUTS_ACTUAL_READBACK_V1.json'; assert not p.exists(); p.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('completed','seconds','total_prerequisite_regular_files','total_prerequisite_bytes')}))

if __name__ == '__main__': main()
