#!/usr/bin/env python3
"""R47 RAZR SLIDE: full-route collision witnesses and fail-closed supplier intake.

Research tool; not manufacturer CAD, FPC body, USB link, life or safety certification.
R46 frozen objects are imported byte-for-byte, never altered by this generator.
"""
from __future__ import annotations
import os, json, sys, math, argparse, hashlib, zipfile
from pathlib import Path
from dataclasses import dataclass
import numpy as np
import cadquery as cq
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN

ROOT=Path(__file__).resolve().parent.parent
R46=root46=ROOT/'baseline'/'R46_source'
R46_ZIP=ROOT/'baseline'/'RAZR_SLIDE_R46_verified_dual_architecture_20261011.zip'
R46_SHA='e31e01aae54560941e6aad7fd0889c9d8c5b9db63f96245f72a363ce82ab4cbb'
R46_MEMBERS=49
R45_SHA='84174df60dc931dda4b7eba331b41b136f25188f5435266d3a74ad2700925080'
STUDY_WIDTH_MM=1.2
STUDY_THICKNESS_MM=.2
STUDY_CLEARANCE_MM=.2
STUDY_END_TRIM_MM=6.


def digest_file(path:Path):
 with open(path,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def write_json(name,obj):
 p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(obj,indent=2,ensure_ascii=False,sort_keys=True,allow_nan=False,default=lambda x: x.item() if isinstance(x,np.generic) else str(x))+'\n',encoding='utf8')
 return p

def parent_attestation():
 assert R46_ZIP.is_file(),R46_ZIP
 assert digest_file(R46_ZIP)==R46_SHA,'R46 parent changed'
 with zipfile.ZipFile(R46_ZIP) as z:
  assert len(z.namelist())==R46_MEMBERS and z.testzip() is None
  for nm in ('src/r46_routing_and_gate.py','reference/r39_reference_unmodified.py',
             'reference/R38_A_unchanged.brep','reference/R38_B_unchanged.brep'):
   assert z.read(nm)==(R46/nm).read_bytes(),nm
  assert hashlib.sha256(z.read('baseline/R45_original_immutable.zip')).hexdigest()==R45_SHA
 return {'baseline_sha256':R46_SHA,'baseline_members':R46_MEMBERS,'R45_sha256':R45_SHA,
         'independent_R39_variants_not_merged':True,
         'source_and_A_B_BRep_bytes_frozen':True,'R46_archive_crc_ok':True}


def import_R46():
 sys.path.insert(0,str(R46/'src'))
 import r46_routing_and_gate as r
 return r


def linearly(a,b,n:int):
 a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
 return [a+(b-a)*t for t in np.linspace(0.,1.,n)]


def sstep(u):return 3*u*u-2*u*u*u


def full_centerline(r,c,s,q,ln,leg_samples=21,arc_samples=61,stub_samples=5):
 """Actual R46 *mathematical* path, including previously untested stubs.
 Sharp 90-degree transitions at connectors have zero allowable corner radius.
 """
 row=r.pose(c,s,q,ln);fold=row['fold_y_mm'];z=row['world_arc_z_mm']
 xa=c.xa();xb=c.xb();YA=r.R39.Y_A;YB=r.R39.Y_B0+s
 ZA=r.R39.Z_A;ZB=r.R39.Z_B0+q;XC=r.R39.X_CONN
 pa=[XC,YA,ZA];pa_leg=[xa,YA,ZA]
 pb_leg=[xb,YB,ZB];pb=[XC,YB,ZB]
 # Stub A / A leg / U / B leg / Stub B in exact R46 source order.
 parts=[('A_CONNECTOR_STUB',linearly(pa,pa_leg,stub_samples))]
 a_leg=[np.array([xa,YA+(fold-YA)*u,ZA+(z-ZA)*sstep(u)]) for u in np.linspace(0,1,leg_samples)]
 parts.append(('A_Z_TRANSITION_LEG',a_leg))
 u=[np.array([c.cx_mm-c.radius_mm*math.cos(theta),fold+c.radius_mm*math.sin(theta),z])
     for theta in np.linspace(0,math.pi,arc_samples)]
 parts.append(('ROLLING_U_ARC',u))
 b_leg=[np.array([xb,fold+(YB-fold)*u,z+(ZB-z)*sstep(u)]) for u in np.linspace(0,1,leg_samples)]
 parts.append(('B_Z_TRANSITION_LEG',b_leg))
 parts.append(('B_CONNECTOR_STUB',linearly(pb_leg,pb,stub_samples)))
 positions=[];segments=[]
 for tag,pts in parts:
  if positions:pts=pts[1:]
  for p in pts:
   if positions:
    prev=positions[-1]
    segment_length=float(np.linalg.norm(p-prev))
    segments.append({'tag':tag,'dl':segment_length})
   positions.append(np.asarray(p,dtype=float))
 center=np.asarray(positions)
 accumulated=np.r_[0.,np.cumsum([x['dl'] for x in segments])]
 return center,accumulated,row,segments


