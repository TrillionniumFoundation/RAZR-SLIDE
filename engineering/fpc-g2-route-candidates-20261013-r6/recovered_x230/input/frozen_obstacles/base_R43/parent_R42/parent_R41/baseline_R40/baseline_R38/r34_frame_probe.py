import json,time
import cadquery as cq
from r25_capture import ROOT,P,blk,intersection
from r30_mechanics import mirrored
from r24_mechanics import r21
from r25_dynamic import POSES
from r33_parts import catalogue_TE_box,keeper_pin
A=cq.importers.importBrep(str(ROOT/'cad/R33_A_R32_BYTE_IDENTICAL.brep')).val()
B0=cq.importers.importBrep(str(ROOT/'cad/R32_B_REAR_CASSETTE_BAYS.brep')).val()
# A deliberately raised top-fed bay with rectangular supplier catalogue AABB only
FRAME=(33.85,35.60,1.60,4.65,1.65,4.05)
POCKET=(34.10,35.35,1.58,4.32,1.95,4.12)
TE_SHIFT_X=.20
TE_SHIFT_Y=.37

def build():
 B=B0
 for side in 'LR':
  sh=mirrored(blk(*FRAME),side); before=B.Volume()
  B=B.fuse(sh).clean(); print('frame',side,sh.Volume(),B.Volume()-before,B.isValid(),len(B.Solids()),flush=True)
 for side in 'LR':
  sh=mirrored(blk(*POCKET),side);before=B.Volume()
  B=B.cut(sh).clean();print('pocket',side,sh.Volume(),before-B.Volume(),B.isValid(),len(B.Solids()),flush=True)
 return B

if __name__=='__main__':
 B=build()
 out={'valid_single':B.isValid() and len(B.Solids())==1,'native_volume':B.Volume(),'new_total_added_net_mm3':B.Volume()-B0.Volume(),'spans':{'frame':FRAME,'pocket':POCKET}}
 for side in 'LR':
  te=catalogue_TE_box(side).translate(((TE_SHIFT_X if side=='L' else -TE_SHIFT_X),TE_SHIFT_Y,0))
  print('TE-B',side,intersection(te,B),flush=True)
  out[f'{side}_te_b']=intersection(te,B)
  out[f'{side}_pin_te']=intersection(te,keeper_pin(side))
 for tag,s,q in POSES:
  ref=r21.r17_assembly(P,s,q,1 if tag=='OPEN_SEATED' else 0)
  trans=(0,s,q-P.z_travel)
  bw=B.translate(trans)
  vals={k:intersection(bw,sh) for k,sh in {'A':A,'OLED':ref['OLED'],'FPC':ref['FPC']}.items()}
  for side in 'LR':
   te=catalogue_TE_box(side).translate(((TE_SHIFT_X if side=='L' else -TE_SHIFT_X),TE_SHIFT_Y,0)).translate(trans)
   vals[f'{side}_TE_A']=intersection(te,A)
   vals[f'{side}_TE_OLED']=intersection(te,ref['OLED'])
   vals[f'{side}_TE_FPC']=intersection(te,ref['FPC'])
  out.setdefault('poses',[]).append({'tag':tag,**vals})
  print('POSE',tag,' '.join(f'{k}:{v:.4g}' for k,v in vals.items()),flush=True)
 (ROOT/'verification/R34_relocated_probe.json').write_text(json.dumps(out,indent=2)+'\n')
