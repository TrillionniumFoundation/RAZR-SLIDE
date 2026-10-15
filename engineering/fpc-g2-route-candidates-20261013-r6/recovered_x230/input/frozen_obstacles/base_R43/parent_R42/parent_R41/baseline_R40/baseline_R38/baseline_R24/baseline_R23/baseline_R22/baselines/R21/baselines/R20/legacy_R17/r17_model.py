"""R17: B-top U OLED / compensating rear slider / local display FPC.
All geometry mm. Design CANDIDATE, not qualified OLED, CAD or OEM production.
X width; Y phone long axis (A fixed, B slides +Y); Z towards viewer.
U is at the upper tip of B, R is a *hypothesis*, not an OEM constraint.
"""
from dataclasses import dataclass,asdict
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
@dataclass(frozen=True)
class Params:
 H:float=94.25
 W:float=73.99
 travel:float=79.75
 T:float=7.2
 z_travel:float=8.2
 R:float=3.4   # OPPO axis is diameter6.8mm but different device/module; assumed candidate
 oled_t:float=.16
 oled_w:float=67.32091996910563  # active rectangle ONLY; physical edges not included
 U_end_clear:float=.60
 OLED_A_start:float=3.
 screen_front_standoff:float=.40
 screen_tail_bottom_margin:float=3.20
 FPC_loop_R:float=2.4  # not FPC-vendor qualified
 FPC_t:float=.15
 FPC_w:float=6.
 FPC_fixed_local_y:float=2.
 FPC_upper_slack_at_max_tail:float=3.55
 OLED_rear_cavity_top_local_z:float=1.35
 FPC_channel_x0:float=24.5
 FPC_channel_x1:float=30.5
 A_bridge_length:float=14.15
 bridge_t:float=.80
 # two-leaf assembly: fixed leaf and retractable/extendable leaf, not validated for loads
 @property
 def O(self):return self.H-self.travel
 @property
 def u(self):return self.R+self.U_end_clear
 @property
 def y_u_local(self):return self.H-self.u
 @property
 def active_h(self):return 7*25.4*22/math.hypot(22,9)
 @property
 def avail_depth(self):return self.T+self.screen_front_standoff-.30
 @property
 def initial_rear(self):return self.y_u_local-self.screen_tail_bottom_margin
 @property
 def Z_A(self):return self.T+self.screen_front_standoff
 @property
 def total_h(self):return self.H+self.travel


def sbend(dz,R,start_y,end_y,zstart,n=18):
 """Two tangent R arcs; vertical in between when dz>2R. Heading along +Y at ends.
 Returns polyline [(Y,Z)...], **analytic** arc length and min longitudinal run.
 """
 if dz < -1e-8: raise ValueError('reverse depth unsupported')
 D=end_y-start_y
 if dz<1e-9:
  return [(start_y,zstart),(end_y,zstart)],D,0.,D
 if dz<=2*R:
  theta=math.acos(max(-1,min(1,1-dz/(2*R))))
  minrun=2*R*math.sin(theta)
  vertical=0.
 else:
  theta=math.pi/2; minrun=2*R;vertical=dz-2*R
 if D<minrun-1e-8:raise ValueError(f'bridge travel insufficient {D} < {minrun}')
 extra_after=D-minrun
 cy=start_y
 p=[(start_y,zstart)]
 for j in range(1,n+1):
  t=theta*j/n
  p.append((cy+R*math.sin(t),zstart-R*(1-math.cos(t))))
 if vertical>1e-9:
  p.append((cy+R,zstart-R-vertical))
 y2,z2=p[-1]
 for j in range(1,n+1):
  t=theta*j/n
  p.append((y2+R*(math.sin(t-theta)+math.sin(theta)),z2+R*(-math.cos(t-theta)+math.cos(theta))))
 if extra_after>1e-9:p.append((end_y,zstart-dz))
 assert abs(p[-1][0]-end_y)<1e-7 and abs(p[-1][1]-(zstart-dz))<1e-7
 L=extra_after+2*R*theta+vertical
 return p,L,minrun,2*R*theta+vertical

