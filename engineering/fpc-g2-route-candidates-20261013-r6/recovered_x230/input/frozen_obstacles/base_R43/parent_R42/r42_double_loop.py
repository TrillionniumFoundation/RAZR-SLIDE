"""R42 exploratory two-flex / half-rate junction motion budget.
This is NOT a wired FPC design or an OEM-approved cassette.  Endpoints and
materials are hypothetical.  Two FLEXES end at a MOVING intermediate carrier;
there is no continuous one-piece FPC and no assembled electrical connector.
"""
from pathlib import Path
import csv, json, math
import numpy as np
from dataclasses import dataclass

ROOT=Path(__file__).resolve().parent
SLIDE=79.75; DOCK=8.20
RADIUS=16.5; FPC_WIDTH=1.20; FPC_THICK=0.15
L1=113.0; L2=99.0
A_X=33.; B_X=33.; C_X=0.
A_Y=70.; B_Y_LOCAL=15.
A_Z=6.05; B_Z_LOCAL=4.80
Z_LIMIT=(-8.2,7.68); X_HALF=36.995

def smooth(u):return 10*u**3-15*u**4+6*u**5

def smoothp(u):return 30*u*u-60*u**3+30*u**4

def smoothpp(u):return 60*u-180*u*u+120*u**3

def stages():
    return [{'stage':'slide','s':round(float(s),6),'q':0.} for s in np.linspace(0,SLIDE,101)]+[{'stage':'dock','s':SLIDE,'q':round(float(q),6)} for q in np.linspace(DOCK/20,DOCK,20)]

def anchors(s,q):
    a=np.array([A_X,A_Y,A_Z]);b=np.array([B_X,B_Y_LOCAL+s,B_Z_LOCAL+q-DOCK]);
    c=np.array([C_X,B_Y_LOCAL+s/2,(a[2]+b[2])/2])
    return a,c,b

def arc_calcs(radius,zdelta,n=1001):
    t=np.linspace(0,np.pi,n)
    u=t/np.pi
    # orientation +/- mirrors X only, curvature invariant
    v=np.column_stack((-radius*np.sin(t),radius*np.cos(t),zdelta*smoothp(u)/np.pi))
    acc=np.column_stack((-radius*np.cos(t),-radius*np.sin(t),zdelta*smoothpp(u)/(np.pi**2)))
    norm=np.linalg.norm(v,axis=1)
    curvature=np.linalg.norm(np.cross(v,acc),axis=1)/(norm**3)
    return float(np.trapezoid(norm,t)),float(1/curvature.max())

def one_loop(start,end,nominal_length,r=RADIUS,orientation=1):
    assert abs(abs(end[0]-start[0])-2*r)<1e-8
    assert orientation*(start[0]-end[0])>0
    arc,min_radius=arc_calcs(r,float(end[2]-start[2]))
    center_y=(nominal_length-arc+float(start[1]+end[1]))/2
    leg1=center_y-start[1];leg2=center_y-end[1]
    x_middle=(start[0]+end[0])/2
    return {'start':start.tolist(),'end':end.tolist(),'nominal_length':nominal_length,
            'radius_geometry_mm':r,'orientation':orientation,'center_y':float(center_y),
            'leg_A_mm':float(leg1),'leg_B_mm':float(leg2),'arc_3d_mm':float(arc),
            'total_length_mm':float(leg1+arc+leg2),
            'minimum_calculated_centerline_radius_mm':float(min_radius),
            'outer_Y_mm':float(center_y+r),'x_middle':float(x_middle)}

def solve(s,q):
    assert 0<=s<=SLIDE and 0<=q<=DOCK and (q==0 or s==SLIDE)
    a,c,b=anchors(s,q)
    u=one_loop(a,c,L1,orientation=1)
    v=one_loop(c,b,L2,orientation=-1)
    return {'s_mm':float(s),'q_mm':float(q),'A':a.tolist(),'C_MOVING_JUNCTION':c.tolist(),'B':b.tolist(),
            'section_1':u,'section_2':v,
            'C_Y_motion_mm':float(s/2),'C_Z_motion_mm':float(q/2),
            'no_carriage_actuator_or_interposer':True}

def centerline(loop,leg_samples=12,arc_samples=70):
    start=np.asarray(loop['start']);end=np.asarray(loop['end']);r=loop['radius_geometry_mm'];cy=loop['center_y'];sign=loop['orientation'];xmid=loop['x_middle']
    pre=np.array([[start[0],start[1]+(cy-start[1])*j/leg_samples,start[2]] for j in range(leg_samples)])
    arc=np.array([[xmid+sign*r*np.cos(np.pi*j/arc_samples),cy+r*np.sin(np.pi*j/arc_samples),start[2]+(end[2]-start[2])*smooth(j/arc_samples)] for j in range(arc_samples+1)])
    post=np.array([[end[0],cy+(end[1]-cy)*j/leg_samples,end[2]] for j in range(1,leg_samples+1)])
    return np.concatenate((pre,arc,post)),(leg_samples,arc_samples)

