"""R21: complete CAD examination of the contact-cartridge recess in the R17
OLED-conduit B shell. Units millimetres. Every part here is a derived design
proxy, not an OEM instrument or qualification. Contact elevations from R19/R20.
"""
from __future__ import annotations
import sys, math, json
from pathlib import Path
import cadquery as cq
ROOT=Path(__file__).resolve().parent
R20=ROOT/'baselines'/'R20'
R17=R20/'legacy_R17'
for pth in [R20,R17]:
 if str(pth) not in sys.path: sys.path.insert(0,str(pth))
from r20_cad import local_assembly, vol as intersection
from r20_model import p as contact_cfg
from r17_model import Params
from r17_cad import b_shell_local, a_shell, assembly as r17_assembly
from r16_cad import blk
P=Params()
# INVENTED, unsigned targets; NOT OEM manufacturing tolerances.
CUT_CLEAR=0.15
FLOOR_SCREEN=.70
HEAD_CAVITY_X_HALF=34.10  # candidate local flare: 0.30mm beyond R17 X33.80 cut
STOW_Y=18.50; STOW_PAD_Z=-.15  # R21 relocated from R19 Y30 to avoid B battery proxy
OPEN_Y=84.75; OPEN_PAD_Z=6.25
# Local B function frame is Z-local; global Z=(-8.2 + second_phase_q).

def box_from_bbox(sh,inflate=.0):
 b=sh.BoundingBox()
 return blk(b.xmin-inflate,b.xmax+inflate,b.ymin-inflate,b.ymax+inflate,b.zmin-inflate,b.zmax+inflate)

def union_solids(shapes):
 sh=shapes[0]
 for u in shapes[1:]:sh=sh.fuse(u)
 return sh.clean()

def stow_pocketed_shell(clearance=CUT_CLEAR):
 """Carve full nominal dog (lateral) and carriage (Z) swept volumes in R17 B.
 The guide ribs overlap B as *intended attachments*. Dog/lug/backbone do not.
 Deliberately do not assume structural adequacy of the remaining rails.
 """
 core=b_shell_local(P)
 # R17 did not reserve 0.30mm clearance from the active OLED at the curved head.
 # Narrow the sidewall by opening the nose cut to X±34.10; not strength qualified.
 core=core.cut(blk(-HEAD_CAVITY_X_HALF,HEAD_CAVITY_X_HALF,P.y_u_local,P.H+.10,-.20,P.T+.15)).clean()
 core=core.cut(blk(-HEAD_CAVITY_X_HALF,HEAD_CAVITY_X_HALF,0.,P.y_u_local+.02,-.20,P.OLED_rear_cavity_top_local_z)).clean()
 # R19 original pocket for the 4 retracting signal spring fingers.
 contact_pockets=[]
 for x in contact_cfg.x_pins:
  contact_pockets.append(blk(x-.90,x+.90,STOW_Y-1.70,STOW_Y+1.70,5.85,7.26))
 for cp in contact_pockets:core=core.cut(cp)
 core=core.clean()
 before=core
 scenes=[local_assembly(retract=t,left_open=left,right_open=right)
         for t in (True,False) for left,right in ((False,False),(True,True))]
 movable_labels=['B_DOG_L','B_DOG_R','B_CARRIER_LUG_L','B_CARRIER_LUG_R','B_BOTTOM_CARRIER_BACKBONE_PROXY']
 sweep=[]
 for key in movable_labels:
  a=[]
  for parts in scenes:
   sh=parts[key].translate(cq.Vector(0,STOW_Y,STOW_PAD_Z+8.2))
   a.append(sh)
  xs=[v.BoundingBox().xmin for v in a];xe=[v.BoundingBox().xmax for v in a]
  ys=[v.BoundingBox().ymin for v in a];ye=[v.BoundingBox().ymax for v in a]
  zs=[v.BoundingBox().zmin for v in a];ze=[v.BoundingBox().zmax for v in a]
  sweep.append(blk(min(xs)-clearance,max(xe)+clearance,min(ys)-clearance,max(ye)+clearance,min(zs)-clearance,max(ze)+clearance))
 for pocket in sweep: core=core.cut(pocket)
 core=core.clean()
 # Ribs are *fixed* guide pieces, intended to be attached to the B frame.
 ribs=[]
 for key in ['B_GUIDE_RIB_L','B_GUIDE_RIB_R']:
  ribs.append(scenes[0][key].translate(cq.Vector(0,STOW_Y,STOW_PAD_Z+8.2)))
 rib_intersections=[intersection(before,x) for x in ribs]
 # R20 fixed ribs fall INSIDE the continuous OLED path at full extension.
 # They are NOT added to the rebuilt B core; instead machined slot walls serve
 # as candidate guides. Their actual machinability and rigidity remain unknown.
 return dict(baseline=before,cut_core=core,body=core,ribs=ribs,swept_pockets=sweep,
  original_rib_overlap_mm3=rib_intersections,cut_volume_mm3=before.Volume()-core.Volume(),
  ribs_rejected_due_to_oled_interference=True,valid=core.isValid(),solids=len(core.Solids()))

