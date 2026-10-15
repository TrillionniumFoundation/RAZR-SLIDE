"""Editable terminal-level research circuit; not a phone PCB or released BOM."""
from pathlib import Path
import csv, hashlib, json, uuid

ROOT=Path(__file__).resolve().parent
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL,'razr-return-r2/'+s))
def effects(size=1.1): return f'(effects (font (size {size} {size})))'
PARTS={
 'INA240A1PW':[(1,'NC','no_connect'),(2,'IN+','input'),(3,'IN-','input'),(4,'GND','power_in'),(5,'VS','power_in'),(6,'REF2','input'),(7,'REF1','input'),(8,'OUT','output')],
 'OPA333DBV':[(1,'OUT','output'),(2,'V-','power_in'),(3,'+IN','input'),(4,'-IN','input'),(5,'V+','power_in')],
 'TLV3202DGK':[(1,'1OUT','output'),(2,'1IN-','input'),(3,'1IN+','input'),(4,'GND','power_in'),(5,'2IN+','input'),(6,'2IN-','input'),(7,'2OUT','output'),(8,'VCC','power_in')],
 'SN74LVC1G08DBV':[(1,'A','input'),(2,'B','input'),(3,'GND','power_in'),(4,'Y','output'),(5,'VCC','power_in')],
 'SN74LVC1G74DCU':[(1,'CLK','input'),(2,'D','input'),(3,'Qn','output'),(4,'GND','power_in'),(5,'Q','output'),(6,'CLRn','input'),(7,'PREn','input'),(8,'VCC','power_in')],
 'TLV803EA29DBZ':[(1,'GND','power_in'),(2,'RESETn','open_collector'),(3,'VDD','power_in')],
 'TPS259470LRPW':[(1,'EN/UVLO','input'),(2,'OVLO','input'),(3,'AUXOFF','input'),(4,'FLTn','open_collector'),(5,'IN','power_in'),(6,'OUT','power_out'),(7,'DVDT','passive'),(8,'GND','power_in'),(9,'ILM','passive'),(10,'ITIMER','passive')],
 'R':[(1,'1','passive'),(2,'2','passive')],
 'C':[(1,'1','passive'),(2,'2','passive')],
 'PORT2':[(1,'1','passive'),(2,'2','passive')],
 'PORT3':[(1,'1','passive'),(2,'2','passive'),(3,'3','passive')],
}
components=[]
def add(ref,part,nets,value=None,role=None):
 assert len(nets)==len(PARTS[part])
 components.append({'ref':ref,'part_candidate':part,'value':value or part,
  'pins':{str(n):{'name':name,'net':net,'type':typ} for (n,name,typ),net in zip(PARTS[part],nets)},
  'role':role,'product_part_selected':False,'footprint_selected':False})
G='A_PACK_N';V='A_LOCAL_3V3_BENCH_ONLY'
add('U_P','INA240A1PW',[None,'A_CUT_OUT','A_TX_P',G,V,'VREF','VREF','VSENSE_P'],role='Positive main branch only, Kelvin to R_P after U_A2 and before launch')
add('U_N','INA240A1PW',[None,'A_RETURN_HARNESS',G,G,V,'VREF','VREF','VSENSE_N'],role='Dedicated MAIN return only. ALL alternate ground bonds upstream on A_PACK_N')
add('U_DIFF','OPA333DBV',['VDIFF',G,'DIFF_PLUS','DIFF_MINUS',V],role='Four equal ratio resistors: VDIFF=VREF+VSENSE_P-VSENSE_N')
add('U_REF','OPA333DBV',['VREF',G,'VREF_DIV','VREF',V],role='Local midpoint buffer; no externally powered reference may phantom feed unpowered analog rail')
add('U_WINDOW','TLV3202DGK',['HI_OK','VDIFF','V_WIN_H',G,'VDIFF','V_WIN_L','LO_OK',V],role='Both outputs HIGH only inside window, including upper and lower signed imbalance')
add('U_WINDOW_AND','SN74LVC1G08DBV',['HI_OK','LO_OK',G,'WINDOW_OK',V])
add('U_CLEAR_AND','SN74LVC1G08DBV',['WINDOW_OK','A_LOCAL_PGOOD',G,'CLEARn',V])
add('U_LATCH','SN74LVC1G74DCU',['SERVICE_ARM_EDGE',V,None,G,'ARMED_Q','CLEARn',V,V],role='D=1, PREn tied HIGH, asynchronously CLEAR on fault or supply bad; no automatic retry')
add('U_ENABLE_AND','SN74LVC1G08DBV',['ARMED_Q','A_LOCAL_PGOOD',G,'EN_DRV',V],role='Hardware driver only; no CPU GPIO OR bypass')
add('U_PGOOD','TLV803EA29DBZ',[G,'A_LOCAL_PGOOD',V],role='Standard DBZ pin 1 ground (no optional R/V pinout). A29 is 2.93V/200ms, conditional 3.3V bench rail only')
add('U_A2','TPS259470LRPW',['U_A2_EN',G,None,None,'A_MID_P','A_CUT_OUT','U_A2_DVDT',G,'U_A2_ILM',None],role='Final independent source cut BEFORE R_P and main cable launch; U_A1 not shared with this driver')
add('R_P','R',['A_CUT_OUT','A_TX_P'],'PARAM_SHUNT_P', 'Four terminal shunt required; Kelvin nodes must not include connector/track drops')
add('R_N','R',['A_RETURN_HARNESS',G],'PARAM_SHUNT_N','Dedicated main branch shunt; NOT aggregate ground shunt')
for ref,nets in [('R_D1',['VSENSE_N','DIFF_MINUS']),('R_D2',['VDIFF','DIFF_MINUS']),('R_D3',['VSENSE_P','DIFF_PLUS']),('R_D4',['VREF','DIFF_PLUS'])]:
 add(ref,'R',nets,'PARAM_MATCHED_RATIO_R')
