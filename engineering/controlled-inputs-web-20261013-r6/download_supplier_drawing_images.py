import requests,hashlib,json
from pathlib import Path
root=Path('/home/qian-qi/RAZR-SLIDE-controlled-inputs-web-r6-20261013')
items=[
('hicenda_mechanical','https://cdn.shopify.com/s/files/1/0734/6592/1614/files/6.67_Inch_Flexible_Display_Drawing.jpg?v=1779530344'),
('hicenda_40pin','https://cdn.shopify.com/s/files/1/0734/6592/1614/files/6.67_Inch_Flexible_Display_40Pins.jpg?v=1779530368')]
for n,u in items:
 d={'name':n,'url':u,'sha256':None}
 try:
  r=requests.get(u,timeout=(8,20));d.update(status=r.status_code,content_type=r.headers.get('Content-Type'));r.raise_for_status()
  if not r.content.startswith(b'\xff\xd8'):raise RuntimeError('not_jpeg')
  p=root/(n+'.jpg');p.write_bytes(r.content);d.update(bytes=len(r.content),sha256=hashlib.sha256(r.content).hexdigest(),native_path=str(p))
 except Exception as e:d.update(error_type=type(e).__name__,error=str(e))
 print(json.dumps(d),flush=True)

