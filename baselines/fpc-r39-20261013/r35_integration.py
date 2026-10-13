"""R35 fused reinforcement, machined dual keyway and bore. Evidence, not certification."""
import cadquery as cq
import json,hashlib,shutil
from r25_capture import ROOT,intersection
from r35_parts import (inboard_rail,arm_guide,fastener_bore,bored_cap,pin,
                       te_signal_envelope,part_metadata)
from r34_integration import A_OUT as R34_A, B_OUT as R34_B
A_OUT=ROOT/'cad/R35_A_R34_UNCHANGED.brep'
B_OUT=ROOT/'cad/R35_B_INBOARD_RAILS_AND_GUIDES.brep'

def build():
    b=cq.importers.importBrep(str(R34_B)).val(); operations=[]
    for side in 'LR':
        before=b.Volume(); b=b.fuse(inboard_rail(side)).clean()
        operations.append(dict(side=side,operation='fuse_inboard_reinforcement',net_delta_mm3=round(b.Volume()-before,9),solids=len(b.Solids())))
    for side in 'LR':
        for name,tool in [('machine_guide',arm_guide(side)),('machine_pin_bore',fastener_bore(side))]:
            before=b.Volume();b=b.cut(tool).clean()
            operations.append(dict(side=side,operation=name,removed_mm3=round(before-b.Volume(),9),solids=len(b.Solids())))
    return b,operations

def run(write=True):
    a=cq.importers.importBrep(str(R34_A)).val(); old=cq.importers.importBrep(str(R34_B)).val()
    b,ops=build()
    caprows=[]
    for side in 'LR':
        cap=bored_cap(side); needle=pin(side);te=te_signal_envelope(side)
        caprows.append(dict(side=side,cap_valid=cap.isValid(),cap_solids=len(cap.Solids()),
          cap_B_intersection_mm3=round(intersection(cap,b),9),
          cap_TE_intersection_mm3=round(intersection(cap,te),9),
          pin_B_intersection_mm3=round(intersection(needle,b),9),
          pin_cap_intersection_mm3=round(intersection(needle,cap),9),
          unbored_cap_volume_mm3=round(cap_bridge_vol(side),9),
          bored_cap_volume_mm3=round(cap.Volume(),9)))
    report=dict(revision='R35 inboard-rail captured front bridge research, NO electrical qualification',
      A_bytes_unchanged=True,B_is_valid=b.isValid(),B_solid_count=len(b.Solids()),
      B_R34_volume_mm3=round(old.Volume(),9),B_R35_volume_mm3=round(b.Volume(),9),
      B_volume_delta_mm3=round(b.Volume()-old.Volume(),9),operations=ops,part_metadata=part_metadata(),
      cap_and_pin=caprows,vendor_native_TE_STEP_imported=False,manufacturing_go=False)
    if write:
        shutil.copyfile(R34_A,A_OUT);cq.exporters.export(b,str(B_OUT))
        for side in 'LR':
            cq.exporters.export(bored_cap(side),str(ROOT/f'cad/R35_{side}_UNQUALIFIED_CAPTURE_BRIDGE.brep'))
            cq.exporters.export(pin(side),str(ROOT/f'cad/R35_{side}_UNQUALIFIED_STEEL_PIN_PROXY.brep'))
        (ROOT/'verification/R35_integration.json').write_text(json.dumps(report,indent=2)+'\n')
    print('R35 INTEGRATION',report['B_solid_count'],report['B_volume_delta_mm3'],report['cap_and_pin'],flush=True)
    return report

def cap_bridge_vol(side):
    from r35_parts import cap_bridge
    return cap_bridge(side).Volume()

if __name__=='__main__':run()
