"""R39 research QA attestation. Does not turn negative geometric tests into a GO."""
import hashlib,zipfile,json,re,subprocess,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=Path(os.environ.get('R39_R38_ZIP','/mnt/data/RAZR_SLIDE_R38_verified_engineering_package_20261011.zip'))
EXPECTED='649c89711e5bd25a357fbac972d1c0e4ac8144841dd34e8b261cd67aa50bb7a6'

def run():
    started=time.time();e=hashlib.file_digest(BASE.open('rb'),'sha256').hexdigest();assert e==EXPECTED
    frozen=[]
    with zipfile.ZipFile(BASE) as zipf:
        assert zipf.testzip() is None
        names=zipf.namelist(); assert len(names)==1094
        for n in names:
            actual=hashlib.sha256((ROOT/n).read_bytes()).hexdigest()
            expected=hashlib.sha256(zipf.read(n)).hexdigest()
            assert expected==actual,f'R38 frozen ancestor mismatch {n}'
            frozen.append(dict(name=n,sha256=expected))
    frozen_payload=dict(source_R38_original_archive_SHA256=e,source_R38_archive_members=len(names),
      frozen_ancestor_bytes_unmodified=True,member_sha256=frozen)
    (ROOT/'audit/R39_R38_frozen_manifest.json').write_text(json.dumps(frozen_payload,ensure_ascii=False,indent=2)+'\n')
    inherited=json.loads((ROOT/'verification/R39_inherited_results.json').read_text())
    assert inherited['source_R38_sha']==EXPECTED and inherited['source_R38_members']==1094
    assert inherited['historical_reexecuted_tests']==697 and inherited['all_passed']
    for row in inherited['receipts']:
        file=ROOT/row['log'];assert row['ok'] and hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
    run=subprocess.run(['python','-m','unittest','-q','test_r39.py'],cwd=ROOT,
        capture_output=True,text=True,timeout=40,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1'})
    log=(run.stdout or '')+(run.stderr or '')
    (ROOT/'verification/R39_new_tests.log').write_text(log)
    m=re.search(r'Ran\s+(\d+)\s+tests?',log)
    assert run.returncode==0 and m is not None and int(m.group(1))==49 and log.rstrip().endswith('OK'),log
    paths=json.loads((ROOT/'verification/R39_path_screen.json').read_text())
    steprecs=json.loads((ROOT/'verification/R39_STEP_manifest.json').read_text())
    assert paths['scenes']==22 and paths['scenario_count']==88 and paths['all_candidates_rejected']
    assert all(z['poses_passing_all_design_screens']==0 for z in paths['constraints_summary'].values())
    breps=json.loads((ROOT/'verification/R39_ribbon_BREP_manifest.json').read_text())
    assert breps['count']==6 and breps['all_unsafe_ghost']
    for br in breps['records']:
        assert hashlib.sha256((ROOT/'cad'/br['file']).read_bytes()).hexdigest()==br['sha256']
    assert len(steprecs['scenarios'])==6
    for st in steprecs['scenarios']:
        assert st['intentional_unsafe_ghost'] and st['parts']==st['valid_solids']==7
        assert hashlib.sha256((ROOT/'cad'/st['step']).read_bytes()).hexdigest()==st['sha256']
    data=dict(revision='R39 actual re-run from R38 source + finite 3D FPC ribbon negative review',
        source_R38_sha256=e,R38_frozen_archive_files=1094,R38_ancestor_bytes_unchanged=True,
        R38_historical_fresh_tests=697,R39_new_fresh_tests=49,total_fresh_test_assertions=746,
        new_tests_exit_code=run.returncode,new_test_log_sha256=hashlib.sha256(log.encode()).hexdigest(),
        test_pass_does_not_equal_hardware_pass=True,
        geometric_poses=paths['scenes'],ribbon_candidates=len(paths['constraints_summary']),
        candidate_pose_combinations=paths['scenario_count'],
        sample_sections_per_pose=81,section_footprint_test_points=405,
        route_candidate_summary=paths['constraints_summary'],
        scenario_STEP_count=6,ghost_STEP_count=6,all_STEP_reimported_valid=True,
        ribbon_BREP_count=6,all_ribbon_BREP_reimported_valid=True,
        supplementary_full_Boolean_attempt_not_a_completed_six_scene_validation=True,
        real_3d_vendor_FPC_or_electrical_connectivity_tested=False,
        OEM_7inch_display_qualified=False,mechanical_safety_qualified=False,
        power_hardware_qualified=False,USB_signal_integrity_qualified=False,
        battery_4700mAh_proven=False,manufacturing_go=False,
        run_seconds=round(time.time()-started,2))
    (ROOT/'verification/R39_results.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    print('R39_ATTEST 746/746 pass, R38 1094 frozen, 6 GHOST STEP, NO-GO',flush=True)
    return data
if __name__=='__main__':run()
