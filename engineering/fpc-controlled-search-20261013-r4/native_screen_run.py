#!/usr/bin/env python3
"""Record real local/remote child exits and unchanged frozen own inputs."""
import argparse,hashlib,json,platform,socket,subprocess,sys
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out=a.out.resolve();root=Path(__file__).resolve().parent
    inputs=['dynamic_input_rules.py','test_dynamic_input_rules.py','input_audit.json','native_screen_run.py']
    before={name:sha(root/name) for name in inputs}
    test=subprocess.run([sys.executable,'-B','-m','unittest','-v','test_dynamic_input_rules.py'],cwd=root,text=True,capture_output=True)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    screen_path=a.out.parent/'dynamic_screen_native.json'
    screen=subprocess.run([sys.executable,'-B',str(root/'dynamic_input_rules.py'),'--folder',str(root),'--out',str(screen_path)],cwd=root,text=True,capture_output=True)
    after={name:sha(root/name) for name in inputs}
    for label,run in [('tests',test),('screen',screen)]:
        a.out.with_name(a.out.stem+'_'+label+'.stdout.log').write_text(run.stdout)
        a.out.with_name(a.out.stem+'_'+label+'.stderr.log').write_text(run.stderr)
    result={'hostname':socket.gethostname(),'platform':platform.platform(),'python_version':platform.python_version(),'python_executable':sys.executable,'actual_test_exit':test.returncode,'actual_screen_exit':screen.returncode,'input_sha256_before':before,'input_sha256_after':after,'frozen_input_bytes_unchanged':before==after,'screen_output_sha256':sha(screen_path) if screen_path.exists() else None,'manufacturing_go':False}
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    if test.returncode or screen.returncode or before!=after:raise SystemExit(1)

if __name__=='__main__':main()
