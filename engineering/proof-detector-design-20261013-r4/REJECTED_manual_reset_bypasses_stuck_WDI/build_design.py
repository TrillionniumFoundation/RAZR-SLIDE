"""Editable terminal-level research circuit; not a phone PCB or released BOM."""
from pathlib import Path
import csv, hashlib, json, uuid

ROOT=Path(__file__).resolve().parent
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL,'razr-proof-detector-r4/'+s))
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
G='ISOLATED_PROBE_G';V='ISOLATED_BENCH_3V3_ONLY'
add('U_OSC','SN74LVC1G14DBV',[None,'OSC_RC',G,'PHASE',V],role='Autonomous RC challenge; timing must be measured, no MCU receipt accepted')
add('R_OSC','R',['PHASE','OSC_RC'],'22k_1pct')
add('C_OSC','C',['OSC_RC',G],'1u_10pct')
add('U_PHASE_N','SN74LVC1G04DBV',[None,'PHASE',G,'PHASE_N',V],role='HIGH phase sampled at falling PHASE, before delayed analog response changes')
add('U_PROBE_BUF','SN74LVC1G04DBV',[None,'PHASE_N',G,'PROBE_DRIVE',V],role='Double inversion reproduces PHASE with separate light-load driver')
add('R_DRIVE','R',['PROBE_DRIVE','PROBE_SENSE'],'47k_1pct',role='Limits current into dedicated dry loop; no main power wiring connected')
add('C_SENSE','C',['PROBE_SENSE',G],'1n_10pct',role='Analog settling delay preserves sample hold; real parasitics/edges still unmeasured')
add('J_A','PORT2',['PROBE_SENSE',G],'DRY_LOOP_A_END_NOT_MAIN_POWER_RETURN')
add('J_B','PORT2',['PROBE_SENSE',G],'DRY_LOOP_B_END_NOT_MAIN_POWER_RETURN')
add('R_REMOTE_SIG','R',['PROBE_SENSE',G],'47k_1pct_REMOTE_B_ONLY',role='Required physically at remote B; same logical nets do not prove location or exclude local matched bridge')
# Ratiometric thresholds nominally 0.4VDD, 0.6VDD and 0.0991VDD.
for name,a,b,r in [('HLO_TOP',V,'TH_HLO','15k_1pct'),('HLO_BOT','TH_HLO',G,'10k_1pct'),('HHI_TOP',V,'TH_HHI','10k_1pct'),('HHI_BOT','TH_HHI',G,'15k_1pct'),('LHI_TOP',V,'TH_LHI','90.9k_1pct'),('LHI_BOT','TH_LHI',G,'10k_1pct')]:
 add('R_'+name,'R',[a,b],r)
add('U_HIGH_WIN','TLV3202DGK',['ABOVE_HLO','TH_HLO','PROBE_SENSE',G,'TH_HHI','PROBE_SENSE','BELOW_HHI',V],role='HIGH result requires sense above 0.4 and below 0.6 of rail')
add('U_LOW','TLV3202DGK',['BELOW_LHI','PROBE_SENSE','TH_LHI',G,G,V,None,V],role='LOW result requires sense below 0.0991 rail; unused half has defined unequal inputs and NC output')
add('U_HVALID_AND','SN74LVC1G08DBV',['ABOVE_HLO','BELOW_HHI',G,'HIGH_VALID',V])
add('U_LOWER_NOT','SN74LVC1G04DBV',[None,'ABOVE_HLO',G,'NOT_ABOVE_HLO',V],role='LOW phase must also demonstrate lower HIGH comparator has changed state')
add('U_LVALID_AND','SN74LVC1G08DBV',['BELOW_LHI','NOT_ABOVE_HLO',G,'LOW_VALID',V])
add('U_PGOOD','TLV803EA29DBZ',[G,'PGOOD',V],role='2.93V threshold, 200ms typical; standard DBZ pin1 GND; exact 3.3V bench supply only')
add('R_PG_PU','R',[V,'PGOOD'],'10k_1pct')
add('U_WATCHDOG','TPS3431DRB',[V,'WD_CWD',V,G,V,'VALID_HEARTBEAT','WD_OK',None,G],role='SET1 and EN hard high prevents software disable; falling WDI edge required; ENOUT unconnected, WDO goes low on missing edges')
add('R_WD_CWD','R',[V,'WD_CWD'],'10k_1pct',role='TI preset 170..230ms watchdog timeout, avoids capacitor-timing typical-only assumption')
add('R_WD_PU','R',[V,'WD_OK'],'10k_1pct')
add('U_CLEAR','SN74LVC1G08DBV',['PGOOD','WD_OK',G,'VALID_CLRn',V],role='Watchdog assertion clears BOTH samples: auto-released WDO cannot restore stale proof')
add('U_SAMPLE_H','SN74LVC1G74DCU',['PHASE_N','HIGH_VALID',None,G,'H_SEEN_VALID','VALID_CLRn',V,V],role='Sample pre-fall HIGH state; asynchronous clear at reset/timeout')
add('U_SAMPLE_L','SN74LVC1G74DCU',['PHASE','LOW_VALID',None,G,'L_SEEN_VALID','VALID_CLRn',V,V],role='Sample pre-rise LOW state; no credit from reset or manual ARM')
add('U_TWO_VALID','SN74LVC1G08DBV',['H_SEEN_VALID','L_SEEN_VALID',G,'TWO_VALID',V])
add('U_RECEIPT','SN74LVC1G08DBV',['PHASE','TWO_VALID',G,'VALID_HEARTBEAT',V],role='Only physical sampled dual-phase validity permits WDI edges')
add('U_SERVICE_LATCH','SN74LVC1G74DCU',['SERVICE_RESET_EDGE',V,None,G,'SERVICE_HEALTH_Q','VALID_CLRn',V,V],role='Reset or watchdog fault clears; ONLY a new manual reset edge can rearm; a held input cannot automatically recover')
add('U_FRESH1','SN74LVC1G08DBV',['TWO_VALID','VALID_CLRn',G,'PRE_FRESH',V])
add('U_FRESH2','SN74LVC1G08DBV',['PRE_FRESH','SERVICE_HEALTH_Q',G,'PROBE_FRESH_OK',V],role='No external proof input; manual reset cannot create two-phase continuity; output DC stuck-high remains a counterexample')
add('J_SERVICE','PORT2',['SERVICE_RESET_EDGE',G],'MANUAL_RESET_ONLY_NO_AUTORETRY')
add('R_SERVICE_PD','R',['SERVICE_RESET_EDGE',G],'10k_1pct')
add('R_SERVICE_Q_PD','R',['SERVICE_HEALTH_Q',G],'10k_1pct')
for logical,net in [('PD_PHASE','PHASE'),('PD_H','H_SEEN_VALID'),('PD_L','L_SEEN_VALID'),('PD_HB','VALID_HEARTBEAT'),('PD_CLEAR','VALID_CLRn'),('PD_FRESH','PROBE_FRESH_OK')]:
 add('R_'+logical,'R',[net,G],'100k_1pct' if logical=='PD_HB' else '10k_1pct')
