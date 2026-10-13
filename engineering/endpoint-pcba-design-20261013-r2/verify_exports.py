#!/usr/bin/env python3
"""Independent geometry/identity check on actual exported Gerber and drills.

Does not import or run the builder. Nominal land dimensions below come from
the frozen native-endpoint primary-source review; they are not process approval.
"""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,re
ROOT=Path(__file__).resolve().parent
native=json.loads((ROOT/'native_pcba_receipt.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def paste_regions(text):
    fmt=re.search(r'%FSLAX(\d)(\d)Y(\d)(\d)\*%',text)
    assert fmt and fmt[2]==fmt[4]=='6'
    regions=[]
    for block in re.findall(r'G36\*(.*?)G37\*',text,re.S):
        points=[(int(x)/1e6,int(y)/1e6) for x,y in re.findall(r'X(-?\d+)Y(-?\d+)D0[12]\*',block)]
        assert len(points)==5 and points[0]==points[-1]
        xs=set(x for x,y in points);ys=set(y for x,y in points)
        assert len(xs)==len(ys)==2
        regions.append({'width_mm':round(max(xs)-min(xs),6),'height_mm':round(max(ys)-min(ys),6),
                        'center_mm':[round((min(xs)+max(xs))/2,6),round((min(ys)+max(ys))/2,6)]})
    return regions
def drills(p,diameter):
    text=p.read_text();assert '; FORMAT={-:-/ absolute / metric / decimal}' in text
    tools=re.findall(r'^T\d+C([\d.]+)$',text,re.M);assert [float(x) for x in tools]==[diameter]
    return [(float(x),float(y)) for x,y in re.findall(r'^X(-?[\d.]+)Y(-?[\d.]+)$',text,re.M)]
rows=[]
for kind,signal,power in [('DP',(.18,.615),(.52,.32)),('DS',(.18,.31),(.53,.33))]:
    folder=ROOT/'research_exports'/kind
    regions=paste_regions((folder/f'endpoint_{kind}-F_Paste.gtp').read_text())
    dims=Counter((p['width_mm'],p['height_mm']) for p in regions)
    assert dims==Counter({signal:24,power:4}),dims
    board=next(r for r in native['boards'] if r['board']==kind)
    pth=drills(folder/f'endpoint_{kind}-PTH.drl',.5)
    npth=drills(folder/f'endpoint_{kind}-NPTH.drl',2)
    expected_pth={(p['position_mm'][0],-p['position_mm'][1]) for p in board['pads'] if p['reference'].startswith('TP')}
    expected_npth={(h['xy'][0],-h['xy'][1]) for h in board['holes']}
    assert len(pth)==26 and set(pth)==expected_pth
    assert len(npth)==3 and set(npth)==expected_npth
    with (folder/f'endpoint_{kind}_placement.csv').open() as f:pos=list(csv.DictReader(f))
    assert len(pos)==1 and pos[0]['Ref']=='J1' and float(pos[0]['PosX'])==100 and float(pos[0]['PosY'])==-100 and pos[0]['Side']=='top'
    assert not any('B_Paste' in p.name for p in folder.iterdir())
    rows.append({'board':kind,'paste_signal_rectangles':24,'paste_power_rectangles':4,
                 'total_nominal_paste_area_mm2':round(sum(p['width_mm']*p['height_mm'] for p in regions),7),
                 'nominal_0_08mm_stencil_volume_mm3_arithmetic_only':round(sum(p['width_mm']*p['height_mm'] for p in regions)*.08,9),
                 'PTH_probe_holes':26,'NPTH_datum_holes':3,'placement_discrete_connector_count':1,
                 'drill_and_placement_axis_convention':'native export x=board_x, y=-board_y, absolute origin'})
for export in native['exports']:assert sha(ROOT/export['path'])==export['sha256']
receipt={'export_files_SHA256_verified':len(native['exports']),'rows':rows,
 'supplier_paste_volume_discrepancy_resolved':False,'mask_expansion_0_hypothesis_qualified':False,
 'material_process_stackup_qualified':False,'native_ERC_in_this_receipt':False,
 'physical_continuity_verified':False,'coupon_fabrication_go':False,'manufacturing_go':False}
(ROOT/'independent_export_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
