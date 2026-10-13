"""Owned, unpowered single-cut reference PCB. This is NOT a phone PCB.

Exact TPS259470LRPW pin function and nominal copper extents are derived from
TI SLVSFC9C sections 5, 8.3, 8.4 and RPW0010A drawing 4225183/A. Component
values and passive lands are explicit bench hypotheses, not qualified parts.
"""
from pathlib import Path
import csv, hashlib, json, uuid

ROOT=Path(__file__).resolve().parent
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL,'razr-cut-module-r4/'+s))
def ef(n=.8): return f'(effects (font (size {n} {n}) (thickness .1)))'
NETS=['PACK_PROTECTED_P','PACK_PROTECTED_N','AFTER_FIRST_CUT_P','BENCH_EN','ILM','DVDT','FLT']
N={v:i+1 for i,v in enumerate(NETS)}
PARTS={
 'TPS259470LRPW':[(1,'EN/UVLO','input'),(2,'OVLO','input'),(3,'AUXOFF','open_collector'),(4,'FLT','open_collector'),(5,'IN','power_in'),(6,'OUT','power_out'),(7,'DVDT','passive'),(8,'GND','power_in'),(9,'ILM','passive'),(10,'ITIMER','passive')],
 'R':[(1,'1','passive'),(2,'2','passive')], 'C':[(1,'1','passive'),(2,'2','passive')],
 'Probe':[(1,'PROBE','passive')], 'BenchSource':[(1,'ISOLATED_BENCH_POWER','power_out')],
}
P='PACK_PROTECTED_P';G='PACK_PROTECTED_N';O='AFTER_FIRST_CUT_P'
COMP=[
 ('U1','TPS259470LRPW','TPS259470LRPW',['BENCH_EN',G,None,'FLT',P,O,'DVDT',G,'ILM',None],100,100,'RPW0010A_OWNED_NOMINAL'),
 ('R1','R','10k_BENCH_DEFAULT_OFF',['BENCH_EN',G],96,98,'Passive_0805_Vertical_BENCH'),
 ('R2','R','1.69k_1percent_BENCH',['ILM',G],104,98.5,'Passive_0805_BENCH'),
 ('R3','R','100k_BENCH_PULLUP',['FLT',P],96,102,'Passive_0805_BENCH'),
 ('C1','C','1uF_50V_BENCH',[P,G],100,95,'Passive_0805_BENCH'),
 ('C2','C','2.2uF_50V_BENCH',[O,G],104,104,'Passive_0805_BENCH'),
 ('C3','C','10nF_50V_BENCH',['DVDT',G],104,101.5,'Passive_0805_BENCH'),
 ('TP1','BenchSource','ISOLATED_BENCH_POSITIVE',[P],90,94,'Probe_1p8mm'),
 ('TP2','BenchSource','ISOLATED_BENCH_REFERENCE',[G],90,92,'Probe_1p8mm'),
 ('TP3','Probe','OUTPUT',[O],110,106,'Probe_1p8mm'),
 ('TP4','Probe','OUTPUT_REFERENCE',[G],110,108,'Probe_1p8mm'),
 ('TP5','Probe','EXTERNAL_BENCH_ENABLE',['BENCH_EN'],90,97.1,'Probe_1p8mm'),
 ('TP6','Probe','ENABLE_REFERENCE',[G],90,99.1,'Probe_1p8mm'),
 ('TP7','Probe','FAULT_OBSERVATION',['FLT'],90,104,'Probe_1p8mm'),
 ('TP8','Probe','FAULT_REFERENCE',[G],90,106,'Probe_1p8mm'),
]
def pad(num,x,y,sx,sy,net,shape='rect',thru=False):
 k='thru_hole' if thru else 'smd';layers='"*.Cu" "*.Mask"' if thru else '"F.Cu" "F.Paste" "F.Mask"'
 drill=' (drill .8)' if thru else ''
 s=f'(pad "{num}" {k} {shape} (at {x} {y}) (size {sx} {sy}){drill} (layers {layers})'
 if net:s+=f' (net {N[net]} "{net}")'
 return s+')'
