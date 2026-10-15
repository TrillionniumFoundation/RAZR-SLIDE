"""Read public manufacturer originals into a directory outside the repository."""
import argparse, datetime, hashlib, json, subprocess, urllib.request
from pathlib import Path

SOURCES = [
    ('LF.pdf', 'https://www.qnityelectronics.com/content/dam/electronics/amer/us/en/electronics/public/documents/en/EI-10118-Pyralux-LF-CL-Data-Sheet.pdf'),
    ('LF.html', 'https://www.qnityelectronics.com/products/pyralux-lf-acrylic-based-coverlay.html'),
    ('AC.html', 'https://www.qnityelectronics.com/products/pyralux-ac-all-polyimide-single-sided-copper-clad-laminate.html'),
    ('AC_manufacturer_mirror.pdf', 'https://www.epectec.com/downloads/DuPont-Pyralux-AC-Data-Sheet.pdf'),
    ('Gatema_outer.pdf', 'https://www.gatema.com/wp-content/uploads/2023/08/design-rules-rigidflex-outer.pdf'),
]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw-dir', required=True);a=ap.parse_args()
    root=Path(a.raw_dir).resolve()
    if 'production-audit' in root.parts or any((p/'.git').exists() for p in [root,*root.parents]):
        raise ValueError('manufacturer originals must remain outside Git')
    root.mkdir(parents=True,exist_ok=False)
    rows=[]
    for name,url in SOURCES:
        row={'name':name,'url':url,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'RAZR-SLIDE-engineering-source-audit/1.0'})
            with urllib.request.urlopen(req,timeout=35) as r:
                data=r.read();row.update(http_status=r.status,final_url=r.geturl(),content_type=r.headers.get('Content-Type'))
            if name.endswith('.pdf') and not data.startswith(b'%PDF'):raise ValueError('not PDF bytes')
            target=root/name;target.write_bytes(data)
            row.update(size=len(data),sha256=hashlib.sha256(data).hexdigest(),raw_path=str(target))
            if name.endswith('.pdf'):
                info=subprocess.run(['pdfinfo',str(target)],capture_output=True,text=True)
                row['pdfinfo_exit']=info.returncode
                row['pages']=[z.split(':',1)[1].strip() for z in info.stdout.splitlines() if z.startswith('Pages:')]
                txt=target.with_suffix('.txt')
                ext=subprocess.run(['pdftotext','-layout',str(target),str(txt)],capture_output=True,text=True)
                row['pdftotext_exit']=ext.returncode
                if ext.returncode==0:
                    b=txt.read_bytes();row['extracted_text_sha256']=hashlib.sha256(b).hexdigest()
                    # Only bounded presence markers; no manufacturer full text is exported.
                    t=b.decode(errors='replace');row['document_markers']={k:k in t for k in ['EI-10118','EI-10122','LF7001','AC181200','IPC-4204','Dynamic']}
            row['downloaded']=True
        except Exception as e:
            row.update(downloaded=False,error_type=type(e).__name__,error=str(e))
        rows.append(row)
    report={'sources':rows,'raw_documents_committed':False,'all_values_are_product_nominals_not_finished_project_stackup':True,'manufacturing_go':False}
    (root/'download-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return 0 if any(r.get('downloaded') for r in rows) else 1

if __name__=='__main__':raise SystemExit(main())
