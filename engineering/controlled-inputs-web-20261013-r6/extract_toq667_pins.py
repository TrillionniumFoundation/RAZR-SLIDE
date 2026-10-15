import argparse,csv,hashlib,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('pdf')
p.add_argument('outdir')
args=p.parse_args()
pdf=Path(args.pdf);out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
expected='f34fc7b63eeffdcc0d4d71d68d14be4b22786ed6de53e69948401c975acb98ed'
assert hashlib.sha256(pdf.read_bytes()).hexdigest()==expected
text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-']).decode('utf-8')
pages=text.split('\f')
assert len(pages)>=39
pins=[]
for index in (5,6):
 block=pages[index].split('2.2')[0]
 for line in block.splitlines():
  m=re.match(r'^\s*(\d{1,2})\s+(\S+)\s+([IOP-])(?:\s|$)',line)
  if m:pins.append({'pin':int(m.group(1)),'symbol':m.group(2),'io_declared':m.group(3)})
assert [x['pin'] for x in pins]==list(range(1,41)),pins
assert pins[37]['symbol']=='TP_SDA' and pins[37]['io_declared']=='I'
with (out/'toq667_40pins.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['pin','symbol','io_declared']);w.writeheader();w.writerows(pins)
facts={'input_pdf_sha256':expected,'pages':39,'pin_count':len(pins),'csv_sha256':hashlib.sha256((out/'toq667_40pins.csv').read_bytes()).hexdigest(),'source_pages':[6,7],'source_scope':'supplier candidate; not selected or controlled project OLED','io_scope':'literal supplier declarations retained, including TP_SDA I; no electrical inference','dynamic_minimum_bend_radius_mm':None,'qualified_cycle_count':None,'complete_module_thickness_mm':None,'neutral_axis_mm':None,'manufacturing_go':False}
(out/'toq667_pin_extraction.json').write_text(json.dumps(facts,indent=2)+'\n')
print(json.dumps(facts),flush=True)

