#!/usr/bin/env python3
"""Owned passive continuity coupons, NOT the phone PCB or released PCBA.

The frozen connector patterns are copied byte for byte. Site names are our
coordinate IDs. Nets C01..C26 denote continuity only, never an OEM signal.
"""
from pathlib import Path
import csv, hashlib, json, re, uuid

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'native-endpoint-20261013'
LIB=ROOT/'RAZR_ENDPOINT_RESEARCH.pretty'
LIB.mkdir(exist_ok=True)
SITES=[f'S_{side}_{i:02d}' for side in ('NEG','POS') for i in range(12)]+['P_L','P_R']
NETS={s:f'C{i+1:02d}' for i,s in enumerate(SITES)}
def uid(text): return str(uuid.uuid5(uuid.NAMESPACE_URL,'razr-owned-coupon-r2/'+text))
def row_map(kind,site):
    if kind=='DP' or site.startswith('P_'): return site
    return site.replace('NEG','TMP').replace('POS','NEG').replace('TMP','POS')
def net(kind,site): return NETS[row_map(kind,site)]
def effects(size=.8): return f'(effects (font (size {size} {size}) (thickness .1)))'

copied=[]
for p in sorted((SOURCE/'RAZR_ENDPOINT_RESEARCH.pretty').glob('*.kicad_mod')):
    (LIB/p.name).write_bytes(p.read_bytes())
    copied.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})

mapping=[]
for s in SITES:
    ds=row_map('DS',s)
    mapping.append({'net':NETS[s],'DP_site':s,'DS_site':ds,'DP_testpoint':f'TP{SITES.index(s)+1:02d}',
                    'DS_testpoint':f'TP{SITES.index(ds)+1:02d}'})
(ROOT/'mating_site_map.json').write_text(json.dumps({'supplier_pin1':None,'coordinate_IDs_owned':True,
 'chosen_transform_DP_local_to_DS_global':{'matrix':[ [1,0,0],[0,-1,0],[0,0,-1]],'translation_mm':[0,0,.6]},
 'board_thickness_mm_hypothesis':.8,'mapping':mapping,'physical_continuity_verified':False,
 'fixture_holes_only_key_correct_orientation_if_three_matching_pins_are_present':True,
 'connector_itself_has_no_polarity':True,'manufacturing_go':False},indent=2)+'\n')

def connector_footprint(kind):
    p=next(LIB.glob(f'*24{kind}*.kicad_mod'))
    txt=p.read_text()
    name=p.stem
    txt=txt.replace(f'(footprint "{name}"',f'(footprint "RAZR_ENDPOINT_RESEARCH:{name}"',1)
    txt=txt.replace('(layer "F.Cu")','(layer "F.Cu")\n  (at 100 100)',1)
    txt=txt.replace('reference "REF**"','reference "J1"')
    txt=txt.replace('(size 0.6 0.6)','(size .8 .8)',1)
    # Assembly outputs intentionally include this research connector. Geometry
    # and mask/paste remain unchanged; exclusion flags are removed only here.
    txt=txt.replace('smd exclude_from_pos_files exclude_from_bom','smd')
    for s in SITES:
        txt=re.sub(r'(\(pad "'+s+r'"[^\n]+)\)',lambda m:m[1]+f' (net {SITES.index(row_map(kind,s))+1} "{net(kind,s)}"))',txt)
    if kind=='DS':
        txt=re.sub(r'(\(xy )(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)(\))',lambda m:m[1]+str(float(m[2])+100)+' '+str(float(m[3])+100)+m[4],txt)
    return txt,name

