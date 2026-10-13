"""Editable terminal-level research circuit; not a phone PCB or released BOM."""
from pathlib import Path
import csv, hashlib, json, uuid

ROOT=Path(__file__).resolve().parent
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL,'razr-proof-selftest-r5/'+s))
def effects(size=1.1): return f'(effects (font (size {size} {size})))'

PARTS={
 'SN74LVC1G14DBV':[(1,'NC','no_connect'),(2,'A','input'),(3,'GND','power_in'),(4,'Y','output'),(5,'VCC','power_in')],
 'SN74LVC1G04DBV':[(1,'NC','no_connect'),(2,'A','input'),(3,'GND','power_in'),(4,'Y','output'),(5,'VCC','power_in')],
 'SN74LVC1G08DBV':[(1,'A','input'),(2,'B','input'),(3,'GND','power_in'),(4,'Y','output'),(5,'VCC','power_in')],
 'SN74LVC1G74DCU':[(1,'CLK','input'),(2,'D','input'),(3,'Qn','output'),(4,'GND','power_in'),(5,'Q','output'),(6,'CLRn','input'),(7,'PREn','input'),(8,'VCC','power_in')],
 'TLV3202DGK':[(1,'1OUT','output'),(2,'1IN-','input'),(3,'1IN+','input'),(4,'GND','power_in'),(5,'2IN+','input'),(6,'2IN-','input'),(7,'2OUT','output'),(8,'VCC','power_in')],
 'TLV803EA29DBZ':[(1,'GND','power_in'),(2,'RESETn','open_collector'),(3,'VDD','power_in')],
 'TPS3431DRB':[(1,'VDD','power_in'),(2,'CWD','input'),(3,'EN','input'),(4,'GND','power_in'),(5,'SET1','input'),(6,'WDI','input'),(7,'WDO','open_collector'),(8,'ENOUT','open_collector'),('EP','THERMAL_PAD','passive')],
 'R':[(1,'1','passive'),(2,'2','passive')],
 'C':[(1,'1','passive'),(2,'2','passive')],
 'TS5A3159DBV':[(1,'NO','passive'),(2,'GND','power_in'),(3,'NC','passive'),(4,'COM','passive'),(5,'V+','power_in'),(6,'IN','input')],
 'TPS22918DBV':[(1,'VIN','power_in'),(2,'GND','power_in'),(3,'ON','input'),(4,'CT','passive'),(5,'QOD','passive'),(6,'VOUT','power_out')],
 'EXTERNAL_BENCH_SUPPLY3':[(1,'TX_3V3_OUT','power_out'),(2,'RX_3V3_OUT','power_out'),(3,'ISOLATED_BENCH_REFERENCE','power_out')],
 'EXTERNAL_COUPON_SUPPLY2':[(1,'COUPON_VIN','power_out'),(2,'ISOLATED_REFERENCE','passive')],
 'PORT2':[(1,'1','passive'),(2,'2','passive')],
 'PORT3':[(1,'1','passive'),(2,'2','passive'),(3,'3','passive')],
 'EXTERNAL_BENCH_SUPPLY2':[(1,'BENCH_3V3_OUT','power_out'),(2,'ISOLATED_BENCH_REFERENCE','power_out')],
}

components=[]
def add(ref,part,nets,value=None,role=None):
 assert len(nets)==len(PARTS[part])
 components.append({'ref':ref,'part_candidate':part,'value':value or part,
  'pins':{str(n):{'name':name,'net':net,'type':typ} for (n,name,typ),net in zip(PARTS[part],nets)},
  'role':role,'product_part_selected':False,'footprint_selected':False})
G='ISOLATED_BENCH_G';V='TX_BENCH_3V3';VR='RX_BENCH_3V3'
def inv(ref,inn,out,rail=V,schmitt=False):
 add(ref,'SN74LVC1G14DBV' if schmitt else 'SN74LVC1G04DBV',[None,inn,G,out,rail])
def gate(ref,a,b,out,rail=V):add(ref,'SN74LVC1G08DBV',[a,b,G,out,rail])
def ff(ref,clk,d,q,clear,rail=V,qn=None):add(ref,'SN74LVC1G74DCU',[clk,d,qn,G,q,clear,rail,rail])
def three(ref,a,b,c,out,rail=V):
 gate(ref+'_1',a,b,ref+'_TMP',rail);gate(ref+'_2',ref+'_TMP',c,out,rail)
