import json,hashlib,time,subprocess
from pathlib import Path
import requests
root=Path('/home/qian-qi/RAZR-SLIDE-controlled-inputs-web-r6-20261013')
root.mkdir(parents=True,exist_ok=True)
inputs=[
('allflex_minimum_bend_7p','https://www.allflexinc.com/wp-content/uploads/2024/03/Minimum-Bend-Radius-Considerations-in-Flexible-Circuits.pdf'),
('allflex_design_28p','https://www.allflexinc.com/wp-content/uploads/2025/05/322822-PC-AllFlex-Circuit_Heater-Design-Guide-0408b.pdf'),
('tianma_consumer_2026_5p','https://usa.tianma.com/wp-content/uploads/2026/05/Tianma-Display-Week-2026-Consumer-Technology.pdf')]
results=[]
for name,url in inputs:
 r={'name':name,'url':url,'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'native_sha256':None}
 try:
  response=requests.get(url,timeout=(8,25),stream=True)
  r.update(http_status=response.status_code,final_url=response.url,content_type=response.headers.get('Content-Type'))
  response.raise_for_status()
  b=b''
  for chunk in response.iter_content(65536):
   b+=chunk
   if len(b)>32000000:raise RuntimeError('bounded_download_limit_32MB')
  if not b.startswith(b'%PDF'):raise RuntimeError('not_pdf_header')
  p=root/(name+'.pdf');p.write_bytes(b)
  r.update(bytes=len(b),native_sha256=hashlib.sha256(b).hexdigest(),native_path=str(p))
  info=subprocess.run(['pdfinfo',str(p)],capture_output=True,text=True)
  r['pdfinfo_returncode']=info.returncode
  r['pdfinfo_metadata']=[l for l in info.stdout.splitlines() if l.startswith(('Pages:','Page size:','PDF version:'))]
  txt=p.with_suffix('.txt')
  ext=subprocess.run(['pdftotext','-layout',str(p),str(txt)],capture_output=True,text=True)
  r['pdftotext_returncode']=ext.returncode
  r['native_extract_sha256']=hashlib.sha256(txt.read_bytes()).hexdigest() if txt.exists() else None
 except Exception as e:r.update(error_type=type(e).__name__,error=str(e))
 results.append(r)
 print(json.dumps(r,ensure_ascii=True),flush=True)
(root/'download_receipt.json').write_text(json.dumps({'records':results,'manufacturing_go':False},indent=2)+'\n')

