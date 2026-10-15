"""R30 B-shell guide sleeve physical CAD witnesses.
No-A presence gating, force, springs, wear and disassembly are NOT qualified.
"""
from __future__ import annotations
import cadquery as cq,json,itertools
from r25_capture import ROOT,blk,intersection
from r22_mechanics import to_blocal
from r30_mechanics import mirrored
from r30_integration import bearing_boss

TAIL=(34.47,34.525,-3.55,-.75,-3.90,-3.65)
BOUNDS=(2.72,5.35)

def tail(side,t):
 return mirrored(blk(TAIL[0],TAIL[1],TAIL[2]+t,TAIL[3]+t,TAIL[4],TAIL[5]),side)

def run(write=True):
 B=cq.importers.importBrep(str(ROOT/'cad'/'R30_B_LONGITUDINAL_REBASE.brep')).val()
 rows=[];samples=0
 for side in 'LR':
  sign=1 if side=='R' else -1
  for t in (0.,.45,.9):
   shape=tail(side,t)
   overlap_len=max(0,min(TAIL[3]+t+5,BOUNDS[1])-max(TAIL[2]+t+5,BOUNDS[0]))
   for w in (.02,.05):
    for dx,dy,dz in itertools.product((-w,0.,w),repeat=3):
     vec=cq.Vector(dx,dy,dz)
     coll=round(intersection(B,to_blocal(shape.translate(vec),'OPEN')),10)
     rows.append(dict(side=side,stroke_mm=t,xyz_mm=(dx,dy,dz),width=w,
         guide_overlap_length_mm=round(overlap_len,5),B_clash_mm3=coll))
     samples+=1
   for axis,off in (('XOUT',(sign*.10,0,0)),('XIN',(-sign*.10,0,0)),('ZUP',(0,0,.10)),('ZDOWN',(0,0,-.10))):
    clash=round(intersection(B,to_blocal(shape.translate(cq.Vector(*off)),'OPEN')),10)
    rows.append(dict(side=side,stroke_mm=t,hard_axis=axis,B_clash_mm3=clash))
  print('R30 GUIDED TAIL',side,'samples',samples,flush=True)
 false_captive=sum(r.get('B_clash_mm3',0.)<1e-8 for r in rows if 'hard_axis' in r)
 jam=sum(r.get('B_clash_mm3',0.)>1e-8 for r in rows if 'width' in r)
 widths={'0.02':sum(x.get('B_clash_mm3',0)>1e-8 for x in rows if x.get('width')==.02),
         '0.05':sum(x.get('B_clash_mm3',0)>1e-8 for x in rows if x.get('width')==.05)}
 out={'revision':'R30 fixed B-shell C-channel tail, OCC translation/retention stress cases',
   'xyz_guide_configurations':samples,'guide_jam_configs':jam,'by_width_jam_configs':widths,
   'hard_axis_probes':24,'hard_axis_fail_to_intercept':false_captive,
   'guide_overlap_min_mm':min(x['guide_overlap_length_mm'] for x in rows if 'guide_overlap_length_mm' in x),
   'guide_overlap_max_mm':max(x['guide_overlap_length_mm'] for x in rows if 'guide_overlap_length_mm' in x),
   'rows':rows,'no_positional_force_wear_fatigue_or_latching_qualification':True,
   'spring_and_fasteners_missing':True,'manufacturing_go':False}
 if write:(ROOT/'verification'/'R30_retention.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 return out
if __name__=='__main__':
 d=run();print('R30 GUIDED',d['xyz_guide_configurations'],'jam',d['guide_jam_configs'],'escaping',d['hard_axis_fail_to_intercept'],flush=True)
