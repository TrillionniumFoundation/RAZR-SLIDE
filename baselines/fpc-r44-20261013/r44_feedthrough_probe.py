#!/usr/bin/env python3
"""Negative ONLY: straight cylindrical GHOST feedthroughs from R42 board anchors to R44 back loop.
These are not a proposed FPC design or authorized cuts; other 3D feedthrough routes untested.
"""
import cadquery as cq,numpy as np,time,json
from pathlib import Path
from r44_rear_bypass import protected,intersectvol,ROOT,R,SLIDE,DOCK
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
TARGETS=[('STOW',0.,0.),('PREDOCK',SLIDE,0.),('OPEN_SEATED',SLIDE,DOCK)]
Z=-7.95
RADIUS_PROXY=0.15

def segment(p,q):
    a=np.array(p,dtype=float);b=np.array(q,dtype=float);d=b-a
    return cq.Solid.makeCylinder(RADIUS_PROXY,float(np.linalg.norm(d)),cq.Vector(*a),cq.Vector(*d))
def run():
    rows=[]; out=ROOT/'evidence';out.mkdir(exist_ok=True)
    for stage,s,q in TARGETS:
        core=protected(s,q)
        a_board=[33.,70.,6.05]; a_ext=[R,70.,Z]
        b_board=[33.,15.+s,4.8+q-DOCK];b_ext=[-R,15.+s,Z+q]
        parts={'A_BOARD_TO_UNBUILT_REAR_ANCHOR':segment(a_board,a_ext),'B_BOARD_TO_UNBUILT_REAR_ANCHOR':segment(b_board,b_ext)}
        hits={key:{obs:round(float(intersectvol(sh,body)),6) for obs,body in core.items()} for key,sh in parts.items()}
        row={'stage':stage,'s_mm':s,'q_mm':q,'hypothetical_direct_feedthrough_endpoints':{'A':[a_board,a_ext],'B':[b_board,b_ext]},
             'proxy_radius_mm':RADIUS_PROXY,'cylindrical_not_flat_fpc':True,'not_an_OEM_authorized_channel':True,
             'protected_intersections_mm3':hits,
             'any_protected_shell_intrusion':any(v>1e-6 for x in hits.values() for key,v in x.items() if 'CORE' in key)}
        rows.append(row)
        print(stage,'A vs Acore',hits['A_BOARD_TO_UNBUILT_REAR_ANCHOR']['A_R38_CORE'],
                'B vs Bcore',hits['B_BOARD_TO_UNBUILT_REAR_ANCHOR']['B_R38_CORE'],flush=True)
    d={'revision':'R44 adversarial direct feedthrough at the rear loop endpoints; not general routing nonexistence',
       'rows':rows,'selected_poses':len(rows),'straight_proxies_not_vendor_FPC':True,
       'any_route_still_requires_OEM_feedthrough_and_PCBA_mounting':True,
       'candidate_go':False,'manufacturing_go':False}
    (out/'R44_direct_feedthrough_rejected.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    return d
if __name__=='__main__':run()
