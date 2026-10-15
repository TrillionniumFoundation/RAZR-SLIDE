#!/usr/bin/env python3
"""R46 two-architecture negative-gate engineering study.

Original parent R45 remains immutable. Calculated paths are unlicensed, unbuilt
centerlines and partial clearance proxies, NOT a physically routed FPC, not USB
signaling proof and not OEM cavity-cut authorization.
"""
from __future__ import annotations
from pathlib import Path
import os, sys, json, hashlib, zipfile, math
from dataclasses import dataclass, asdict
import numpy as np
from scipy.optimize import brentq
import cadquery as cq
from shapely.geometry import LineString

ROOT=Path(__file__).resolve().parent.parent
REFERENCE=ROOT/'reference'
RESULTS=ROOT/'results'
CAD=ROOT/'cad'
sys.path.insert(0,str(REFERENCE))
import r39_reference_unmodified as R39

PARENT_FILE='RAZR_SLIDE_R45_verified_negative_gate_20261011.zip'
PARENT_SHA='84174df60dc931dda4b7eba331b41b136f25188f5435266d3a74ad2700925080'
PARENT_MEMBER_COUNT=56
REFERENCE_NAMES=['R38_A_unchanged.brep','R38_B_unchanged.brep','r39_reference_unmodified.py']
SLIDE=79.75
DOCK=8.20
STUDY_RIBBON_WIDTH=1.2
STUDY_RIBBON_THICKNESS=0.2
STUDY_CLEARANCE=0.2
Z_BAY_STUDY=3.5


