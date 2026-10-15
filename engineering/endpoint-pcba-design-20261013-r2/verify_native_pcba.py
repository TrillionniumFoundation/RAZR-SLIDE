#!/usr/bin/env python3
"""Independent verification through actual KiCad engines, not builder import.

Run in extracted KiCad7 environment. Native DRC, native XML schematic netlist,
native board topology and actual negative controls all have to agree. ERC is
explicitly unexecuted in this KiCad7-only environment.
"""
from pathlib import Path
import csv, hashlib, itertools, json, os, re, subprocess, sys
import xml.etree.ElementTree as ET
import pcbnew

ROOT=Path(__file__).resolve().parent
CLI=Path(os.environ.get('RAZR_KICAD_CLI','/home/qian-qi/Documents/Codex/RAZR_SLIDE_WORK_20261013/native_endpoint_kicad_verify/extracted/usr/bin/kicad-cli'))
LOG=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args):
    p=subprocess.run([str(CLI),*args],cwd=ROOT,text=True,capture_output=True)
    LOG.append({'argv':[str(CLI),*args],'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    assert p.returncode==0,LOG[-1]
def mm(v):return round(pcbnew.ToMM(v),6)
def pos(item):p=item.GetPosition();return [mm(p.x),mm(p.y)]
def drc(board,path,serialized_source=None):
    source=Path(serialized_source or board.GetFileName()).resolve()
    if source.name.startswith('REJECTED_'):
        source.with_suffix('.kicad_pro').write_bytes((ROOT/'endpoint_DP.kicad_pro').read_bytes())
    p=subprocess.run([sys.executable,str(ROOT/'native_drc_one.py'),str(source),str(path)],cwd=ROOT,text=True,capture_output=True)
    assert p.returncode==0,(p.stdout,p.stderr)
    result=json.loads(p.stdout)
    LOG.append({'fresh_native_DRC':result,'exit_code':p.returncode})
    return result['counts']

spec=json.loads((ROOT/'mating_site_map.json').read_text())
rows=[]
for kind in ('DP','DS'):
    title='endpoint_'+kind; boardpath=ROOT/(title+'.kicad_pcb')
    board=pcbnew.LoadBoard(str(boardpath));board.BuildConnectivity()
    connector=next(fp for fp in board.GetFootprints() if fp.GetReference()=='J1')
    allpads=list(board.GetPads()); cp=list(connector.Pads())
    assert len(cp)==28 and len({p.GetNumber() for p in cp})==26
    assert len(allpads)==57 and len(list(board.GetTracks()))==80
    pads=[];by_net={}
    for p in allpads:
        ref=p.GetParent().GetReference(); name=p.GetNumber(); n=p.GetNetname()
        pads.append({'reference':ref,'site':name,'net':n,'position_mm':pos(p),'size_mm':[mm(p.GetSize().x),mm(p.GetSize().y)],'drill_mm':[mm(p.GetDrillSize().x),mm(p.GetDrillSize().y)]})
        if n: by_net.setdefault(n,[]).append((ref,name))
    assert len(by_net)==26
    for row in spec['mapping']:
        n=row['net'];site=row[kind+'_site'];tp=row[kind+'_testpoint']
        expected=[('J1',site)]*(2 if site.startswith('P_') else 1)+[(tp,'1')]
        assert sorted(by_net[n])==sorted(expected),(kind,n,by_net[n],expected)
    native_drc=drc(board,ROOT/(title+'_DRC.rpt'))
    assert all(v==0 for v in native_drc.values()),native_drc
    assert board.GetConnectivity().GetUnconnectedCount(False)==0
    command(['sch','export','netlist','--format','kicadxml','--output',title+'.net',title+'.kicad_sch'])
    xml=ET.parse(ROOT/(title+'.net')).getroot()
    snets={n.attrib['name']:sorted((p.attrib['ref'],p.attrib['pin']) for p in n.findall('node')) for n in xml.findall('nets/net')}
    assert len(snets)==26
    for row in spec['mapping']:
        expected=sorted([('J1',row[kind+'_site']),(row[kind+'_testpoint'],'1')])
        assert snets[row['net']]==expected,(kind,row['net'],snets[row['net']],expected)
    # Native BOM is extracted from the schematic; probe pads are fabricated PCB
    # features and are explicitly not 26 ordered electronic components.
    with (ROOT/(title+'_native_BOM.csv')).open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['reference','value','footprint','procurement_role'])
        for comp in xml.findall('components/comp'):
            ref=comp.attrib['ref']
            writer.writerow([ref,comp.findtext('value'),comp.findtext('footprint'),'connector only' if ref=='J1' else 'PCB probe feature; no discrete part'])
    (ROOT/'research_exports'/kind).mkdir(parents=True,exist_ok=True)
    command(['pcb','export','gerbers','--output',f'research_exports/{kind}/','--layers','F.Cu,B.Cu,F.Paste,F.Mask,B.Mask,F.SilkS,Edge.Cuts',title+'.kicad_pcb'])
    command(['pcb','export','drill','--output',f'research_exports/{kind}/','--excellon-separate-th','--generate-map','--map-format','svg',title+'.kicad_pcb'])
    command(['pcb','export','pos','--output',f'research_exports/{kind}/{title}_placement.csv','--format','csv','--units','mm','--smd-only',title+'.kicad_pcb'])
    command(['pcb','export','svg','--output',f'research_exports/{kind}/endpoint_{kind}_board.svg','--page-size-mode','2','--exclude-drawing-sheet','--layers','F.Cu,B.Cu,F.Paste,F.Mask,B.Mask,F.SilkS,Edge.Cuts',title+'.kicad_pcb'])
    (ROOT/'research_exports'/kind/'schematic').mkdir(exist_ok=True)
    command(['sch','export','svg','--output',f'research_exports/{kind}/schematic/',title+'.kicad_sch'])
    native_board_svg=ROOT/'research_exports'/kind/f'endpoint_{kind}_board.svg'
    native_schematic_svg=ROOT/'research_exports'/kind/'schematic'/f'endpoint_{kind}.svg'
    assert native_board_svg.exists() and sha(native_board_svg)!=sha(native_schematic_svg)
    stale=ROOT/'research_exports'/kind/f'endpoint_{kind}.svg'
    if stale.exists():
        assert 'Eeschema-SVG' in stale.read_text()
        stale.rename(ROOT/f'REJECTED_svg_stale_parent_{kind}.svg')
    # Hole geometry is read from actual boards, not the generator's constants.
    holes=[{'reference':fp.GetReference(),'xy':pos(fp)} for fp in board.GetFootprints() if fp.GetReference().startswith('H')]
    zones=[]
    for z in connector.Zones():
        bb=z.GetBoundingBox();zones.append({'tracks_allowed':z.GetDoNotAllowTracks()==False,'pads_allowed':z.GetDoNotAllowPads()==False,'vias_allowed':z.GetDoNotAllowVias()==False,'copperpour_allowed':z.GetDoNotAllowCopperPour()==False,'bbox_mm':[mm(bb.GetX()),mm(bb.GetY()),mm(bb.GetWidth()),mm(bb.GetHeight())]})
    if kind=='DS':
        assert len(zones)==1
        assert all(zones[0][x]==False for x in ('tracks_allowed','pads_allowed','vias_allowed','copperpour_allowed'))
        assert zones[0]['bbox_mm']==[97.635,99.41,4.73,1.18],zones
    rows.append({'board':kind,'native_DRC':native_drc,'native_unconnected':0,'pads':pads,'native_schematic_nets':snets,'tracks':[{'net':t.GetNetname(),'start':[mm(t.GetStart().x),mm(t.GetStart().y)],'end':[mm(t.GetEnd().x),mm(t.GetEnd().y)],'width_mm':mm(t.GetWidth())} for t in board.GetTracks()], 'holes':holes,'connector_keepout':zones,'native_board_sha256':sha(boardpath),'native_schematic_sha256':sha(ROOT/(title+'.kicad_sch'))})

# Real native negative controls prove that a report-writing return True is not
# mistaken for passing DRC. Preserve both rejected native boards and reports.
negative=[]
for case in ('missing_route','wrong_net_bridge'):
    board=pcbnew.LoadBoard(str(ROOT/'endpoint_DP.kicad_pcb'))
    if case=='missing_route':
        chosen=next(t for t in board.GetTracks() if t.GetNetname()=='C01' and abs(mm(t.GetStart().y)-99.4075)<.000001)
        board.Remove(chosen)
    else:
        probes={fp.GetReference():fp for fp in board.GetFootprints()}
        t=pcbnew.PCB_TRACK(board);t.SetStart(probes['TP01'].GetPosition());t.SetEnd(probes['TP02'].GetPosition());t.SetWidth(pcbnew.FromMM(.1));t.SetLayer(pcbnew.F_Cu);t.SetNetCode(board.GetNetcodeFromNetname('C01'));board.Add(t)
    board.BuildConnectivity()
    bad=ROOT/('REJECTED_'+case+'.kicad_pcb');pcbnew.SaveBoard(str(bad),board)
    report=ROOT/('REJECTED_'+case+'_native_DRC.rpt');counts=drc(board,report,bad)
    if case=='missing_route':assert counts['unconnected pads']>0
    else:
        txt=report.read_text()
        assert counts['DRC violations']>0 and '[clearance]' in txt and 'actual 0.0000 mm' in txt and '[C01]' in txt and '[C02]' in txt
    negative.append({'case':case,'native_DRC':counts,'board_sha256':sha(bad),'report_sha256':sha(report),'correctly_rejected':True})

# Actual three-hole matching under our chosen Rx180 datum and the opposite
# Ry180 orientation. This is fixture keying, not connector intrinsic polarity.
coords={row['board']:[(h['xy'][0]-100,h['xy'][1]-100) for h in row['holes']] for row in rows}
ds=set(coords['DS']);correct=set((x,-y) for x,y in coords['DP']);wrong=set((-x,y) for x,y in coords['DP'])
assert correct==ds and wrong!=ds
datum={'Rx180_three_holes_match':True,'Ry180_three_holes_match':False,'DS_relative_holes_mm':sorted(ds),'DP_Rx180_holes_mm':sorted(correct),'DP_Ry180_holes_mm':sorted(wrong),'key_pins_present_or_physical_trial':False}
exports=[{'path':str(p.relative_to(ROOT)),'size':p.stat().st_size,'sha256':sha(p)} for p in sorted((ROOT/'research_exports').rglob('*')) if p.is_file()]
receipt={'native_KiCad_version':pcbnew.Version(),'host':'qian-qi','boards':rows,'negative_controls':negative,'datum':datum,'exports':exports,'command_log':LOG,'native_ERC_executed':False,'native_ERC_reason':'KiCad7 CLI has no erc subcommand; actual ERC remains pending','real_PCBA_built':False,'full_phone_PCB':False,'supplier_OEM_net_assignment':None,'physical_continuity_verified':False,'coupon_fabrication_go':False,'manufacturing_go':False}
(ROOT/'native_pcba_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'native_KiCad':pcbnew.Version(),'boards':2,'native_DRC_each':rows[0]['native_DRC'],'native_schematic_board_26_net_identity_each':True,'native_negative_controls_rejected':2,'native_ERC_executed':False,'manufacturing_go':False},indent=2))
