"""R40 hypothetical inboard rolling-U interchamber FPC cassette. Research only.

A B header relocation is required, not part of a manufactured connector.
An exact inextensible-length spatial centreline is constructed for real
R38 79.75mm Y then 8.2mm Z trajectory (not linearly coupled).
No actual flex/copper neutral plane, connector CAD, board cut permission, or life data.
"""
from pathlib import Path
import math,json,csv
import numpy as np
ROOT=Path(__file__).resolve().parent
SLIDE=79.75; DOCK=8.2
A=np.array([33.,70.,6.05]); B_Y_LOCAL=15.; B_Z_LOCAL=4.8
WIDTH=1.2; THICK=0.15
RADII=(15.,16.5,18.); LENGTHS=(110.,119.,130.)
R_SCREEN_ASSUMED=15. # material sensitivity, not OEM permission

def poses():
    p=[{'stage':'slide','s':round(float(s),6),'q':0.} for s in np.linspace(0.,SLIDE,101)]
    p += [{'stage':'dock','s':SLIDE,'q':round(float(q),6)} for q in np.linspace(DOCK/20,DOCK,20)]
    return p

def smooth(u):return 10*u**3-15*u**4+6*u**5

def smooth_p(u):return 30*u*u-60*u**3+30*u**4

def smooth_pp(u):return 60*u-180*u*u+120*u**3

def arc_data(r,q,N=1201):
    theta=np.linspace(0,np.pi,N);u=theta/np.pi
    dz=(B_Z_LOCAL+q-DOCK)-A[2]
    dvz=dz*smooth_p(u)/np.pi
    ddvz=dz*smooth_pp(u)/(np.pi*np.pi)
    vx=-r*np.sin(theta);vy=r*np.cos(theta)
    ax=-r*np.cos(theta);ay=-r*np.sin(theta)
    v=np.column_stack((vx,vy,dvz));acc=np.column_stack((ax,ay,ddvz))
    speed=np.linalg.norm(v,axis=1)
    cross=np.linalg.norm(np.cross(v,acc),axis=1)
    kappa=cross/(speed**3)
    length=float(np.trapezoid(speed,theta))
    return length, float(1/kappa.max()),float(np.max(np.abs(dvz))),theta

def solve(s,q,r=16.5,length=119.):
    arc,rmin,twist_rate,theta=arc_data(r,q)
    ay=A[1];by=B_Y_LOCAL+s
    # Both straight legs must approach the round top on +Y side of anchors.
    yc=(length-arc+ay+by)/2.
    la=yc-ay;lb=yc-by
    left_x=A[0];right_x=A[0]-2*r
    is_kinematic=(la>=0 and lb>=0)
    box={'xmin':round(right_x-WIDTH/2,5),'xmax':round(left_x+WIDTH/2,5),
         'ymin':round(min(ay,by),5),'ymax':round(yc+r+WIDTH/2,5),
         'zmin':round(min(A[2],B_Z_LOCAL+q-DOCK)-THICK/2,5),
         'zmax':round(max(A[2],B_Z_LOCAL+q-DOCK)+THICK/2,5)}
    return {'s_mm':s,'q_mm':q,'R_mm_assumed':r,'L_mm_assumed':length,
        'A_anchor':A.tolist(),'B_RELOCATED_LOCAL_x_mm':right_x,'B_world_anchor':[right_x,by,B_Z_LOCAL+q-DOCK],
        'connector_relocation_B_x_mm':round(right_x-32.7,5),
        'U_top_y_mm':yc,'arc_3d_length_mm':arc,'leg_A_mm':la,'leg_B_mm':lb,
        'verified_math_length_mm':arc+la+lb,'min_bend_R_mm':rmin,
        'bend_R15_sensitivity_pass':rmin>=R_SCREEN_ASSUMED,
        'kinematic_leg_lengths_nonnegative':is_kinematic,
        'max_chassis_X_overhang_mm':max(0.,left_x+WIDTH/2-36.995,-36.995-(right_x-WIDTH/2)),
        'U_top_exceeds_stow_housing_Y_mm':max(0.,yc+r+WIDTH/2-94.25) if s==0 and q==0 else None,
        'box':box,'twist_rate_z_vs_theta_max_mm_per_rad':twist_rate}

def points(sol, each_leg=18, around=75):
    # Straight leg A then semi-circle U with smooth Z interpolation then back on B side.
    r=sol['R_mm_assumed']; yc=sol['U_top_y_mm'];bx=sol['B_RELOCATED_LOCAL_x_mm']
    by=sol['B_world_anchor'][1];bz=sol['B_world_anchor'][2]
    p=[]
    for j in range(each_leg):
        t=j/each_leg;p.append([A[0],A[1]+t*(yc-A[1]),A[2]])
    for j in range(around+1):
        u=j/around;theta=np.pi*u
        p.append([A[0]-r+r*np.cos(theta),yc+r*np.sin(theta),A[2]+(bz-A[2])*smooth(u)])
    for j in range(1,each_leg+1):
        t=j/each_leg;p.append([bx,yc+(by-yc)*t,bz])
    return np.array(p)

def run(write=True):
    rows=[]
    for r in RADII:
        for length in LENGTHS:
            for ix,st in enumerate(poses()):
                t=solve(st['s'],st['q'],r,length)
                rows.append({'pose_index':ix, 'stage':st['stage'], **t})
    cases=[]
    for r in RADII:
        for L in LENGTHS:
            a=[row for row in rows if row['R_mm_assumed']==r and row['L_mm_assumed']==L]
            cases.append({'radius':r,'length':L,'positions':len(a),
                'kinematic_leg_failures':sum(not x['kinematic_leg_lengths_nonnegative'] for x in a),
                'radius15_screen_failures':sum(not x['bend_R15_sensitivity_pass'] for x in a),
                'min_R_mm':min(x['min_bend_R_mm'] for x in a),
                'min_leg_mm':min(min(x['leg_A_mm'],x['leg_B_mm']) for x in a),
                'stow_Y_overhang_mm':a[0]['U_top_exceeds_stow_housing_Y_mm'],
                'B_new_anchor_local_x_mm':a[0]['B_RELOCATED_LOCAL_x_mm']})
    res={'revision':'R40 rolling-U inboard FPC cassette geometry-screen, NOT qualified hardware',
         'sampled_real_two_stage_positions':121,'total_parameterized_scenarios':len(rows),
         'hypothetical_stacks':{'width_mm':WIDTH,'thickness_mm':THICK},
         'sensitivity_R15_NOT_vendor_min_bend_approval':True,
         'cases':cases,'anchor_B_relocation_required':True,
         'real_connector_B_mount_and_FPC_not_built':True,'mechanical_cassette_not_built':True,
         'OEM_protected_core_permission_missing':True,'manufacturing_go':False}
    if write:
        (ROOT/'verification').mkdir(exist_ok=True)
        (ROOT/'verification/R40_motion.json').write_text(json.dumps(res,indent=2,ensure_ascii=False)+'\n')
        cols=['pose_index','stage','s_mm','q_mm','R_mm_assumed','L_mm_assumed','U_top_y_mm',
              'arc_3d_length_mm','leg_A_mm','leg_B_mm','verified_math_length_mm','min_bend_R_mm',
              'bend_R15_sensitivity_pass','kinematic_leg_lengths_nonnegative',
              'max_chassis_X_overhang_mm','connector_relocation_B_x_mm']
        with (ROOT/'verification/R40_1089_cases.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows)
    print(json.dumps(res,ensure_ascii=False,indent=2));return res

if __name__=='__main__':run()