def fp(ref,part,value,nets,x,y,name):
 s=[f'(footprint "OwnedCut:{name}" (layer "F.Cu") (at {x} {y}) (attr {"through_hole" if name.startswith("Probe") else "smd"})',
 f'(fp_text reference "{ref}" (at 0 -1.9) (layer "F.Fab") {ef(.8)})',
 f'(fp_text value "{value}" (at 0 0) (layer "F.Fab") {ef(.4)})']
 if part=='TPS259470LRPW':
  # Nominal L lands are formed by overlapping same-number copper rectangles.
  # Square corners and 100% paste are explicit unqualified bench deviations
  # from the vendor R0.05 and 82/93% example stencil.
  for pin,side,ys in [(1,-1,-1),(4,-1,1),(7,1,1),(10,1,-1)]:
   s.append(pad(pin,side*.9,ys*.7,.6,.3,nets[pin-1]))
   s.append(pad(pin,side*.725,ys*.875,.25,.65,nets[pin-1]))
  for pin,side,yy in [(2,-1,-.225),(3,-1,.225),(8,1,.225),(9,1,-.225)]:
   s.append(pad(pin,side*.9,yy,.6,.25,nets[pin-1]))
  s.append(pad(5,-.25,0,.3,2.4,nets[4]));s.append(pad(6,.25,0,.3,2.4,nets[5]))
 elif name.startswith('Probe'):s.append(pad(1,0,0,1.8,1.8,nets[0],'circle',True))
 elif name=='Passive_0805_Vertical_BENCH':
  s.extend([pad(1,0,-.9,1.1,.9,nets[0]),pad(2,0,.9,1.1,.9,nets[1])])
 else:s.extend([pad(1,-.9,0,.9,1.1,nets[0]),pad(2,.9,0,.9,1.1,nets[1])])
 s+=[')'];return '\n'.join(s)
lines=['(kicad_pcb (version 20221018) (generator "razr_owned_cut_reference_r4")','(general (thickness 1.6)) (paper "A4")',
 '(layers (0 "F.Cu" signal) (31 "B.Cu" signal) (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user) (38 "B.Mask" user) (39 "F.Mask" user) (40 "Dwgs.User" user) (41 "Cmts.User" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))',
 '(setup (pad_to_mask_clearance .03)) (net 0 "")']
for n in NETS:lines.append(f'(net {N[n]} "{n}")')
(ROOT/'OwnedCut.pretty').mkdir(exist_ok=True)
for c in COMP:
 f=fp(*c);lines.append(f)
 # The standalone library preserves exact local pad dimensions, no net links.
 name=c[-1];raw=fp('REF**',c[1],c[2],[None]*len(c[3]),0,0,name)
 (ROOT/'OwnedCut.pretty'/f'{name}.kicad_mod').write_text(raw+'\n')
routes=[]
def route(net,points,width=.12,layer='F.Cu'):
 for a,b in zip(points,points[1:]):
  s=f'(segment (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (width {width}) (layer "{layer}") (net {N[net]}) (tstamp {uid(str((net,a,b,layer)))}))'
  lines.append(s);routes.append({'net':net,'a':a,'b':b,'width_mm':width,'layer':layer,'sexpr':s})
