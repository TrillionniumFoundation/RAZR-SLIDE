#!/usr/bin/env python3
"""Retrieve public manufacturer inputs without redistributing their files."""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path

def hirose(part, kind):
    path=f'/api/v1/products/{part}/documents/{kind}/content'
    if kind!='model_3d_step':path+='?lang=EN'
    import urllib.parse
    return f'https://www.hirose.com/en/product/p/{part}/documents?path='+urllib.parse.quote(path,safe='')

SOURCES={
 'hirose_DP_2d.pdf':hirose('CL0673-5024-0-53','drawing_2d'),
 'hirose_DS_2d.pdf':hirose('CL0673-5025-0-53','drawing_2d'),
 'hirose_DP_spec.pdf':hirose('CL0673-5024-0-53','spec_sheet'),
 'hirose_DS_spec.pdf':hirose('CL0673-5025-0-53','spec_sheet'),
 'hirose_DP_step.zip':hirose('CL0673-5024-0-53','model_3d_step'),
 'hirose_DS_step.zip':hirose('CL0673-5025-0-53','model_3d_step'),
 'hirose_guideline.pdf':hirose('CL0673-5024-0-53','items/515c108a-21a6-4e26-a862-8e9a8efe52e8'),
 'we_2025_flex_guide.pdf':'https://www.we-online.com/files/pdf1/design-guide-flex-solutions-cbt-en.pdf',
 'we_pureflex_rules.pdf':'https://www.we-online.com/files/pdf1/design-rules-pureflex-cbt-en.pdf',
 'we_FLEX1_stackup.pdf':'https://www.we-online.com/files/pdf1/en_flex1_1f-ri_030_17_2v13.pdf',
 'we_FLEX2_stackup.pdf':'https://www.we-online.com/files/pdf1/en_flex2_2f-ri_027_17_2v13.pdf',
 'we_FLEX2_ipc2581.cvg':'https://www.we-online.com/files/cvg1/en_flex2_2f-ri_027_17_2v13.cvg',
 'sierra_dynamic_rules.html':'https://www.protoexpress.com/blog/flex-pcb-design-guidelines-for-manufacturing/',
}

def fetch_one(item,out):
    name,url=item
    row={'name':name,'source_url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat()}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'RAZR-SLIDE engineering source verification'})
        with urllib.request.urlopen(req,timeout=45) as response:
            payload=response.read()
            row.update(status_code=response.status,final_url=response.url,content_type=response.headers.get('Content-Type'))
        path=out/name;path.write_bytes(payload)
        row.update(size_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),raw_path=str(path.resolve()))
        if name.endswith('.pdf'):
            if not payload.startswith(b'%PDF-'):raise ValueError('response is not PDF')
            from pypdf import PdfReader
            row['page_count']=len(PdfReader(path).pages)
        if name.endswith('.zip'):
            with zipfile.ZipFile(path) as z:
                if z.testzip() is not None:raise ValueError('ZIP CRC mismatch')
                row['members']=[{'name':m.filename,'size_bytes':m.file_size,'sha256':hashlib.sha256(z.read(m)).hexdigest()} for m in z.infolist() if not m.is_dir()]
        row['retrieval_verified']=True
    except Exception as exc:
        row.update(retrieval_verified=False,error_type=type(exc).__name__,error=str(exc))
    return row

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[2]
    raw=a.raw_dir.resolve()
    if raw==root or root in raw.parents:raise ValueError('vendor raw inputs must remain outside this git worktree')
    raw.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        rows=list(ex.map(lambda item:fetch_one(item,raw),SOURCES.items()))
    report={'results':rows,'successful_count':sum(r['retrieval_verified'] for r in rows),'third_party_raw_files_committed':False,'public_generic_inputs_are_project_qualified':False,'emails_or_NDA_or_orders_sent':0,'manufacturing_go':False}
    a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'successful':report['successful_count'],'attempted':len(rows),'manufacturing_go':False}))
    if report['successful_count']!=len(rows):raise SystemExit(1)

if __name__=='__main__':main()