def supervisor(prefix,rail):
 add(prefix+'_PG','TLV803EA29DBZ',[G,prefix+'_PGOOD',rail],role='Actual local 3.3V supervisor; not an externally asserted flag')
 add(prefix+'_PG_PU','R',[rail,prefix+'_PGOOD'],'10k_1pct')
def wd(prefix,node,rail):
 add(prefix+'_WD','TPS3431DRB',[rail,prefix+'_CWD',rail,G,rail,node,prefix+'_WD_OK',None,G])
 add(prefix+'_CWD_R','R',[rail,prefix+'_CWD'],'10k_1pct_170to230ms')
 add(prefix+'_WD_PU','R',[rail,prefix+'_WD_OK'],'10k_1pct')
add('U_OSC','SN74LVC1G14DBV',[None,'OSC_RC',G,'PHASE',V])
add('R_OSC','R',['PHASE','OSC_RC'],'22k_1pct');add('C_OSC','C',['OSC_RC',G],'1u_10pct')
inv('U_PHASE_N','PHASE','PHASE_N')
# Delayed advance avoids changing decoder while the sample gate is still high.
add('R_ADVANCE','R',['PHASE','ADVANCE_RC'],'10k_1pct')
add('C_ADVANCE','C',['ADVANCE_RC',G],'10n_10pct')
inv('U_ADVANCE_N','ADVANCE_RC','ADVANCE_N',schmitt=True)
inv('U_ADVANCE','ADVANCE_N','ADVANCE_CLK')
supervisor('TX',V)
ff('U_JOHNSON_A','ADVANCE_CLK','STATE_B_N','STATE_A','TX_PGOOD',qn='STATE_A_N')
ff('U_JOHNSON_B','ADVANCE_CLK','STATE_A','STATE_B','TX_PGOOD',qn='STATE_B_N')
for ref,a,b,dec in [('U_DEC_NL','STATE_A_N','STATE_B_N','STATE_NL'),('U_DEC_NH','STATE_A','STATE_B_N','STATE_NH'),('U_DEC_TH','STATE_A','STATE_B','STATE_TH'),('U_DEC_TL','STATE_A_N','STATE_B','STATE_TL')]:gate(ref,a,b,dec)
# Dedicated dry loop. It remains separate from every actual phone return.
inv('U_DRIVE_N','STATE_A','DRIVE_N');inv('U_DRIVE','DRIVE_N','CHALLENGE_DRIVE')
add('R_DRIVE','R',['CHALLENGE_DRIVE','NORMAL_LOOP_NODE'],'47k_1pct')
add('J_DRY_A','PORT2',['NORMAL_LOOP_NODE',G],'DRY_LOOP_A_NOT_MAIN_N')
add('J_DRY_B','PORT2',['NORMAL_LOOP_NODE',G],'DRY_LOOP_B_NOT_MAIN_N')
add('R_REMOTE_SIG','R',['NORMAL_LOOP_NODE',G],'47k_1pct_AT_REMOTE_B_ONLY')
add('R_TEST_LIMIT','R',['CHALLENGE_DRIVE','TEST_INJECT_NODE'],'220k_1pct',role='Known high/low injection limited in energy; it does not bypass remote loop in normal states')
add('U_TEST_MUX','TS5A3159DBV',['TEST_INJECT_NODE',G,'NORMAL_LOOP_NODE','PROBE_SENSE',V,'STATE_B'],role='NC in normal LOW/HIGH; NO in test HIGH/LOW. Stuck route must fail a phase pattern')
add('C_SENSE','C',['PROBE_SENSE',G],'1n_10pct')
for name,a,b,r in [('HLO_TOP',V,'TH_HLO','15k_1pct'),('HLO_BOT','TH_HLO',G,'10k_1pct'),('HHI_TOP',V,'TH_HHI','10k_1pct'),('HHI_BOT','TH_HHI',G,'15k_1pct'),('LHI_TOP',V,'TH_LHI','90.9k_1pct'),('LHI_BOT','TH_LHI',G,'10k_1pct')]:add('R_'+name,'R',[a,b],r)
add('U_HIGH_WIN','TLV3202DGK',['ABOVE_HLO','TH_HLO','PROBE_SENSE',G,'TH_HHI','PROBE_SENSE','BELOW_HHI',V])
add('U_LOW_WIN','TLV3202DGK',['BELOW_LHI','PROBE_SENSE','TH_LHI',G,G,V,None,V])
for ref,inn,out in [('U_NOT_HLO','ABOVE_HLO','NOT_HLO'),('U_NOT_HHI','BELOW_HHI','NOT_HHI'),('U_NOT_LHI','BELOW_LHI','NOT_LHI')]:inv(ref,inn,out)
three('U_NORMAL_LOW_MATCH','NOT_HLO','BELOW_HHI','BELOW_LHI','MATCH_LOW')
three('U_NORMAL_HIGH_MATCH','ABOVE_HLO','BELOW_HHI','NOT_LHI','MATCH_HIGH')
three('U_TEST_HIGH_MATCH','ABOVE_HLO','NOT_HHI','NOT_LHI','MATCH_TEST_HIGH')
wd('TX','ACTUAL_TX_WDI',V)
gate('U_TX_CLEAR','TX_PGOOD','TX_WD_OK','TX_CLRn')
for name,d in [('NL','MATCH_LOW'),('NH','MATCH_HIGH'),('TH','MATCH_TEST_HIGH'),('TL','MATCH_LOW')]:
 gate('U_SAMPLE_CLK_'+name,'PHASE_N','STATE_'+name,'SAMPLE_CLK_'+name)
 ff('U_SAMPLE_'+name,'SAMPLE_CLK_'+name,d,'VALID_'+name,'TX_CLRn')
