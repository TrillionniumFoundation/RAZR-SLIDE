"""Independent comparison of native KiCad XML to physical-pin design map.
Native root-sheet local net names have exactly one leading '/', as observed
in the actual XML. No arbitrary nested-sheet path stripping is permitted.
"""
from pathlib import Path
import hashlib, json, xml.etree.ElementTree as ET

def verify(folder, output):
 p=Path(folder);root=ET.parse(p/'native-return.xml').getroot();expected=json.loads((p/'terminal_netlist.json').read_text())['components'];actual={};duplicates=[]
 for net in root.find('nets'):
  for node in net.findall('node'):
   key=(node.attrib['ref'],node.attrib['pin'])
   if key in actual:duplicates.append(key)
   actual[key]=net.attrib['name']
 wrong=[];mapped=[];expectedkeys=set()
 for c in expected:
  for pin,term in c['pins'].items():
   key=(c['ref'],pin);expectedkeys.add(key);a=actual.get(key);e=term['net']
   if e is not None and a!='/'+e:wrong.append({'ref':c['ref'],'pin':pin,'expected_root_sheet_name':'/'+e,'actual':a})
   if e is None and a is not None and not a.startswith('unconnected-('+c['ref']+'-'):wrong.append({'ref':c['ref'],'pin':pin,'expected':None,'actual':a})
   mapped.append({'physical_ref':c['ref'],'logical_ref':c['logical_ref'],'pin':pin,'logical_net':e,'native_net':a})
 extras=[list(key) for key in actual if key not in expectedkeys]
 native_refs={c.attrib['ref'] for c in root.find('components')};expected_refs={c['ref'] for c in expected}
 receipt={'native_KiCad7_netlist_and_svg_export':True,'KiCad_version':'7.0.11','native_component_count':len(native_refs),'expected_component_count':len(expected_refs),
 'expected_physical_pins':len(expectedkeys),'native_mapped_physical_pins':len(actual),'wrong_net_mappings':wrong,'duplicate_native_pin_entries':duplicates,'unexpected_native_pin_entries':extras,
 'reference_sets_match':native_refs==expected_refs,'mapped_pins':mapped,'root_sheet_name_convention':'exact / prefix, never arbitrary path stripping',
 'physical_hardware':False,'manufacturing_go':False,'parser_is_ERC':False,'PCB_present':False,
 'sha256':{str(q.relative_to(p)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [p/'native-return.xml',p/'return_sensing_research.kicad_sch',p/'native-tests-corrected.log',p/'native-simulation_receipt.json',p/'native-svg-corrected/return_sensing_research.svg']}}
 output.write_text(json.dumps(receipt,indent=2)+'\n')
 assert not wrong and not duplicates and not extras and native_refs==expected_refs
 assert len(actual)==len(expectedkeys)
 print(json.dumps({'native_components':len(native_refs),'native_mapped_pins':len(actual),'wrong_net_mappings':len(wrong),'manufacturing_go':False}))
 return receipt

if __name__=='__main__':
 import argparse
 q=argparse.ArgumentParser();q.add_argument('folder',type=Path);q.add_argument('--output',type=Path,required=True);a=q.parse_args();verify(a.folder,a.output)