def gross_contains(pt,bb,tol=1e-4):
 return bb.xmin-tol<=pt[0]<=bb.xmax+tol and bb.ymin-tol<=pt[1]<=bb.ymax+tol and bb.zmin-tol<=pt[2]<=bb.zmax+tol


def count_inside(shape, pts, arclengths, trim, max_witnesses=1):
 bb=shape.BoundingBox();inside=[]
 # One OCC classifier per solid and pose. This is the same classification
 # as CadQuery Compound.isInside but avoids re-initializing for every point.
 classifier=BRepClass3d_SolidClassifier(shape.wrapped)
 total=float(arclengths[-1])
 for idx,(pt,t) in enumerate(zip(pts,arclengths)):
  if idx % 2 and idx not in (len(pts)-1,):continue
  if t<trim or t>total-trim:continue
  if gross_contains(pt,bb):
   classifier.Perform(gp_Pnt(*map(float,pt)),1e-6)
   if classifier.State()==TopAbs_IN or classifier.IsOnAFace():inside.append(idx)
 witnesses=[]
 for i in inside[:max_witnesses]:
  pt=pts[i];sphere=cq.Solid.makeSphere(0.12,cq.Vector(*map(float,pt)))
  try:vol=float(shape.intersect(sphere).Volume())
  except Exception:vol=None
  witnesses.append({'point_xyz_mm':[round(float(v),5) for v in pt],
   'arclength_from_A_mm':round(float(arclengths[i]),5),
   'local_ball_radius_mm':0.12,'local_sphere_intersection_mm3':None if vol is None else round(vol,9),
   'point_isInside_geometry':True,
   'OCC_local_ball_ambiguous':vol is None or vol<=1e-9})
 return {'free_span_sample_count':sum(trim<=arclengths[i]<=total-trim for i in range(0,len(arclengths),2)),
         'free_span_centerline_inside_count':len(inside),
         'witnesses':witnesses,
         'no_collision_proof_not_established_even_if_count_zero':True}