add('R_REF_TOP','R',[V,'VREF_DIV'],'PARAM_REF_R')
add('R_REF_BOT','R',['VREF_DIV',G],'PARAM_REF_R')
add('R_WIN_TOP','R',[V,'V_WIN_H'],'PARAM_WINDOW_OUTER_R')
add('R_WIN_MID','R',['V_WIN_H','V_WIN_L'],'PARAM_WINDOW_CENTER_R')
add('R_WIN_BOT','R',['V_WIN_L',G],'PARAM_WINDOW_OUTER_R')
for ref,net in [('R_HIOK_PD','HI_OK'),('R_LOOK_PD','LO_OK'),('R_WINDOW_PD','WINDOW_OK'),('R_CLEAR_PD','CLEARn'),('R_ARM_PD','SERVICE_ARM_EDGE'),('R_Q_PD','ARMED_Q'),('R_PG_PD','A_LOCAL_PGOOD')]:
 add(ref,'R',[net,G],'PARAM_DEFAULT_LOW_R')
add('R_PG_PU','R',[V,'A_LOCAL_PGOOD'],'PARAM_PGOOD_PULLUP')
add('R_ENABLE_SER','R',['EN_DRV','U_A2_EN'],'PARAM_ENABLE_SER')
add('R_ENABLE_PD','R',['U_A2_EN',G],'PARAM_ENABLE_PD_LOCAL_AT_EFUSE')
add('R_ILM','R',['U_A2_ILM',G],'PARAM_ILM_NO_PRODUCT_VALUE')
add('C_DVDT','C',['U_A2_DVDT',G],'PARAM_DVDT_NO_PRODUCT_VALUE')
for ref,net in [('C_P',V),('C_N',V),('C_DIFF',V),('C_REF',V),('C_WINDOW',V),('C_LOGIC',V),('C_PGOOD',V)]:
 add(ref,'C',[net,G],'PARAM_LOCAL_BYPASS')
add('J_MID','PORT2',['A_MID_P',G],'PROTECTED_AFTER_U_A1_PORT_NOT_RAW_CELL')
add('J_MAIN','PORT2',['A_TX_P','A_RETURN_HARNESS'],'MAIN_PAIR_UNSELECTED_STATIC_CONNECTOR')
add('J_ALTERNATE_BOND','PORT2',[G,G],'CHARGE_USB_SIGNAL_REFERENCE_ALL_UPSTREAM_NOT_RAW_CELL')
add('J_SUPPLY','PORT2',[V,G],'ISOLATED_BENCH_3V3_ONLY_LOCAL_REGULATOR_UNSELECTED')
add('J_ARM','PORT2',['SERVICE_ARM_EDGE',G],'MANUAL_BENCH_REARM_NO_AUTORETRY')
add('J_MONITOR','PORT3',['VDIFF','VSENSE_P','VSENSE_N'],'HIGH_IMPEDANCE_ISOLATED_INSTRUMENTS_REQUIRED')

# KiCad requires annotated references ending in a number. Keep the expressive
# architecture aliases separately; U_A2 is logical_ref U_A2, physical_ref U11.
counts={}
for c in components:
 prefix='R' if c['part_candidate']=='R' else 'C' if c['part_candidate']=='C' else 'J' if c['part_candidate'].startswith('PORT') else 'U'
 counts[prefix]=counts.get(prefix,0)+1
 c['logical_ref']=c['ref'];c['ref']=prefix+str(counts[prefix])

netlist={'schema':'razr-slide-local-return-sensing-terminal-netlist-r2','manufacturing_go':False,
 'phone_complete_PCB':False,'fabrication_netlist':False,'components':components,
 'all_component_values_are_parameters':True,'research_bench_synthetic_values_file':'synthetic_fixture.json',
 'local_measurement_reference':'protected A_PACK_N, never raw CELL_N',
 'alternate_reference_or_USB_ground_disconnected_in_fault_free_motion':False,
 'source_sense_isolation_cut':'U_A2 EN/UVLO pin1','other_source_independent_cut':'U_A1 remains separately driven outside this local circuit',
 'B_receiver_reverse_block':'U_ARX unchanged outside this local circuit',
 'unimplemented':['actual local regulator','pack/OEM exact interfaces','sense open diagnosis','persistent service rearm lockout','whole-board segregation','VBUS and remote charger cuts','downstream voltage sensing/bleed']}
