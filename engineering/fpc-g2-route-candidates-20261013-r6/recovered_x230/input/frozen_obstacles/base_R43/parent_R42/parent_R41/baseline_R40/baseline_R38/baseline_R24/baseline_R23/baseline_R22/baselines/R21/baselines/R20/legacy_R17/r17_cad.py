"""R17 partial physical packaging CAD. OLED/FPC centerline strips from r17_model.
Modified functional cores are NOT OEM components; two interleaving bridge leaves
are solids but their actual cam, end locks, contact forces are not solved.
"""
import sys,json,hashlib
from pathlib import Path
import cadquery as cq
from shapely.geometry import LineString
from r17_model import Params,draw_screen,draw_internal_fpc,ROOT
sys.path.insert(0,str(ROOT/'legacy_R16'))
from r16_model import G
from r16_cad import A_frame,B_frame_local,blk

OUT=ROOT/'cad';OUT.mkdir(exist_ok=True)
def extrude_2d_path(path,t,width,x_center=0.):
 geom=LineString(path)
 assert geom.is_simple, 'centerline self cross'
 pol=geom.buffer(t/2,resolution=5,cap_style=2,join_style=1)
 assert pol.is_valid and pol.geom_type=='Polygon'
 arr=list(pol.exterior.coords)
 v=cq.Workplane('YZ').polyline(arr).close().extrude(width).val().translate(cq.Vector(x_center-width/2,0,0))
 assert v.isValid() and v.Volume()>0
 return v

def a_shell(p):
 g=G();v=A_frame(g)
 # remove old stationary full-width bridge in interleaved central region
 v=v.cut(blk(-33.75,33.75,p.travel,p.H, p.T-p.bridge_t-0.06,p.T+0.10))
 # reserve a 2*bridge_t telescoping bay behind the fixed top skin
 L=p.A_bridge_length
 v=v.cut(blk(-33.75,33.75,p.travel-L,p.travel,p.T-2*p.bridge_t,p.T+.10)).clean()
 return v

def a_fixed_leaf(p):
 L=p.A_bridge_length
 return blk(-33.5,33.5,p.travel-L,p.travel,p.T-p.bridge_t,p.T)

def a_moving_leaf(p,deploy=0.):
 """Stage after both axes seated: longitudinal translation at lower Z,
 then lift into display plane. proxy; actuator/load/collision sweeps not qualified.
 deploy 0..1; [0,0.5] Y feed, [0.5,1] lift.
 """
 L=p.A_bridge_length
 if deploy<=.5:
  off=L*2*deploy;lift=0
 else:
  off=L;lift=p.bridge_t*(2*deploy-1)
 return blk(-33.5,33.5,p.travel-L+off,p.travel+off,
            p.T-2*p.bridge_t+lift,p.T-p.bridge_t+lift)

def b_shell_local(p):
 g=G();v=B_frame_local(g)
 # avoid OLED on return at Zlocal≈0.8, and create actual U headspace
 v=v.cut(blk(-33.80,33.80,0,p.y_u_local+.015,-.10,p.OLED_rear_cavity_top_local_z))
 v=v.cut(blk(-33.80,33.80,p.y_u_local,p.H+.04,-.1,p.T+.1))
 # Dedicated FPC motion aisle; missing realistic EMI / signal / stiffness assessment
 v=v.cut(blk(p.FPC_channel_x0,p.FPC_channel_x1,0,p.y_u_local+.015,
                 p.OLED_rear_cavity_top_local_z,7.05))
 return v.clean()

def assembly(p,s,q,bridge_deploy=0.,fixed_old_bridge=False,use_old_B=False):
 from r16_cad import A_frame
 A=A_frame(G()) if fixed_old_bridge else a_shell(p)
 leaf=a_fixed_leaf(p)
 moving=a_moving_leaf(p,bridge_deploy)
 B_local=B_frame_local(G()) if use_old_B else b_shell_local(p)
 B=B_local.translate(cq.Vector(0,s,-p.z_travel+q))
 screen=extrude_2d_path(draw_screen(p,s,q,18)['path'],p.oled_t,p.oled_w)
 fl=draw_internal_fpc(p,s,q,18)
 fpc_local=extrude_2d_path(fl['path_local'],p.FPC_t,p.FPC_w,
                           x_center=(p.FPC_channel_x0+p.FPC_channel_x1)/2)
 FPC=fpc_local.translate(cq.Vector(0,s,-p.z_travel+q))
 # tunnel channel is open along the center while B nose is behind A
 # the fixed leaf always supports the last 14.15 mm of the A surface
 return dict(A=A,A_fixed_skin=leaf,A_moving_leaf=moving,B=B,OLED=screen,FPC=FPC)

def overlap(a,b):return float(a.intersect(b).Volume())