def calculate(paths='default',export=True):
 src=import_R46()
 A=cq.importers.importBrep(str(R46/'reference/R38_A_unchanged.brep')).val()
 B=cq.importers.importBrep(str(R46/'reference/R38_B_unchanged.brep')).val()
 assert A.isValid() and B.isValid()
 selected=[src.CANDIDATES[i] for i in (1,3,4)]
 poses=[('STOW',0.,0.),('MID',src.SLIDE/2,0.),('PREDOCK',src.SLIDE,0.),
        ('DOCK_Q4',src.SLIDE,4.),('OPEN_SEATED',src.SLIDE,src.DOCK)]
 rows=[];step_files=[]
 for c in selected:
  ln=src.target_length(c)
  for tag,s,q in poses:
   pts,dist,p,parts=full_centerline(src,c,s,q,ln)
   B_world=B.translate((0,s,q-src.DOCK))
   collision_A=count_inside(A,pts,dist,STUDY_END_TRIM_MM,max_witnesses=1 if tag=='STOW' else 0)
   collision_B=count_inside(B_world,pts,dist,STUDY_END_TRIM_MM,max_witnesses=1 if tag=='STOW' else 0)
   uA=pts[9]-pts[8];stubA=pts[8]-pts[7]
   # Both intentional 90-degree connector-to-Y turns; zero-radius joint.
   a_turn_deg=90.
   b_turn_deg=90.
   encircle_radius=math.hypot(STUDY_WIDTH_MM/2+STUDY_CLEARANCE_MM,
                              STUDY_THICKNESS_MM/2+STUDY_CLEARANCE_MM)
   result={'candidate':c.name,'pose':tag,'s_mm':s,'q_mm':q,
       'target_analytic_length_mm':round(ln,8),
       'polyline_length_mm':round(float(dist[-1]),8),
       'polyline_chord_error_mm':round(float(ln-dist[-1]),8),
       'free_span_trim_at_each_connector_mm':STUDY_END_TRIM_MM,
       'connector_stub_sharp_corner_count':2,
       'connector_stub_corner_angle_deg':[a_turn_deg,b_turn_deg],
       'minimum_bend_radius_at_both_connector_stubs_mm':0,
       'no_valid_manufacturing_fillets_or_strain_relief':True,
       'assumed_R15_qualified_by_vendor':False,
       'hypothetical_circumscribed_envelope_radius_mm':round(encircle_radius,5),
       'circumscribed_radius_is_not_a_real_ribbon_geometry':True,
       'A_body':collision_A,'B_moving_body':collision_B,
       'free_span_point_samples_with_body_interference':collision_A['free_span_centerline_inside_count']+collision_B['free_span_centerline_inside_count'],
       'physical_usb_continuity_verified':False,
       'manufacturing_go':False}
   rows.append(result)
   if export and c==selected[0] and tag in ('STOW','MID','OPEN_SEATED'):
    # Five analytic spline segments, not a laminated solid or valid USB FPC.
    # Each connector-to-longitudinal-leg intersection remains a sharp kink.
    xa=c.xa();xb=c.xb();yf=p['fold_y_mm'];za=src.R39.Z_A;zb=src.R39.Z_B0+q
    yy=src.R39.Y_A;yb=src.R39.Y_B0+s;zc=p['world_arc_z_mm'];xc=src.R39.X_CONN
    def cv(v):return cq.Vector(*map(float,v))
    segs=[cq.Edge.makeLine(cv((xc,yy,za)),cv((xa,yy,za))),
     cq.Edge.makeSpline([cv((xa,yy+(yf-yy)*u,za+(zc-za)*(3*u*u-2*u*u*u))) for u in np.linspace(0,1,14)]),
     cq.Edge.makeSpline([cv((c.cx_mm-c.radius_mm*math.cos(t),yf+c.radius_mm*math.sin(t),zc)) for t in np.linspace(0,math.pi,36)]),
     cq.Edge.makeSpline([cv((xb,yf+(yb-yf)*u,zc+(zb-zc)*(3*u*u-2*u*u*u))) for u in np.linspace(0,1,14)]),
     cq.Edge.makeLine(cv((xb,yb,zb)),cv((xc,yb,zb)))]
    wire=cq.Compound.makeCompound(segs)
    obj=cq.Compound.makeCompound([A,B_world,wire])
    name=f'R47_{c.name}_{tag}_FULL_CENTERLINE_ONLY_GHOST.step'
    path=ROOT/'cad'/name
    cq.exporters.export(obj,str(path),exportType='STEP')
    importback=cq.importers.importStep(str(path)).val()
    assert importback.isValid() and len(importback.Solids())>=2
    step_files.append({'file':'cad/'+name,'sha256':digest_file(path),
      'reimported_solids':len(importback.Solids()),'is_ghost':True,
      'not_ribbon':True,'not_usb':True,'not_supplier_approved':True})
  print(c.name,'done',flush=True)
 summary={'revision':'R47 full route negative clearance and vendor intake gate',
   'source_R46_sha256':R46_SHA,'source_R46_immutable_members':R46_MEMBERS,
   'geometry_source':'R46 math centerline, all 5 route segments; NOT real FPC material',
   'root_reference_frame':'B_world = B_local + (0,s,q-8.2)',
   'tested_candidate_count':len(selected),'tested_poses_per_candidate':len(poses),
   'actual_BRep_point_inside_tests':True,'full_route_sampled_every_second_polyline_vertex':True,
   'fpc_proxy_width_mm':STUDY_WIDTH_MM,'fpc_proxy_thickness_mm':STUDY_THICKNESS_MM,
   'clearance_assumption_mm':STUDY_CLEARANCE_MM,
   'source_3D_data_is_not_OEM':True,'no_real_FPC':True,
   'usb_in_motion_physical_copper_required':True,
   'existing_36_of_64_mechanical_unsafe':True,
   'existing_three_PCB_bypass_hazards':True,
   'no_flex_material_endurance_test':True,
   'no_USB_TDR_VNA_eye_BER_test':True,
   'all_paths_with_unqualified_connector_kinks':True,
   'no_manufacturing_or_electrical_approval':True,'manufacturing_go':False,
   'pose_records':rows}
 write_json('results/R47_full_span_OCC_and_curvature.json',summary)
 write_json('results/R47_STEP_manifest.json',{'files':step_files,'ghost_only':True,'not_full_real_FPC':True})
 return summary


