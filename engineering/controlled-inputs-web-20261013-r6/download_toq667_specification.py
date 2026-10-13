import json,hashlib,subprocess,time
from pathlib import Path
import requests
root=Path('/home/qian-qi/RAZR-SLIDE-controlled-inputs-web-r6-20261013')
url='https://tailorpixels.com/wp-content/uploads/2026/01/TOQ667XHT-01C-6.67-inch-Flexible-Touch-AMOLED-2400x1080-MIPI.pdf'
d={'name':'tailorpixels_TOQ667XHT_01C_39p','url':url,'sha256':None,'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
try:
 r=requests.get(url,timeout=(8,25));d.update(http_status=r.status_code,final_url=r.url,content_type=r.headers.get('Content-Type'));r.raise_for_status()
 if not r.content.startswith(b'%PDF'):raise RuntimeError('not_pdf')
 p=root/'tailorpixels_TOQ667XHT_01C_39p.pdf';p.write_bytes(r.content)
 d.update(bytes=len(r.content),sha256=hashlib.sha256(r.content).hexdigest(),native_path=str(p))
 info=subprocess.run(['pdfinfo',str(p)],capture_output=True,text=True)
 d['pdfinfo_returncode']=info.returncode
 d['pdfinfo_metadata']=[l for l in info.stdout.splitlines() if l.startswith(('Pages:','Page size:','PDF version:'))]
 text=p.with_suffix('.txt')
 ext=subprocess.run(['pdftotext','-layout',str(p),str(text)],capture_output=True,text=True);d['pdftotext_returncode']=ext.returncode
 d['native_text_sha256']=hashlib.sha256(text.read_bytes()).hexdigest() if text.exists() else None
except Exception as e:d.update(error_type=type(e).__name__,error=str(e))
print(json.dumps(d),flush=True)
(root/'tailorpixels_download_receipt.json').write_text(json.dumps(d,indent=2)+'\n')

