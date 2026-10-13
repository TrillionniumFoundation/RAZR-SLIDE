"""Catalogue-only negative hardware fit checks, not vendor-native CAD or certification."""
import json
import cadquery as cq
from r25_capture import ROOT,intersection
from r30_mechanics import mirrored
from r35_parts import bored_cap,te_signal_envelope,PIN_X0,PIN_X1,PIN_Y,PIN_Z
from r36_parts import rejected_square_nut

def oversized_standard_ring_shaft(side):
    # DIN6799-0.8 catalogue recommends ~1.2mm application shaft.
    s=cq.Solid.makeCylinder(.60,PIN_X1-PIN_X0,
       cq.Vector(PIN_X0,PIN_Y,PIN_Z),cq.Vector(1,0,0))
    return mirrored(s,side)

def run(write=True):
    B=cq.importers.importBrep(str(ROOT/'cad/R36_B_INBOARD_KEEPER_BOSSES_AND_CLEARANCE_BORES.brep')).val()
    rows=[]
    for side in 'LR':
        large=oversized_standard_ring_shaft(side)
        cap=bored_cap(side)
        te=te_signal_envelope(side)
        nut=rejected_square_nut(side)
        rows.append(dict(side=side,standard_ring_shaft_diameter_mm=1.2,
           current_pin_diameter_mm=.22,
           large_shaft_B_shell_overlap_mm3=round(intersection(large,B),9),
           large_shaft_R35_cap_overlap_mm3=round(intersection(large,cap),9),
           large_shaft_TE_catalogue_gauge_overlap_mm3=round(intersection(large,te),9),
           square_nut_R36_B_interference_mm3=round(intersection(nut,B),9)))
    out=dict(revision='R36 rejected direct DIN6799-0.8 conversion + M0.8 square-nut envelope',
      sources={'American_Ring_DIN6799_0p8':'https://americanring.com/products/snap-ring.aspx?item=DIN6799-0.8&units=metric',
       'Matsumoto_TE_00085':'https://www.ipros.com/product/detail/2000404048/',
       'Matsumoto_TN_00005':'https://matsumotoneji.cart.fc2.com/?ca=77'},
      large_shaft_is_only_catalogue_diameter_surrogate=True,
      square_nut_is_only_catalogue_AABB=True,
      native_hardware_3D_not_acquired=True,
      rows=rows,direct_existing_pin_to_DIN_ring_is_not_a_drop_in_replacement=True,
      no_structural_signoff=True,manufacturing_go=False)
    if write:(ROOT/'verification/R36_catalogue_fit.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print('R36 CATALOGUE',rows,flush=True)
    return out
if __name__=='__main__':run()
