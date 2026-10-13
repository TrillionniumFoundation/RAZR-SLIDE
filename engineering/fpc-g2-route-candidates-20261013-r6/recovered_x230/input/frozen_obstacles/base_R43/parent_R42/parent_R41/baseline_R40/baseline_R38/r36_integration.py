"""R36 nominal keeper/boss & M0.8 screw-clearance path in real R35 OCC shell.
This does not prove screw retention or pin shear strength.
"""
import cadquery as cq,shutil,json
from r25_capture import ROOT,intersection
from r35_parts import bored_cap,pin,te_signal_envelope
from r36_parts import boss,keeper,catalog_m08x2_screw,mount_bore,rejected_square_nut,rejected_nut_pocket,metadata
A=ROOT/'cad/R36_A_R35_UNCHANGED.brep'; B=ROOT/'cad/R36_B_INBOARD_KEEPER_BOSSES_AND_CLEARANCE_BORES.brep'

def run(write=True):
    old=cq.importers.importBrep(str(ROOT/'cad/R35_B_INBOARD_RAILS_AND_GUIDES.brep')).val()
    b=old
    operations=[]
    for side in 'LR':
        before=b.Volume();b=b.fuse(boss(side)).clean()
        operations.append(dict(side=side,op='fuse_rear_support_boss',delta_mm3=round(b.Volume()-before,9),solids=len(b.Solids())))
    for side in 'LR':
        before=b.Volume();b=b.cut(mount_bore(side)).clean()
        operations.append(dict(side=side,op='clearance_bore_for_M0p8_proxy',delta_mm3=round(b.Volume()-before,9),solids=len(b.Solids())))
    part_rows=[]
    for side in 'LR':
        c=keeper(side);s=catalog_m08x2_screw(side);p=pin(side);g=te_signal_envelope(side)
        part_rows.append(dict(side=side,keeper_valid=c.isValid(),keeper_solid_count=len(c.Solids()),
           keeper_vs_B=round(intersection(c,b),9),screw_vs_B=round(intersection(s,b),9),
           screw_vs_keeper=round(intersection(s,c),9),keeper_vs_pin=round(intersection(c,p),9),
           keeper_vs_TE=round(intersection(c,g),9),keeper_vs_bridge=round(intersection(c,bored_cap(side)),9),
           stopped_pin_0p05_overlap=round(intersection(c,p.translate((.05 if side=='L' else -.05,0,0))),9),
           square_nut_catalogue_vs_B=round(intersection(rejected_square_nut(side),b),9),
           square_nut_catalogue_vs_bridge=round(intersection(rejected_square_nut(side),bored_cap(side)),9)))
    # Rejected branch intentionally cut as a separate disposable test solid, NEVER exported as R36 shell.
    nut_b=b
    rejected_changes=[]
    for side in 'LR':
        before=nut_b.Volume();nut_b=nut_b.cut(rejected_nut_pocket(side)).clean()
        rejected_changes.append(dict(side=side,removed_mm3=round(before-nut_b.Volume(),9),valid=nut_b.isValid(),solids=len(nut_b.Solids())))
    out=dict(revision='R36 paired pin-head catch plate + catalog-M0.8 screw *unthreaded* trial',
       original_R35_B_volume_mm3=round(old.Volume(),8),revised_B_volume_mm3=round(b.Volume(),8),
       revised_B_delta_mm3=round(b.Volume()-old.Volume(),8),B_valid=b.isValid(),B_solids=len(b.Solids()),
       operations=operations,parts=part_rows,rejected_square_nut_pockets=rejected_changes,
       vendor_native_STEP_imported=False,screw_assembly_thread_retention_unproven=True,
       electronics_battery_occupied_envelope_not_imported=True,part_metadata=metadata(),manufacturing_go=False)
    if write:
        shutil.copyfile(ROOT/'cad/R35_A_R34_UNCHANGED.brep',A)
        cq.exporters.export(b,str(B))
        for side in 'LR':
            cq.exporters.export(keeper(side),str(ROOT/f'cad/R36_{side}_PIN_HEAD_STOPPER_UNQUALIFIED.brep'))
            cq.exporters.export(catalog_m08x2_screw(side),str(ROOT/f'cad/R36_{side}_M0p8x2_CATALOGUE_SCREW_PROXY.brep'))
        (ROOT/'verification/R36_integration.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('R36 B',out['B_valid'],out['B_solids'],'delta',out['revised_B_delta_mm3'],'parts',part_rows,flush=True)
    return out
if __name__=='__main__':run()
