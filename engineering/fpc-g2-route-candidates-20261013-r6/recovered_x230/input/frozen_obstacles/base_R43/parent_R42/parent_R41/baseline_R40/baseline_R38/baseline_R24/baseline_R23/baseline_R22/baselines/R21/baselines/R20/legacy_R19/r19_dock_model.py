"""R19 floating off-rail terminal-contact conceptual study.
Coordinates and cabin shapes inherited from R16. These are NEVER vendor CAD.
No mechanical release, current, FPC/OLED reliability or manufacturing approval.
Vendor TE 2199001-1: 2.4 x 1.05 mm PCB footprint, H_uncompressed 1.2,
working height 0.7-1.0 mm; max 1.5A signal application (not power-qualified here).
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import math,sys,json,itertools,hashlib
from typing import Literal
sys.path.insert(0,str(Path(__file__).resolve().parent/'sources'))
from r16_model import G
from r16_cad import A_frame, B_frame_local, blk
import cadquery as cq

ROOT=Path(__file__).resolve().parent

@dataclass(frozen=True)
class Params:
 W:float=73.99
 H:float=94.25
 slide:float=79.75
 align:float=8.2
 # Contact WORKING HEIGHT (not compression) provided by vendor
 h_free:float=1.2
 h_lo:float=.7
 h_hi:float=1.
 h_nom:float=.85
 # All below are prospective goals/assumptions not vendor tolerances.
 normal_error_old:float=.25
 normal_error_goal:float=.12
 normal_error_desired_margin:float=.02
 stow_retract:float=.85
 open_retract:float=.70
 pad_t:float=.15
 stow_y:float=30.
 open_A_y:float=84.75
 open_B_y:float=5.
 x_pins:tuple=(-12.,-4.,4.,12.)
 contact_x_width:float=1.05
 contact_y_length:float=2.4
 pad_x_width:float=2.1
 pad_y_length:float=3.4
 contact_force_assumed_N:float=.45 # no vendor force-displacement curve validated
 current_max_vendor_A:float=1.5 # SPEC rating per contact; NOT approved power interface
 def __post_init__(self):
  assert math.isclose(self.open_A_y-self.open_B_y,self.slide)
  assert self.h_lo<=self.h_nom<=self.h_hi
  assert self.stow_retract>self.h_free-self.h_nom
  assert self.open_retract>self.h_free-self.h_nom

p=Params()
g=G()

def contact_window(delta:float,params=p):
 # Working height nominal +- manufacturing/stop registration residual.
 lo=params.h_nom-delta;hi=params.h_nom+delta
 return dict(residual_mm=delta,worst_low_mm=lo,worst_high_mm=hi,
             lower_margin_mm=lo-params.h_lo,upper_margin_mm=params.h_hi-hi,
             passes=(lo>=params.h_lo and hi<=params.h_hi))

def witness(phase:str,s:float,q:float,stow_extended=False,open_extended=False,latched=False):
 if phase=='STOW': allowed=abs(s)<1e-8 and abs(q)<1e-8
 elif phase=='OPEN': allowed=abs(s-g.Y)<1e-8 and abs(q-g.Z)<1e-8
 else: allowed=False
 # A contact shall never be commanded extended solely from position; requires real lock proof.
 can_command=(allowed and latched)
 return dict(phase=phase,can_command=can_command,
   failure=(stow_extended or open_extended) and not can_command,
   cannot_prove_real_latch=True)

def assembly(s:float=0.,q:float=0.,mode:Literal['RETRACTED','STOW_DOCK','OPEN_DOCK']='RETRACTED'):
 assert 0<=s<=g.Y and 0<=q<=g.Z
 A=A_frame(g)
 B=B_frame_local(g)
 # Open endpoint B floating island (unactuated linkage/cams still missing!)
 island=blk(-16,16,3.2,7.0,4.35,5.40)
 # Fixed rib carriers tie to B's main body at local Y>=14.5
 ribs=[blk(x0,x1,5.0,15.0,3.9,4.35) for x0,x1 in [(-16,-14),(14,16)]]
 # B stow contact recesses: voids within B full-width core; eliminates rigid proxy penetration.
 for x in p.x_pins:
  B=B.cut(blk(x-.90,x+.90,p.stow_y-1.70,p.stow_y+1.70,5.85,7.26))
 B=B.clean()
 # This assembly deliberately does NOT model actuator/cartridge support spanning recess!
 transform=cq.Vector(0,s,-g.Z+q)
 B=B.translate(transform)
 island=island.translate(transform)
 ribs=[r.translate(transform) for r in ribs]
 elements={'A_FRAME_R16':A,'B_FRAME_RECESSED':B,'B_OPEN_FLOATING_ISLAND':island}
 for i,r in enumerate(ribs):elements[f'B_ISLAND_RIB_{i}']=r
 # Both A pads attached to cabin-fixed surfaces. Opposite normals in stowed vs opened poses.
 for i,x in enumerate(p.x_pins):
  elements[f'A_STOW_PAD_{i}']=blk(x-p.pad_x_width/2,x+p.pad_x_width/2,
   p.stow_y-p.pad_y_length/2,p.stow_y+p.pad_y_length/2,-p.pad_t,0)
  elements[f'A_OPEN_PAD_{i}']=blk(x-p.pad_x_width/2,x+p.pad_x_width/2,
   p.open_A_y-p.pad_y_length/2,p.open_A_y+p.pad_y_length/2,
   g.T-g.bridge_thickness-p.pad_t,g.T-g.bridge_thickness)
  # stow: top of B core local Z=7.2; retract DOWN into cabin pocket
  stow_base=g.T if mode=='STOW_DOCK' else g.T-p.stow_retract
  stow_height=p.h_nom if mode=='STOW_DOCK' else p.h_free
  elements[f'B_STOW_FINGER_PROXY_{i}']=blk(x-p.contact_x_width/2,x+p.contact_x_width/2,
   p.stow_y-p.contact_y_length/2+s,p.stow_y+p.contact_y_length/2+s,
   stow_base-g.Z+q,stow_base+stow_height-g.Z+q)
  # open: top of B island local 5.40; retracted island/contacts move DOWN
  open_base=5.4 if mode=='OPEN_DOCK' else 5.4-p.open_retract
  open_height=p.h_nom if mode=='OPEN_DOCK' else p.h_free
  elements[f'B_OPEN_FINGER_PROXY_{i}']=blk(x-p.contact_x_width/2,x+p.contact_x_width/2,
   p.open_B_y-p.contact_y_length/2+s,p.open_B_y+p.contact_y_length/2+s,
   open_base-g.Z+q,open_base+open_height-g.Z+q)
 # Broken/dummy modes are rejected by state machine (not physically prevented yet).
 return elements

def volume(a,b):return float(a.intersect(b).Volume())

def exact_audit(s,q,mode='RETRACTED'):
 v=assembly(s,q,mode)
 # Collision pairs that MUST have no positive-volume overlap.
 pairs=[]
 for i in range(4):
  for a,b in [(f'A_STOW_PAD_{i}',f'B_STOW_FINGER_PROXY_{i}'),
              (f'A_OPEN_PAD_{i}',f'B_OPEN_FINGER_PROXY_{i}'),
              ('A_FRAME_R16',f'B_STOW_FINGER_PROXY_{i}'),
              ('A_FRAME_R16',f'B_OPEN_FINGER_PROXY_{i}'),
              ('B_FRAME_RECESSED',f'B_STOW_FINGER_PROXY_{i}'),
              ('A_FRAME_R16','B_OPEN_FLOATING_ISLAND')]:
   pairs.append((a,b,volume(v[a],v[b])))
 # Rib B intersects B frame by design for attachment. A bridge vs island must not collide.
 pairs.append(('A_FRAME_R16','B_FRAME_RECESSED',volume(v['A_FRAME_R16'],v['B_FRAME_RECESSED'])))
 return dict(s_mm=s,q_mm=q,mode=mode,collisions=[(a,b,round(n,9)) for a,b,n in pairs if n>1e-6],
  worst_intersection_mm3=max([n for _,_,n in pairs]+[0]),parts=len(v))

def model_data():
 vendor=dict(name='TE Connectivity 2199001-1', url='https://www.te.com/en/product-2199001-1.html',
        contact_length_mm=2.4,contact_width_mm=1.05,uncompressed_height_mm=1.2,
        operating_height_range_mm=[.7,1.0],max_current_each_A=1.5,
        circuit_application='Signal; do NOT treat as qualified 4700mAh battery power path')
 sections=[contact_window(e) for e in [0,.05,.08,.1,.12,.14,.15,.16,.2,.25]]
 # Real independent mechanical stages need failure-closed; no fabricated proof.
 return dict(version='R19 prototype dock cartridge feasibility; NOT RELEASE',
  r16_origin=['A fixed cabin H94.25/W73.99', 'B rear cabin +79.75Y, +8.2Z'],
  assumptions=asdict(p),vendor_reference=vendor, working_gap_window=sections,
  stow_nominal_contact_gap_mm=.85,open_nominal_contact_gap_mm=.85,
  stow_retracted_gap_nominal_mm=.5,open_retracted_gap_nominal_mm=.35,
  off_rail_electrical_station='A core underface @Y30 (closed); A bridge underside @Y84.75 (open)',
  open_tertiary_contact_carrier='B open floating island local Y3.2..7.0, X+-16, Z4.35..5.4 (actuator not yet designed)',
  current_estimate=dict(four_fingers_per_port=True,meets_parallel_current_without_sharing_evidence=False,
    separate_battery_power_during_motion_required=True),
  gates=dict(contact_height_in_0_12mm_target_residual=contact_window(.12)['passes'],
    existing_0_25mm_error_safe=contact_window(.25)['passes'],
    verified_local_pocket_fits_real_contact_vendor_CAD=False,
    real_actuator_spring_return_both_interfaces=False,
    mechanical_A_B_lock_confirmed=False,
    OLED_R3_4_approved=False,
    real_A_B_battery_charge_power_verified=False,
    all_stage_touch_support_qualified=False,
    manufacturing_release=False))

if __name__=='__main__':print(json.dumps(model_data(),ensure_ascii=False,indent=2))
