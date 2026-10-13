#!/usr/bin/env python3
"""Execute immutable transferred STEP checks on the actual X230 CAD runtime."""
import hashlib,json,platform,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent
PAYLOAD_ROOT=HERE.parents[2]
PYTHON='/home/qian/RAZR-SLIDE-work-20261013/cad-venv/bin/python'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def snapshot(m):
    actual={}
    for row in m['files']:
        path=PAYLOAD_ROOT/row['path']
        digest=sha(path)
        if digest!=row['sha256'] or path.stat().st_size!=row['size']:
            raise ValueError('Transferred input size/SHA differs: '+row['path'])
        actual[row['path']]=digest
    return actual

def main():
    m=json.loads((HERE/'transfer-input-manifest.json').read_text())
    before=snapshot(m);native=[]
    for stem,script in [('geometry','verify_exported_veto.py'),('material-support','verify_material_support_path.py'),('full-payload','verify_full_payload.py')]:
        started=time.monotonic()
        with (HERE/(stem+'.stdout.log')).open('wb') as out,(HERE/(stem+'.stderr.log')).open('wb') as err:
            r=subprocess.run([PYTHON,str(PROJECT/'independent'/script)],cwd=PAYLOAD_ROOT,stdout=out,stderr=err,check=False)
        native.append({'operation':stem,'native_exit_code':r.returncode,'elapsed_monotonic_seconds':time.monotonic()-started,
            'stdout_sha256':sha(HERE/(stem+'.stdout.log')),'stderr_sha256':sha(HERE/(stem+'.stderr.log'))})
    after=snapshot(m)
    result={'host':platform.node(),'configured_host':'x230','python_runtime':PYTHON,
        'transfer_manifest_sha256':sha(HERE/'transfer-input-manifest.json'),
        'input_file_count':len(before),'before_source_hashes':before,'after_source_hashes':after,
        'all_transferred_source_and_STEP_bytes_unchanged':before==after,'native_operations':native,
        'manufacturing_go':False}
    (HERE/'remote-native-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'configured_host':'x230','host':platform.node(),'native_operations':native,
                     'all_transferred_source_and_STEP_bytes_unchanged':before==after,'manufacturing_go':False},indent=2))
    if before!=after or any(r['native_exit_code']!=0 for r in native):
        raise SystemExit(1)
if __name__=='__main__':main()
