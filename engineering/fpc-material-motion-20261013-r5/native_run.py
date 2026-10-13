#!/usr/bin/env python3
"""Record natural child exits on fixed material-motion inputs."""
import argparse,hashlib,json,platform,socket,subprocess,sys
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out-dir',type=Path,required=True);a=p.parse_args();out=a.out_dir.resolve();out.mkdir(parents=True,exist_ok=True);root=Path(__file__).resolve().parent
    own=['material_motion.py','test_material_motion.py','condition_material_cases.py','conditional_section_inputs.json','native_run.py','frozen_source_manifest.json']
    frozen=[r['copy'] for r in json.loads((root/'frozen_source_manifest.json').read_text())['inputs']]
    before={n:sha(root/n) for n in own+frozen}
    commands=[('tests',[sys.executable,'-B','-m','unittest','-v','test_material_motion.py']),('motion',[sys.executable,'-B',str(root/'material_motion.py'),'--out-dir',str(out)]),
      ('sections',[sys.executable,'-B',str(root/'condition_material_cases.py'),'--history',str(out/'material_history.npz'),'--out',str(out/'conditional_material_report.json')])]
    exits={}
    for name,command in commands:
        run=subprocess.run(command,cwd=root,text=True,capture_output=True);exits[name]=run.returncode
        (out/(name+'.stdout.log')).write_text(run.stdout);(out/(name+'.stderr.log')).write_text(run.stderr)
        print(name,'actual exit',run.returncode,flush=True)
        if run.returncode:break
    after={n:sha(root/n) for n in before}
    result={'hostname':socket.gethostname(),'python':platform.python_version(),'platform':platform.platform(),'cadquery':__import__('cadquery').__version__,
     'actual_child_exits':exits,'frozen_input_count':len(before),'input_sha256_before':before,'input_sha256_after':after,'all_input_bytes_unchanged':before==after,'manufacturing_go':False}
    (out/'native_receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    if any(exits.get(n)!=0 for n in ('tests','motion','sections')) or before!=after:raise SystemExit(1)

if __name__=='__main__':main()
