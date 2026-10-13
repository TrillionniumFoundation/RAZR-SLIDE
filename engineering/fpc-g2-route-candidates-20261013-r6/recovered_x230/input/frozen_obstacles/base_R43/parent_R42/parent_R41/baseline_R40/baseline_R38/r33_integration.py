"""R33 actual OCC B housing pin-ports and two bored non-electrical gauges.
Only a concept keeper; axle clip, shear strength and double-ended snap-lock absent.
"""
from __future__ import annotations
import json,hashlib,shutil
import cadquery as cq
from r25_capture import ROOT,intersection
from r33_parts import bore,bored_gauge,keeper_pin,constraints

A_BASE=ROOT/'cad/R32_A_R31_UNMODIFIED.brep'
B_BASE=ROOT/'cad/R32_B_REAR_CASSETTE_BAYS.brep'
A_OUT=ROOT/'cad/R33_A_R32_BYTE_IDENTICAL.brep'
B_OUT=ROOT/'cad/R33_B_BILATERAL_PIN_PORTS.brep'

def run(write=True):
    A=cq.importers.importBrep(str(A_BASE)).val()
    B=cq.importers.importBrep(str(B_BASE)).val()
    raw=B.Volume(); cuts=[]
    for side in 'LR':
        before=B.Volume()
        B=B.cut(bore(side)).clean()
        g=bored_gauge(side)
        pin=keeper_pin(side)
        assert g.isValid() and len(g.Solids())==1
        assert pin.isValid() and len(pin.Solids())==1
        cuts.append(dict(side=side,actual_B_removed_mm3=round(before-B.Volume(),9),
                         gauge_bore_removed_mm3=round(__import__('r32_cartridge').gauge(side).Volume()-g.Volume(),9),
                         pin_assembled_B_interference_mm3=round(intersection(B,pin),9),
                         pin_assembled_gauge_interference_mm3=round(intersection(g,pin),9),
                         gauge_B_interference_mm3=round(intersection(g,B),9),
                         B_valid_single=B.isValid() and len(B.Solids())==1))
        print('R33 BORE',side,cuts[-1],flush=True)
    assert B.isValid() and len(B.Solids())==1
    d=dict(revision='R33 removable keeper pin initial CAD: rear cassette envelope remains unpowered',
           R32_A_sha256=hashlib.sha256(A_BASE.read_bytes()).hexdigest(),
           R32_B_sha256=hashlib.sha256(B_BASE.read_bytes()).hexdigest(),
           A_valid_single=A.isValid() and len(A.Solids())==1,
           B_valid_single=B.isValid() and len(B.Solids())==1,
           A_export_byte_equal_source=True,
           B_R32_mm3=round(raw,9),B_R33_mm3=round(B.Volume(),9),
           bore_cut_mm3=round(raw-B.Volume(),9),
           bored_channels=cuts,geometry_constraints=constraints(),
           axial_pin_clip_retainer_not_designed=True,
           cassette_does_not_contain_actual_TE_spring_contact=True,
           no_contact_a_side_mating_geometry=True,
           no_load_force_lifetime_material_or_process_signoff=True,
           manufacturing_go=False)
    if write:
        shutil.copyfile(A_BASE,A_OUT)
        cq.exporters.export(B,str(B_OUT))
        for side in 'LR':
            cq.exporters.export(bored_gauge(side),str(ROOT/f'cad/R33_{side}_BORED_UNPOWERED_GAUGE.brep'))
            cq.exporters.export(keeper_pin(side),str(ROOT/f'cad/R33_{side}_KEEPER_PIN_UNQUALIFIED.brep'))
        (ROOT/'verification/R33_integration.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    return d,(A,B)
if __name__=='__main__':run()