def board(kind):
    con,name=connector_footprint(kind)
    lines=['(kicad_pcb (version 20221018) (generator "razr_owned_coupon_r2")',
     ' (general (thickness .8)) (paper "A4")',
     ' (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (32 "B.Adhes" user "B.Adhesive") (33 "F.Adhes" user "F.Adhesive") (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen") (38 "B.Mask" user) (39 "F.Mask" user) (40 "Dwgs.User" user "User.Drawings") (41 "Cmts.User" user "User.Comments") (44 "Edge.Cuts" user) (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard") (48 "B.Fab" user) (49 "F.Fab" user))',
     ' (setup (pad_to_mask_clearance 0)) (net 0 "")']
    for s in SITES: lines.append(f' (net {SITES.index(s)+1} "{NETS[s]}")')
    lines.append(con)
    def track(a,b,n,width=.10):
        lines.append(f' (segment (start {a[0]:.6f} {a[1]:.6f}) (end {b[0]:.6f} {b[1]:.6f}) (width {width}) (layer "F.Cu") (net {n}) (tstamp {uid(kind+str(a)+str(b)+str(n))}))')
    for i,s in enumerate(SITES):
        n=SITES.index(row_map(kind,s))+1
        if s.startswith('S_'):
            side=-1 if 'NEG' in s else 1
            idx=int(s[-2:]); x=100-1.925+.35*idx
            y=100+side*(.5925 if kind=='DP' else .745)
            tx=100-8.25+1.5*idx; ty=100+side*10
            # Exit each land perpendicular before expanding the ordered fan.
            a=(x,y); b=(x,100+side*1.5); c=(tx,100+side*8.0); d=(tx,ty)
            track(a,b,n);track(b,c,n);track(c,d,n)
        else:
            side=-1 if s=='P_L' else 1
            x=100+side*(2.515 if kind=='DP' else 2.630)
            py=.325 if kind=='DP' else .785
            tx=100+side*17;ty=100
            bx=100+side*3.35
            track((x,100-py),(bx,100-py),n,.18)
            track((x,100+py),(bx,100+py),n,.18)
            track((bx,100-py),(bx,100+py),n,.18)
            track((bx,100),(tx,ty),n,.18)
        ref=f'TP{i+1:02d}'
        lines.append(f' (footprint "Owned_Coupon:ProbePad_1mm_NO_PASTE" (layer "F.Cu") (at {tx} {ty}) (attr through_hole exclude_from_pos_files exclude_from_bom) (fp_text reference "{ref}" (at 0 {(-2.5 if ty<100 else 2.5)} 90) (layer "F.SilkS") {effects()}) (fp_text value "PROBE_ONLY_{s}" (at 0 0) (layer "F.Fab") {effects(.4)}) (pad "1" thru_hole circle (at 0 0) (size 1 1) (drill .5) (layers "*.Cu" "*.Mask") (net {n} "{net(kind,s)}")))')
    holes=[(-15,-12),(15,-12),(-12,12)]
    if kind=='DP':holes=[(x,-y) for x,y in holes]
    for i,(x,y) in enumerate(holes,1):
        lines.append(f' (footprint "Owned_Coupon:Datum_2mm_NPTH" (layer "F.Cu") (at {100+x} {100+y}) (attr board_only exclude_from_pos_files exclude_from_bom) (fp_text reference "H{i}" (at 0 -2) (layer "F.SilkS") {effects()}) (fp_text value "FIXTURE_DATUM_UNQUALIFIED" (at 0 0) (layer "F.Fab") {effects(.4)}) (pad "" np_thru_hole circle (at 0 0) (size 2 2) (drill 2) (layers "*.Cu" "*.Mask")))')
    lines.append(f' (gr_rect (start 80 82) (end 120 118) (stroke (width .05) (type default)) (fill none) (layer "Edge.Cuts") (tstamp {uid(kind+"outline")}))')
    for txt,x,y in [(f'{kind} RESEARCH ONLY',100,83.3),('NO SIGNAL/VOLTAGE ASSIGNMENT',100,116.7)]:
        lines.append(f' (gr_text "{txt}" (at {x} {y}) (layer "F.SilkS") {effects(.8)} (tstamp {uid(kind+txt)}))')
    lines.append(')')
    (ROOT/f'endpoint_{kind}.kicad_pcb').write_text('\n'.join(lines)+'\n')
    return name

