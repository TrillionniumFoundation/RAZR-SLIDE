"""Research STEP scenes. An exported GHOST is an intentional collision or missing retention.
Never treat STEP import success as assembly clearance, spring/latch safety or release.
"""
import hashlib,json
import cadquery as cq
from r25_capture import ROOT,P,blk
from r24_mechanics import r21
from r35_parts import pin,bored_cap,te_signal_envelope
from r36_parts import keeper,catalog_m08x2_screw
from r37_parts import lip

SCENES=[
 ('01_STOW_NOMINAL_UNPOWERED',0.,0.,'nominal'),
 ('02_OPEN_SEATED_UNPOWERED',P.travel,P.z_travel,'nominal'),
 ('03_OPEN_PRESEAT_0p05',P.travel,P.z_travel-.05,'nominal'),
 ('04_CAP_FORCED_FORWARD_0p05_GHOST',P.travel,P.z_travel,'withdraw'),
 ('05_CAP_FRONT_FEED_JAM_GHOST',P.travel,P.z_travel,'front_insertion'),
 ('06_ONE_INTEGRAL_LIP_FRACTURED_GHOST',P.travel,P.z_travel,'one_lip_broken'),
 ('07_PEM_TOP_SHEET_HOLE_SPLIT_GHOST',P.travel,P.z_travel,'pem_rejected')]

def run(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad/R37_A_R36_IDENTICAL.brep')).val()
 B=cq.importers.importBrep(str(ROOT/'cad/R37_B_INTEGRAL_FRONT_STOP_LIPS.brep')).val()
 original_B=cq.importers.importBrep(str(ROOT/'cad/R36_B_INBOARD_KEEPER_BOSSES_AND_CLEARANCE_BORES.brep')).val()
 data=[]
 for name,s,q,mode in SCENES:
  ref=r21.r17_assembly(P,s,q,1 if s==P.travel and q==P.z_travel else 0)
  tr=(0,s,q-P.z_travel)
  # Preserve RIGHT lip, fracture LEFT lip only in this GHOST scene.
  # The previous revision erroneously replaced B with the original two-lip-free B.
  shell=original_B.fuse(lip('R')).clean() if mode=='one_lip_broken' else B
  if mode=='one_lip_broken':
   assert shell.isValid() and len(shell.Solids())==1
   assert shell.Volume()>original_B.Volume() and shell.Volume()<B.Volume()
   assert abs(cq.importers.importBrep(str(ROOT/'cad/R36_B_INBOARD_KEEPER_BOSSES_AND_CLEARANCE_BORES.brep')).val().Volume() - original_B.Volume())<1e-6
  parts={'A_R36_UNCHANGED':A,
         'B_R37_INTEGRAL_LIPS_RESEARCH': shell.translate(tr),
         'OLED_SURROGATE_UNLICENSED':ref['OLED'],
         'FPC_SURROGATE_UNLICENSED':ref['FPC']}
  for side in 'LR':
   cap=bored_cap(side)
   if mode=='withdraw':cap=cap.translate((0,-.05,0))
   if mode=='front_insertion':cap=cap.translate((0,-2.0,0))
   p=pin(side)
   if mode=='one_lip_broken' and side=='L':
    cap=cap.translate((0,-2.5,0))
   for label,shape in [('R35_BRIDGE',cap),('R35_STUD_PIN',p),('TE_SIGNAL_CATALOGUE_AABB_ONLY',te_signal_envelope(side)),
                       ('R36_STOPPER_STILL_UNTHREADED',keeper(side)),('R36_M08_PROXY_STILL_UNTHREADED',catalog_m08x2_screw(side))]:
    parts[f'{side}_{label}']=shape.translate(tr)
  if mode=='pem_rejected':
   # A disconnected two-solid flange after drilling a 1.47mm top-sheet hole
   # into the too-narrow R36-style keeper; drawn as a GHOST NOT an installable part.
   from r37_catalogue import PEM_TOP_HOLE_D
   from r36_parts import axis_cylinder,KEEPER
   from r30_mechanics import mirrored
   test=blk(31.69,32.44,KEEPER[2],KEEPER[3],KEEPER[4],KEEPER[5])
   test=test.cut(axis_cylinder(PEM_TOP_HOLE_D/2,31.65,32.49))
   for idx,sh in enumerate(test.Solids()):
    parts[f'R_PEM_FRAGMENT_{idx+1}_REJECTED']=sh.translate(tr)
  ass=cq.Assembly(name='R37_'+name)
  for label,body in parts.items():
   color=cq.Color(.94,.24,.2) if mode!='nominal' and label.startswith(('L_','R_')) else cq.Color(.28,.62,.78) if label.startswith('B_') else cq.Color(.74,.76,.78)
   ass.add(body,name=label,color=color)
  path=ROOT/'cad'/f'R37_{name}.step'
  if write:ass.save(str(path),exportType='STEP')
  imported=cq.importers.importStep(str(path)).solids().vals()
  assert len(imported)==len(parts) and all(p.isValid() for p in imported),(name,len(parts),len(imported))
  data.append(dict(scene=name,mode=mode,ghost=mode!='nominal',file=path.name,
       left_lip_removed_right_lip_preserved=(mode=='one_lip_broken'),
       parts=len(parts),reimported_valid_solids=len(imported),
       bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
  print('R37 STEP',name,'parts',len(parts),'ghost',mode!='nominal',flush=True)
 out=dict(revision='R37 research STEP scenes including failed rigid insertion and PEM candidate',
          scenes=data,count=len(data),ghost_count=sum(r['ghost'] for r in data),
          original_R36_A_unchanged=True,has_vendor_native_STEP=False,
          no_real_qualified_elastic_latch=True,manufacturing_go=False)
 if write:(ROOT/'verification/R37_STEP_manifest.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 return out
if __name__=='__main__':run()