def run():
 p=Params()
 scenes=[('01_STOWED',0.,0.,0.),('02_Y_25PCT',p.travel*.25,0.,0.),
         ('03_Y_50PCT',p.travel*.5,0.,0.),('04_PREDOCK',p.travel,0.,0.),
         ('05_Z_HALF',p.travel,p.z_travel*.5,0.),('06_SEATED_BRIDGE_PARKED',p.travel,p.z_travel,0.),
         ('07_BRIDGE_FEED',p.travel,p.z_travel,.5),('08_BRIDGE_EXTENDED',p.travel,p.z_travel,1.)]
 rows=[]
 for name,s,q,k in scenes:
  solids=assembly(p,s,q,k)
  d={}
  for key in ('A','A_fixed_skin','A_moving_leaf','B','FPC'):
   if key!='FPC':d[f'OLED_vs_{key}_mm3']=overlap(solids['OLED'],solids[key])
  d['FPC_vs_B_mm3']=overlap(solids['FPC'],solids['B'])
  d['FPC_vs_OLED_mm3']=overlap(solids['FPC'],solids['OLED'])
  d['A_core_vs_B_mm3']=overlap(solids['A'],solids['B'])
  d['moving_leaf_vs_A_shell_mm3']=overlap(solids['A_moving_leaf'],solids['A'])
  d['moving_leaf_vs_fixed_skin_mm3']=overlap(solids['A_moving_leaf'],solids['A_fixed_skin'])
  ass=cq.Assembly(name=f'R17_{name}')
  colors={'A':cq.Color(.43,.49,.56),'A_fixed_skin':cq.Color(.29,.66,.54),'A_moving_leaf':cq.Color(.98,.66,.19),
          'B':cq.Color(.18,.48,.78),'OLED':cq.Color(.10,.78,.86),'FPC':cq.Color(.90,.32,.60)}
  for key,sh in solids.items():ass.add(sh,name=key+'_CONCEPT_NOT_OEM',color=colors[key])
  file=OUT/f'R17_{name}.step'
  ass.save(str(file),exportType='STEP')
  reimp=cq.importers.importStep(str(file)).solids().vals()
  assert len(reimp)==6 and all(x.isValid() for x in reimp)
  row=dict(state=name,s=s,q=q,bridge_deploy=k,solids=len(reimp),intersections_mm3=d,sha256=hashlib.sha256(file.read_bytes()).hexdigest())
  rows.append(row)
  print(name,'OLED/A',round(d['OLED_vs_A_mm3'],4),'OLED/B',round(d['OLED_vs_B_mm3'],4),'FPC/B',round(d['FPC_vs_B_mm3'],4),flush=True)
 # create definitive counterexample for unrevised R16 OLED path
 old=assembly(p,0,0,0,True,True)
 old_metric={'screen_in_R16_original_A_bridge_mm3':overlap(old['OLED'],old['A']),
             'screen_in_R16_original_B_core_mm3':overlap(old['OLED'],old['B']),
             'fpc_in_R16_original_B_core_mm3':overlap(old['FPC'],old['B'])}
 assert old_metric['screen_in_R16_original_A_bridge_mm3']>1.
 assert old_metric['screen_in_R16_original_B_core_mm3']>1.
 out={'states':rows,'original_R16_clashes':old_metric,
      'nominal_stage_3D_interference_scope':'Only six named concept solids per pose; OEM internals and actuation omitted',
      'all_stages_safe_to_manufacture':False}
 (ROOT/'verification'/'R17_CAD_selected_poses.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
 print('OLD COUNTEREXAMPLE',old_metric)
 return out

if __name__=='__main__':run()

def export_assumed_equipment():
 """9th CAD: visual occupancy proxies only, not manufacturer CAD or component fit approval."""
 from r17_verify import batteries_and_oem_proxies
 p=Params();s=p.travel;q=p.z_travel
 parts=assembly(p,s,q,1)
 cells=batteries_and_oem_proxies(p)
 for key,sh in cells.items():
  parts[key]=sh if key.startswith('A_') else sh.translate(cq.Vector(0,s,-p.z_travel+q))
 # check the new proxies do not intersect screen/FPC nor each other except engineered containment in the cores
 names=list(cells)
 physical={'A_battery_ASSUMED':parts['A_battery_ASSUMED'],
           'B_battery_ASSUMED':parts['B_battery_ASSUMED'],
           'B_PCB_ASSUMED':parts['B_PCB_ASSUMED'],
           'B_camera_ASSUMED':parts['B_camera_ASSUMED']}
 for k,sh in physical.items():
  assert overlap(sh,parts['OLED'])<1e-6 and overlap(sh,parts['FPC'])<1e-6,k
 for i,a in enumerate(names):
  for b in names[i+1:]:assert overlap(physical[a],physical[b])<1e-6,(a,b)
 out=cq.Assembly(name='R17_ASSUMED_INTERNAL_COMPONENT_ENVELOPES_NOT_OEM')
 palette={'A_battery_ASSUMED':cq.Color(.35,.74,.47),'B_battery_ASSUMED':cq.Color(.35,.74,.47),
          'B_PCB_ASSUMED':cq.Color(.28,.41,.76),'B_camera_ASSUMED':cq.Color(.79,.44,.21)}
 for key,sh in parts.items():out.add(sh,name=key+'_PROXY',color=palette.get(key,cq.Color(.55,.72,.79)))
 fn=OUT/'R17_09_COMPONENT_ENVELOPES_NOT_OEM.step';out.save(str(fn),exportType='STEP')
 ss=cq.importers.importStep(str(fn)).solids().vals();assert len(ss)==10 and all(x.isValid() for x in ss)
 return {'filename':fn.name,'reimport_valid_solids':len(ss),'size_bytes':fn.stat().st_size}
