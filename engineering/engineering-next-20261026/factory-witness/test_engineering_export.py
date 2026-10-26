from pathlib import Path
import hashlib,io,json,os,subprocess,sys,tarfile,tempfile,zipfile
HERE=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='razr-f1-export-check-',dir='/tmp') as td:
 root=Path(td)/'repo';root.mkdir();case=Path(td)/'case';case.mkdir();out=Path(td)/'engineering'
 for part in ('factory','readback'):
  f=case/part/'worker';f.mkdir(parents=True)
  pair={'a':'A_BACK_PANEL','b':'L_KEY','common_mm3':0.24558784938224748,'rejected':True,'method':'native_common'}
  r={'schema':'fixture','functional_source_commit':'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560','pose':'near','execution_completed':False,'pairs':[pair], 'positive_pairs':[pair],'finite_pose_clear':False,'candidate_go':False,'status':'partial','identity_before':{'repository_head_at_start':'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560','worktree_status_at_start':'','available_source_sha256':{str(root/'integration/a.py'):'abc'},'environment':{'passed':True,'checked_package_count':43,'private_fixture_marker':'MUST_NOT_ESCAPE_RUNTIME'}},'identity_after':{'source_bytes_and_locked_environment_unchanged':True,'environment_after':{'passed':True,'checked_package_count':43}},'resource':{'seconds':1.,'worker_peak_RSS_bytes':1024}}
  (f/'report.json').write_text(json.dumps(r));(f/'pairs.jsonl').write_text(json.dumps(pair)+'\n');(f/'bodies').mkdir();(f/'bodies/A_BACK_PANEL.step').write_bytes(b'ISO-10303-21;\nEND-ISO-10303-21;\n')
 raw=case/'factory-runner.namespace/raw';raw.mkdir(parents=True);(raw/'mountinfo.txt').write_text('MUST_NOT_ESCAPE_RUNTIME')
 (raw.parent/'prepared.json').write_text('{"environment":{"private_fixture_marker":"MUST_NOT_ESCAPE_RUNTIME"}}')
 archive=Path(sys.argv[1]).resolve()
 with tarfile.open(archive) as tar:
  with zipfile.ZipFile(io.BytesIO(tar.extractfile('c2-slide-L1-O72-40210275856-1.zip').read())) as z:
   for c in (2,3,4,5,7,8,9,10):
    rel=f'run/case-{c:03d}/result.json';p=case/'original-L1-inputs'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(rel))
 before={str(p.relative_to(case)):hashlib.sha256(p.read_bytes()).hexdigest() for p in case.rglob('*') if p.is_file()}
 run=subprocess.run([sys.executable,'-B',str(HERE/'export_f1_engineering.py'),'--case',str(case),'--output',str(out)],env={**os.environ,'GITHUB_WORKSPACE':str(root)},capture_output=True,text=True)
 assert run.returncode==0,run.stderr
 assert all(hashlib.sha256((case/k).read_bytes()).hexdigest()==v for k,v in before.items())
 assert not any('MUST_NOT_ESCAPE_RUNTIME' in p.read_text() for p in out.rglob('*') if p.is_file())
 for part in ('factory','readback'):
  assert (out/part/'worker/pairs.jsonl').read_bytes()==(case/part/'worker/pairs.jsonl').read_bytes()
  p=json.loads((out/part/'worker/report.engineering.json').read_text());r=json.loads((case/part/'worker/report.json').read_text())
  assert p['derived_projection_not_raw_original'] and p['engineering_record']['pairs']==r['pairs'] and not p['engineering_record']['execution_completed'] and not p['engineering_record']['finite_pose_clear']
 for c in (2,3,4,5,7,8,9,10):
  r=json.loads((case/f'original-L1-inputs/run/case-{c:03d}/result.json').read_text());p=json.loads((out/f'original-L1-inputs/run/case-{c:03d}/result.engineering.json').read_text())['engineering_record']
  expected=json.loads(json.dumps(r['material_exports']).replace('/home/runner/work/RAZR-SLIDE/RAZR-SLIDE/','repository/'))
  assert p['material_exports']==expected and p['native_raw']==r['native_raw'] and 'trace' not in p
 scope=json.loads((out/'EXPORT_SCOPE.json').read_text());assert scope['raw_runtime_durable_preservation_claimed'] is False and scope['raw_producer_reader_reports_modified'] is False
 print(json.dumps({'fixture_passed':True,'original_raw_files_unchanged':len(before),'eight_actual_L1_geometric_results_retained':True,'complete_pair_rows_identical':True,'runtime_fixture_marker_absent':True,'partial_and_failure_status_not_promoted':True,'new_CAD_executed':False}))
