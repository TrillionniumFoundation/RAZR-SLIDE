"""R25 STOW-stage2 contact-carrier shutter CAD, self-auditing prototype.

Two new closed shutters lie behind the R24 early-opening cam.  In a *selected*
STOW mating state, two engaged key-capture pawls cease to interfere with a
manually driven stage2 gate.  When either pawl is parked (fail-closed), its
solid physically obstructs gate motion.  Full OPEN station duplicate extends
beyond B envelope and is rejected.  This is NOT a kinematic spring proof.
"""
from __future__ import annotations
import sys,json
from pathlib import Path
import cadquery as cq
ROOT=Path(__file__).resolve().parent
from r25_capture import (P,blk,intersection,to_global,pawl,
              PORT_DATA,X_CENTERS,PAWL_W)
from r24_mechanics import outboard_lugs,carrier_arms,a_key

GATE_SHIFT_MM=2.0
B_NATIVE_HALF_WIDTH=36.995

def new_carrier_ear(side,extension):
 """Continuous OCC lug+bridging web.  Separate local ear is NOT a bearing proof."""
 l= -34.26 if side=='L' else 34.26
 x0,x1=l-.13,l+.13
 ear=blk(x0,x1,-5.40,-5.23,-3.64+extension,-3.24+extension)
 # Bridge overlaps BOTH new and old outboard lug in the STOW bay.
 # x centre ±34.26, width 0.15
 l= -34.26 if side=='L' else 34.26
 web=blk(l-.075,l+.075,-5.33,-4.67,-3.60+extension,-3.38+extension)
 old=outboard_lugs(extension)[f'B_R24_OUTBOARD_LUG_{side}']
 return old.fuse(web).fuse(ear).clean()

def shutter_stow(side,stroke=0.):
 """Metallic single-piece hypothetical 2nd-stage shutter and side dog.
 A long underside tie is below the A STOW key in the nominal CAD envelope.
 Translation is an *independent manual/lost motion* degree of freedom,
 unbuilt spring, stop, bearings and tamper-resistant enclosure.
 """
 if not (0.<=stroke<=GATE_SHIFT_MM):raise ValueError(stroke)
 sign=-1 if side=='L' else 1
 l=sign*34.26
 dog=sign*35.85
 x0,x1=(l-.13,l+.13)
 outer=(dog-.20,dog+.20)
 if side=='L':
  left,right=outer[0],x1
 else:
  left,right=x0,outer[1]
 shapes=[
  blk(x0,x1,-5.56,-5.17,-3.1,-2.25), # carrier Z blocker
  blk(l-.08,l+.08,-5.56,-5.45,-4.60,-2.52), # inner rail/downcast
  blk(left,right,-5.56,-5.45,-4.68,-4.48), # low bypass below A key
  blk(*outer,-5.56,-5.45,-4.60,-2.35), # outer connecting riser
  blk(*outer,-5.56,-5.45,-2.75,-2.35), # dog at X=parked pawl
 ]
 shape=shapes[0]
 for x in shapes[1:]:shape=shape.fuse(x)
 shape=shape.clean().translate(cq.Vector(0,stroke,0))
 return shape

def study(write=True):
 rows=[]
 for side in 'LR':
  for extension in (0.,.8):
   ear=new_carrier_ear(side,extension)
   for stroke in (0.,2.):
    stop=shutter_stow(side,stroke)
    rows.append(dict(side=side,carriage_z_extension=extension,gate_stroke_mm=stroke,
         new_ear_gate_interference_mm3=round(intersection(ear,stop),8),
         connected_new_carrier_ear=ear.isValid() and len(ear.Solids())==1,
         connected_monolithic_shutter=stop.isValid() and len(stop.Solids())==1))
 # The independent physical captive pawl 'dog' blocks an STOW gate trying
 # to slide open when pawl PARKED. It cannot block because of a Boolean.
 dog_paths=[]
 for side in 'LR':
  for captured in (False,True):
   probe=[]
   for shift in (0.,.03,.06,.08,.10,.20,.40,1.,2.):
    v=intersection(pawl('STOW',side,captured),shutter_stow(side,shift))
    probe.append(dict(shift=shift,interference_mm3=round(v,8)))
   dog_paths.append(dict(side=side,capture_pawl_engaged=captured,gate_translation_probe=probe,
                  blocked_over_first_0p1_mm=any(x['interference_mm3']>1e-8 for x in probe if x['shift']<=.1),
                  full_stroke_clear=all(x['interference_mm3']<1e-8 for x in probe)))
 # Reject naive copy of STOW shutter to OPEN: OPEN port B-local Y -5.56
 # maps into shell-native Y=-0.56 and loses mounting to the equal-size B.
 from r22_mechanics import station_position
 st_y,_=station_position('STOW');op_y,_=station_position('OPEN')
 open_reuse_native_y_min=-5.56+op_y
 open_parked_outermax=abs(X_CENTERS['R'])+PORT_DATA['OPEN']['park_out']+PAWL_W/2
 out=dict(revision='R25 STOW secondary hard shutter + parked-pawl interlock OCC only',
   new_ear_interference_cases=rows,pawl_to_gate_physical_interlock=dog_paths,
   stow_nominal_carrier_retracted_clear=all(x['new_ear_gate_interference_mm3']<1e-8 for x in rows if x['carriage_z_extension']==0),
   stow_ext_0p8_is_blocked_when_shutter_closed=all(x['new_ear_gate_interference_mm3']>1e-7 for x in rows if x['carriage_z_extension']==.8 and x['gate_stroke_mm']==0),
   stow_ext_0p8_clear_when_shutter_open=all(x['new_ear_gate_interference_mm3']<1e-8 for x in rows if x['carriage_z_extension']==.8 and x['gate_stroke_mm']==2),
   parked_pawl_physically_vetoes_manual_shutter_motion=all(x['blocked_over_first_0p1_mm'] for x in dog_paths if not x['capture_pawl_engaged']),
   captured_pawl_shutter_path_clear=all(x['full_stroke_clear'] for x in dog_paths if x['capture_pawl_engaged']),
   naive_open_copy_B_native_y_min_mm=round(open_reuse_native_y_min,6),
   naive_open_copy_intrudes_outside_equal_envelope_mm=round(max(0,-open_reuse_native_y_min),6),
   open_capture_pawl_min_outer_shell_edge_margin_mm=round(B_NATIVE_HALF_WIDTH-open_parked_outermax,6),
   naive_open_copy_rejected=True,
   spring_and_follower_ACTUAL_geometry_missing=True,
   two_stage_force_path_FEA_missing=True,manufacturing_go=False)
 if write:
  (ROOT/'verification'/'R25_gate.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 return out

if __name__=='__main__':
 r=study();print(json.dumps({k:v for k,v in r.items() if k not in ('new_ear_interference_cases','pawl_to_gate_physical_interlock')},ensure_ascii=False,indent=2));
 print('COUNTEREXAMPLES', [x for x in r['pawl_to_gate_physical_interlock'] if x['capture_pawl_engaged'] and not x['full_stroke_clear']])
