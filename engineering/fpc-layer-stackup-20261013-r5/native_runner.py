"""Independent-host validation with exact input bytes; no physical qualification."""
import hashlib,json,subprocess,sys
from pathlib import Path
p=Path(__file__).resolve().parent
names=['layer_stackup.py','test_layer_stackup.py','native_runner.py']
before={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in names}
steps=[]
for name,cmd in [('tests',[sys.executable,'-B','-m','unittest','-v','test_layer_stackup']),('sections',[sys.executable,'-B','layer_stackup.py'])]:
 r=subprocess.run(cmd,cwd=p,capture_output=True,text=True)
 (p/(name+'.stdout.log')).write_text(r.stdout)
 (p/(name+'.stderr.log')).write_text(r.stderr)
 steps.append({'name':name,'command':cmd,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
after={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in names}
result={'steps':steps,'source_sha256_before':before,'source_sha256_after':after,'unchanged':before==after,'manufacturing_go':False}
(p/'native_execution.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(0 if before==after and all(r['exit_code']==0 for r in steps) else 1)
