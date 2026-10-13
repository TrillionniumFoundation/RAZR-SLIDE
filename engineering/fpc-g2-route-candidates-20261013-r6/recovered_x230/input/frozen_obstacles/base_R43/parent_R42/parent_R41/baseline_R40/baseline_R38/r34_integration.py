"""R34 actual BRep refit with separated signal-envelope side frame.

B is rebuilt from *frozen R32* to eliminate R33 unretained cross pins.
Two tiny original R32 forward FRAME chips detach when the new front mouth is cut;
they are explicitly removed as machining debris, not kept as hidden solids.
This is a packaging candidate only.  Does not create a real connector.
"""
from __future__ import annotations
import hashlib,json,shutil
import cadquery as cq
from r25_capture import ROOT,intersection,blk
from r30_mechanics import mirrored
from r34_parts import FRAME,POCKET,rail_frame,top_front_open_pocket,te_signal_envelope,frame_dimensions,front_insert_throat

A_BASE=ROOT/'cad/R33_A_R32_BYTE_IDENTICAL.brep'
B_BASE=ROOT/'cad/R32_B_REAR_CASSETTE_BAYS.brep'
A_OUT=ROOT/'cad/R34_A_R33_UNCHANGED.brep'
B_OUT=ROOT/'cad/R34_B_OPEN_SIGNAL_ENVELOPE_CRADLES.brep'

# Sample occupancy cells for the REAL final OCC solid. They are merely material
# presence witnesses, not proof of strength or minimum section through all y.
WITNESSES={
 'INBOARD_SIDE_WALL':(33.88,34.07,2.20,3.80,2.15,3.55),
 'OUTBOARD_SIDE_WALL':(35.38,35.57,2.20,3.80,2.15,3.55),
 'REAR_STOP':(34.20,35.25,4.36,4.59,2.10,3.50),
 'FLOOR':(34.22,35.23,2.10,3.80,1.68,1.90),
}

def build():
    B0=cq.importers.importBrep(str(B_BASE)).val()
    B=B0; steps=[]
    for side in 'LR':
        frame=rail_frame(side); before=B.Volume(); overlap=intersection(B,frame)
        B=B.fuse(frame).clean()
        steps.append(dict(op='frame_fuse',side=side,frame_volume_mm3=round(frame.Volume(),9),
                          original_overlap_mm3=round(overlap,9),
                          actual_new_B_volume_mm3=round(B.Volume()-before,9),
                          all_B_solids=len(B.Solids())))
    for side in 'LR':
        before=B.Volume(); c=top_front_open_pocket(side)
        B=B.cut(c).clean()
        steps.append(dict(op='pocket_cut',side=side,actual_removed_mm3=round(before-B.Volume(),9),
                          connected_solids_before_debris_removal=len(B.Solids())))
    # Pocket initially detaches two tiny R32 front stubs. Rather than just
    # discarding disconnected BReps, perform an actual machined through-throat
    # operation which clears those pieces AND lets the envelope slide in via Y.
    interim_solids=list(B.Solids()); main=max(interim_solids,key=lambda s:s.Volume())
    floating=[dict(volume_mm3=round(s.Volume(),9),
                    bbox_native_mm=[round(q,6) for q in (s.BoundingBox().xmin,s.BoundingBox().xmax,
                                s.BoundingBox().ymin,s.BoundingBox().ymax,
                                s.BoundingBox().zmin,s.BoundingBox().zmax)])
              for s in interim_solids if s is not main]
    assert len(floating)==2 and all(abs(x['volume_mm3']-.0664)<1e-6 for x in floating)
    for side in 'LR':
        before=B.Volume(); B=B.cut(front_insert_throat(side)).clean()
        steps.append(dict(op='front_throat_cut',side=side,actual_removed_mm3=round(before-B.Volume(),9),
                          resulting_connected_solids=len(B.Solids())))
    assert B.isValid() and len(B.Solids())==1
    return B0,B,steps,floating

def run(write=True):
    a=cq.importers.importBrep(str(A_BASE)).val()
    b0,b,steps,removed=build()
    witnesses=[]
    for name,limits in WITNESSES.items():
        for side in 'LR':
            sh=mirrored(blk(*limits),side)
            witnesses.append(dict(side=side,name=name,
                actual_solid_occupancy_fraction=round(intersection(b,sh)/sh.Volume(),8),
                not_a_minimum_continuous_wall_measurement=True))
    te=[]
    for side in 'LR':
        sh=te_signal_envelope(side)
        te.append(dict(side=side,TE_nominal_AABB_to_new_B_intersection_mm3=round(intersection(sh,b),9),
                       catalogue_box_is_not_OEM_STEP=True))
    d=dict(revision='R34 separate TRUE SIZE nominal TE *signal* AABB cradle - NO electrical or load qualification',
        R33_A_original_sha256=hashlib.sha256(A_BASE.read_bytes()).hexdigest(),
        R32_B_original_sha256=hashlib.sha256(B_BASE.read_bytes()).hexdigest(),
        B_rebased_on_R32_no_old_R33_unsupported_keeper_pins=True,
        A_unchanged_bytes=True,
        B_R32_volume_mm3=round(b0.Volume(),9),B_R34_volume_mm3=round(b.Volume(),9),
        B_R34_net_volume_delta_mm3=round(b.Volume()-b0.Volume(),9),
        B_is_valid_single_solid=b.isValid() and len(b.Solids())==1,
        operations=steps,orphan_R32_frame_chips_removed=removed,
        interim_orphan_volume_removed_by_throat_mm3=round(sum(x['volume_mm3'] for x in removed),9),
        final_orphan_solids=0,
        front_throat_actual_added_cut_mm3=round(sum(q['actual_removed_mm3'] for q in steps if q['op']=='front_throat_cut'),9),
        frame_budget=frame_dimensions(),section_witnesses=witnesses,
        TE_catalogue_box_fit_in_candidate_B=te,
        physical_retention_or_axial_capture_installed=False,
        A_side_mating_pad_and_controlled_contact_sequence=False,
        selected_qualified_power_connector=False,
        usb_signal_integrity_qualified=False,
        oled_vendor_module_geometry_or_lifetime_qualified=False,
        manufacturing_go=False)
    if write:
        shutil.copyfile(A_BASE,A_OUT)
        cq.exporters.export(b,str(B_OUT))
        for side in 'LR':
            cq.exporters.export(te_signal_envelope(side),str(ROOT/f'cad/R34_{side}_TE_SIGNAL_CATALOGUE_AABB_PROXY_NOT_VENDOR.step'))
        (ROOT/'verification/R34_integration.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    print('R34 INTEGRATION B',d['B_R34_volume_mm3'], 'orphan chips cleared',d['interim_orphan_volume_removed_by_throat_mm3'], 'occupancy',witnesses,flush=True)
    return d,(a,b)
if __name__=='__main__':run()