def calculate(write=True):
    rows=[]
    for stage in stages():
        s,q=stage['s'],stage['q'];m=solve(s,q)
        ycap=max(94.25,94.25+s)
        pointX=[];pointZ=[];ymx=[]
        for n in ('section_1','section_2'):
            f=m[n];p,_=centerline(f,4,30)
            pointX.extend([p[:,0].min(),p[:,0].max()]);pointZ.extend([p[:,2].min(),p[:,2].max()]);ymx.append(p[:,1].max())
        row={'stage':stage['stage'],'s_mm':s,'q_mm':q,
             'L1_mm':m['section_1']['total_length_mm'],'L2_mm':m['section_2']['total_length_mm'],
             'error_1_mm':m['section_1']['total_length_mm']-L1,'error_2_mm':m['section_2']['total_length_mm']-L2,
             'minimum_R_mm':min(m['section_1']['minimum_calculated_centerline_radius_mm'],m['section_2']['minimum_calculated_centerline_radius_mm']),
             'minimum_leg_mm':min(m['section_1']['leg_A_mm'],m['section_1']['leg_B_mm'],m['section_2']['leg_A_mm'],m['section_2']['leg_B_mm']),
             'envelope_X_excess_mm':max(0.,-X_HALF-min(pointX),max(pointX)-X_HALF),
             'envelope_Z_excess_mm':max(0.,Z_LIMIT[0]-min(pointZ),max(pointZ)-Z_LIMIT[1]),
             'envelope_Y_overhang_math_mm':max(0.,max(ymx)-ycap),
             'carrier_position_xyz':m['C_MOVING_JUNCTION']}
        rows.append(row)
    sumry={'revision':'R42 TWO SEPARATE FLEX CIRCUITS + unbuilt half-speed moving junction; research mathematical screen ONLY',
        'parent_R41_SHA256':'f0be97f2661a59d9db87adca18ecc4d961dcb6142b65f9a17b0f452b461dbef6',
        'stages_positions':len(stages()),'sections_per_pose':2,'math_cases':len(rows)*2,
        'research_radius_mm':RADIUS,'section_lengths_mm':[L1,L2],'total_flex_length_mm':L1+L2,
        'flex_width_mm':FPC_WIDTH,'flex_thickness_mm':FPC_THICK,
        'A_end_xyz':anchors(0,0)[0].tolist(),'B_end_stow_xyz':anchors(0,0)[2].tolist(),
        'B_end_seated_xyz':anchors(SLIDE,DOCK)[2].tolist(),
        'C_carrier_stow_xyz':anchors(0,0)[1].tolist(),'C_carrier_seated_xyz':anchors(SLIDE,DOCK)[1].tolist(),
        'maximum_abs_solved_length_error_mm':max(max(abs(z['error_1_mm']),abs(z['error_2_mm'])) for z in rows),
        'minimum_bend_centerline_radius_mm':min(z['minimum_R_mm'] for z in rows),
        'minimum_straight_leg_mm':min(z['minimum_leg_mm'] for z in rows),
        'max_X_envelope_overhang_centerline_mm':max(z['envelope_X_excess_mm'] for z in rows),
        'max_Z_envelope_overhang_centerline_mm':max(z['envelope_Z_excess_mm'] for z in rows),
        'max_Y_envelope_overhang_centerline_mm':max(z['envelope_Y_overhang_math_mm'] for z in rows),
        'new_carriage_and_two_interposer_terminals_not_built':True,
        'real_copper_diel_stack_life_power_USB_SI_missing':True,
        'only_math_not_Occ_clearance':True,'candidate_go':False,'manufacturing_go':False}
    if write:
        (ROOT/'verification').mkdir(exist_ok=True)
        with (ROOT/'verification/R42_motion_121_positions.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=[k for k in rows[0] if k!='carrier_position_xyz']+['carrier_x_mm','carrier_y_mm','carrier_z_mm']);w.writeheader()
            for row in rows:
                flat={k:v for k,v in row.items() if k!='carrier_position_xyz'}
                flat.update(zip(['carrier_x_mm','carrier_y_mm','carrier_z_mm'],row['carrier_position_xyz']));w.writerow(flat)
        (ROOT/'verification/R42_motion_budget.json').write_text(json.dumps(sumry,ensure_ascii=False,indent=2)+'\n')
    return sumry

if __name__=='__main__':print(json.dumps(calculate(),indent=2,ensure_ascii=False))