gate('U_PAIR_NORMAL','VALID_NL','VALID_NH','NORMAL_VALID')
gate('U_PAIR_TEST','VALID_TH','VALID_TL','TEST_VALID')
gate('U_ALL_VALID','NORMAL_VALID','TEST_VALID','ALL_VALID')
gate('U_TX_HEARTBEAT','PHASE','ALL_VALID','TX_HEARTBEAT')
add('R_TX_WDI_SER','R',['TX_HEARTBEAT','ACTUAL_TX_WDI'],'1k_1pct')
add('R_TX_WDI_PD','R',['ACTUAL_TX_WDI',G],'100k_1pct')
ff('U_TX_REQUEST','TX_SERVICE_EDGE',V,'TX_PENDING','TX_CLRn')
inv('U_TX_WDI_N','ACTUAL_TX_WDI','ACTUAL_TX_WDI_N')
ff('U_TX_ARM','ACTUAL_TX_WDI_N','TX_PENDING','TX_ARMED','TX_CLRn')
three('U_TX_QUAL','ALL_VALID','TX_CLRn','TX_ARMED','TX_QUALIFIED')
# Two separate dynamic outputs; shared source logic is NOT fault independence.
gate('U_DYN_A','PHASE','TX_QUALIFIED','DYN_A_TX')
gate('U_DYN_B','PHASE_N','TX_QUALIFIED','DYN_B_TX')
add('R_LINK_A','R',['DYN_A_TX','ACTUAL_RX_A_WDI'],'1k_1pct')
add('R_LINK_B','R',['DYN_B_TX','ACTUAL_RX_B_WDI'],'1k_1pct')
add('R_RX_A_PD','R',['ACTUAL_RX_A_WDI',G],'100k_1pct')
add('R_RX_B_PD','R',['ACTUAL_RX_B_WDI',G],'100k_1pct')
supervisor('RX',VR)
wd('RX_A','ACTUAL_RX_A_WDI',VR);wd('RX_B','ACTUAL_RX_B_WDI',VR)
three('U_RX_CLEAR','RX_PGOOD','RX_A_WD_OK','RX_B_WD_OK','RX_CLRn',VR)
ff('U_RX_REQUEST','RX_SERVICE_EDGE',VR,'RX_PENDING','RX_CLRn',VR)
inv('U_RX_A_N','ACTUAL_RX_A_WDI','ACTUAL_RX_A_WDI_N',VR)
inv('U_RX_B_N','ACTUAL_RX_B_WDI','ACTUAL_RX_B_WDI_N',VR)
ff('U_RX_A_SEEN','ACTUAL_RX_A_WDI_N','RX_PENDING','RX_A_SEEN','RX_CLRn',VR)
ff('U_RX_B_SEEN','ACTUAL_RX_B_WDI_N','RX_PENDING','RX_B_SEEN','RX_CLRn',VR)
gate('U_RX_BOTH','RX_A_SEEN','RX_B_SEEN','RX_BOTH_SEEN',VR)
gate('U_RX_PERMIT_A','RX_BOTH_SEEN','RX_CLRn','RX_EN_A_DRV',VR)
gate('U_RX_PERMIT_B','RX_BOTH_SEEN','RX_CLRn','RX_EN_B_DRV',VR)
add('R_ON_A_SER','R',['RX_EN_A_DRV','COUPON_ON_A'],'1k_1pct')
add('R_ON_B_SER','R',['RX_EN_B_DRV','COUPON_ON_B'],'1k_1pct')
add('R_ON_A_PD','R',['COUPON_ON_A',G],'10k_1pct')
add('R_ON_B_PD','R',['COUPON_ON_B',G],'10k_1pct')
# Concrete two-cut micro-power coupon; never a 2-A qualification or cell path.
add('U_COUPON_A','TPS22918DBV',['COUPON_INPUT_3V3',G,'COUPON_ON_A','CT_A','QOD_A','COUPON_MID'],role='First forward-only research cut; no reverse-blocking or overcurrent qualification')
add('U_COUPON_B','TPS22918DBV',['COUPON_MID',G,'COUPON_ON_B','CT_B','QOD_B','COUPON_OUT'],role='Second series research cut controlled through separate final ON net')
for name,inn,out,qod,ct in [('A','COUPON_INPUT_3V3','COUPON_MID','QOD_A','CT_A'),('B','COUPON_MID','COUPON_OUT','QOD_B','CT_B')]:
 add('C_CUT_IN_'+name,'C',[inn,G],'1u_INPUT')
 add('C_CUT_CT_'+name,'C',[ct,G],'1n_RESEARCH_SLEW')
 add('R_CUT_QOD_'+name,'R',[out,qod],'10k_OUTPUT_DISCHARGE')