def via(net,x,y):lines.append(f'(via (at {x} {y}) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net {N[net]}) (tstamp {uid(str((net,x,y,"via")))}))')
route(P,[(99.75,98.8),(99.75,97),(99.1,95)],.25)
route(P,[(99.1,95),(98,93),(90,94)],.5)
route(P,[(99.1,95),(97.4,95.3)]);via(P,97.4,95.3)
route(P,[(97.4,95.3),(97.4,102.6)],.2,'B.Cu');via(P,97.4,102.6);route(P,[(97.4,102.6),(96.9,102)])
route(O,[(100.25,101.2),(100.25,103),(103.1,104)],.25)
route(O,[(103.1,104),(103.1,106),(106,107),(110,106)],.5)
route('BENCH_EN',[(99.1,99.3),(98,99.3),(98,97.1),(96,97.1),(90,97.1)])
route('FLT',[(99.1,100.7),(94.2,100.7),(94.2,102),(95.1,102),(92,104),(90,104)])
route('ILM',[(100.9,99.775),(102,99.775),(103.1,98.5)])
route('DVDT',[(100.9,100.7),(102,100.7),(103.1,101.5)])
for a,b in [((99.1,99.775),(98.2,99.775)),((100.9,100.225),(102.7,100.225)),((96,98.9),(95.5,99.5)),((100.9,95),(101.6,95)),((104.9,98.5),(105.6,98.5)),((104.9,101.5),(105.6,101.5)),((104.9,104),(105.6,104))]:
 route(G,[a,b]);via(G,*b);route(G,[b,(b[0],110)],.2,'B.Cu')
for x,y in [(90,92),(90,99.1),(90,106)]:route(G,[(x,y),(87,y),(87,110)],.3,'B.Cu')
route(G,[(87,110),(110,110),(110,108)],.5,'B.Cu')
lines.append(f'(gr_rect (start 85 89) (end 114 113) (stroke (width .05) (type default)) (fill none) (layer "Edge.Cuts") (tstamp {uid("edge")}))')
lines.append(f'(gr_text "UNPOWERED REFERENCE - NOT PHONE PCB" (at 99.5 111.9) (layer "F.SilkS") {ef(.8)} (tstamp {uid("label")}))')
lines.append(')')
board='\n'.join(lines)+'\n';(ROOT/'cut_reference.kicad_pcb').write_text(board)
bad=board.replace(next(r['sexpr'] for r in routes if r['net']=='ILM'),'')
(ROOT/'REJECTED_missing_ILM_route.kicad_pcb').write_text(bad)
project={'meta':{'filename':'cut_reference.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':.1,'min_track_width':.1,'min_hole_clearance':.25,'min_copper_edge_clearance':.25}}},'net_settings':{'classes':[{'name':'Default','clearance':.1,'track_width':.12,'via_diameter':.6,'via_drill':.3}],'meta':{'version':3}},'erc':{'erc_exclusions':[]}}
for title in ['cut_reference','REJECTED_missing_ILM_route']:(ROOT/f'{title}.kicad_pro').write_text(json.dumps(project,indent=2)+'\n')
(ROOT/'fp-lib-table').write_text('(fp_lib_table (lib (name "OwnedCut") (type "KiCad") (uri "${KIPRJMOD}/OwnedCut.pretty") (options "") (descr "Owned nominal single-cut bench patterns, unqualified")))\n')

def sym(part,embedded=False):
 pins=PARTS[part];h=max(5.08,(len(pins)+1)*1.27);y0=(len(pins)-1)*1.27
 a=[f'(symbol "{"OwnedCut:" if embedded else ""}{part}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)',f'(property "Reference" "U" (at 0 {h+2.54} 0) {ef()})',f'(property "Value" "{part}" (at 0 {-h-2.54} 0) {ef()})',f'(symbol "{part}_0_1" (rectangle (start -12.7 {h}) (end 12.7 {-h}) (stroke (width .254) (type default)) (fill (type background))))',f'(symbol "{part}_1_1"']
 for i,(p,name,typ) in enumerate(pins):a.append(f'(pin {typ} line (at -17.78 {y0-i*2.54} 0) (length 5.08) (name "{name}" {ef(.8)}) (number "{p}" {ef(.8)}))')
 return '\n'.join(a+['))'])
