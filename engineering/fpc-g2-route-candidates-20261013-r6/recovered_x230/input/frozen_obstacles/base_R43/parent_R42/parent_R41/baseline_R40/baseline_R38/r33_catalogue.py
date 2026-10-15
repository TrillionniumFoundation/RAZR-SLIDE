"""TE catalogued dimensions -> actual OCC volume as a conservative PROXY.
Does not imply a native, oriented, mounted or manufacturable supplier CAD model.
"""
from __future__ import annotations
import itertools,json
import cadquery as cq
from r25_capture import ROOT,intersection
from r33_parts import catalogue_TE_box,TE_SOURCE,TE_CATALOGUE_MM
from r32_cartridge import CHANNEL

def run(write=True):
    B=cq.importers.importBrep(str(ROOT/'cad/R33_B_BILATERAL_PIN_PORTS.brep')).val()
    permutations=sorted(set(itertools.permutations((TE_CATALOGUE_MM['width'],TE_CATALOGUE_MM['length'],TE_CATALOGUE_MM['uncompressed_height']))))
    spans=tuple(CHANNEL[j]-CHANNEL[i] for i,j in ((0,1),(2,3),(4,5)))
    rows=[]
    for side in 'LR':
        for dim in permutations:
            te=catalogue_TE_box(side,dim)
            v=intersection(te,B)
            fits=all(a<=b for a,b in zip(dim,spans))
            rows.append(dict(side=side,xyz_dimension_mm=dim,
                      nominal_channel_xyz_mm=spans,
                      possible_axis_aligned_channel_fit=fits,
                      B_shell_interference_mm3=round(v,7)))
        print('R33 TE CATALOGUE PROXY',side,'six variants',flush=True)
    d=dict(revision='R33 official catalog dimensional negative fit: AABB/OCC proxy, NO manufacturer STEP',
           te_official_url=TE_SOURCE,part_number='2199001-1',
           te_catalogue_dimensions=TE_CATALOGUE_MM,
           download_of_native_supplier_STEP_attempted_but_NOT_completed=True,
           actual_oem_supplier_CAD_imported=False,
           configurations=len(rows),rows=rows,
           axis_aligned_channel_fit_count=sum(x['possible_axis_aligned_channel_fit'] for x in rows),
           R32_and_R33_channel_not_an_electrical_connector=True,
           signal_rating_must_not_be_counted_for_dual_battery_power=True,
           USB_high_speed_return_path_SI_not_qualified=True,
           real_battery_main_power_connection_NOT_SELECTED=True,
           real_signal_first_make_last_break_position_NOT_MEASURED=True,
           actual_OLED_panel_not_selected_and_lifetime_not_qualified=True,
           manufacturing_go=False)
    if write:(ROOT/'verification/R33_catalogue.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    return d
if __name__=='__main__':run()
