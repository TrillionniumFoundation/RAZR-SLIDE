"""Privacy/integrity regression only; synthetic fixture is never CAD evidence."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent


def ref(path):
    return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}


def main():
    with tempfile.TemporaryDirectory(prefix='razr-k1-export-test-') as tmp:
        root=Path(tmp)/'repository';root.mkdir();case=Path(tmp)/'near';case.mkdir()
        prior=case/'prerequisite';prior.mkdir();(prior/'known.step').write_text('SYNTHETIC FIXTURE; NOT CAD\n')
        manifest={'schema':'fixture-only','members':{'known.step':ref(prior/'known.step')}}
        (prior/'ENGINEERING_MANIFEST.json').write_text(json.dumps(manifest))
        # An unexpected raw file under prerequisite must not be allowed merely
        # because its parent directory once held an engineering artifact.
        (prior/'unexpected-runtime.txt').write_text('K1_PRIVATE_RUNTIME_MUST_NOT_ESCAPE')
        sources=case/'source/k1';sources.mkdir(parents=True)
        binding={'fixture_only_not_runtime_evidence':True,'poses':{'near':{
            'engineering_manifest_sha256':ref(prior/'ENGINEERING_MANIFEST.json')['sha256']}}}
        bp=sources/'K1_F1A_BINDING.json';bp.write_text(json.dumps(binding))
        (case/'K1-driver-source.json').write_text(json.dumps({'K1_F1A_BINDING.json':ref(bp)}))
        worker=case/'factory/worker';worker.mkdir(parents=True)
        report={'schema':'synthetic-privacy-fixture-not-CAD','pose':'near','execution_completed':False,
            'candidate_name':'key_forward_loop_v1','candidate_application':{'material_accounts':{'R_KEY':{'removed_mm3':.594}}},
            'candidate_inventory':{'R_KEY':{'candidate_source_sha256':'fixture'}},
            'candidate_material_exports':{},'original_baseline_material_comparisons':{},
            'pairs':[],'finite_pose_clear':False,'candidate_go':False,
            'identity_before':{'environment':{'private':'K1_PRIVATE_RUNTIME_MUST_NOT_ESCAPE'}},
            'external_source_sha256':{'private-locator':'K1_PRIVATE_RUNTIME_MUST_NOT_ESCAPE'}}
        rp=worker/'report.json';rp.write_text(json.dumps(report))
        raw_before={str(p.relative_to(case)):ref(p) for p in case.rglob('*') if p.is_file()}
        output=Path(tmp)/'engineering'
        result=subprocess.run([sys.executable,'-B',str(HERE/'export_k1_engineering.py'),'--case',str(case),'--output',str(output)],
            env={**os.environ,'GITHUB_WORKSPACE':str(root)},capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        assert all(ref(case/rel)==value for rel,value in raw_before.items())
        assert not (output/'prerequisite/unexpected-runtime.txt').exists()
        assert (output/'prerequisite/known.step').read_bytes()==(prior/'known.step').read_bytes()
        assert all('K1_PRIVATE_RUNTIME_MUST_NOT_ESCAPE' not in p.read_text() for p in output.rglob('*') if p.is_file())
        projection=json.loads((output/'factory/worker/report.engineering.json').read_text())
        assert projection['derived_projection_not_raw_original'] and projection['original']==ref(rp)
        got=projection['engineering_record']
        assert got['candidate_application']==report['candidate_application']
        assert got['candidate_inventory']==report['candidate_inventory']
        assert got['execution_completed'] is False and got['finite_pose_clear'] is False and got['candidate_go'] is False
        scope=json.loads((output/'EXPORT_SCOPE.json').read_text())
        assert scope['raw_producer_reader_reports_modified'] is False and scope['raw_runtime_durable_preservation_claimed'] is False
        assert scope['local_runtime_verification_results']['prerequisite_original_manifest_verified'] is True
        print(json.dumps({'synthetic_fixture_passed':True,'actual_CAD_execution_claimed':False,
            'unexpected_prerequisite_runtime_excluded':True,'secret_runtime_fixture_marker_absent':True,
            'new_candidate_geometric_fields_retained':True,'all_raw_fixture_bytes_unchanged':True,
            'partial_results_not_promoted':True}))


if __name__=='__main__':main()
