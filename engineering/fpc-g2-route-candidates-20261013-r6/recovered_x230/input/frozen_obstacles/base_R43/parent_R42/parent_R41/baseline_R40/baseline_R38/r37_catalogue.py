"""PEM TA-10-075 official catalogue DIMENSIONS only; NOT genuine native CAD.
Reject a naive switch from M0.8 to clinch pin. An enlarged base hole can
be boolean-cut, but existing keeper thickness/height cannot serve as a top sheet.
"""
import cadquery as cq,json
from r25_capture import ROOT,blk,intersection
from r30_mechanics import mirrored
from r35_parts import pin,bored_cap,te_signal_envelope
from r36_parts import KEEPER,SCREW_AXIS_Y,SCREW_AXIS_Z,axis_cylinder
from r37_parts import (PEM,PEM_TOP_MIN,PEM_TOP_MAX,PEM_TOP_HOLE_D,
                       PEM_BASE_HOLE_D,PEM_BASE_MIN,PEM_EDGE_MIN,R36_KEEPER_THICKNESS)

def run(write=True):
    b=cq.importers.importBrep(str(ROOT/'cad/R36_B_INBOARD_KEEPER_BOSSES_AND_CLEARANCE_BORES.brep')).val()
    a=cq.importers.importBrep(str(ROOT/'cad/R36_A_R35_UNCHANGED.brep')).val()
    rows=[]
    for side in 'LR':
        base_hole=mirrored(axis_cylinder(PEM_BASE_HOLE_D/2,32.15,34.30),side)
        cut=b.cut(base_hole).clean()
        # Catalog top sheet 0.71..0.79 thick along screw X; its 1.47mm
        # circular hole destroys the existing 0.96mm-high keeper flange.
        flange=mirrored(blk(31.69,32.44,KEEPER[2],KEEPER[3],KEEPER[4],KEEPER[5]),side)
        sheet_hole=mirrored(axis_cylinder(PEM_TOP_HOLE_D/2,31.65,32.49),side)
        machined=flange.cut(sheet_hole).clean()
        rows.append(dict(side=side,
            original_keeper_x_thickness_mm=R36_KEEPER_THICKNESS,
            vendor_top_sheet_min_thickness_mm=PEM_TOP_MIN,
            thickness_shortfall_mm=round(PEM_TOP_MIN-R36_KEEPER_THICKNESS,5),
            existing_keeper_z_height_mm=round(KEEPER[5]-KEEPER[4],5),
            vendor_top_sheet_hole_diameter_mm=PEM_TOP_HOLE_D,
            bigger_top_sheet_drill_makes_disconnected_solids=len(machined.Solids()),
            longer_proxy_panel_A_nominal_overlap_mm3=round(intersection(machined,a),9),
            PEM_base_hole_diameter_mm=PEM_BASE_HOLE_D,
            R36_original_base_bore_diameter_mm=.83,
            base_hole_cut_net_B_volume_loss_mm3=round(b.Volume()-cut.Volume(),9),
            re_bored_B_valid=cut.isValid(),re_bored_B_solids=len(cut.Solids()),
            vendor_panel_min_thickness_mm=PEM_BASE_MIN,
            vendor_hole_edge_min_mm=PEM_EDGE_MIN,
            real_base_material_or_edge_GDT_not_verified=True,
            top_sheet_does_not_fit_existing_keeper=True,
            PEM_native_3D_not_imported=True))
        print('PEM',side,'new hole cut',rows[-1]['base_hole_cut_net_B_volume_loss_mm3'],
              'split panel',len(machined.Solids()),flush=True)
    out=dict(revision='R37 manufacturer-catalogue PEM TA-10-075 negative fit, NOT vendor STEP',
       source_vendor='PennEngineering TA-10-075',
       vendor_url='https://catalog.pemnet.com/item/sheet-to-sheet-attachment/pem-type-ta--self-clinching-micropem--tackpin-/ta-10-075',
       PEM_is_self_clinching_no_screw_thread=True,
       PEM_requires_suitable_aluminum_base_panel=True,
       vendor_top_sheet_min_max_mm=[PEM_TOP_MIN,PEM_TOP_MAX],
       vendor_base_hole_mm=PEM_BASE_HOLE_D,
       vendor_top_sheet_hole_mm=PEM_TOP_HOLE_D,
       real_3D_supplier_model_acquired=False,rows=rows,
       suitable_existing_assembly=False,manufacturing_go=False)
    if write:(ROOT/'verification/R37_catalogue.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    return out
if __name__=='__main__':run()