add('R_COUPON_LOAD','R',['COUPON_OUT',G],'10k_MICROPOWER_RESEARCH_LOAD')
for name,net in [('TX_SERVICE','TX_SERVICE_EDGE'),('RX_SERVICE','RX_SERVICE_EDGE')]:
 add('J_'+name,'PORT2',[net,G],'MANUAL_BENCH_REQUEST_NO_AUTORETRY');add('R_'+name+'_PD','R',[net,G],'10k_1pct')
add('J_SUPPLY','EXTERNAL_BENCH_SUPPLY3',[V,VR,G],'EXTERNAL_ISOLATED_LAB_TX_RX_3V3_NOT_PHONE_REGULATORS')
add('J_POWER','EXTERNAL_COUPON_SUPPLY2',['COUPON_INPUT_3V3',G],'EXTERNAL_CURRENT_LIMITED_3V3_COUPON_ONLY')
add('J_LINK_A','PORT2',['ACTUAL_RX_A_WDI',G],'RESEARCH_DYNAMIC_LINK_A')
add('J_LINK_B','PORT2',['ACTUAL_RX_B_WDI',G],'RESEARCH_DYNAMIC_LINK_B')
add('J_OUTPUT','PORT2',['COUPON_OUT',G],'ISOLATED_RESEARCH_LOAD_NO_PHONE_CONNECTION')
for i,c in enumerate(list(components)):
 if c['part_candidate'] not in ('R','C','TPS22918DBV') and not c['part_candidate'].startswith(('PORT','EXTERNAL_')):
  rail=next(q['net'] for q in c['pins'].values() if q['type']=='power_in' and q['net'] in (V,VR))
  add('C_BYP_'+str(i),'C',[rail,G],'100n_LOCAL_AT_IC')

# KiCad requires annotated references ending in a number. Keep the expressive
# architecture aliases separately; U_A2 is logical_ref U_A2, physical_ref U11.
counts={}
for c in components:
 prefix='R' if c['part_candidate']=='R' else 'C' if c['part_candidate']=='C' else 'J' if c['part_candidate'].startswith(('PORT','EXTERNAL_')) else 'U'
 counts[prefix]=counts.get(prefix,0)+1
 c['logical_ref']=c['ref'];c['ref']=prefix+str(counts[prefix])