def open_contact_island(reinforcement_mm=.8,clearance=CUT_CLEAR):
 """R19 open island (local B) extended downward by optional stiffener.
 Below the contact feet base Z=4.60, the hypothesized minimum remaining floor
 changes from 0.25 to 0.25+reinforcement. This is NOT a strength proof.
 """
 orig=blk(-16,16,3.2,7.,4.35,5.40)
 lower=blk(-16,16,3.2,7.,4.35-reinforcement_mm,4.35) if reinforcement_mm else None
 body=union_solids([orig,lower]) if lower else orig
 poses=[local_assembly(retract=retract,left_open=False,right_open=False) for retract in (True,False)]
 pockets=[]
 for i,x in enumerate(contact_cfg.x_pins):
  candidates=[s[f'B_TE_CONTACT_RECT_PROXY_{i}'].translate(cq.Vector(0,OPEN_Y,OPEN_PAD_Z)) for s in poses]
  # Translate X/Y back into B's own local frame, Z already global=B-local at dock.
  xs=[s.BoundingBox().xmin for s in candidates];xe=[s.BoundingBox().xmax for s in candidates]
  ys=[s.BoundingBox().ymin-79.75 for s in candidates];ye=[s.BoundingBox().ymax-79.75 for s in candidates]
  zs=[s.BoundingBox().zmin for s in candidates];ze=[s.BoundingBox().zmax for s in candidates]
  # The contact emerges beyond the island top, so cutting there does not matter.
  pockets.append(blk(min(xs)-clearance,max(xe)+clearance,min(ys)-clearance,max(ye)+clearance,min(zs)-clearance,max(ze)+clearance))
 for hole in pockets:body=body.cut(hole)
 body=body.clean()
 remain=(4.60-clearance)-(4.35-reinforcement_mm)
 return dict(original=orig,carved=body,reinforcement_mm=reinforcement_mm,
   pocket_sweeps=pockets,bottom_floor_nominal_mm=remain,one_solid=len(body.Solids())==1,valid=body.isValid(),
   remaining_before_cut_only_nominal_mm=.25,volume_extra_mm3=body.Volume()-orig.Volume())