for i,c in enumerate(list(components)):
 if c['ref'].startswith('U_'):add('C_BYP_'+str(i),'C',[V,G],'100n_LOCAL_AT_IC')
add('J_SUPPLY','EXTERNAL_BENCH_SUPPLY2',[V,G],'ISOLATED_3V3_BENCH_SUPPLY_NOT_IMPLEMENTED_PHONE_REGULATOR')
add('J_PROOF_OUT','PORT2',['PROBE_FRESH_OK',G],'OUTPUT_TO_RESEARCH_GATE_ONLY_NO_PHONE_CONNECTION')
add('J_ANALOG','PORT3',['PROBE_SENSE','PHASE','VALID_HEARTBEAT'],'ISOLATED_HIGH_Z_MEASUREMENT_PORT')

# KiCad requires annotated references ending in a number. Keep the expressive
# architecture aliases separately; U_A2 is logical_ref U_A2, physical_ref U11.
counts={}
for c in components:
 prefix='R' if c['part_candidate']=='R' else 'C' if c['part_candidate']=='C' else 'J' if c['part_candidate'].startswith(('PORT','EXTERNAL_')) else 'U'
 counts[prefix]=counts.get(prefix,0)+1
 c['logical_ref']=c['ref'];c['ref']=prefix+str(counts[prefix])

netlist={'schema':'razr-slide-dynamic-proof-detector-r4','manufacturing_go':False,
 'phone_complete_PCB':False,'fabrication_netlist':False,'components':components,
 'component_values_are_research_fixture_values':True,'physical_hardware':False,
 'local_measurement_reference':'isolated 3.3V bench reference; no phone pack, USB or main power-return connected',
 'continuity_proof_generation_implemented':'editable schematic only; autonomous two-phase dry-loop detector and hardware freshness timer',
 'unimplemented':['physical assembly/measurement','actual powered main return isolation','OFF leakage and welded-cut diagnosis','full phone PCB','final output stuck-high independent cut','comparator self-test','material signal identity','phone rail regulator'],
 'freshness_timer':'TPS3431 SET1/EN hard tied high, CWD 10k to supply; 170..230 ms timeout, both sampled-valid FFs and independent manual-service latch asynchronously cleared when WDO low',
 'proof_boundary':'research dry loop only; not actual complete main power-return continuity proof',
 'manufacturing_go':False}
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
title='proof_detector_research';rid=uid('schematic')
lines=['(kicad_sch (version 20230121) (generator eeschema)',f'(uuid {rid}) (paper "A0")',
 '(title_block (title "AUTONOMOUS DRY LOOP PROOF AND WATCHDOG - RESEARCH") (date "2026-10-13") (rev "r4") (comment 1 "Dry loop only; no phone powered-return qualification; manufacturing=false"))',
 '(lib_symbols','\n'.join(symbol_definition(p,True) for p in PARTS),')']
for i,c in enumerate(components):
 x=101.6+(i%5)*152.4;y=50.8+(i//5)*50.8;ref=c['ref'];part=c['part_candidate'];pins=PARTS[part];y0=(len(pins)-1)*1.27
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
