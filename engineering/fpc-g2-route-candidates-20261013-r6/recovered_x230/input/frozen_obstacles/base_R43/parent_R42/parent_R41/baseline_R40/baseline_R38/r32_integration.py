"""R32 OCC housing remodel: two open-mouth, removable-GAUGE cassette bays.

The B-side support is fused behind the contact station, then a real channel is
cut through the mouth.  The previous R31 male-key geometry is immutable.
This is a study of mechanical packaging and insertion, NOT a load-bearing
latch, electrical mating system or durable use qualification.
"""
from __future__ import annotations
import hashlib,json,shutil
import cadquery as cq
from r25_capture import ROOT,intersection,blk
from r32_cartridge import frame,channel,gauge,nominal_frame_wall_budget

A_BASE=ROOT/'cad'/'R31_A_POSITIVE_OPEN_SHELVES.brep'
B_BASE=ROOT/'cad'/'R31_B_PRESENCE_POCKETS.brep'
A_OUT=ROOT/'cad'/'R32_A_R31_UNMODIFIED.brep'
B_OUT=ROOT/'cad'/'R32_B_REAR_CASSETTE_BAYS.brep'

# Specimen occupancy indicates actual OCC solid overlap, not force or stress.
MATERIAL_WITNESSES={
 'R_INBOARD_FRAME_WEB':(34.55,34.74,2.,3.25,2.38,2.92),
 'R_OUTBOARD_FRAME_WEB':(35.11,35.33,2.,3.25,2.38,2.92),
 'R_ROOF':(34.80,35.03,2.05,3.25,2.97,3.28),
 'R_FLOOR':(34.80,35.03,2.05,3.25,2.02,2.33),
 'R_REAR_STOP':(34.80,35.03,3.72,3.98,2.40,2.90),
}

def run(write=True):
    A=cq.importers.importBrep(str(A_BASE)).val()
    B0=cq.importers.importBrep(str(B_BASE)).val()
    B=B0;add=[];cuts=[]
    for s in 'LR':
        sh=frame(s);b0=B.Volume();inter=intersection(B,sh)
        B=B.fuse(sh).clean()
        add.append(dict(side=s,frame_mm3=round(sh.Volume(),9),preexisting_B_overlap_mm3=round(inter,9),
                        actual_added_mm3=round(B.Volume()-b0,9),valid=B.isValid(),connected=len(B.Solids())==1))
    reinforced=B
    for s in 'LR':
        cut=channel(s);v=B.Volume();B=B.cut(cut).clean()
        cuts.append(dict(side=s,channel_mm3=round(cut.Volume(),9),actual_cut_mm3=round(v-B.Volume(),9),
                         valid=B.isValid(),connected=len(B.Solids())==1))
    occupancy=[]
    for n,limits in MATERIAL_WITNESSES.items():
        b=blk(*limits)
        occupancy.append(dict(cell=n,box_mm3=round(b.Volume(),9),
                              actual_final_B_material_fraction=round(intersection(B,b)/b.Volume(),7)))
    d=dict(revision='R32 mechanical packaging gauge for two open-mouth side cassettes',
        R31_A_SHA256=hashlib.sha256(A_BASE.read_bytes()).hexdigest(),
        R31_B_SHA256=hashlib.sha256(B_BASE.read_bytes()).hexdigest(),
        A_unmodified_equal_SHA256=hashlib.sha256(A_BASE.read_bytes()).hexdigest(),
        B_R31_mm3=round(B0.Volume(),9),B_frame_fused_mm3=round(reinforced.Volume(),9),B_R32_mm3=round(B.Volume(),9),
        actual_B_frame_added_mm3=round(reinforced.Volume()-B0.Volume(),9),
        actual_B_channel_removed_mm3=round(reinforced.Volume()-B.Volume(),9),
        A_valid_single=A.isValid() and len(A.Solids())==1,
        B_valid_single=B.isValid() and len(B.Solids())==1,
        frame_fuse=add,channel_cuts=cuts,box_material_witnesses=occupancy,
        nominal_dimensions=nominal_frame_wall_budget(),
        old_R29_forward_lip_remains_in_historical_B_geometry=True,
        no_evidence_new_support_receives_any_A_or_carrier_force=True,
        independent_removable_fastener_not_designed=True,
        cassette_is_non_electrical_solid_envelope_only=True,
        no_material_GDT_FEA_or_sample_strength=True,
        manufacturing_go=False)
    if write:
        shutil.copyfile(A_BASE,A_OUT);cq.exporters.export(B,str(B_OUT))
        (ROOT/'verification'/'R32_integration.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    print('R32 INTEGRATION',d['B_R32_mm3'], 'added',d['actual_B_frame_added_mm3'],
          'cut',d['actual_B_channel_removed_mm3'], 'valid',d['B_valid_single'],flush=True)
    return d,(A,B)

if __name__=='__main__':run()
