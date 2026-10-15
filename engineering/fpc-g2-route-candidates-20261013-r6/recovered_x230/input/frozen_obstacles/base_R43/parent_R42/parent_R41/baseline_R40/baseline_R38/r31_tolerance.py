"""R31 adversarial offsets for proposed A-key contact and B-pawl guard.
Each XYZ perturbation is an ASSUMED relative placement; not OEM GD&T.
Ideal follower travel uses intersecting shelf/head projected XY footprint and
vertical datum. Tests include nominal full seat, 0.05 mm early, no-A blocking,
and swept B-plunger clearance in two endpoint positions.
"""
from __future__ import annotations
import itertools,json
import cadquery as cq
from r25_capture import ROOT,P,intersection
from r22_mechanics import to_blocal
from r31_presence import (SHELF_WORLD,follower_down,interposer,pawl_position,
                           PAWL_LATERAL_STROKE)

def overlap(a0,a1,b0,b1):return min(a1,b1)>max(a0,b0)

def lift_with_offset(q,dx,dy,dz):
    # B plunger head x34.43..34.535, world y79.83..79.98 at OPEN seated.
    # Only a supported A nose passing this footprint supplies mechanical drive.
    contacting=overlap(SHELF_WORLD[0]+dx,SHELF_WORLD[1]+dx,34.43,34.535) and \
        overlap(SHELF_WORLD[2]+dy,SHELF_WORLD[3]+dy,79.83,79.98)
    return max(0.,min(.4,q-7.8-dz)) if contacting else 0.

def row_for(side,w,dx,dy,dz,B):
    # A alignment drifts; a datum offset in Z changes actual actuator travel.
    pre=lift_with_offset(8.15,dx,dy,dz)
    seat=lift_with_offset(8.2,dx,dy,dz)
    transit=.25
    noA=interposer(side,0.)
    # No-A guard is B-fixed and pawl may be independently perturbed by +-w.
    ppos=pawl_position(side,transit).translate(cq.Vector(dx,dy,dz))
    noA_block=intersection(noA,ppos)
    early_clash=intersection(interposer(side,pre),pawl_position(side,transit))
    seat_clash=intersection(interposer(side,seat),pawl_position(side,transit))
    # B-shell relative tolerances are an independent question: test both
    # default (spring return) and end-of-stroke positions.
    cases=[]
    for shift in (0.,.4):
        test_shape=to_blocal(interposer(side,shift).translate(cq.Vector(dx,dy,dz)),'OPEN')
        cases.append(round(intersection(B,test_shape),10))
    return dict(side=side,width_mm=w,xyz_mm=(dx,dy,dz),
        contact_stroke_early_8p15_mm=round(pre,6),seat_8p20_mm=round(seat,6),
        no_A_pawl_sweep_0p25_clash_mm3=round(noA_block,10),
        at_q8p15_pawl_path_clash_mm3=round(early_clash,10),
        at_q8p20_pawl_path_clash_mm3=round(seat_clash,10),
        B_body_clashes_mm3=cases)

def run(write=True):
    B=cq.importers.importBrep(str(ROOT/'cad'/'R31_B_PRESENCE_POCKETS.brep')).val()
    rows=[]
    for side in 'LR':
        for w in (.02,.05):
            for xyz in itertools.product((-w,0.,w),repeat=3):
                rows.append(row_for(side,w,*xyz,B))
        print('R31 TOLERANCE',side,'complete',len(rows),flush=True)
    summary=[]
    for w in (.02,.05):
        a=[x for x in rows if x['width_mm']==w]
        summary.append(dict(width_mm=w,configurations=len(a),
          false_release_before_seat=sum(x['at_q8p15_pawl_path_clash_mm3']<1e-9 for x in a),
          seat_refuses_to_release=sum(x['at_q8p20_pawl_path_clash_mm3']>1e-9 for x in a),
          no_A_guard_misses_middle_sweep=sum(x['no_A_pawl_sweep_0p25_clash_mm3']<1e-9 for x in a),
          B_cavity_interference_configurations=sum(any(v>1e-9 for v in x['B_body_clashes_mm3']) for x in a)))
    out={'revision':'R31 assumed key/bearings +/-0.02/0.05mm tolerance pressure, not GD&T or force test',
      'configurations':len(rows),'per_width':summary,'rows':rows,
      'mechanical_seat_0p05_before_end_not_safe_with_0p05_z_datum_ambiguity':True,
      'failed_to_establish_tolerance_robust_positive_latch':True,
      'force_free_linear_kinematics_only':True,
      'manufacturing_go':False}
    if write:(ROOT/'verification'/'R31_tolerance.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    return out
if __name__=='__main__':
 d=run();print('R31 TOL',d['per_width'],flush=True)