(ROOT/'OwnedCut.kicad_sym').write_text('(kicad_symbol_lib (version 20220914) (generator kicad_symbol_editor)\n'+'\n'.join(sym(p) for p in PARTS)+')\n')
(ROOT/'sym-lib-table').write_text('(sym_lib_table (lib (name "OwnedCut") (type "KiCad") (uri "${KIPRJMOD}/OwnedCut.kicad_sym") (options "") (descr "Owned datasheet-pin single-cut reference symbols")))\n')
rootid=uid('schematic')
s=['(kicad_sch (version 20230121) (generator eeschema)',f'(uuid {rootid}) (paper "A2")','(title_block (title "SINGLE-CUT BENCH REFERENCE - NOT PHONE PCB") (date "2026-10-13") (rev "r4") (comment 1 "Bench values, no physical qualification, manufacturing=false"))','(lib_symbols','\n'.join(sym(p,True) for p in PARTS),')']
for i,(ref,part,value,nets,bx,by,fpname) in enumerate(COMP):
 x=76.2+(i%3)*127;y=50.8+(i//3)*63.5;pins=PARTS[part];y0=(len(pins)-1)*1.27
 s +=[f'(symbol (lib_id "OwnedCut:{part}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(ref+"symbol")})',f'(property "Reference" "{ref}" (at {x} {y-20.32} 0) {ef()})',f'(property "Value" "{value}" (at {x} {y+20.32} 0) {ef(.7)})',f'(property "Footprint" "OwnedCut:{fpname}" (at {x} {y} 0) (effects (font (size 1 1)) hide))']
 for p,_,_ in pins:s.append(f'(pin "{p}" (uuid {uid(ref+str(p))}))')
 s.append(f'(instances (project "cut_reference" (path "/{rootid}" (reference "{ref}") (unit 1)))))')
 for j,(pin,_,_) in enumerate(pins):
  px=x-17.78;py=y-y0+j*2.54;net=nets[j]
  if net is None:s.append(f'(no_connect (at {px} {py}) (uuid {uid(ref+str(pin)+"nc")}))')
  else:s +=[f'(wire (pts (xy {px-12.7} {py}) (xy {px} {py})) (stroke (width 0) (type default)) (uuid {uid(ref+str(pin)+"wire")}))',f'(label "{net}" (at {px-12.7} {py} 0) (effects (font (size .8 .8)) (justify left bottom)) (uuid {uid(ref+str(pin)+"label")}))']
(ROOT/'cut_reference.kicad_sch').write_text('\n'.join(s+[')'])+'\n')
facts={'schema':'single-cut-reference-r4','manufacturing_go':False,'phone_complete_PCB':False,'circuit_role':'first discharge source cut U_A1 bench reference only','package_copper':'nominal L copper extents from RPW0010A, overlapping same-number pads','package_deviations':['square rather than R0.05 copper corners','full-area paste rather than TI 82/93 percent example; requires stencil review'],'bench_conditions':{'input_V':[2.7,4.4],'external_enable_V':3.3,'load_current_qualified_A':None,'R_ILM_ohm':1690,'nominal_ILIM_A':3334/1690,'device_tolerance_ILIM_fraction':.1,'C_dvdt_F':1e-8,'nominal_slew_V_per_ms':.2,'R_EN_default_off_ohm':10000,'cell_voltage_or_current_frozen':False},'unimplemented':['pack protection/cell/OEM pin mapping','real phone control supply/enable generation','Schottky/TVS transient qualification','second source cut/receiver/charge/USB cuts','isolation diagnosis and finite fault energy','thermal/current rating of copper and passive actual MPNs','production DFM and assembly/physical tests'],'components':[{'ref':c[0],'part':c[1],'value':c[2],'nets':c[3],'x_mm':c[4],'y_mm':c[5],'footprint':c[6]} for c in COMP],'routing_segments':len(routes)}
(ROOT/'reference_terminal_map.json').write_text(json.dumps(facts,indent=2)+'\n')
with (ROOT/'bench_BOM_NOT_RELEASED.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['ref','part','value','footprint','MPN_selected_for_phone','physical_qualified'])
 for c in COMP:w.writerow([c[0],c[1],c[2],c[6],False,False])
print(json.dumps({'components':len(COMP),'physical_mapped_pins':sum(len(c[3]) for c in COMP),'routes':len(routes),'manufacturing_go':False}))
