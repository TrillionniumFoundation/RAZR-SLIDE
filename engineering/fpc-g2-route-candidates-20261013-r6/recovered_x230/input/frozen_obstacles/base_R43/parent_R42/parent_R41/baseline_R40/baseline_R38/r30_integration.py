"""R30 B-shell OCC rebase: restore pre-R28/29 rail from immutable R27 BREP,
then FUSE actual rear sleeves to B and CUT discrete moving-part envelopes.
A unchanged, no fabrication approval from these rigid solids.
"""
from __future__ import annotations
import cadquery as cq,json,hashlib
from r25_capture import ROOT,blk,intersection
from r22_mechanics import to_blocal
from r24_integration import inflated_bbox
from r30_mechanics import (gate,carrier,PLATE_X,PLATE_Y,PLATE_Z,
                           sliding_tail,TAIL_GUIDE_SWEEP_PAD,mirrored)

A_BASE=ROOT/'cad'/'R29_A_R28_FROZEN_KEYS.brep'
B_BASE=ROOT/'cad'/'R27_B_CAPTIVE_OPEN_GATE_CUT.brep'
PAD=.025

def bearing_boss(side):
 # B-local fixture: y beyond A male key on correctly seated dock.
 # Material connects into B's existing R27 lower side rail.
 return mirrored(blk(34.31,35.05,2.72,5.35,.75,3.30),side)

def moving_cutters():
 for side in 'LR':
  shapes={
    'RETAIN_R29_SLOT_PLATE':mirrored(blk(*PLATE_X,*PLATE_Y,*PLATE_Z),side),
    'RETAIN_R29_LOWER_BRIDGE':mirrored(blk(34.32,34.51,-4.17,-4.08,-4.012,-3.88),side),
    'R29_FOLLOWER':carrier(side,0.),
    'R30_LONG_TAIL':sliding_tail(side,0.),
  }
  for label,sh in shapes.items():
   if label=='R29_FOLLOWER':
    source=[carrier(side,0.),carrier(side,.8)]
   else:
    source=[sh,sh.translate((0,.9,0))]
   pad=TAIL_GUIDE_SWEEP_PAD if label=='R30_LONG_TAIL' else PAD
   yield side,label,to_blocal(inflated_bbox(source,pad=pad),'OPEN')

def run(write=True):
 A=cq.importers.importBrep(str(A_BASE)).val()
 old=cq.importers.importBrep(str(B_BASE)).val();B=old;rows=[]
 for side in 'LR':
  B=B.fuse(bearing_boss(side)).clean()
  print('R30 FUSED B BOSS',side,'valid',B.isValid(),'solids',len(B.Solids()),flush=True)
 reinforced=B;added=reinforced.Volume()-old.Volume()
 for side,label,sh in moving_cutters():
  before=B.Volume();B=B.cut(sh).clean()
  r={'side':side,'component':label,'actual_new_B_cut_mm3':round(before-B.Volume(),8),
     'cutter_mm3':round(sh.Volume(),8),'valid':B.isValid(),'connected_solids':len(B.Solids())}
  rows.append(r);print('R30 B CUT',side,label,r['actual_new_B_cut_mm3'],'connected',r['connected_solids'],flush=True)
 d={'revision':'R30 R27-shell rebase and real long-tail B guide bosses; frozen R29 cam geometry',
   'R29_A_SHA256':hashlib.sha256(A_BASE.read_bytes()).hexdigest(),
   'R27_B_SHA256':hashlib.sha256(B_BASE.read_bytes()).hexdigest(),
   'B_R27_volume_mm3':round(old.Volume(),8),'B_R30_volume_mm3':round(B.Volume(),8),
   'actual_boss_added_over_R27_mm3':round(added,8),
   'pocket_removed_from_reinforced_mm3':round(reinforced.Volume()-B.Volume(),8),
   'B_NET_delta_over_R27_mm3':round(B.Volume()-old.Volume(),8),
   'subtractions':rows,
   'A_valid_single_body':A.isValid() and len(A.Solids())==1,
   'B_valid_single_body':B.isValid() and len(B.Solids())==1,
   'actual_boss_behind_key_nominal_datum':True,
   'sleeve_tail_nominal_sweep_clearance_per_axis_mm':TAIL_GUIDE_SWEEP_PAD,
   'R29_0p03mm_forward_lip_still_a_veto':True,
   'thin_R24_0p22mm_original_web_still_not_qualified':True,
   'no_qualified_bearing_anchor_fasteners_springs_or_material':True,
   'manufacturing_go':False}
 if write:
  cq.exporters.export(A,str(ROOT/'cad'/'R30_A_R29_KEYS_FROZEN.brep'))
  cq.exporters.export(B,str(ROOT/'cad'/'R30_B_LONGITUDINAL_REBASE.brep'))
  (ROOT/'verification'/'R30_integration.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
 return d,(A,B)
if __name__=='__main__':
 x,_=run();print('R30 BODY',x['B_NET_delta_over_R27_mm3'],x['B_valid_single_body'])
