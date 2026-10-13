#!/usr/bin/env python3
"""Run in the extracted KiCad 7 environment; verify native pad and keepout data.

Requires actual pcbnew, not a surrogate S-expression parser. Native source
footprint hashes and engine-read geometry are bound into the receipt.
"""
from pathlib import Path
import datetime,hashlib,json,platform
import pcbnew
ROOT=Path('/home/qian-qi/Documents/Codex/RAZR_SLIDE_WORK_20261013/native_endpoint_kicad_verify')
LIB=ROOT/'RAZR_ENDPOINT_RESEARCH.pretty'
rows=[]
for p in sorted(LIB.glob('*.kicad_mod')):
    f=pcbnew.FootprintLoad(str(LIB),p.stem)
    assert f is not None,p.name
    pads=list(f.Pads());sites=set(x.GetNumber() for x in pads)
    assert len(pads)==28 and len(sites)==26
    paste=[x for x in f.GraphicalItems() if x.GetLayer()==pcbnew.F_Paste]
    assert len(paste)==28
    role='DP' if '24DP_' in p.name else 'DS'
    zones=list(f.Zones());assert len(zones)==(0 if role=='DP' else 1)
    if zones:
        z=zones[0]
        assert z.GetIsRuleArea()
        assert all(getattr(z,k)() for k in ['GetDoNotAllowTracks','GetDoNotAllowVias','GetDoNotAllowPads','GetDoNotAllowCopperPour'])
        assert not z.GetDoNotAllowFootprints()
    geometry=[]
    for pad in pads:
        pos=pad.GetPosition();size=pad.GetSize()
        geometry.append(dict(site=pad.GetNumber(),x_mm=pcbnew.ToMM(pos.x),
            y_mm=pcbnew.ToMM(pos.y),w_mm=pcbnew.ToMM(size.x),h_mm=pcbnew.ToMM(size.y)))
    rows.append(dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        native_pad_count=len(pads),native_electrical_site_count=len(sites),
        native_stencil_primitive_count=len(paste),native_keepout_count=len(zones),
        pad_dimensions_read_by_native_engine=geometry))
assert len(rows)==2
svgs=[dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    for p in sorted((ROOT/'svg').glob('*.svg'))]
assert len(svgs)==2 and all(x['bytes']>1000 for x in svgs)
assert (ROOT/'native_footprint_export_repaired.exit').read_text().strip()=='0'
packages=[dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    for p in sorted(ROOT.glob('*.deb'))]
rec=dict(machine=platform.node(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    native_engine='KiCad '+pcbnew.Version(),runtime_unprivileged_deb_extraction_only=True,
    installed_packages_mutated=False,user_existing_KiCad_config_mutated=False,
    rows=rows,svgs=svgs,runtime_packages=packages,
    source_serialization_rejection_retained='REJECTED_DS_keepout_serialization.kicad_mod',
    native_KiCad_engine_load_verified=True,physical_PCBA_qualified=False,manufacturing_go=False)
(ROOT/'native_kicad_receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
print(json.dumps(rec,indent=2))
