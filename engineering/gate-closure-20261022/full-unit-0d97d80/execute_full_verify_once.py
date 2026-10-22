#!/usr/bin/env python3
"""Copy one authorized clean HEAD with copy2, then execute the canonical full runner once."""
from __future__ import annotations
import argparse,datetime,hashlib,importlib.metadata,json,os,platform,re,shutil,stat,subprocess,sys,time,traceback
from pathlib import Path
BASE=Path('/dev/shm/razr-slide-1104895ba7b9')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def require(value,message):
    if not value:raise ValueError(message)
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(path,data):Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True,env={**os.environ,'GIT_NO_REPLACE_OBJECTS':'1','GIT_OPTIONAL_LOCKS':'0'}).strip()
def clean_head(root,expected):
    require(git(root,'cat-file','-t',expected)=='commit','expected identity is not an actual Git commit')
    require(git(root,'rev-parse','HEAD')==expected,'checked-out HEAD differs from authorized commit')
    require(Path(git(root,'rev-parse','--show-toplevel')).resolve()==root.resolve(),'Git working tree points outside isolated root')
    require(not git(root,'status','--porcelain=v1','--untracked-files=all'),'worktree is not clean')
def inventory(root):
    result={'head':git(root,'rev-parse','HEAD'),'present':{},'missing':[],'mismatched':[],'unsupported':[]}
    entries=git(root,'ls-tree','-r','-z','--full-tree','HEAD').split('\0')
    for entry in entries:
        if not entry:continue
        header,name=entry.split('\t',1);mode,kind,oid=header.split();path=root/name
        if mode=='120000' and path.is_symlink():data=os.readlink(path).encode()
        elif kind=='blob' and mode in ('100644','100755') and path.is_file() and not path.is_symlink():data=path.read_bytes()
        elif not path.exists() and not path.is_symlink():result['missing'].append(name);continue
        else:result['unsupported'].append({'path':name,'mode':mode,'kind':kind});continue
        actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        result['present'][name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'git_blob':oid}
        if actual!=oid:result['mismatched'].append(name)
    result['full_checkout_verified']=not(result['missing'] or result['mismatched'] or result['unsupported'])
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-head',required=True)
    parser.add_argument('--source',type=Path,default=BASE/'repo')
    parser.add_argument('--isolated-copy',type=Path,required=True)
    parser.add_argument('--run-directory',type=Path,required=True)
    args=parser.parse_args();source=args.source.resolve();dest=args.isolated_copy.resolve();run=args.run_directory.resolve()
    require(re.fullmatch('[0-9a-f]{40}',args.expected_head) is not None,'full authorized commit SHA required')
    require(dest.is_relative_to(BASE) and run.is_relative_to(BASE),'project tmpfs destinations required')
    require(not dest.exists() and not run.exists(),'new isolated source and evidence directories required')
    require(not dest.is_relative_to(source) and not run.is_relative_to(source),'outputs must remain outside root source')
    clean_head(source,args.expected_head)
    require((source/'.git').is_dir() and not (source/'.git').is_symlink(),'self-contained .git directory required')
    require(not (source/'.git/objects/info/alternates').exists(),'external Git object alternate would escape isolated copy')
    manifest=json.loads((source/'tools/test_suites.json').read_text())
    require(len(manifest['suites'])==36 and manifest['minimum_total_tests']==1461,'final 36-suite/1461 configuration is not installed')
    paths=[p for p in source.rglob('*') if p.is_file() and not p.is_symlink()]
    copy_bytes=sum(p.stat().st_size for p in paths)
    require(shutil.disk_usage(BASE).free>copy_bytes+256*1024*1024,'insufficient project tmpfs for physical copy and bounded test outputs')
    run.mkdir(parents=True);(run/'tmp').mkdir()
    report={'schema':'razr-full-unit-isolated-one-round-v1','started_utc':utc(),'expected_head':args.expected_head,
            'source_repository':str(source),'isolated_repository':str(dest),'copy_method':'shutil.copytree(copy_function=shutil.copy2, symlinks=True), including .git',
            'source_files_to_copy':len(paths),'source_file_bytes_to_copy':copy_bytes,'canonical_full_runner_executions':0,
            'configured_suites':36,'configured_minimum_tests':1461,'runtime_lock_reproduced':False,
            'dependency_installation_or_fixture_bypass_performed':False,'complete_checkout_claimed':False,
            'python_executable':sys.executable,'python':sys.version,'platform':platform.platform(),'packages':{},
            'physical_or_product_release_granted':False}
    write(run/'controller-report.json',report)
    try:
        shutil.copytree(source,dest,copy_function=shutil.copy2,symlinks=True)
        clean_head(source,args.expected_head);clean_head(dest,args.expected_head)
        hardlinks=[]
        for path in paths:
            copied=dest/path.relative_to(source)
            if copied.exists():
                a=path.stat();b=copied.stat()
                if (a.st_dev,a.st_ino)==(b.st_dev,b.st_ino):hardlinks.append(path.relative_to(source).as_posix())
        require(not hardlinks,'physical source copy contains a shared inode')
        before=inventory(dest);write(run/'git-tree-inventory-before.json',before)
        require(not before['mismatched'] and not before['unsupported'],'copied present source bytes do not match actual HEAD tree')
        report.update(source_copy_clean=True,shared_regular_file_inodes=0,
                      copied_present_tracked_files=len(before['present']),missing_tracked_paths=len(before['missing']),
                      full_checkout_verified=before['full_checkout_verified'],git_tree_inventory_before_sha256=sha(run/'git-tree-inventory-before.json'))
        for package in ['cadquery','cadquery-ocp','numpy','scipy','shapely','scikit-fem']:
            try:report['packages'][package]=importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:report['packages'][package]=None
        report['declared_python_version']=(dest/'.python-version').read_text().strip()
        report['pyproject_sha256']=sha(dest/'pyproject.toml');report['uv_lock_sha256']=sha(dest/'uv.lock')
        report['missing_native_archive_inputs']=[name for name in before['missing'] if name.endswith('.tar.gz')]
        marker=run/'ONE_CANONICAL_RUN_STARTED.json'
        with marker.open('x') as stream:json.dump({'expected_head':args.expected_head,'started_utc':utc()},stream)
        command=[sys.executable,'-B',str(dest/'tools/verify.py'),'--output',str(run/'results')]
        env={**os.environ,'TMPDIR':str(run/'tmp'),'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1',
             'OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_OPTIONAL_LOCKS':'0'}
        report.update(command=command,canonical_full_runner_executions=1,execution_started_utc=utc(),
                      requested_environment={key:env[key] for key in ['TMPDIR','PYTHONDONTWRITEBYTECODE','OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']})
        write(run/'controller-report.json',report)
        print('ISOLATED_FULL_VERIFY_START',args.expected_head,'missing_tracked',len(before['missing']),flush=True)
        with (run/'canonical-run.stdout.log').open('w') as log:
            proc=subprocess.Popen(command,cwd=dest,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
            for line in proc.stdout:
                log.write(line);log.flush();print(line,end='',flush=True)
            code=proc.wait()
        report.update(canonical_exit_code=code,execution_finished_utc=utc())
        canonical_path=run/'results/report.json'
        if canonical_path.exists():
            canonical=json.loads(canonical_path.read_text())
            report.update(canonical_report_sha256=sha(canonical_path),canonical_scope=canonical['scope'],
                          actual_tests_run=canonical['tests_run'],canonical_passed=canonical['passed'],
                          canonical_source_bytes_unchanged=canonical['source_bytes_unchanged'],
                          suites_observed=len(canonical['suite_results']),
                          suite_outcomes=[{key:row.get(key) for key in ['id','tests_run','minimum_tests','passed','exit_code','failures','errors','skipped','seconds']} for row in canonical['suite_results']])
        after=inventory(dest);write(run/'git-tree-inventory-after.json',after)
        report.update(git_tree_inventory_after_sha256=sha(run/'git-tree-inventory-after.json'),
                      source_inventory_unchanged=before==after,source_head_after=git(dest,'rev-parse','HEAD'),
                      source_status_after=git(dest,'status','--porcelain=v1','--untracked-files=all'),
                      canonical_stdout_sha256=sha(run/'canonical-run.stdout.log'))
        return code
    except Exception as exc:
        report['controller_error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        print('CONTROLLER_ERROR',type(exc).__name__,str(exc),flush=True)
        return 2
    finally:
        report['finished_utc']=utc();write(run/'controller-report.json',report)
        print('CONTROLLER_REPORT',run/'controller-report.json',flush=True)

if __name__=='__main__':raise SystemExit(main())
