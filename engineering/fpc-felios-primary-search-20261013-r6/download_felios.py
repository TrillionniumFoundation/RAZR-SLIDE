"""Anonymous primary-source acquisition; originals stay outside Git."""
from pathlib import Path
import argparse,hashlib,json,subprocess,urllib.request
sources=[('felios_legacy.pdf','https://industrial.panasonic.com/cdbs/www-data/pdf/EMD0000/ast-ind-261831.pdf'),('felios_202212.pdf','https://industrial.panasonic.com/cdbs/www-data/pdf/EMD0000/ast-ind-261836.pdf')]
a=argparse.ArgumentParser();a.add_argument('--raw-dir',required=True);p=Path(a.parse_args().raw_dir).resolve()
if any((q/'.git').exists() for q in [p,*p.parents]) or 'production-audit' in p.parts:raise ValueError('raw vendor documents cannot be placed in Git')
p.mkdir(parents=True,exist_ok=False)
rows=[]
for name,url in sources:
 row={'name':name,'url':url}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'RAZR-SLIDE-source-audit/1.0'}),timeout=25) as r:
   b=r.read();row.update(http_status=r.status,final_url=r.geturl(),content_type=r.headers.get('Content-Type'))
  if not b.startswith(b'%PDF'):raise ValueError('not PDF')
  f=p/name;f.write_bytes(b);row.update(size=len(b),sha256=hashlib.sha256(b).hexdigest(),raw_path=str(f))
  q=subprocess.run(['pdfinfo',str(f)],capture_output=True,text=True,timeout=10);row['pdfinfo_exit']=q.returncode;row['pages']=[x.split(':',1)[1].strip() for x in q.stdout.splitlines() if x.startswith('Pages:')]
  q=subprocess.run(['pdftotext','-layout',str(f),str(f.with_suffix('.txt'))],capture_output=True,text=True,timeout=10);row['pdftotext_exit']=q.returncode
  if q.returncode==0:row['text_sha256']=hashlib.sha256(f.with_suffix('.txt').read_bytes()).hexdigest()
  row['downloaded']=True
 except Exception as e:row.update(downloaded=False,error_type=type(e).__name__,error=str(e))
 rows.append(row);(p/(name+'.receipt.json')).write_text(json.dumps(row,indent=2)+'\n')
report={'sources':rows,'raw_docs_committed':False,'project_selected_FPC':False,'manufacturing_go':False};(p/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
raise SystemExit(0 if all(x.get('downloaded') for x in rows) else 1)