def intake_contract(payload:dict,root:Path):
 """Fail closed: a self-filled data form cannot certify a physical product.

 External native files and approvals are required; even a syntactically complete
 input is NOT a verified third-party signoff or real hardware measurement.
 """
 expected={
 'OEM_complete_A_B_CAD':('cad_path','sha256','vendor_id','coordinate_frame','written_cutout_authorization'),
 'FPC_dynamic_stackup':('model','vendor_id','laminate_layers','neutral_axis','dynamic_R_mm','allowed_torsion_deg','design_cycle_target','sample_cycle_test_report'),
 'USB_real_link':('protocol','bitrate_Gbps','differential_pairs','shield_ground','TDR_receipt','VNA_receipt','BER_eye_receipt','in_motion_no_disconnect_trace'),
 'A_B_connector_and_stress_relief':('header_model','mate_model','PCB_land_patterns','fixing_drawings','strain_relief_GD_T'),
 'Battery_power_isolation':('two_BMS_models','reverse_blocking','thermal_report','energized_dock_bypass_fixtures','live_break_test'),
 'OLED_qualified_module':('module_id','OEM_full_3D','dynamic_R_mm','flattening_force_report','300k_cycle_evidence','long_storage_recovery'),
 'Mechanical_fail_closed':('two_end_lock_CAD','loaded_force_retraction','spring_pin_breakage_receipts','36_64_adversarial_closure'),
 }
 details=[]
 for section,keys in expected.items():
  data=payload.get(section)
  if not isinstance(data,dict):
   details.append({'section':section,'missing':list(keys),'supplied':False});continue
  miss=[k for k in keys if data.get(k) in (None,'',[],{},False)]
  details.append({'section':section,'missing':miss,'supplied':True})
 native=payload.get('native_files',[])
 verified_native=[];invalid_native=[]
 if not isinstance(native,list):invalid_native.append('native_files_not_list');native=[]
 for item in native:
  if not isinstance(item,dict) or not item.get('path') or not item.get('sha256'):
   invalid_native.append('missing_path_or_sha');continue
  p=root/item['path']
  if not p.is_file():invalid_native.append('missing_'+item['path']);continue
  if digest_file(p)!=item['sha256']:
   invalid_native.append('hash_mismatch_'+item['path']);continue
  verified_native.append(item['path'])
 complete=all(not d['missing'] for d in details) and not invalid_native and bool(verified_native)
 # An external independent witness chain and actual qualification must be established
 # outside this user-supplied schema; never turn a populated JSON into release.
 return {'schema_sections':len(details),'supplier_sections_complete':sum(not d['missing'] for d in details),
   'missing_sections_or_fields':details,'native_files_verified':verified_native,
   'native_file_errors':invalid_native,'self_reported_data_complete':complete,
   'physical_measurements_independently_witnessed':False,
   'real_USB_link_continuity_qualified':False,
   'OEM_CAD_release_to_cut_authenticated':False,
   'manufacturing_go':False}


def run():
 write_json('results/R47_lineage.json',parent_attestation())
 data=calculate(export=True)
 template=json.loads((ROOT/'R47_VENDOR_INTAKE_TEMPLATE.json').read_text(encoding='utf8'))
 verdict=intake_contract(template,ROOT/'vendor_inputs')
 write_json('results/R47_vendor_intake_gate.json',verdict)
 assert not verdict['manufacturing_go'] and not data['manufacturing_go']
 return data,verdict

if __name__=='__main__':
 x,y=run();print('R47: candidate-pose count',len(x['pose_records']),'OEM section ready',y['supplier_sections_complete'],'manufacturing NO-GO')
