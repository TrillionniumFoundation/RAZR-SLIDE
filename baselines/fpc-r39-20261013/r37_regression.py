"""Run R21-R36 fresh unit tests in separate R36 source ZIP extraction.
Preserves every byte of R37's inherited 977 files. Not a hardware qualification.
"""
from pathlib import Path
import concurrent.futures,datetime,json,os,re,subprocess,time,zipfile,hashlib,shutil
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'files/RAZR_SLIDE_R36_verified_engineering_package_20261011.zip'
CELL=ROOT.parent/'R37_fresh_R36_test_cell'
VERIF=ROOT/'verification'
CASES=[
 ('R21',28,'baseline_R24/baseline_R23/baseline_R22/baselines/R21','test_r21.py'),
 ('R22',37,'baseline_R24/baseline_R23/baseline_R22','test_r22.py'),
 ('R22_adversarial',11,'baseline_R24/baseline_R23/baseline_R22','test_r22_adversarial.py'),
 ('R23',22,'baseline_R24/baseline_R23','test_r23.py'),
 ('R24',25,'baseline_R24','test_r24.py'),
 ('R25',30,'.','test_r25.py'),('R26',38,'.','test_r26.py'),('R27',35,'.','test_r27.py'),
 ('R28',42,'.','test_r28.py'),('R29',40,'.','test_r29.py'),('R30',40,'.','test_r30.py'),
 ('R31',45,'.','test_r31.py'),('R32',40,'.','test_r32.py'),('R33',40,'.','test_r33.py'),
 ('R34',36,'.','test_r34.py'),('R35',50,'.','test_r35.py'),('R36',54,'.','test_r36.py')]

def run():
    if CELL.exists():shutil.rmtree(CELL)
    CELL.mkdir(exist_ok=True)
    if SOURCE.exists():
        assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='0f5219663e6eae8c6817e6082c0d60172dcd9228386d3ec661fdbc9b9c2cf74d'
        with zipfile.ZipFile(SOURCE) as z:
            assert z.testzip() is None
            z.extractall(CELL)
        evidence_mode='verified_external_zip'
    else:
        frozen=json.loads((ROOT/'audit/R37_R36_immutable.json').read_text())
        assert len(frozen['entries'])==977
        for row in frozen['entries']:
            src=ROOT/row['path']
            assert src.is_file() and hashlib.sha256(src.read_bytes()).hexdigest()==row['sha256']
            dst=CELL/row['path'];dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,dst)
        evidence_mode='internal_manifest_only_no_external_zip'
    print('R37 fresh R36 cell',evidence_mode,flush=True)
    (VERIF/'R37_inherited_progress.json').write_text(json.dumps(dict(status='running',completed=0,total=len(CASES)))+'\n')
    def task(case):
        name,count,folder,file=case
        path=CELL/folder
        dest=VERIF/f'R37_inherited_{name}.log'
        start=time.perf_counter()
        p=subprocess.run(['python3','-m','unittest','-q',file],cwd=path,
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1'},
            capture_output=True,text=True)
        dest.write_text((p.stdout or '')+(p.stderr or ''))
        contents=dest.read_text()
        m=re.search(r'Ran\s+(\d+)\s+tests?',contents)
        valid=p.returncode==0 and m is not None and int(m.group(1))==count and contents.rstrip().endswith('OK')
        return dict(label=name,expected_count=count,actual_count=int(m.group(1)) if m else None,
            returncode=p.returncode,success=valid,seconds=round(time.perf_counter()-start,2),
            log=str(dest.relative_to(ROOT)),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
            error_tail=contents[-500:] if not valid else None)
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futs={ex.submit(task,case):case[0] for case in CASES}
        for f in concurrent.futures.as_completed(futs):
            r=f.result();results.append(r)
            print('R37 inherited',r['label'],r['actual_count'],r['success'],r['seconds'],flush=True)
            (VERIF/'R37_inherited_progress.json').write_text(json.dumps(dict(status='running',completed=len(results),total=len(CASES),rows=results),indent=2)+'\n')
    ok=all(r['success'] for r in results) and sum(r['actual_count'] or 0 for r in results)==613
    out=dict(success=ok,R36_fresh_inherited_count=sum(r['actual_count'] or 0 for r in results),
        cases=sorted(results,key=lambda r:[c[0] for c in CASES].index(r['label'])),
        isolation_path=str(CELL),source_verification_mode=evidence_mode,manufacturing_go=False)
    (VERIF/'R37_inherited_receipts.json').write_text(json.dumps(out,indent=2)+'\n')
    (VERIF/'R37_inherited_exit.code').write_text('0\n' if ok else '1\n')
    print('R37 HISTORICAL COMPLETE',ok,out['R36_fresh_inherited_count'],flush=True)
    if not ok:raise SystemExit(1)
if __name__=='__main__':run()