(ROOT/'terminal_netlist.json').write_text(json.dumps(netlist,indent=2)+'\n')
with (ROOT/'terminal_map.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['physical_ref','logical_ref','conditional_part','physical_pin','name','net','pin_type','product_selected'])
 for c in components:
  for n,p in c['pins'].items():w.writerow([c['ref'],c['logical_ref'],c['part_candidate'],n,p['name'],p['net'] or 'UNCONNECTED',p['type'],False])

def symbol_definition(part,qualified=False):
 name=('OwnedReturn:' if qualified else '')+part
 pins=PARTS[part];h=max(7.62,(len(pins)+1)*2.54/2);y0=(len(pins)-1)*1.27
 ref='R' if part=='R' else 'C' if part=='C' else 'J' if part.startswith('PORT') else 'U'
 out=[f'(symbol "{name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)',
 f'(property "Reference" "{ref}" (at 0 {h+2.54} 0) {effects()})',
 f'(property "Value" "{part}" (at 0 {-h-2.54} 0) {effects()})',
 '(property "Footprint" "" (at 0 0 0) (effects (font (size 1.1 1.1)) hide))',
 f'(symbol "{part}_0_1" (rectangle (start -12.7 {h}) (end 12.7 {-h}) (stroke (width .254) (type default)) (fill (type background))))',
 f'(symbol "{part}_1_1"']
 for i,(n,p,typ) in enumerate(pins):
  out.append(f'(pin {typ} line (at -17.78 {y0-i*2.54} 0) (length 5.08) (name "{p}" {effects(.85)}) (number "{n}" {effects(.85)}))')
 out+=['))'];return '\n'.join(out)

(ROOT/'OwnedReturn.kicad_sym').write_text('(kicad_symbol_lib (version 20220914) (generator kicad_symbol_editor)\n'+'\n'.join(symbol_definition(p) for p in PARTS)+')\n')
(ROOT/'sym-lib-table').write_text('(sym_lib_table (lib (name "OwnedReturn") (type "KiCad") (uri "${KIPRJMOD}/OwnedReturn.kicad_sym") (options "") (descr "Owned exact physical-pin research symbols; no production assignment")))\n')
title='return_sensing_research';rid=uid('schematic')
lines=['(kicad_sch (version 20230121) (generator eeschema)',f'(uuid {rid}) (paper "A1")',
 '(title_block (title "RETURN SENSING RESEARCH - NOT FOR FABRICATION") (date "2026-10-13") (rev "r2") (comment 1 "All values PARAMETER; manufacture=false; native parser not ERC"))',
 '(lib_symbols','\n'.join(symbol_definition(p,True) for p in PARTS),')']
for i,c in enumerate(components):
 x=105+(i%5)*155;y=57+(i//5)*48;ref=c['ref'];part=c['part_candidate'];pins=PARTS[part];y0=(len(pins)-1)*1.27
 lines += [f'(symbol (lib_id "OwnedReturn:{part}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(ref+"instance")})',
 f'(property "Reference" "{ref}" (at {x} {y-17} 0) {effects()})',
 f'(property "Value" "{c["value"]}" (at {x} {y+17} 0) {effects(.8)})',
 '(property "Footprint" "" (at 0 0 0) (effects (font (size 1.1 1.1)) hide))']
 for n in c['pins']:lines.append(f'(pin "{n}" (uuid {uid(ref+n)}))')
 lines.append(f'(instances (project "{title}" (path "/{rid}" (reference "{ref}") (unit 1)))))')
 for j,(n,p,typ) in enumerate(pins):
  py=y-y0+j*2.54;net=c['pins'][str(n)]['net'];endx=x-17.78
  if net is None:lines.append(f'(no_connect (at {endx} {py}) (uuid {uid(ref+str(n)+"nc")}))')
  else:
   startx=endx-12.7
   lines += [f'(wire (pts (xy {startx} {py}) (xy {endx} {py})) (stroke (width 0) (type default)) (uuid {uid(ref+str(n)+"wire")}))',
    f'(label "{net}" (at {startx} {py} 0) (effects (font (size .85 .85)) (justify left bottom)) (uuid {uid(ref+str(n)+"label")}))']
lines.append(')');(ROOT/f'{title}.kicad_sch').write_text('\n'.join(lines)+'\n')
(ROOT/f'{title}.kicad_pro').write_text(json.dumps({'meta':{'filename':f'{title}.kicad_pro','version':1},'erc':{'erc_exclusions':[]}},indent=2)+'\n')
print(json.dumps({'components':len(components),'mapped_physical_pins':sum(len(c['pins']) for c in components),'manufacturing_go':False,'native_parser_pending':True}))
