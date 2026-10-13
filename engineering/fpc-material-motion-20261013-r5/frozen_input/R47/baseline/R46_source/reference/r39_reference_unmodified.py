"""RAZR SLIDE R39: multi-axis rolling-U FPC geometric feasibility screen.

This script produces a 3D *routing skeleton* and envelope collision tests, NOT
an electrical interconnect or a vendor-approved dynamic-flex laminate.

The two straight legs and the planar semicircle are joined with continuous
first derivatives at the bend. The x-axis transitions at connector footprints
are SHARP routing placeholders, NOT physically allowable FPC bend details.
The B-leg z offset changes with docking and is a smoothstep z interpolation;
its analytical length is integrated and the U center advances to keep a fixed
centerline length for all two-axis poses. Bender/fixing/captive routes are NOT
modeled. Tubular envelope radius 0.60mm is a conservative spatial proxy for a
hypothetical 1.2mm-wide laminate, NOT its actual cross section.

DO NOT manufacture, energize or claim endurance based on these envelopes.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import pi, sin, cos, sqrt
import json, hashlib, os
from pathlib import Path
from typing import Sequence
import numpy as np
from scipy.optimize import brentq

ROOT=Path(__file__).resolve().parent
BASE_SHA='649c89711e5bd25a357fbac972d1c0e4ac8144841dd34e8b261cd67aa50bb7a6'

def verify_R38_source():
    source=Path(os.environ.get('R38_SOURCE_ZIP','/mnt/data/RAZR_SLIDE_R38_verified_engineering_package_20261011.zip'))
    if source.is_file():
        observed=hashlib.file_digest(open(source,'rb'),'sha256').hexdigest()
        assert observed==BASE_SHA, 'R38 original ZIP mismatch'
        return True
    manifest=json.loads((ROOT/'audit/R39_R38_immutable_manifest.json').read_text())
    assert manifest['source_R38_sha256']==BASE_SHA and len(manifest['entries'])==1094
    for row in manifest['entries']:
        p=ROOT/row['path']
        assert p.is_file() and p.stat().st_size==row['bytes']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],row['path']
    return False
Y_A=70.0
Y_B0=15.0
X_CONN=32.70
Z_A=5.75+0.30   # catalogue proxy only, chosen surface midpoint
Z_B0=4.50+0.30-8.20
SLIDE=79.75
DOCK=8.20
HALF_OUTER_WIDTH=36.995
HYPOTHETICAL_ENVELOPE_RADIUS=0.60
SCREEN_HALF_WIDTH_ASSUMED=33.66045998455

@dataclass(frozen=True)
class Family:
    name:str
    r:float
    center_x:float
    classification:str
    def xa(self):return self.center_x-self.r
    def xb(self):return self.center_x+self.r
    def stub_length(self):return abs(X_CONN-self.xa())+abs(X_CONN-self.xb())

FAMILIES=(
 Family('INBOARD_R2p5_UNLICENSED',2.50,31.00,'compact, unqualified minimum bend radius'),
 Family('INBOARD_R15_SCREENING',15.00,19.00,'internal routing, initial 100x thickness dynamic radius screening'),
 Family('OUTBOARD_R15_SCREENING',15.00,38.50,'external routing, known width violation'),
)
NODES,WEIGHTS=np.polynomial.legendre.leggauss(48)
QUAD_U=(NODES+1)/2
QUAD_W=WEIGHTS/2

def smoothstep(u):return 3*u*u-2*u*u*u

def blend_integral(dy:float,dz:float):
    """Analytic speed of constant-y-rate and cubic z progress."""
    return float(np.sum(QUAD_W*np.sqrt(dy*dy+(dz*6*QUAD_U*(1-QUAD_U))**2)))

def length_given_fold(f:Family,yb:float,zb:float,fold:float):
    assert fold>=max(Y_A,yb)-1e-6
    return f.stub_length()+(fold-Y_A)+pi*f.r+blend_integral(fold-yb,Z_A-zb)

def length_target(f:Family):
    # The endpoint path consists of 79.75mm longitudinal slide followed by
    # 8.20mm normal motion. Required max length is searched over that path.
    candidates=[length_given_fold(f,Y_B0+s,Z_B0,max(Y_A,Y_B0+s)) for s in np.linspace(0,SLIDE,81)]
    candidates += [length_given_fold(f,Y_B0+SLIDE,Z_B0+q,max(Y_A,Y_B0+SLIDE)) for q in np.linspace(0,DOCK,41)]
    return max(candidates)+20.0

def fold_y(f:Family,s:float,q:float,length:float):
    yb=Y_B0+s;zb=Z_B0+q
    y0=max(Y_A,yb)
    assert length_given_fold(f,yb,zb,y0)<=length+1e-6
    return brentq(lambda y:length_given_fold(f,yb,zb,y)-length,y0,y0+length,xtol=2e-12)

def line_points(a,b,n):return [np.asarray(a)+(np.asarray(b)-np.asarray(a))*t for t in np.linspace(0,1,n)]

def centerline(f:Family,s:float,q:float,ln:float,nleg=21,narc=65):
    assert 0<=s<=SLIDE and 0<=q<=DOCK
    ya=Y_A;yb=Y_B0+s;zb=Z_B0+q
    fy=fold_y(f,s,q,ln)
    pa=np.array([X_CONN,ya,Z_A]);pb=np.array([X_CONN,yb,zb])
    a_leg=np.array([f.xa(),ya,Z_A]);b_leg=np.array([f.xb(),yb,zb])
    points=[pa,a_leg]
    points += line_points(a_leg,[f.xa(),fy,Z_A],nleg)[1:]
    for t in np.linspace(0,pi,narc)[1:]:
        points.append(np.array([f.center_x-f.r*cos(t),fy+f.r*sin(t),Z_A]))
    for u in np.linspace(0,1,nleg)[1:]:
        points.append(np.array([f.xb(),fy+(yb-fy)*u,Z_A+(zb-Z_A)*smoothstep(u)]))
    points.append(pb)
    points=np.array(points,dtype=float)
    chord=np.linalg.norm(np.diff(points,axis=0),axis=1).sum()
    # Minimum pointwise radius on compensating B leg.
    dy=abs(fy-yb);dz=abs(zb-Z_A)
    uu=np.linspace(0,1,101)
    dz_du=dz*6*uu*(1-uu)
    dz2_du=dz*(6-12*uu)
    k=(dy*np.abs(dz2_du))/((dy*dy+dz_du*dz_du)**1.5)
    r_b=float(1/np.max(k)) if max(k)>1e-14 else float('inf')
    # Main arc radius f.r; anchor stubs have unbounded curvature at corners.
    return dict(points=points,fold_y_mm=float(fy),
        centerline_exact_mm=float(length_given_fold(f,yb,zb,fy)),
        centerline_polyline_mm=float(chord),
        nominal_main_arc_radius_mm=f.r,
        ideal_B_compensation_min_radius_mm=r_b,
        estimated_inner_X_mm=float(points[:,0].min()-HYPOTHETICAL_ENVELOPE_RADIUS),
        estimated_outer_X_mm=float(points[:,0].max()+HYPOTHETICAL_ENVELOPE_RADIUS),
        max_width_overrun_right_mm=max(0,float(points[:,0].max()+HYPOTHETICAL_ENVELOPE_RADIUS-HALF_OUTER_WIDTH)))

def all_path_states():
    rows=[(float(s),0.0) for s in np.linspace(0,SLIDE,321)]
    rows.extend((SLIDE,float(q)) for q in np.linspace(0,DOCK,161)[1:])
    return rows

def nominal_references():
    return [('STOW',0.,0.),('QUARTER',SLIDE/4,0.),('MID',SLIDE/2,0.),('THREE_QUARTER',SLIDE*3/4,0.),
     ('OPEN_PREDOCK',SLIDE,0.),('OPEN_Q2',SLIDE,2.),('OPEN_Q4',SLIDE,4.),('OPEN_Q6p61',SLIDE,6.61),
     ('OPEN_Q8p15',SLIDE,8.15),('OPEN_SEATED',SLIDE,DOCK)]

def run_kinematics():
    base_external=verify_R38_source()
    res={'revision':'R39 analytic constant-length rolling-U candidate families, no vendor approval',
         'base_R38_source_zip_sha256':BASE_SHA,
         'base_R38_source_zip_external_verified_this_run':base_external,
         'endpoint_A_proxy_xyz_mm':[X_CONN,Y_A,Z_A],
         'endpoint_B_proxy_stow_xyz_mm':[X_CONN,Y_B0,Z_B0],
         'slide_mm':SLIDE,'normal_dock_mm':DOCK,
         'design_study_laminate_thickness_mm':.15,
         'design_study_width_mm':1.20,
         'hypothetical_round_collision_envelope_radius_mm':HYPOTHETICAL_ENVELOPE_RADIUS,
         'rollover_model':'two x-separated Y legs, planar XY U radius R, smooth z gradient in B leg',
         'critical_limitations':['connector-to-loop stubs have unphysical sharp bends',
             'no captive guides, stress-relief, torsion, cable stackup, contact continuity or BMS',
             'centerline roll speed solved kinematically, not physically driven',
             'FPC width 1.2mm cannot be assumed to carry chosen data and current paths'],
         'families':[],'manufacturing_go':False}
    for f in FAMILIES:
        L=length_target(f)
        states=[];polydev=0;exactdev=0;maxxb=0;mincurvature=1e9
        for s,q in all_path_states():
            data=centerline(f,s,q,L)
            polydev=max(polydev,abs(data['centerline_polyline_mm']-L))
            exactdev=max(exactdev,abs(data['centerline_exact_mm']-L))
            maxxb=max(maxxb,data['max_width_overrun_right_mm'])
            mincurvature=min(mincurvature,data['ideal_B_compensation_min_radius_mm'])
            states.append({'s_mm':round(s,5),'q_mm':round(q,5),'fold_y_mm':round(data['fold_y_mm'],5),
                           'exact_centerline_mm':round(data['centerline_exact_mm'],6),
                           'polyline_centerline_mm':round(data['centerline_polyline_mm'],6),
                           'right_width_overrun_mm':round(data['max_width_overrun_right_mm'],5),
                           'B_leg_R_min_mm':round(data['ideal_B_compensation_min_radius_mm'],5)})
        references=[]
        for tag,s,q in nominal_references():
            p=centerline(f,s,q,L)
            references.append({'tag':tag,'s_mm':s,'q_mm':q,'fold_y_mm':round(p['fold_y_mm'],6),
              'points_xyz_mm':[[round(float(t),5) for t in row] for row in p['points']],
              'B_leg_R_min_mm':round(p['ideal_B_compensation_min_radius_mm'],6)})
        res['families'].append({'name':f.name,'model_classification':f.classification,
            'nominal_U_arc_R_mm':f.r,'laneA_x_mm':f.xa(),'laneB_x_mm':f.xb(),
            'target_analytic_length_mm':round(L,7),'samples_total':len(states),
            'analytic_length_max_deviation_mm':round(exactdev,9),
            'polyline_approximation_max_deviation_mm':round(polydev,8),
            'maximum_right_width_violation_mm':round(maxxb,5),
            'minimum_B_z_transition_local_radius_mm':round(mincurvature,5),
            'anchors_with_unqualified_sharp_corner':True,
            'manufacturing_feasible_claimed':False,
            'dynamic_states':states,'reference_paths':references})
    (ROOT/'verification').mkdir(exist_ok=True)
    (ROOT/'verification/R39_centerlines.json').write_text(json.dumps(res,indent=2,ensure_ascii=False)+'\n')
    return res

if __name__=='__main__':
    z=run_kinematics()
    for f in z['families']:
      print(f['name'],'length',f['target_analytic_length_mm'],'n',f['samples_total'],
            'max_x_violation',f['maximum_right_width_violation_mm'],
            'polyline_length_error',f['polyline_approximation_max_deviation_mm'],
            'BminR',f['minimum_B_z_transition_local_radius_mm'],flush=True)