def draw_screen(p:Params,s:float,q:float,n=24):
 assert 0<=s<=p.travel and 0<=q<=p.z_travel
 Uy=s+p.y_u_local
 zfrontB=p.Z_A-p.z_travel+q
 dz=p.Z_A-zfrontB
 trans,Ltrans,minrun, Lsbend=sbend(dz,p.R,p.travel,Uy,p.Z_A,n)
 # constant neutral length determined in original stowed geometry
 u0=p.y_u_local
 _,Ltrans0,_,_=sbend(p.z_travel,p.R,p.travel,u0,p.Z_A,8)
 total=(p.travel-p.OLED_A_start)+Ltrans0+math.pi*p.R+p.initial_rear
 front=(p.travel-p.OLED_A_start)+Ltrans
 Lrear=total-front-math.pi*p.R
 tail_local_y=p.y_u_local-Lrear
 path=[(p.OLED_A_start,p.Z_A),(p.travel,p.Z_A)]
 path+=trans[1:]
 centerZ=zfrontB-p.R
 for j in range(1,n*2+1):
  theta=math.pi*j/(n*2)
  path.append((Uy+p.R*math.sin(theta),centerZ+p.R*math.cos(theta)))
 path.append((Uy-Lrear,zfrontB-2*p.R))
 return dict(path=path,front_length=front,transition_length=Ltrans,transition_run_min=minrun,
             transition_S_end_y=(p.travel+minrun if dz>1e-9 else p.travel),
             unsupported_transition_nominal_span_mm=max(0.,p.O, (p.travel+minrun if dz>1e-9 else p.travel)-p.travel),
             rear_length=Lrear,tail_y_local=tail_local_y,total_len=total,curvature_radius=p.R,
             U_top_y=Uy+p.R,U_tangent_y=Uy,U_tangent_z_front=zfrontB,U_tangent_z_rear=zfrontB-2*p.R,
             z_rear_local=p.Z_A-2*p.R,bridge_dz=dz,
             min_source_tail_margin=tail_local_y)

def draw_internal_fpc(p:Params,s:float,q:float,n=30):
 d=draw_screen(p,s,q,7)
 my=d['tail_y_local']
 # moving U on B: two Y-running legs separated in Z by 2 R_FPC.
 # midpoint moves half the tail movement; total neutral length is invariant.
 max_tail=draw_screen(p,p.travel,0,7)['tail_y_local']
 yc_max=max_tail+p.FPC_upper_slack_at_max_tail
 yc=yc_max+(my-max_tail)/2
 z0=1.95
 z1=z0+2*p.FPC_loop_R
 path=[(p.FPC_fixed_local_y,z1),(yc,z1)]
 for j in range(1,n+1):
  a=math.pi*j/n
  path.append((yc+p.FPC_loop_R*math.sin(a), (z0+z1)/2+p.FPC_loop_R*math.cos(a)))
 path.append((my,z0))
 L=2*yc-p.FPC_fixed_local_y-my+math.pi*p.FPC_loop_R
 return dict(path_local=path,center_local_y=yc,max_y=yc+p.FPC_loop_R,
             moving_end_y=my,length_mm=L,fixed_end_y=p.FPC_fixed_local_y,
             z_min=z0,z_max=z1,nominal_width_mm=p.FPC_w,
             headroom_to_OLED_U_start=p.y_u_local-(yc+p.FPC_loop_R),
             still_needs_electrical_pinout_and_fatigue=True)

def sweep(p=Params(),ny=2001,nq=401):
 states=[]
 for j in range(ny):states.append((p.travel*j/(ny-1),0.))
 for j in range(1,nq):states.append((p.travel,p.z_travel*j/(nq-1)))
 total=[];tail=[];headroom=[];fpc_len=[];minrun=[];front=[]
 for s,q in states:
  d=draw_screen(p,s,q,7);f=draw_internal_fpc(p,s,q,7)
  total.append(d['total_len']);tail.append(d['tail_y_local']);headroom.append(f['headroom_to_OLED_U_start']);fpc_len.append(f['length_mm']);minrun.append(d['transition_run_min']);front.append(d['front_length'])
 return dict(samples=len(states),Y_states=ny,Z_states=nq,
             oled_max_length_drift_mm=max(total)-min(total),fpc_max_length_drift_mm=max(fpc_len)-min(fpc_len),
             min_OLED_tail_bottom_margin_mm=min(tail),max_tail_y_local_mm=max(tail),
             min_FPC_to_U_hood_longitudinal_gap_mm=min(headroom),
             min_screen_front_route_mm=min(front),max_screen_front_route_mm=max(front),
             total_OLED_neutral_mm=total[0],fpc_neutral_mm=fpc_len[0])

if __name__=='__main__':
 import json
 print(json.dumps({'params':asdict(Params()),'metrics':sweep()},indent=2))
