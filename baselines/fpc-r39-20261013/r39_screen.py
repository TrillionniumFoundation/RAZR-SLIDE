"""R39 finite-sample, 3D ribbon-footprint OCC inside-solid survey.

Not continuous collision detection, not physical equilibrium. To avoid hiding
near misses, test centre+four full-width/thickness section corners at 81
arclength parameter locations per pose and record all observed penetrations.
"""
import json, math, time
from pathlib import Path
import numpy as np
import cadquery as cq
from r25_capture import ROOT, P
from r24_mechanics import r21
from r39_path import Candidate,curve,LENGTH_TARGET_MM,FPC_WIDTH_MM,FPC_THICKNESS_MM

CANDIDATES=(
 ('INBOARD_SERPENTINE_125',Candidate('INBOARD_SERPENTINE',-4.,2.,2),125.),
 ('INNER_SIDE_SERPENTINE_125',Candidate('INNER_SIDE_SERPENTINE',2.5,2.,2),125.),
 ('OUTBOARD_SINGLE_BOW_125',Candidate('OUTBOARD_SINGLE_BOW',17.,4.,1),125.),
 ('GENTLE_INBOARD_SINGLE_BOW_150',Candidate('GENTLE_INBOARD_SINGLE_BOW',-12.,12.,1),150.),
)
SCENES=[]
for i in range(17):SCENES.append((f'SLIDE_{i:02d}',round(P.travel*i/16,7),0.))
for i,q in enumerate([1.025,2.05,4.1,6.15,8.2]):SCENES.append((f'FINAL_DOCK_{i:02d}',float(P.travel),q))

def frames(tangents):
    previous=None
    rows=[]
    for t in tangents:
        if previous is None:
            w=np.cross(np.array([0,0,1]),t)
            if np.linalg.norm(w)<1e-10:w=np.array([1.,0.,0.])-t[0]*t
        else:w=previous-t*np.dot(t,previous)
        w=w/np.linalg.norm(w)
        v=np.cross(t,w);v=v/np.linalg.norm(v)
        rows.append((w,v))
        previous=w
    return rows

def sample_points(path, stride=5):
    """Return sampled centre and ribbon rectangular section corners."""
    pts=path['points']; uv=frames(path['tangent']);res=[]
    for k in list(range(0,len(pts),stride)) + ([] if (len(pts)-1)%stride==0 else [len(pts)-1]):
        p=pts[k];w,b=uv[k]
        corners=[p,p-.5*FPC_WIDTH_MM*w-.5*FPC_THICKNESS_MM*b,
                 p+.5*FPC_WIDTH_MM*w-.5*FPC_THICKNESS_MM*b,
                 p+.5*FPC_WIDTH_MM*w+.5*FPC_THICKNESS_MM*b,
                 p-.5*FPC_WIDTH_MM*w+.5*FPC_THICKNESS_MM*b]
        res.extend((k,float(q[0]),float(q[1]),float(q[2])) for q in corners)
    return res

