"""Independently rerun frozen R21-R38 test suites from an untouched R38 ZIP.
Do NOT mistake these assertion suites for hardware qualification, and do NOT
count archived PASS logs. Abnormal exit / count mismatch / timeout is FAIL.
"""
import os,re,json,time,hashlib,zipfile,subprocess,concurrent.futures
from pathlib import Path
from r38_inherited import CASES
ROOT=Path(__file__).resolve().parent
INPUT=Path(os.environ.get('R39_R38_ZIP','/mnt/data/RAZR_SLIDE_R38_verified_engineering_package_20261011.zip'))
SOURCE_EXPECTED='649c89711e5bd25a357fbac972d1c0e4ac8144841dd34e8b261cd67aa50bb7a6'
CELL=Path(os.environ.get('R39_LEGACY_CELL','/mnt/data/R39_legacy_fresh_cell'))
OUT=ROOT/'verification'
CASES39=CASES + [('R38',36,'.','test_r38.py')]

def run():
    start=time.time();CELL.mkdir(parents=True,exist_ok=True);OUT.mkdir(exist_ok=True)
    sha=hashlib.file_digest(INPUT.open('rb'),'sha256').hexdigest()
    if sha!=SOURCE_EXPECTED:raise RuntimeError(f'Invalid R38 frozen zip {sha}')
    with zipfile.ZipFile(INPUT) as z:
        if z.testzip() is not None:raise RuntimeError('R38 original archive CRC failed')
        names=z.namelist()
        if len(names)!=1094:raise RuntimeError('Unexpected archived source count')
        z.extractall(CELL)
        for n in names:
            if hashlib.sha256((CELL/n).read_bytes()).digest()!=hashlib.sha256(z.read(n)).digest():raise RuntimeError('frozen file mismatch '+n)
    print('R39 frozen source verified',sha,len(names),flush=True)
    def task(c):
        label,expected,rel,name=c
        dest=OUT/f'R39_inherited_{label}.log'
        t=time.monotonic()
        try:
            p=subprocess.run(['python','-m','unittest','-q',name],cwd=CELL/rel,
                env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},capture_output=True,text=True,timeout=180)
            content=(p.stdout or '')+(p.stderr or '')
            rc=p.returncode
        except subprocess.TimeoutExpired as e:
            content='TIMED OUT '+str(e);rc=-1000
        dest.write_text(content)
        m=re.search(r'Ran\s+(\d+)\s+tests?',content)
        actual=int(m.group(1)) if m else None
        passed=rc==0 and actual==expected and content.rstrip().endswith('OK')
        return dict(suite=label,expected=expected,actual=actual,exit_code=rc,
            ok=passed,seconds=round(time.monotonic()-t,3),
            log=str(dest.relative_to(ROOT)),sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
    records=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures={executor.submit(task,c):c[0] for c in CASES39}
        for future in concurrent.futures.as_completed(futures):
            try:r=future.result()
            except BaseException as exc:r={'suite':futures[future],'ok':False,'exception':repr(exc)}
            records.append(r)
            print('R39 RETEST',r['suite'],r.get('actual'),'PASS' if r.get('ok') else 'FAIL','t',r.get('seconds'),flush=True)
            progress=dict(basis='frozen R38 SHA verified',finished=len(records),total=len(CASES39),items=sorted(records,key=lambda x:x['suite']))
            (OUT/'R39_inherited_progress.json').write_text(json.dumps(progress,indent=2)+'\n')
    total=sum(r.get('actual') or 0 for r in records)
    okay=all(r.get('ok') for r in records) and total==697
    result=dict(source_R38_sha=sha,source_R38_members=len(names),
        fresh_isolated_source_test_cell=str(CELL),total_suites=len(records),
        historical_reexecuted_tests=total,expected_tests=697,all_passed=okay,
        receipts=sorted(records,key=lambda x:x['suite']),
        wall_s=round(time.time()-start,3),hardware_mfg_go=False)
    (OUT/'R39_inherited_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('R39 frozen history summary',total,okay,flush=True)
    if not okay:raise SystemExit(1)
    return result
if __name__=='__main__':run()