def schematic(kind,name):
    title=f'endpoint_{kind}'; rootid=uid(title+'schematic')
    es='(effects (font (size 1.27 1.27)))'
    lines=['(kicad_sch (version 20230121) (generator eeschema)',f'(uuid {rootid}) (paper "A4")',
     '(lib_symbols',
     ' (symbol "Owned:Endpoint26" (pin_numbers hide) (pin_names (offset 1.016)) (in_bom yes) (on_board yes)',
     f' (property "Reference" "J" (at 0 38.1 0) {es}) (property "Value" "Endpoint26" (at 0 -38.1 0) {es})',
     f' (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
     ' (symbol "Endpoint26_0_1" (rectangle (start -7.62 68.58) (end 7.62 -68.58) (stroke (width .254) (type default)) (fill (type background))))',
     ' (symbol "Endpoint26_1_1"']
    for i,s in enumerate(SITES):
        lines.append(f' (pin passive line (at -12.7 {63.5-i*5.08:.4f} 0) (length 5.08) (name "{s}" {es}) (number "{s}" {es}))')
    lines += ['))', ' (symbol "Owned:Probe" (pin_numbers hide) (pin_names (offset 0) hide) (in_bom yes) (on_board yes)',
     f' (property "Reference" "TP" (at 0 2.54 0) {es}) (property "Value" "PROBE_ONLY" (at 0 -2.54 0) {es})',
     ' (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
     ' (symbol "Probe_0_1" (circle (center 0 0) (radius .762) (stroke (width .254) (type default)) (fill (type none))))',
     f' (symbol "Probe_1_1" (pin passive line (at -2.54 0 0) (length 2.54) (name "PROBE" {es}) (number "1" {es})))', '))']
    def instance(lib,ref,val,x,y,pins,fp):
        id_=uid(kind+ref+'instance')
        lines.append(f' (symbol (lib_id "Owned:{lib}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {id_})')
        if ref=='J1':
            lines.append(f' (property "Reference" "{ref}" (at {x} {y-73.66} 0) {es}) (property "Value" "{val}" (at {x} {y+73.66} 0) {es})')
        else:
            left='(effects (font (size 1.27 1.27)) (justify left))'
            lines.append(f' (property "Reference" "{ref}" (at {x+3.81} {y} 0) {left}) (property "Value" "{val}" (at {x+16.51} {y} 0) {left})')
        lines.append(f' (property "Footprint" "{fp}" (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))')
        for p in pins:lines.append(f' (pin "{p}" (uuid {uid(kind+ref+p)}))')
        lines.append(f' (instances (project "{title}" (path "/{rootid}" (reference "{ref}") (unit 1)))))')
    instance('Endpoint26','J1',f'BM28_24{kind}_COORDINATE_SITES',101.6,101.6,SITES,f'RAZR_ENDPOINT_RESEARCH:{name}')
    for i,s in enumerate(SITES):
        y=38.1+i*5.08
        instance('Probe',f'TP{i+1:02d}',f'PROBE_{s}',152.4,y,['1'],'Owned_Coupon:ProbePad_1mm_NO_PASTE')
        for a,b in [((76.2,y),(88.9,y)),((139.7,y),(149.86,y))]:
            lines.append(f' (wire (pts (xy {a[0]} {a[1]:.4f}) (xy {b[0]} {b[1]:.4f})) (stroke (width 0) (type default)) (uuid {uid(kind+str(a)+str(b))}))')
            lines.append(f' (global_label "{net(kind,s)}" (shape bidirectional) (at {a[0]} {a[1]:.4f} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {uid(kind+str(a)+"label")}))')
    lines.append(')')
    (ROOT/f'{title}.kicad_sch').write_text('\n'.join(lines)+'\n')

for kind in ('DP','DS'):
    name=board(kind);schematic(kind,name)
    project={'meta':{'filename':f'endpoint_{kind}.kicad_pro','version':1},
      'board':{'design_settings':{'rules':{'min_clearance':.10,'min_track_width':.10,'min_hole_clearance':.25,'min_copper_edge_clearance':.25},'defaults':{'clearance_min':.10}}},
      'net_settings':{'classes':[{'name':'Default','clearance':.10,'track_width':.10,'via_diameter':.6,'via_drill':.3}],'meta':{'version':3}},
      'erc':{'erc_exclusions':[]}}
    (ROOT/f'endpoint_{kind}.kicad_pro').write_text(json.dumps(project,indent=2)+'\n')
(ROOT/'RAZR_ENDPOINT_ASSEMBLY.pretty').mkdir(exist_ok=True)
(ROOT/'Owned_Coupon.pretty').mkdir(exist_ok=True)
for p in LIB.glob('*.kicad_mod'):
    (ROOT/'RAZR_ENDPOINT_ASSEMBLY.pretty'/p.name).write_text(p.read_text().replace('smd exclude_from_pos_files exclude_from_bom','smd'))
