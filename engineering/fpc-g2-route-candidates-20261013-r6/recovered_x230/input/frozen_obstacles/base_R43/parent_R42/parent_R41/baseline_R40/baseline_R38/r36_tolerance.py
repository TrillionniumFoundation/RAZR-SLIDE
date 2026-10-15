"""Hypothetical XYZ pose stress for R36 keeper, not GD&T or force analysis."""
import json,itertools
import cadquery as cq
from r25_capture import ROOT,intersection
from r36_parts import keeper,catalog_m08x2_screw,catalog_m08x2_shank,catalog_m08x2_head
from r35_parts import pin
WIDTHS=(.02,.05,.10)
def run(write=True):
    B=cq.importers.importBrep(str(ROOT/'cad/R36_B_INBOARD_KEEPER_BOSSES_AND_CLEARANCE_BORES.brep')).val()
    rows=[]
    for w in WIDTHS:
        for side in 'LR':
            k=keeper(side);p=pin(side);screw=catalog_m08x2_screw(side);stem=catalog_m08x2_shank(side);head=catalog_m08x2_head(side)
            for dx,dy,dz in itertools.product((-w,0,w),repeat=3):
                target=k.translate((dx,dy,dz))
                rows.append(dict(side=side,hypothesized_error_mm=w,xyz=[dx,dy,dz],
                     keeper_vs_B=round(intersection(target,B),9),
                     keeper_vs_R35_installed_pin=round(intersection(target,p),9),
                     keeper_vs_M08_screw_AABB=round(intersection(target,screw),9),
                     keeper_vs_M08_screw_shank=round(intersection(target,stem),9),
                     keeper_vs_M08_screw_head=round(intersection(target,head),9)))
            print('R36 TOL',w,side,27,'configs',flush=True)
    agg={str(w):dict(configurations=sum(x['hypothesized_error_mm']==w for x in rows),
          keeper_B_jam=sum(x['hypothesized_error_mm']==w and x['keeper_vs_B']>1e-7 for x in rows),
          keeper_installed_pin_jam=sum(x['hypothesized_error_mm']==w and x['keeper_vs_R35_installed_pin']>1e-7 for x in rows),
          keeper_M08_shank_hole_jam=sum(x['hypothesized_error_mm']==w and x['keeper_vs_M08_screw_shank']>1e-7 for x in rows),
          keeper_M08_head_axial_contact=sum(x['hypothesized_error_mm']==w and x['keeper_vs_M08_screw_head']>1e-7 for x in rows))
          for w in WIDTHS}
    out=dict(revision='R36 hypothetical XYZ offsets, NOT manufacturer GD&T',configurations=len(rows),
             intersections_per_config=4,records=rows,aggregation=agg,
             fastener_mating_torque_or_threads_not_tested=True,
             pin_under_load_deformation_not_tested=True,
             real_OLED_board_battery_envelopes_not_imported=True,manufacturing_go=False)
    if write:(ROOT/'verification/R36_tolerance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('R36 TOL aggregate',agg,flush=True)
    return out
if __name__=='__main__':run()