def scan(write=True):
    start=time.monotonic()
    A=cq.importers.importBrep(str(ROOT/'cad/R38_A_R37_BYTE_IDENTICAL.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad/R38_B_PROVISIONAL_STATIC_HEADER_CLEARANCE.brep')).val()
    rows=[]
    for name,s,q in SCENES:
        ref=r21.r17_assembly(P,s,q,1 if name=='FINAL_DOCK_04' else 0)
        Bcur=B.translate((0,s,q-P.z_travel))
        solids={'A_chassis':A,'B_chassis':Bcur,'OLED_hypothesis':ref['OLED'],'old_display_FPC_not_cross_chamber':ref['FPC']}
        full_x_range=(min(A.BoundingBox().xmin,Bcur.BoundingBox().xmin),max(A.BoundingBox().xmax,Bcur.BoundingBox().xmax))
        full_z_range=(min(A.BoundingBox().zmin,Bcur.BoundingBox().zmin,ref['OLED'].BoundingBox().zmin),max(A.BoundingBox().zmax,Bcur.BoundingBox().zmax,ref['OLED'].BoundingBox().zmax))
        for key,cn,L in CANDIDATES:
            c=curve(cn,s,q,n=401,target=L)
            samples=sample_points(c,stride=5)
            counts={};first_hits={}
            for solidname,solid in solids.items():
                bb=solid.BoundingBox();cnt=0;first=None
                for index,x,y,z in samples:
                    if x < bb.xmin-1e-4 or x > bb.xmax+1e-4 or y < bb.ymin-1e-4 or y > bb.ymax+1e-4 or z < bb.zmin-1e-4 or z > bb.zmax+1e-4:continue
                    if solid.isInside(cq.Vector(x,y,z),1e-5):
                        cnt+=1
                        if first is None:first=dict(path_fraction=round(index/400,4),x=round(x,4),y=round(y,4),z=round(z,4))
                counts[solidname]=cnt
                first_hits[solidname]=first
            all_points=np.array([(x,y,z) for _,x,y,z in samples])
            outside_x=np.logical_or(all_points[:,0]<full_x_range[0],all_points[:,0]>full_x_range[1]); outside_z=np.logical_or(all_points[:,2]<full_z_range[0],all_points[:,2]>full_z_range[1])
            row=dict(candidate=key,pose=name,slide_mm=s,dock_mm=q,assumed_length_mm=L,
                numerical_arclength_mm=round(c['numerical_length'],9),
                sampled_polyline_length_mm=round(c['polyline_length'],7),
                length_absolute_error_mm=round(abs(c['numerical_length']-L),10),
                minimum_bend_radius_mm=round(c['min_centerline_radius_mm'],6),
                approx_outer_fiber_strain=float(round(c['approx_fiber_bending_strain'],6)),
                band_width_mm=FPC_WIDTH_MM,band_thickness_mm=FPC_THICKNESS_MM,
                full_width_ribbon_sample_count=len(samples),sample_inside_solid_counts=counts,
                first_hits=first_hits,outside_current_chassis_width_footprint_samples=int(outside_x.sum()),
                outside_assembled_proxy_z_footprint_samples=int(outside_z.sum()),
                curve_point_bounds={k:[round(v,5) for v in ar] for k,ar in c['point_bounds'].items()},
                passes_geometry_and_R7p5_screen=False,physical_OEM_permission=False)
            row['passes_geometry_and_R7p5_screen']=(sum(counts.values())==0 and not outside_x.any() and not outside_z.any() and row['minimum_bend_radius_mm']>=7.5)
            rows.append(row)
        print(name, 'done',round(time.monotonic()-start,2),'sec',flush=True)
    summary={}
    for key,_,_ in CANDIDATES:
        c=[r for r in rows if r['candidate']==key]
        summary[key]=dict(poses=len(c),target_length_mm=c[0]['assumed_length_mm'],
            max_length_error_mm=max(r['length_absolute_error_mm'] for r in c),
            worst_minimum_bend_radius_mm=min(r['minimum_bend_radius_mm'] for r in c),
            poses_with_observed_any_solid_penetration=sum(sum(r['sample_inside_solid_counts'].values())>0 for r in c),
            total_sampled_solid_penetrations=sum(sum(r['sample_inside_solid_counts'].values()) for r in c),
            poses_exceeding_chassis_width=sum(r['outside_current_chassis_width_footprint_samples']>0 for r in c),
            poses_exceeding_assembled_proxy_z=sum(r['outside_assembled_proxy_z_footprint_samples']>0 for r in c),
            poses_passing_assumed_R2p5=sum(r['minimum_bend_radius_mm']>=2.5 for r in c),
            poses_passing_assumed_R7p5=sum(r['minimum_bend_radius_mm']>=7.5 for r in c),
            poses_passing_assumed_R15=sum(r['minimum_bend_radius_mm']>=15.0 for r in c),
            poses_passing_all_design_screens=sum(r['passes_geometry_and_R7p5_screen'] for r in c))
    out=dict(revision='R39 CONTINUOUS 3D CENTERLINE / FINITE SECTION OCC PENETRATION SCREEN, NOT OEM FPC',
        original_R38_geometry_reference='R38_A_R37_BYTE_IDENTICAL + R38_B_PROVISIONAL_STATIC_HEADER_CLEARANCE',
        product_travel_y_mm=P.travel,product_final_dock_z_mm=P.z_travel,
        scenes=len(SCENES),scenario_count=len(rows),
        geometric_sample_spacing_parameter=1/80,section_samples_per_location=5,
        tested_physical_footprint_thickness_mm=FPC_THICKNESS_MM,
        tested_physical_footprint_width_mm=FPC_WIDTH_MM,
        materials_and_fatigue_lifetime_not_qualified=True,
        strictly_finite_sampling_not_entire_swept_continuum=True,
        no_OEM_FPC_stackup_clamp_harness_or_tail_step=True,
        no_live_electrical_connection_implemented=True,
        constraints_summary=summary,rows=rows,
        all_candidates_rejected=all(d['poses_passing_all_design_screens']==0 for d in summary.values()),
        manufacturing_go=False)
    if write:
        (ROOT/'verification/R39_path_screen.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('COMPLETE',round(time.monotonic()-start,2),'sec\n',json.dumps(summary,indent=2),flush=True)
    return out
if __name__=='__main__':scan()
