#!/usr/bin/env python3
"""Recover actual RA laminate order codes, not a finished project FPC."""
import argparse,concurrent.futures,json
from pathlib import Path
from download_primary_inputs import fetch_one
from bs4 import BeautifulSoup

SOURCES={
 'qnity_AC_product.html':'https://www.qnityelectronics.com/products/pyralux-ac-all-polyimide-single-sided-copper-clad-laminate.html',
 'legacy_dupont_AP.pdf':'https://www.dupont.com/content/dam/dupont/amer/us/en/ei-transformation/public/documents/en/EI-10124-Pyralux-AP-Data-Sheet.pdf',
 'legacy_dupont_AC.pdf':'https://www.dupont.com/content/dam/electronics/amer/us/en/electronics/public/documents/en/EI-10122-Pyralux-AC-Data-Sheet%2020230328.pdf',
}

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();raw=a.raw_dir.resolve()
    if Path(__file__).resolve().parents[2] in raw.parents:raise ValueError('raw manufacturer materials must stay outside git')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:retrieval=list(ex.map(lambda item:fetch_one(item,raw),SOURCES.items()))
    html=raw/'qnity_AC_product.html'
    if not retrieval[0]['retrieval_verified']:raise ValueError('current official source not received')
    soup=BeautifulSoup(html.read_bytes(),'html.parser');found={}
    for tr in soup.select('tr'):
        cells=[' '.join(td.get_text(' ',strip=True).split()) for td in tr.find_all(['td','th'])]
        if cells and cells[0] in ('AC181200RY','AC182500RY'):
            if len(cells)!=9 or cells[6]!='RA':raise ValueError('unexpected public product table structure')
            found[cells[0]]={'order_code':cells[0],'foil_type':cells[6],'copper_nominal_um':float(cells[4]),'polyimide_nominal_um':float(cells[7]),'nominal_base_only_thickness_um':float(cells[4])+float(cells[7]),'single_sided':cells[1],'adhesive_type':cells[3],'project_selected':False,'finished_total_stackup_tolerance_um':None,'coverlay_and_coverlay_adhesive':None,'project_dynamic_radius_mm':None,'project_dynamic_cycles':None,'full_artwork_netlist':None}
    if set(found)!=set(('AC181200RY','AC182500RY')):raise ValueError('expected exact public RA material codes missing')
    report={'retrieval':retrieval,'exact_RA_laminate_candidates':list(found.values()),'is_finished_OLED_FPC_or_intercabin_harness':False,'secured_technical_documents_sign_in_wall_observed':True,'sign_in_or_NDA_or_inquiry_submitted':False,'public_monotonic_elongation_is_dynamic_fatigue_life':False,'actual_target_dynamic_flex_qualification_received':False,'manufacturing_go':False}
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'current_public_RA_codes':list(found),'public_retrieval_successes':sum(r['retrieval_verified'] for r in retrieval),'legacy_failures_preserved':[r['name'] for r in retrieval if not r['retrieval_verified']],'manufacturing_go':False}))

if __name__=='__main__':main()