netlist={'schema':'razr-slide-selftest-dynamic-dual-receiver-r5','manufacturing_go':False,
 'phone_complete_PCB':False,'fabrication_netlist':False,'components':components,
 'physical_hardware':False,'dry_loop_is_actual_main_return':False,
 'implemented_editable_schematic':['Johnson four-state phase generator with delayed advance','known-rail switch-injection checks all three comparator outputs','four hardware valid-sample FFs','TX edge-qualified manual rearm and watchdog','dual dynamic outputs','two independent receiver watchdogs and edge sample latches','two series micro-power research load switches'],
 'missing_qualification':['actual main return diagnostic isolation','all PCB and assembly','exact RC/setup/hold/load/routing qualification','true multi-fault common-cause independence','any physical OEM qualification'],
 'dynamic_links_are_independent_fault_domains':False,
 'shared_TX_comparators_clock_and_logic':True,
 'receiver_supply_and_dry_probe_are_bench_only':True}
(ROOT/'terminal_netlist.json').write_text(json.dumps(netlist,indent=2)+'\n')
with (ROOT/'terminal_map.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['physical_ref','logical_ref','conditional_part','physical_pin','name','net','pin_type','product_selected'])
 for c in components:
  for n,p in c['pins'].items():w.writerow([c['ref'],c['logical_ref'],c['part_candidate'],n,p['name'],p['net'] or 'UNCONNECTED',p['type'],False])

def symbol_definition(part,qualified=False):
 name=('OwnedProof:' if qualified else '')+part
 pins=PARTS[part];h=max(7.62,(len(pins)+1)*2.54/2);y0=(len(pins)-1)*1.27
 ref='R' if part=='R' else 'C' if part=='C' else 'J' if part.startswith(('PORT','EXTERNAL_')) else 'U'
 out=[f'(symbol "{name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)',
 f'(property "Reference" "{ref}" (at 0 {h+2.54} 0) {effects()})',
 f'(property "Value" "{part}" (at 0 {-h-2.54} 0) {effects()})',
 '(property "Footprint" "" (at 0 0 0) (effects (font (size 1.1 1.1)) hide))',
 f'(symbol "{part}_0_1" (rectangle (start -12.7 {h}) (end 12.7 {-h}) (stroke (width .254) (type default)) (fill (type background))))',
 f'(symbol "{part}_1_1"']
 for i,(n,p,typ) in enumerate(pins):
  out.append(f'(pin {typ} line (at -17.78 {y0-i*2.54} 0) (length 5.08) (name "{p}" {effects(.85)}) (number "{n}" {effects(.85)}))')
 out+=['))'];return '\n'.join(out)

(ROOT/'OwnedProof.kicad_sym').write_text('(kicad_symbol_lib (version 20220914) (generator kicad_symbol_editor)\n'+'\n'.join(symbol_definition(p) for p in PARTS)+')\n')
(ROOT/'sym-lib-table').write_text('(sym_lib_table (lib (name "OwnedProof") (type "KiCad") (uri "${KIPRJMOD}/OwnedProof.kicad_sym") (options "") (descr "Owned pin-accurate dry-loop prototype symbols; no production assignment")))\n')
title='proof_selftest_research';rid=uid('schematic')
lines=['(kicad_sch (version 20230121) (generator eeschema)',f'(uuid {rid}) (paper "A0")',
 '(title_block (title "SELF TEST AND DUAL DYNAMIC RECEIVERS - RESEARCH") (date "2026-10-13") (rev "r5") (comment 1 "Dry loop/coupon only; no phone power qualification; manufacturing=false"))',
 '(lib_symbols','\n'.join(symbol_definition(p,True) for p in PARTS),')']
for i,c in enumerate(components):
 x=63.5+(i%10)*114.3;y=50.8+(i//10)*44.45;ref=c['ref'];part=c['part_candidate'];pins=PARTS[part];y0=(len(pins)-1)*1.27
 lines += [f'(symbol (lib_id "OwnedProof:{part}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(ref+"instance")})',
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
