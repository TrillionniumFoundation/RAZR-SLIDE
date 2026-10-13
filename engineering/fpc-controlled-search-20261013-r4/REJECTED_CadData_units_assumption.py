#!/usr/bin/env python3
"""Own facts/hash audit of actually downloaded public inputs; no raw republish."""
from __future__ import annotations
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
from pypdf import PdfReader

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def extract(raw:Path,receipt:Path,baseline:Path):
    rows=json.loads(receipt.read_text())['results']
    for row in rows:
        if not row.get('retrieval_verified'):raise ValueError('unverified retrieval: '+row['name'])
        if sha(raw/row['name'])!=row['sha256']:raise ValueError('download bytes changed: '+row['name'])
    f1=PdfReader(raw/'we_FLEX1_stackup.pdf');f2=PdfReader(raw/'we_FLEX2_stackup.pdf')
    text1='\n'.join(p.extract_text() for p in f1.pages);text2='\n'.join(p.extract_text() for p in f2.pages)
    for expected,text in [('FLEX1_1F-Ri_030_17_2V13',text1),('ED Base Copper',text1),('0.097mm',text1),('0.303mm',text1),('0.120mm',text2),('0.276mm',text2),('plating',text2)]:
        if expected not in text:raise ValueError('expected source identity/fact missing: '+expected)
    source=raw/'we_FLEX2_ipc2581.cvg';tree=ET.parse(source);ns={'i':'http://webstds.ipc.org/2581'}
    if tree.getroot().attrib.get('revision')!='B':raise ValueError('unexpected IPC-2581 revision')
    cad=tree.find('.//i:CadData',ns)
    if cad is None or cad.attrib.get('units')!='MILLIMETER':raise ValueError('unconfirmed XML length units')
    stack=tree.find('.//i:Stackup',ns)
    if stack is None:raise ValueError('missing stackup')
    layers=[dict(e.attrib,thickness_mm=float(e.attrib['thickness'])) for e in stack.findall('.//i:StackupLayer',ns)]
    total=sum(e['thickness_mm'] for e in layers)
    xml_total=float(stack.attrib['overallThickness'])
    if abs(total-xml_total)>1e-9:raise ValueError('XML own layer thickness sum inconsistent')
    flex_names=['flexible Soldermask Top','Top Side','Polyimide','Bottom Side','flexible Soldermask']
    flex_total=sum(e['thickness_mm'] for e in layers if e['layerOrGroupRef'] in flex_names)
    unused=[e for e in layers if e['layerOrGroupRef']=='not used']
    if len(unused)!=1:raise ValueError('changed unused-layer ambiguity')
    prior=json.loads(baseline.read_text())
    current={e['name']:e for e in rows}
    repeats=[]
    for row in prior['results']:
        kind='DP' if row['type']=='header' else 'DS'
        fresh=current['hirose_'+kind+'_step.zip']
        old_members={m['name']:m for m in row['members']}
        matches=fresh['sha256']==row['zip_sha256'] and all(m['sha256']==old_members[m['name']]['sha256'] for m in fresh['members'])
        if not matches:raise ValueError('fresh Hirose CAD differs from prior authority')
        repeats.append({'kind':kind,'ZIP_and_all_member_bytes_match_prior_R66':True})
    return {'download_hashes_rechecked':len(rows),'PDF_pages':sum(r.get('page_count',0) for r in rows),'raw_files_unchanged':True,
      'hirose_fresh_CAD_vs_R66':repeats,
      'vendor_standard_profiles':[
       {'id':'FLEX1_1F-Ri_030_17_2V13','supplier':'Wuerth Elektronik','template_revision':'10/2023','use':'A_FLEX_TO_INSTALL','copper_layers':1,'base_copper':'ED','flex_thickness_mm':.097,'rigid_thickness_mm':.303,'flex_thickness_tolerance_plus_mm':.05,'flex_thickness_tolerance_minus_mm':.05,'rigid_tolerance_fraction':.10,'solder_surface':'ENIG','foil_thickness_mm':.017,'polyimide_mm':.05,'flex_soldermask_each_mm':.015,'project_selected':False,'dynamic_qualified':False,'source_file':'we_FLEX1_stackup.pdf','PDF_flex_page_index':1},
       {'id':'FLEX2_2F-Ri_027_17_2V13','supplier':'Wuerth Elektronik','template_revision':'10/2023','use':'A_FLEX_TO_INSTALL','copper_layers':2,'base_copper':'NOT_STATED','copper_plated_in_flex':True,'flex_thickness_mm':.120,'rigid_thickness_mm':.276,'flex_thickness_tolerance_plus_mm':.05,'flex_thickness_tolerance_minus_mm':.05,'rigid_tolerance_fraction':.10,'solder_surface':'ENIG','final_copper_each_mm':.020,'polyimide_mm':.05,'flex_soldermask_each_mm':.015,'project_selected':False,'dynamic_qualified':False,'source_file':'we_FLEX2_stackup.pdf','PDF_flex_page_index':1}],
      'FLEX2_machine_readable_conflict':{'raw_xml_sha256':sha(source),'revision':'B','units':'MILLIMETER','overall_thickness_mm':xml_total,'all_layer_sum_mm':total,'raw_layers':layers,'PDF_rigid_total_mm':.276,'PDF_flex_total_mm':.120,'XML_flex_named_layers_sum_mm':flex_total,'not_used_layer_mm':unused[0]['thickness_mm'],'XML_stackup_tolerances':{k:stack.attrib[k] for k in ('tolPlus','tolMinus')},'PDF_actual_flex_tolerance_plus_minus_mm':.05,'PDF_surface_finish_mm':.006,'conditional_sum_excluding_not_used_plus_PDF_finish_mm':total-unused[0]['thickness_mm']+.006,'conditional_interpretation_is_supplier_approved':False,'source_modified':False,'release_disposition':'REJECT_AUTOMATIC_MATERIAL_AND_GDT_IMPORT; supplier must resolve package'},
      'facts_extracted_do_not_qualify_project_FPC':True,'manufacturing_go':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=extract(a.raw_dir,a.receipt,a.baseline);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('download_hashes_rechecked','PDF_pages','raw_files_unchanged','manufacturing_go')}))

if __name__=='__main__':main()
