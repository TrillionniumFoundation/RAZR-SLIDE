"""Repair actual empty-index setup failure without changing admission gates."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent

def ident(p):
    b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

def main():
    # Real tiny Git control, explicitly not a RAZR functional-source artifact.
    with tempfile.TemporaryDirectory(dir=ROOT,prefix='index-control-') as td:
        base=Path(td);repo=base/'repo';repo.mkdir();work=base/'work'
        def git(*args,cwd=repo,input=None):
            return subprocess.check_output(['git',*args],cwd=cwd,input=input,stderr=subprocess.STDOUT)
        git('init','-q');(repo/'kept.txt').write_bytes(b'kept\n');(repo/'excluded.txt').write_bytes(b'excluded\n')
        git('add','.');git('-c','user.name=Synthetic Control','-c','user.email=synthetic-control@example.invalid','commit','-q','-m','Explicit synthetic index control')
        sha=git('rev-parse','HEAD').decode().strip()
        git('worktree','add','--detach','--no-checkout',str(work),sha)
        git('sparse-checkout','init','--no-cone',cwd=work)
        git('sparse-checkout','set','--no-cone','--stdin',cwd=work,input=b'/kept.txt\n')
        before=git('status','--porcelain','--untracked-files=all',cwd=work).decode()
        assert before and not (work/'kept.txt').exists()
        git('read-tree','-mu','HEAD',cwd=work)
        after=git('status','--porcelain','--untracked-files=all',cwd=work).decode()
        assert after=='' and (work/'kept.txt').read_bytes()==b'kept\n' and not (work/'excluded.txt').exists()
        control={'synthetic_fixture_not_RAZR_evidence':True,'before_status':before,'after_status':after,'exact_selected_file_present':True,'excluded_file_absent':True,'complete_actual_files':sorted(str(p.relative_to(work)) for p in work.rglob('*') if p.is_file())}
    old=ROOT/'setup_fresh_s4_runtime_r7_v2.py';src=old.read_text()
    line="        run(['git', 'sparse-checkout', 'set', '--no-cone', '--stdin'], worktree, 'sparse-set', patterns)\n"
    assert src.count(line)==1
    src=src.replace(line,line+"        run(['git', 'read-tree', '-mu', 'HEAD'], worktree, 'populate-sparse-index')\n",1)
    new=ROOT/'setup_fresh_s4_runtime_r7_v3.py';assert not new.exists();ast.parse(src);new.write_text(src)
    regold=ROOT/'register_local_setup_r7_v2.py';reg=regold.read_text().replace('setup_fresh_s4_runtime_r7_v2.py','setup_fresh_s4_runtime_r7_v3.py')
    reg=reg.replace('genuine-s4-worktree-v2','genuine-s4-worktree-v3').replace('pinned-uv-0.10.10-v2','pinned-uv-0.10.10-v3')
    reg=reg.replace("('setup-' + args.stage + '-v2')","('setup-' + args.stage + '-v3')").replace('setup-assess_only-v2/','setup-assess_only-v3/').replace("'_CONTRACT_V2.json'","'_CONTRACT_V3.json'")
    reg=reg.replace('RAZR_R7_LOCAL_SETUP_REGISTERED_CONTRACT_V2','RAZR_R7_LOCAL_SETUP_REGISTERED_CONTRACT_V3')
    regnew=ROOT/'register_local_setup_r7_v3.py';assert not regnew.exists();ast.parse(reg);regnew.write_text(reg)
    runold=ROOT/'register_and_run_native_local_r7_v3.py';run=runold.read_text().replace('genuine-s4-worktree-v2','genuine-s4-worktree-v3').replace('setup-install_only-v2/','setup-install_only-v3/').replace('R7_SETUP_INSTALL_ONLY_CONTRACT_V2.json','R7_SETUP_INSTALL_ONLY_CONTRACT_V3.json').replace('setup_fresh_s4_runtime_r7_v2.py','setup_fresh_s4_runtime_r7_v3.py')
    run=run.replace("('setup-assess_only-v2', 'setup-install_only-v2')","('setup-assess_only-v3', 'setup-install_only-v3')")
    runnew=ROOT/'register_and_run_native_local_r7_v4.py';assert not runnew.exists();ast.parse(run);runnew.write_text(run)
    fullold=ROOT/'register_full_factory_local_r7_v2.py';full=fullold.read_text().replace('register_and_run_native_local_r7_v3.py','register_and_run_native_local_r7_v4.py').replace('R7_SETUP_INSTALL_ONLY_CONTRACT_V2.json','R7_SETUP_INSTALL_ONLY_CONTRACT_V3.json')
    fullnew=ROOT/'register_full_factory_local_r7_v3.py';assert not fullnew.exists();ast.parse(full);fullnew.write_text(full)
    record={'schema':'RAZR_R7_SETUP_V3_INDEX_REVISION_AND_ACTUAL_CONTROL_V1','gates_relaxed':False,'actual_synthetic_control':control,
            'source_versions':{p.name:ident(p) for p in (old,new,regold,regnew,runold,runnew,fullold,fullnew)},
            'original_failed_v2_preserved':True,'installer_started_by_this_preparation':False}
    (ROOT/'R7_SETUP_V3_INDEX_REVISION_AND_ACTUAL_CONTROL_V1.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))

if __name__=='__main__':main()