def open_contact_cradle(reinforcement_mm=.8,clearance=CUT_CLEAR):
 """Second iteration: side dog guide pockets and a protected carriage backbone
 actually tied to the existing B island through material. All actuator springs,
 screw features, assembly clearance, service access, and contact force are missing.
 """
 island=open_contact_island(reinforcement_mm,clearance)
 side_rails=[blk(-20.5,-16.0,3.2,7.0,3.0,5.5),blk(16.0,20.5,3.2,7.0,3.0,5.5)]
 backbone_guide=blk(-16.,16.,1.25,3.65,1.8,4.5)
 bracket=union_solids([island['carved'],*side_rails,backbone_guide])
 loc={}
 for key in ['B_DOG_L','B_DOG_R','B_CARRIER_LUG_L','B_CARRIER_LUG_R','B_BOTTOM_CARRIER_BACKBONE_PROXY']:
  sample=[]
  for retract in (True,False):
   for lo,ro in ((False,False),(True,True)):
    part=local_assembly(retract,lo,ro)[key].translate(cq.Vector(0,5.0,OPEN_PAD_Z))
    sample.append(part)
  box=blk(min(s.BoundingBox().xmin for s in sample)-clearance,
           max(s.BoundingBox().xmax for s in sample)+clearance,
           min(s.BoundingBox().ymin for s in sample)-clearance,
           max(s.BoundingBox().ymax for s in sample)+clearance,
           min(s.BoundingBox().zmin for s in sample)-clearance,
           max(s.BoundingBox().zmax for s in sample)+clearance)
  bracket=bracket.cut(box)
  loc[key]=box
 bracket=bracket.clean()
 return dict(body=bracket,pockets=loc,island=island,valid=bracket.isValid(),solids=len(bracket.Solids()),
  added_bracket_volume_mm3=bracket.Volume()-island['carved'].Volume())

def run_dock_integration(clearance=CUT_CLEAR,reinforcement=.8,poses=None):
 if poses is None:poses=[('STOW',0.,0.,0.),('Y_HALF',39.875,0.,0.),('PREDOCK',79.75,0.,0.),('Z_HALF',79.75,4.1,0.),('OPEN',79.75,8.2,1.)]
 stow=stow_pocketed_shell(clearance);cradle=open_contact_cradle(reinforcement,clearance);isl=cradle['island']
 # Reinforced open island links to B core through original R19 support ribs.
 isle_ribs=[blk(a,b,5.,15.,3.9,4.35) for a,b in ((-16.,-14.),(14.,16.))]
 # NOTE a real island must be supported; fuse after carving and see connectivity.
 B_rebuilt=union_solids([stow['body'],cradle['body'],*isle_ribs])
 out=[]
 for stage,s,q,leaf in poses:
  r17=r17_assembly(P,s,q,leaf)
  b=B_rebuilt.translate(cq.Vector(0,s,-P.z_travel+q))
  contacts=local_assembly(True,False,False)
  # Physical baseline core+island should avoid screen and FPC throughout.
  hits={f'{x}_vs_{y}_mm3':round(intersection(a,bsh),6) for x,a in [('B_rebuilt',b)]
   for y,bsh in [('OLED',r17['OLED']),('B_local_FPC',r17['FPC']),('A_core',r17['A']),('A_fixed_skin',r17['A_fixed_skin']),('A_moving_leaf',r17['A_moving_leaf'])]}
  # Only active station contact carriage volume counted; inactive station still inside B.
  env=isl['carved'].translate(cq.Vector(0,s,-P.z_travel+q))
  out.append(dict(state=stage,s=s,q=q,leaf=leaf,intersections=hits,
    B_shell_volume_mm3=round(B_rebuilt.Volume(),3),B_one_solid=(len(B_rebuilt.Solids())==1)))
 return dict(built_b_core=B_rebuilt,stow=stow,island=isl,cradle=cradle,poses=out,
       prototype_assumed_oled_radius_mm=P.R,real_part_data=False)

if __name__=='__main__':
 obj=run_dock_integration()
 print('STOW',obj['stow']['cut_volume_mm3'],obj['stow']['solids'])
 print('ISLAND',obj['island']['bottom_floor_nominal_mm'],obj['island']['one_solid'])
 print('FULL B',len(obj['built_b_core'].Solids()),obj['built_b_core'].isValid())
 for p in obj['poses']: print(p['state'],p['intersections'])
