"""Supplemental nominal seat diagnostics, not supplier tolerance or capacity.

Rotation boundary is for a centered ideal sharp hexagon, not actual nut
chamfers or translated/tilted reachability. Unit load is normalization only.
"""
from pathlib import Path
import sys,math,json
R=Path('/home/qian-qi/RAZR-SLIDE-frame-anchor-20261015');O=Path('/tmp/razr-frame-anchor-20261015');sys.path.insert(0,str(R/'integration'))
import verify_frame_nut_anchor as w
_,base,h=w.p.w.w.w.load_new('/tmp/razr-panel-shear-20261015/native-v2/manifest.json');_,new,h2=w.load(O/'native-final/manifest.json',base);h.update(h2)
# support = a*cos(theta)+a/sqrt(3)*sin(theta); pocket apothem1.28.
a=1.25;amplitude=a/math.cos(math.pi/6)
angle=math.pi/6-math.acos(1.28/amplitude);degrees=math.degrees(angle)
rows=[]
for i,(x,y) in enumerate(w.CENTERS):
 nut=new[f'FRAME_{i}_NUT_SHNS_M1_NOMINAL'];frame=new['A_FRAME'];checks=[]
 for sign in (-1,1):
  contact=nut.rotate((x,y,0),(x,y,1),sign*degrees);past=nut.rotate((x,y,0),(x,y,1),sign*(degrees+.05))
  hit=w.v.common(contact,frame);over=w.v.common(past,frame);distance=contact.distance(frame)
  assert hit<=w.TOL and over>w.TOL and distance<1e-6
  checks.append({'direction':sign,'ideal_centered_contact_deg':sign*degrees,'contact_common_mm3':hit,'extra0p05deg_common_mm3':over})
 patches=w.p.w.planar_contacts(nut,{'A_FRAME':frame});seat=[p for p in patches if p['normal_into_cover'][2]>.999999]
 fit=w.p.w.equilibrium(seat,nut.Center().toTuple(),(0,0,-1),(x,y,2.95));up=w.p.w.equilibrium(seat,nut.Center().toTuple(),(0,0,1),(x,y,2.95))
 assert fit['feasible'] and not up['feasible']
 rows.append({'index':i,'nominal_seat_contact_area_mm2':sum(p['area_mm2'] for p in seat),'downward_normalized_unit_case':fit,'upward_normal_only_not_held':up,'rotation_checks':checks})
 print('NUT',i,'AREA',rows[-1]['nominal_seat_contact_area_mm2'],'ANGLE',degrees,flush=True)
assert all(w.v.sha(f)==value for f,value in h.items())
result={'input_sha256':h,'native_templates_sha_bound':True,'rows':rows,'ideal_radial_pocket_wall_from_boss_cylinder_mm':1.8-2.56/math.sqrt(3),
        'nominal_remaining_shoulder_height_mm':2.55-1.2,'not_global_minimum_wall_or_stress_solution':True,
        'native_seat_area_not_actual_chamfered_bearing_area':True,'does_not_verify_screw_nut_thread_connection':True,
        'no_torque_or_preload_or_strength_assigned':True,'supplemental_not_in704_tests':True}
(O/'nut-seat-diagnostics.json').write_text(json.dumps(result,indent=2)+'\n')
