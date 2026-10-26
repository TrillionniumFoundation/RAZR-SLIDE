"""Small adversarial byte/projection check; no native CAD execution."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent

def main():
 with tempfile.TemporaryDirectory(prefix='k3-owned-export-check-',dir=HERE) as td:
  root=Path(td);case=root/'case';repository=root/'repository';repository.mkdir();source=case/'source/k3';source.mkdir(parents=True)
  (source/'export_k3_engineering.py').write_bytes((HERE/'export_k3_engineering.py').read_bytes())
  raw='PRIVATE_RUNTIME_MARKER /tmp/private-location author@example.invalid'
  (case/'raw').mkdir();(case/'raw/caller.json').write_text(raw)
  worker=case/'factory/worker';worker.mkdir(parents=True)
  report={'schema':'fixture','candidate_name':'panel_key_travel_stops_v1','functional_source_commit':'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560',
   'execution_completed':True,'pilot_clear':False,'pilot_preconditions_passed':False,'complete_preview_exports_retained':True,
   'precondition_failures':[{'stage':'contact','error_type':'ValueError','original_error_message_sha256':hashlib.sha256(raw.encode()).hexdigest()}],
   'original_precondition_failure':'ValueError: '+raw,'command':raw,'environment':{'secret':raw},
   'identity_before':{'repository_head_at_start':'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560','worktree_status_at_start':'',
    'environment':{'passed':True,'checked_package_count':43},'native_input_roles':[]},
   'identity_after':{'repository_head_at_finish':'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560',
    'source_bytes_and_locked_environment_unchanged':True,'environment_after':{'passed':True,'checked_package_count':43}}}
  rp=worker/'report.json';rp.write_text(json.dumps(report));(worker/'whole.step').write_text('scientific original STEP fixture\n')
  (worker/'pairs.jsonl').write_text('');before={str(p.relative_to(case)):hashlib.sha256(p.read_bytes()).hexdigest() for p in case.rglob('*') if p.is_file()}
  out=root/'engineering';run=subprocess.run([sys.executable,'-B',str(HERE/'export_k3_engineering.py'),'--case',str(case),'--output',str(out)],
   env={**os.environ,'GITHUB_WORKSPACE':str(repository)},capture_output=True,text=True)
  assert run.returncode==0,run.stderr
  after={str(p.relative_to(case)):hashlib.sha256(p.read_bytes()).hexdigest() for p in case.rglob('*') if p.is_file()};assert before==after
  scope=json.loads((out/'EXPORT_SCOPE.json').read_text());manifest=json.loads((out/'ENGINEERING_MANIFEST.json').read_text())
  assert scope['schema']=='razr-K3-engineering-export-scope-v1'
  assert scope['raw_producer_reader_reports_modified'] is False and scope['raw_runtime_durable_preservation_claimed'] is False
  assert scope['all_copied_original_bytes_verified'] is True
  assert {str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()}==set(manifest['members'])|{'ENGINEERING_MANIFEST.json'}
  for rel,ref in manifest['members'].items():
   b=(out/rel).read_bytes();assert len(b)==ref['bytes'] and hashlib.sha256(b).hexdigest()==ref['sha256']
   if not rel.startswith('source/'):
    assert b'PRIVATE_RUNTIME_MARKER' not in b and b'private-location' not in b and b'author@example.invalid' not in b
  for row in scope['omitted_runtime_file_hashes']:assert set(row)=={'category','sha256','bytes'}
  projection=json.loads((out/'factory/worker/report.engineering.json').read_text())
  assert projection['derived_projection_not_raw_original'] is True
  assert projection['original']['sha256']==before['factory/worker/report.json']
  science=projection['engineering_record'];assert science['pilot_clear'] is False and science['pilot_preconditions_passed'] is False
  assert science['original_precondition_error_type']=='ValueError' and 'original_precondition_failure' not in science
  assert (out/'factory/worker/whole.step').read_bytes()==(worker/'whole.step').read_bytes()
  return {'test':'K3 engineering-only export adversarial fixture','passed':True,
   'raw_source_bytes_unchanged':True,'private_runtime_fields_absent':True,'true_precondition_rejection_preserved':True,
   'complete_manifest_exact_member_set_and_hashes_verified':True,'raw_runtime_durability_claimed':False,'native_CAD_executed':False}

if __name__=='__main__':print(json.dumps(main(),sort_keys=True))
