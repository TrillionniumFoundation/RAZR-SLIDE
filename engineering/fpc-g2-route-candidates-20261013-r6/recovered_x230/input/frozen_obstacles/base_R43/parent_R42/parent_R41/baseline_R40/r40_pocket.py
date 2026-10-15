"""R40 negative B-chassis pocket cost for five rolling-U ribbon poses.

This cuts only in a *disposable hypothetical CAD copy* and never alters the
frozen R38 original, nor grants permission to cut OEM electronics volume.
Five poses are an optimistic lower bound, NOT the full swept clearance.
"""
import json,time,hashlib,sys
from pathlib import Path
import cadquery as cq
from r40_motion import ROOT,DOCK
from r40_occ import POSES,ribbon,intersectvol
sys.path[:0]=[str(ROOT/'baseline_R38'),str(ROOT/'baseline_R38/baseline_R24')]
from r38_parts import size_proxy

def run():
    p=ROOT/'baseline_R38/cad/R38_B_PROVISIONAL_STATIC_HEADER_CLEARANCE.brep'
    baseline=cq.importers.importBrep(str(p)).val()
    modified=baseline
    modifications=[]
    for name,s,q in POSES:
        t=time.monotonic();sol,wire=ribbon(s,q)
        # Move a world-frame cable into B-local coordinates for B cutting.
        local=wire.translate((0,-s,DOCK-q))
        before=modified.Volume()
        original_overlap=intersectvol(baseline,local)
        modified=modified.cut(local).clean()
        delta=before-modified.Volume()
        modifications.append({'pose':name,'B_current_overlap_mm3':round(original_overlap,8),
             'additional_B_solid_removed_mm3':round(delta,8),
             'remaining_valid':modified.isValid(),
             'remaining_solids':len(modified.Solids()),'elapsed_s':round(time.monotonic()-t,3)})
        print(name,'original_overlap',round(original_overlap,7),'incremental_removed',round(delta,7),
              'B valid',modified.isValid(),'B solid_count',len(modified.Solids()),flush=True)
    # A second new B header cut is required because B x-anchor moved 32.7mm.
    relocated=size_proxy((0.,15.,4.5))
    original_header_intersection=intersectvol(baseline,relocated)
    header_after_prev=intersectvol(modified,relocated)
    before=modified.Volume(); modified=modified.cut(relocated).clean()
    actual_total_removed=baseline.Volume()-modified.Volume()
    output=ROOT/'cad/R40_GHOST_B_CORE_DISSECTED_FIVE_POSITION_CUT_NOT_AUTHORIZED.brep'
    cq.exporters.export(modified,str(output))
    loaded=cq.importers.importBrep(str(output)).val()
    assert abs(modified.Volume()-loaded.Volume())<1e-5
    rows={'revision':'R40 minimum 5-position B-material sacrificial negative pocket',
      'poses':modifications,'R38_original_B_brep_sha256':hashlib.file_digest(open(p,'rb'),'sha256').hexdigest(),
      'hypothetical_B_core_removed_mm3':round(actual_total_removed,8),
      'B_header_new_anchor_x_mm':0.,
      'B_header_original_collision_mm3':round(original_header_intersection,8),
      'B_header_collision_after_five_clearances_mm3':round(header_after_prev,8),
      'remaining_B_valid':loaded.isValid(),'remaining_B_solids':len(loaded.Solids()),
      'this_CAD_cut_DOES_NOT_authorize_OEM_core_changes':True,
      'five_poses_NOT_complete_continuous_swept_volume':True,
      'FPC_electrical_or_vendor_qualified':False,'manufacturing_go':False,
      'negative_CAD_brep':output.name,'brep_sha256':hashlib.file_digest(open(output,'rb'),'sha256').hexdigest()}
    (ROOT/'verification/R40_pocket.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
    return rows

if __name__=='__main__':run()
