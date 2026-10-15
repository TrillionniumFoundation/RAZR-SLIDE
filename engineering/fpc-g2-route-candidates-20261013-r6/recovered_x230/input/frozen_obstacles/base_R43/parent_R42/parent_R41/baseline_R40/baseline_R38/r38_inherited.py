"""Fresh, isolated R21-R37 tests using original unmodified R37 ZIP.
No archived test output is counted; each case requires new exit=0 and Ran N / OK.
"""
import os,re,json,hashlib,zipfile,subprocess,time,concurrent.futures,shutil
from pathlib import Path
from r37_regression import CASES as R21_R36_CASES
ROOT=Path(__file__).resolve().parent
SOURCE=Path(os.environ.get('R37_SOURCE_ZIP','/mnt/data/files/RAZR_SLIDE_R37_verified_engineering_package_20261011.zip'))
CELL=Path('/mnt/data/R38_fresh_R37_test_cell')
CASES=R21_R36_CASES + [('R37',48,'.','test_r37.py')]
OUT=ROOT/'verification'
EXPECTED_ZIP_SHA='b0013a530c980d10a53a48fb25db0919636ac81184b8f20c1e98a0704838b487'

def run():
    if CELL.exists():shutil.rmtree(CELL)
    CELL.mkdir(parents=True)
    if SOURCE.exists():
        with open(SOURCE,'rb') as f:observed=hashlib.file_digest(f,'sha256').hexdigest()
        assert observed==EXPECTED_ZIP_SHA
        with zipfile.ZipFile(SOURCE) as z:
            assert z.testzip() is None
            z.extractall(CELL)
            total_members=len(z.namelist())
        provenance='external_R37_zip_verified'
    else:
        # Reproducible offline regression, NOT an independent chain-of-custody check.
        frozen=json.loads((ROOT/'audit/R38_R37_frozen_manifest.json').read_text())
        assert frozen['R37_original_zip_sha256']==EXPECTED_ZIP_SHA
        for entry in frozen['entries']:
            src=ROOT/entry['path']
            assert src.is_file() and hashlib.sha256(src.read_bytes()).hexdigest()==entry['sha256']
            dst=CELL/entry['path'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
        total_members=len(frozen['entries'])
        observed=None
        provenance='internal_manifest_only_no_external_source'
    assert total_members==1043
    results=[]
    (OUT/'R38_inherited_progress.json').write_text(json.dumps({'status':'running','completed':0,'total':len(CASES)})+'\n')
    def task(case):
        label,n,path,file=case
        t=time.perf_counter()
        p=subprocess.run(['python','-m','unittest','-q',file],cwd=CELL/path,
             env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1'},
             capture_output=True,text=True,timeout=300)
        dest=OUT/f'R38_inherited_{label}.log'
        dest.write_text((p.stdout or '')+(p.stderr or ''))
        s=dest.read_text();m=re.search(r'Ran\s+(\d+)\s+tests?',s)
        got=int(m.group(1)) if m else None
        good=p.returncode==0 and got==n and s.rstrip().endswith('OK')
        return {'label':label,'expected_count':n,'actual_count':got,'exit_code':p.returncode,
                'success':good,'elapsed_s':round(time.perf_counter()-t,3),
                'log':str(dest.relative_to(ROOT)),
                'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
                'failure_excerpt':s[-800:] if not good else None}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        futures={ex.submit(task,c):c[0] for c in CASES}
        for f in concurrent.futures.as_completed(futures):
            try:record=f.result()
            except BaseException as exc:
                record={'label':futures[f],'success':False,'error':str(exc),'actual_count':None}
            results.append(record)
            print('R38 FRESH',record['label'],record.get('actual_count'),record['success'],flush=True)
            (OUT/'R38_inherited_progress.json').write_text(json.dumps({'status':'running','completed':len(results),'total':len(CASES),'rows':results},indent=2)+'\n')
    total=sum(q.get('actual_count') or 0 for q in results)
    ok=all(q['success'] for q in results) and total==661
    report={'status':'passed' if ok else 'failed','success':ok,'fresh_total':total,
            'original_zip_sha256':observed,'original_member_count':total_members,'provenance_mode':provenance,
            'independent_test_cell':str(CELL),'cases':results,'manufacturing_go':False}
    (OUT/'R38_inherited_results.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'R38_inherited_progress.json').write_text(json.dumps({'status':report['status'],'completed':len(results),'total':len(CASES),'rows':results},indent=2)+'\n')
    print('R38 FRESH INHERITED SUMMARY',total,ok,flush=True)
    if not ok:raise SystemExit(1)
if __name__=='__main__':run()