def sha_bytes(bs):return hashlib.sha256(bs).hexdigest()
def sha_file(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(rel, obj):
 p=ROOT/rel;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def verify_parent(parent):
 parent=Path(parent)
 assert parent.is_file(),str(parent)
 assert sha_file(parent)==PARENT_SHA,'R45 immutable SHA mismatch'
 with zipfile.ZipFile(parent) as z:
  assert z.testzip() is None and len(z.namelist())==PARENT_MEMBER_COUNT
  for nm in REFERENCE_NAMES:
   assert z.read('reference/'+nm)==(REFERENCE/nm).read_bytes(),nm
  # Parent R44 remains nested unchanged. Other R39 variants are deliberately NOT merged.
  assert sha_bytes(z.read('baseline/R44_original_immutable.zip'))=='fa6690ddf2186143016108e1a2758c0b3c1a8e1e3295b741ffdf3c0dfc5598f5'
 return {'R45_sha256':PARENT_SHA,'R45_members':PARENT_MEMBER_COUNT,
         'reference_3_files_bitidentical':True,'R44_nested_parent_bitidentical':True,
         'alternate_R39_provenance_not_merged':True}


@dataclass(frozen=True)
class Candidate:
 name:str
 radius_mm:float
 cx_mm:float
 alpha:float
 extra_length_mm:float
 def xa(self):return self.cx_mm-self.radius_mm
 def xb(self):return self.cx_mm+self.radius_mm
 def stub(self):return abs(R39.X_CONN-self.xa())+abs(R39.X_CONN-self.xb())

CANDIDATES=[
 Candidate('INBOARD_R15_ALPHA20_LOW_SLACK',15.,19.,.20,17.17180365),
 Candidate('INBOARD_R15_ALPHA25_LOW_SLACK',15.,19.,.25,17.17180365),
 Candidate('INBOARD_R15_ALPHA25_MID_SLACK',15.,19.,.25,20.),
 Candidate('INBOARD_R15_ALPHA30_MID_SLACK',15.,19.,.30,20.),
 Candidate('INBOARD_R15_SHIFTED_X23',15.,23.,.25,20.),
 Candidate('INBOARD_R10_UNLICENSED',10.,25.,.25,20.),
 Candidate('OUTBOARD_R15_WIDTH_FAIL',15.,38.5,.25,20.),
]


def world_z_arc(c,q):
 return c.alpha*R39.Z_A+(1.-c.alpha)*(Z_BAY_STUDY+q-DOCK)

def length(c,s,q,y_fold):
 ya=R39.Y_A;yb=R39.Y_B0+s;zb=R39.Z_B0+q;z=world_z_arc(c,q)
 return c.stub()+R39.blend_integral(y_fold-ya,z-R39.Z_A)+math.pi*c.radius_mm+R39.blend_integral(y_fold-yb,zb-z)

def target_length(c):
 vals=[length(c,s,0.,max(R39.Y_A,R39.Y_B0+s)) for s in np.linspace(0,SLIDE,81)]
 vals += [length(c,SLIDE,q,max(R39.Y_A,R39.Y_B0+SLIDE)) for q in np.linspace(0,DOCK,41)]
 return max(vals)+c.extra_length_mm

def fold_y(c,s,q,L):
 lower=max(R39.Y_A,R39.Y_B0+s)
 assert length(c,s,q,lower)<=L+1e-8
 return float(brentq(lambda y:length(c,s,q,y)-L,lower,lower+L,xtol=1e-11))

def curvature_min(dy,dz):
 uu=np.linspace(0,1,1001)
 d1=dz*6*uu*(1-uu);d2=dz*(6-12*uu)
 # Parameter invariant radius of x-constant (y,z) transition.
 k=np.abs(dy*d2)/(dy*dy+d1*d1)**1.5
 m=float(np.max(k))
 return 1/m if m>1e-13 else None

def pose(c,s,q,L):
 yf=fold_y(c,s,q,L);z=world_z_arc(c,q)
 rA=curvature_min(yf-R39.Y_A,z-R39.Z_A)
 rB=curvature_min(yf-(R39.Y_B0+s),(R39.Z_B0+q)-z)
 rough_Xmin=c.xa()-(STUDY_RIBBON_WIDTH/2+STUDY_CLEARANCE)
 rough_Xmax=c.xb()+(STUDY_RIBBON_WIDTH/2+STUDY_CLEARANCE)
 # Curved width is unknown; this is only an isotropic planar study margin.
 return dict(s_mm=float(s),q_mm=float(q),fold_y_mm=yf,world_arc_z_mm=z,
   B_local_arc_z_mm=z-q+DOCK,length_exact_mm=length(c,s,q,yf),
   A_leg_min_radius_mm=rA,B_leg_min_radius_mm=rB,
   x_study_min_mm=rough_Xmin,x_study_max_mm=rough_Xmax,
   width_overrun_mm=max(0.,rough_Xmax-36.995, -36.995-rough_Xmin),
   B_local_arc_in_gross_z=0<=z-q+DOCK<=7.2,
   A_arc_in_gross_z=-3.4<=z<=7.2,
   B_local_y_overrun_mm=max(0.,yf+c.radius_mm-s-94.25),
   A_anchor_connected_in_geometry=True,B_anchor_connected_in_geometry=True)

def main_arc(c,row):
 fy=row['fold_y_mm'];z=row['world_arc_z_mm']
 pts=[(c.cx_mm-c.radius_mm*math.cos(t),fy+c.radius_mm*math.sin(t)) for t in np.linspace(0,math.pi,121)]
 proxy=LineString(pts).buffer(STUDY_RIBBON_WIDTH/2+STUDY_CLEARANCE,resolution=8)
 assert proxy.is_valid and proxy.geom_type=='Polygon'
 shp=cq.Workplane('XY').polyline(list(proxy.exterior.coords)[:-1]).close().extrude(STUDY_RIBBON_THICKNESS).translate((0,0,z-STUDY_RIBBON_THICKNESS/2)).val()
 assert shp.isValid() and len(shp.Solids())==1
 return shp

def sampled_arc_occ(c,states,a,b,step_export=False):
 records=[];outputs=[]
 for tag,s,q in states:
  row=pose(c,s,q,target_length(c))
  arc=main_arc(c,row)
  bw=b.translate((0,s,q-DOCK))
  av=a.intersect(arc).Volume();bv=bw.intersect(arc).Volume()
  rec={'pose':tag,'s_mm':s,'q_mm':q,
      'proxy_arc_intersection_A_mm3':round(av,8),'proxy_arc_intersection_B_mm3':round(bv,8),
      'B_world_translation_mm':[0,s,q-DOCK],
      'positive_intersection_rejection':bool(av>1e-8 or bv>1e-8),
      'zero_main_arc_intersection_does_not_qualify_whole_ribbon':True}
  records.append(rec)
  if step_export:
   fname=f'R46_{c.name}_{tag}_U_ARC_ONLY_GHOST.step'
   compound=cq.Compound.makeCompound([a,bw,arc])
   assert compound.isValid()
   f=CAD/fname;f.parent.mkdir(parents=True,exist_ok=True)
   cq.exporters.export(compound,str(f),exportType='STEP')
   reread=cq.importers.importStep(str(f)).val()
   solids=reread.Solids()
   assert len(solids)>=3 and all(y.isValid() for y in solids)
   outputs.append({'filename':'cad/'+fname,'reimported_solids':len(solids),'sha256':sha_file(f),
                   'GHOST':True,'no_real_FPC':True,'only_main_arc_proxy_not_full_fpc':True})
 return records,outputs


def fpc_study():
 report={'revision':'R46 3D length-resolved Z-sharing U-centerline and OCC main-arc negative screening',
   'units':'mm','sliding_total_mm':SLIDE,'normal_dock_mm':DOCK,'states_total':len(R39.all_path_states()),
   'source_lineage':'R45 frozen R44->R43->R42->R41->R39; NOT alternate R39 revision',
   'A_world_anchor_xyz':[R39.X_CONN,R39.Y_A,R39.Z_A],
   'B_world_stow_anchor_xyz':[R39.X_CONN,R39.Y_B0,R39.Z_B0],
   'study_only_width_mm':STUDY_RIBBON_WIDTH,'study_only_thickness_mm':STUDY_RIBBON_THICKNESS,
   'study_only_buffer_mm':STUDY_CLEARANCE,'unqualified_anchor_stubs_with_sharp_bends':True,
   'total_length_exact_is_math_not_conserved_deformed_material':True,
   'no_vendor_permitted_full_3D_FPC_route':True,'no_oem_keepout_approval':True,
   'physical_USB_continuity_verified':False,'manufacturing_go':False,'candidates':[]}
 for c in CANDIDATES:
  target=target_length(c)
  positions=[pose(c,s,q,target) for s,q in R39.all_path_states()]
  errors=[abs(x['length_exact_mm']-target) for x in positions]
  def finite_min(k):return min(p[k] for p in positions if p[k] is not None)
  rec={'candidate':asdict(c),'analytic_target_length_mm':round(target,7),
    'sampled_positions':len(positions),'max_analytic_length_deviation_mm':max(errors),
    'global_min_A_leg_radius_mm':finite_min('A_leg_min_radius_mm'),
    'global_min_B_leg_radius_mm':finite_min('B_leg_min_radius_mm'),
    'main_U_radius_mm':c.radius_mm,
    'states_outside_B_gross_Z':sum(not p['B_local_arc_in_gross_z'] for p in positions),
    'states_outside_A_gross_Z':sum(not p['A_arc_in_gross_z'] for p in positions),
    'states_with_Y_overhang':sum(p['B_local_y_overrun_mm']>1e-8 for p in positions),
    'max_B_Y_overhang_mm':max(p['B_local_y_overrun_mm'] for p in positions),
    'max_lateral_width_violation_mm':max(p['width_overrun_mm'] for p in positions),
    'B_local_U_Z_range_mm':[min(p['B_local_arc_z_mm'] for p in positions),max(p['B_local_arc_z_mm'] for p in positions)],
    'full_ribbon_valid':False,'USB_signaling_measured':False,'vendor_qualified_dynamic_lifetime':False,
    'physical_USB_continuity_proven':False,
    'midline_3D_path_and_exact_length_computed':True,
    'selected_pose_data':[{'tag':t,**{k:round(v,6) if isinstance(v,float) else v for k,v in pose(c,s,q,target).items()}}
     for t,s,q in R39.nominal_references()]}
  report['candidates'].append(rec)
  print(c.name,'max_err',rec['max_analytic_length_deviation_mm'],'xvio',rec['max_lateral_width_violation_mm'],
     'Yvio',rec['max_B_Y_overhang_mm'],'grossZB',rec['states_outside_B_gross_Z'],flush=True)
 return report


def physical_usb_graph_path(topology:str,s:float,q:float,*,fpc_intact:bool=True,dock_bounced_open:bool=False):
 """Ideal graph reachability only, never a USB PHY/BER or continuity measurement.

 Treat radio as NON-physical, never count it as an A/B copper path.
 Physical wire exists in model for FPC/HYBRID only. Dock contacts are assumed
 made at the two seated endpoints, not in flight. The graph algorithm prevents
 a software recovery, cache or radio channel from being treated as a USB wire.
 """
 edges=[]
 if topology in ('CONTINUOUS_FPC','DOCK_PLUS_FPC_HYBRID') and fpc_intact:
  edges.extend([('A_USB','FPC_COPPER'),('FPC_COPPER','B_USB')])
 terminal= (abs(s)<1e-10 and abs(q)<1e-10) or (abs(s-SLIDE)<1e-10 and abs(q-DOCK)<1e-10)
 if topology in ('DOCK_ONLY','DOCK_PLUS_FPC_HYBRID','DOCK_PLUS_RADIO') and terminal and not dock_bounced_open:
  edges.extend([('A_USB','MECHANICAL_DOCK'),('MECHANICAL_DOCK','B_USB')])
 graph={}
 for u,v in edges:
  graph.setdefault(u,set()).add(v);graph.setdefault(v,set()).add(u)
 seen={'A_USB'};stack=['A_USB']
 while stack:
  for v in graph.get(stack.pop(),()):
   if v not in seen:seen.add(v);stack.append(v)
 return 'B_USB' in seen

def topology_study():
 states=[dict(s_mm=s,q_mm=q) for s,q in R39.all_path_states()]
 def terminal(s,q):
  # Conditional idealized behavior: contact at exactly the two seated endpoints.
  if abs(s)<1e-10 and abs(q)<1e-10:return 'STOW_DOCK'
  if abs(s-SLIDE)<1e-10 and abs(q-DOCK)<1e-10:return 'OPEN_DOCK'
  return None
 dock_connected=sum(terminal(v['s_mm'],v['q_mm']) is not None for v in states)
 assert dock_connected==2
 ideal_graph_counts={name:sum(physical_usb_graph_path(name,v['s_mm'],v['q_mm']) for v in states)
   for name in ('CONTINUOUS_FPC','DOCK_ONLY','DOCK_PLUS_FPC_HYBRID','DOCK_PLUS_RADIO')}
 assert ideal_graph_counts['DOCK_ONLY']==2
 assert ideal_graph_counts['DOCK_PLUS_RADIO']==2 # RF itself never counts as copper
 assert ideal_graph_counts['DOCK_PLUS_FPC_HYBRID']==len(states) # conditional good FPC
 assert ideal_graph_counts['CONTINUOUS_FPC']==len(states)
 ideal_break_counts={name:sum(physical_usb_graph_path(name,v['s_mm'],v['q_mm'],fpc_intact=False)
   for v in states) for name in ideal_graph_counts}
 assert ideal_break_counts['DOCK_PLUS_FPC_HYBRID']==2 # endpoint does NOT heal mid-slide FPC failure
 transitions=[(states[i],states[i+1]) for i in range(len(states)-1)]
 # Every disconnection or downshift on USB requires product rejection, even with radio/cache.
 grid=[
 {'topology':'CONTINUOUS_FPC','wired_USB_in_theory_all_states':True,'real_FPC_exists':False,'qualified':False,
  'dock_used_as_USB_hot_switch':False,'rejected_by_definition':False},
 {'topology':'DOCK_ONLY','wired_USB_in_theory_all_states':False,'ideal_endpoints_connected':dock_connected,
  'ideal_intermediate_positions_disconnected':len(states)-dock_connected,'qualified':False,'rejected_by_definition':True},
 {'topology':'DOCK_PLUS_FPC_HYBRID','wired_USB_in_theory_all_states':True,'real_FPC_exists':False,'dock_used_as_USB_hot_switch':False,
  'dock_optional_power_or_secondary_signals_only':True,'qualified':False,'rejected_by_definition':False},
 {'topology':'DOCK_PLUS_RADIO','wired_USB_in_theory_all_states':False,'qualified':False,'rejected_by_definition':True}
 ]
 faults=[
  {'case':'MID_SLIDE_FREEZE','s_mm':SLIDE/2,'q_mm':0,'dock_closed':False,'dock_only_USB_live':False,'hybrid_USB_with_good_FPC_ideally_live':True},
  {'case':'PREDOCK','s_mm':SLIDE,'q_mm':0,'dock_closed':False,'dock_only_USB_live':False,'hybrid_USB_with_good_FPC_ideally_live':True},
  {'case':'NORMAL_DOCK_APPROACH','s_mm':SLIDE,'q_mm':8.15,'dock_closed':False,'dock_only_USB_live':False,'hybrid_USB_with_good_FPC_ideally_live':True},
  {'case':'STOW_CONTACT_BOUNCE','s_mm':0,'q_mm':0,'contact_bounce_breaks_dock_only_USB':True,'FPC_would_continue_if_real_and_qualified':True},
  {'case':'FPC_CONDUCTOR_FRACTURE','s_mm':SLIDE/2,'q_mm':0,'FPC_carries_USB':True,'USB_live':False,'dock_cannot_restore_USB_mid_slide':True},
  {'case':'SINGLE_POWER_SWITCH_WELDED','s_mm':SLIDE/2,'q_mm':0,'energized_exposed_contacts_risk':True,'USB_continuity_not_power_isolation_proof':True},
  {'case':'PCB_POWER_BYPASS','s_mm':SLIDE/2,'q_mm':0,'single_point_exposed_live_contact_risk':True,'USB_continuity_not_power_isolation_proof':True},
  {'case':'REVERSE_BEFORE_DOCK','s_mm':SLIDE-1,'q_mm':0,'dock_only_USB_live':False,'FPC_must_work_both_directions':True},
 ]
 report={'revision':'R46 strict hard-gate: uninterrupted real physical interpod USB during complete two-axis motion',
   'user_authorized_USB_disconnection_during_slide':False,
   'owner_decision_prohibit_reinterpreting_as_reconnect':True,
   'requires_actual_A_to_B_USB_conductors_and_reference_ground_at_every_position':True,
   'requires_qualified_active_USB_link_at_all_positions':True,
   'USB_interface_generation_data_rate_not_yet_frozen':True,
   'hypothetical_states_total':len(states),'transition_count':len(transitions),
   'ideal_dock_connected_positions':dock_connected,
   'ideal_dock_only_disconnected_positions':len(states)-dock_connected,
   'dock_only_full_sweep_compliant':False,
   'ideal_model_graph_connected_positions':ideal_graph_counts,
   'ideal_model_positions_after_FPC_fracture':ideal_break_counts,
   'these_graph_counts_are_not_physical_test_data':True,
   'wired_mid_motion_bypass_required_if_keeping_endpoint_dock':True,
   'hybrid_docking_must_not_disconnect_USB_path':True,
   'wireless_or_data_buffering_is_not_physical_USB':True,
   'no_energized_exposed_power_contacts_during_travel':True,
   'three_single_point_PCB_bypasses_still_unresolved':True,
   'mechanical_36_of_64_unsafe_still_unresolved':True,
   'candidate_topologies':grid,'fault_injections':faults,
   'firmware_emulation_link_training_does_not_substitute_physical_connection':True,
   'no_electrical_measurements_yet':True,'manufacturing_go':False}
 return report


def run(parent,export=True):
 lineage=verify_parent(parent)
 save('results/R46_lineage.json',lineage)
 geometry=fpc_study()
 save('results/R46_3D_fixed_length_scan.json',geometry)
 electrical=topology_study()
 save('results/R46_USB_topology_and_faults.json',electrical)
 a=cq.importers.importBrep(str(REFERENCE/'R38_A_unchanged.brep')).val()
 b=cq.importers.importBrep(str(REFERENCE/'R38_B_unchanged.brep')).val()
 assert a.isValid() and b.isValid()
 poses=[('STOW',0.,0.),('MID',SLIDE/2,0.),('OPEN_SEATED',SLIDE,DOCK)]
 results=[];steps=[]
 for c in (CANDIDATES[1],CANDIDATES[3],CANDIDATES[4]):
  records,out=sampled_arc_occ(c,poses,a,b,step_export=export and c==CANDIDATES[1]);results.append({'candidate':c.name,'poses':records})
  steps.extend(out)
 save('results/R46_OCC_main_arc_probes.json',{'scope':'MAIN U ARC only; actual 3D FPC route absent',
   'probe_band_width_mm':STUDY_RIBBON_WIDTH,'proxy_study_thickness_mm':STUDY_RIBBON_THICKNESS,
   'probe_states':results,'manufacturing_go':False})
 save('results/R46_STEP_manifest.json',{'files':steps,'GHOST_only':True,'not_a_full_FPC_or_wired_USB':True})
 return {'lineage':lineage,'fpc_candidates':len(geometry['candidates']),
   'motion_states_per_candidate':geometry['states_total'],'OCC_arc_candidate_count':len(results),
   'OCC_arc_pose_count':sum(len(x['poses']) for x in results),
   'STEP_count':len(steps),'continuous_USB_qualified':False,'dock_only_compliant':False,
   'manufacturing_go':False}

if __name__=='__main__':
 parent=Path(os.environ.get('R46_R45_PARENT','/mnt/data/files/'+PARENT_FILE))
 print('R46 source',parent,flush=True)
 save('results/R46_results.json',run(parent))
 print('R46 geometry/topology run complete',flush=True)