(ROOT/'Owned_Coupon.pretty'/'ProbePad_1mm_NO_PASTE.kicad_mod').write_text('(footprint \"ProbePad_1mm_NO_PASTE\" (version 20221018) (generator razr_owned_coupon_r2) (layer \"F.Cu\") (attr through_hole exclude_from_pos_files exclude_from_bom) (fp_text reference \"REF**\" (at 0 -2.5 90) (layer \"F.SilkS\") '+effects() + ') (fp_text value \"PROBE_ONLY\" (at 0 0) (layer \"F.Fab\") '+effects(.4)+') (pad \"1\" thru_hole circle (at 0 0) (size 1 1) (drill .5) (layers \"*.Cu\" \"*.Mask\")))\n')
(ROOT/'Owned_Coupon.pretty'/'Datum_2mm_NPTH.kicad_mod').write_text('(footprint \"Datum_2mm_NPTH\" (version 20221018) (generator razr_owned_coupon_r2) (layer \"F.Cu\") (attr board_only exclude_from_pos_files exclude_from_bom) (fp_text reference \"REF**\" (at 0 -2) (layer \"F.SilkS\") '+effects() + ') (fp_text value \"FIXTURE_DATUM_UNQUALIFIED\" (at 0 0) (layer \"F.Fab\") '+effects(.4)+') (pad \"\" np_thru_hole circle (at 0 0) (size 2 2) (drill 2) (layers \"*.Cu\" \"*.Mask\")))\n')
(ROOT/'fp-lib-table').write_text('(fp_lib_table (lib (name "RAZR_ENDPOINT_RESEARCH")(type "KiCad")(uri "${KIPRJMOD}/RAZR_ENDPOINT_ASSEMBLY.pretty")(options "")(descr "Assembly flags only; exact research geometry")) (lib (name "Owned_Coupon")(type "KiCad")(uri "${KIPRJMOD}/Owned_Coupon.pretty")(options "")(descr "Owned unqualified probe and datum patterns")))\n')
with (ROOT/'research_BOM.csv').open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(['board','reference','quantity','component','part_selection_status','assembly_role'])
    for kind in ('DP','DS'):
        writer.writerow([kind,'J1',1,f'BM28B0.6-24{kind}/2-0.35V(53)','exact series; supplier authority conflicts unresolved','static continuity connector'])
        writer.writerow([kind,'TP01-TP26',26,'PCB copper probe pads','no discrete parts','unpowered continuity measurement only'])
(ROOT/'build_receipt.json').write_text(json.dumps({'frozen_library_copies':copied,'boards':2,'independent_electrical_nets_per_board':26,
 'connector_copper_lands_per_board':28,'probe_pads_per_board':26,'snapshot_before_native_validation':True,
 'authoritative_native_validation':'native_pcba_receipt.json; later independent ERC receipts if present',
 'phone_full_PCB':False,'continuity_coupon_complete_routing_candidate':True,'coupon_fabrication_go':False,
 'manufacturing_go':False},indent=2)+'\n')
print('Created two owned passive continuity PCBA candidates; native parser/DRC still required.')

# Exact owned symbol library accompanies the embedded cache, so actual ERC
# can compare against a real local library instead of waiving missing symbols.
text=(ROOT/'endpoint_DP.kicad_sch').read_text()
start=text.index('(lib_symbols');depth=0;quoted=False;escaped=False;end=None
for i,ch in enumerate(text[start:],start):
    if escaped:escaped=False;continue
    if ch=='\\' and quoted:escaped=True;continue
    if ch=='"':quoted=not quoted;continue
    if quoted:continue
    if ch=='(':depth+=1
    elif ch==')':
        depth-=1
        if depth==0:end=i+1;break
assert end is not None
body=text[start+len('(lib_symbols'):end-1].replace('(symbol "Owned:','(symbol "')
(ROOT/'Owned_Coupon.kicad_sym').write_text('(kicad_symbol_lib (version 20211014) (generator razr_owned_coupon_r2)'+body+')\n')
(ROOT/'sym-lib-table').write_text('(sym_lib_table (lib (name "Owned")(type "KiCad")(uri "${KIPRJMOD}/Owned_Coupon.kicad_sym")(options "")(descr "Owned coordinate-site continuity-only symbols")))\n')
