"""Run real KiCad 9 parser/ERC and owned model in an isolated R4 output dir."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile,xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent
runtime=Path('/home/alex/RAZR-SLIDE-kicad9-erc-runtime-20261013-r2')
env=dict(os.environ,LD_LIBRARY_PATH=str(runtime/'root/usr/lib/x86_64-linux-gnu'),
 XDG_CONFIG_HOME=str(runtime/'config'),KICAD_STOCK_DATA_HOME=str(runtime/'root/usr/share/kicad'))
cli=str(runtime/'root/usr/bin/kicad-cli')
names=['proof_detector_research.kicad_sch','proof_detector_research.kicad_pro',
       'OwnedProof.kicad_sym','sym-lib-table','terminal_netlist.json','proof_model.py','test_proof_model.py']
before={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in names}
rows=[]
commands=[('version',[cli,'--version']),
 ('netlist',[cli,'sch','export','netlist','--format','kicadxml','-o',str(P/'native.xml'),str(P/names[0])]),
 ('svg',[cli,'sch','export','svg','-o',str(P/'svg'),str(P/names[0])]),
 ('ERC',[cli,'sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(P/'ERC.json'),str(P/names[0])]),
 ('model',[sys.executable,str(P/'test_proof_model.py')])]
for op,args in commands:
 r=subprocess.run(args,env=env,cwd=P,capture_output=True,text=True)
 rows.append({'operation':op,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 (P/(op+'.stdout.log')).write_text(r.stdout);(P/(op+'.stderr.log')).write_text(r.stderr)
expected=json.loads((P/'terminal_netlist.json').read_text())['components'];actual={};duplicate=[]
xml=ET.parse(P/'native.xml').getroot()
for net in xml.find('nets'):
 for node in net.findall('node'):
  key=(node.attrib['ref'],node.attrib['pin'])
  if key in actual:duplicate.append(key)
  actual[key]=net.attrib['name']
wrong=[];keys=set()
for c in expected:
 for pin,term in c['pins'].items():
  key=c['ref'],pin;keys.add(key);a=actual.get(key);e=term['net']
  if e is not None and a!='/'+e:wrong.append({'key':key,'expected':'/'+e,'actual':a})
  if e is None and a is not None and not a.startswith('unconnected-('+c['ref']+'-'):wrong.append({'key':key,'expected':None,'actual':a})
extras=sorted(set(actual)-keys)
erc=json.loads((P/'ERC.json').read_text());counts={}
for sheet in erc.get('sheets',[]):
 for v in sheet.get('violations',[]):counts[v['type']]=counts.get(v['type'],0)+1
after={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in names}
receipt={'rows':rows,'native_components':len(xml.find('components')),'expected_components':len(expected),
 'native_pins':len(actual),'expected_pins':len(keys),'wrong_pin_mappings':wrong,'duplicates':duplicate,'extra_pins':extras,
 'ERC_counts':counts,'before':before,'after':after,'inputs_unchanged':before==after,
 'ERC_is_physical_qualification':False,'manufacturing_go':False}
(P/'native_execution.json').write_text(json.dumps(receipt,indent=2)+'\n')
with tarfile.open(P/'native_outputs.tar.gz','w:gz') as t:
 for n in ['native.xml','ERC.json','native_execution.json','model_receipt.json','version.stdout.log','version.stderr.log',
           'netlist.stdout.log','netlist.stderr.log','svg.stdout.log','svg.stderr.log','ERC.stdout.log','ERC.stderr.log',
           'model.stdout.log','model.stderr.log']:
  t.add(P/n,arcname=n)
 t.add(P/'svg',arcname='svg')
ok=all(r['exit']==0 for r in rows) and not wrong and not duplicate and not extras and not counts and before==after
print(json.dumps({'native_success':ok,'rows':[{k:r[k] for k in ['operation','exit']} for r in rows],
 'ERC_counts':counts,'native_pins':len(actual),'expected_pins':len(keys),
 'native_outputs_bytes':(P/'native_outputs.tar.gz').stat().st_size,
 'native_outputs_sha256':hashlib.sha256((P/'native_outputs.tar.gz').read_bytes()).hexdigest(),
 'manufacturing_go':False}))
raise SystemExit(0 if ok else 1)
