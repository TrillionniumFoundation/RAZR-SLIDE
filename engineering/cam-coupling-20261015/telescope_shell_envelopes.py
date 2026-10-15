"""Additional same-kernel continuous nominal telescope/shell envelope check.
Not a full-scene, force, guide-clearance or release/relock qualification.
"""
from pathlib import Path
import json,sys,math
ROOT=Path('/home/qian-qi/RAZR-SLIDE-coupling-20261015')
OUT=Path('/tmp/razr-coupling-20261015')
sys.path.insert(0,str(ROOT/'integration'))
import verify_cam_coupling as v
from straight_envelope import swept_cylinder
r,p,hashes=v.load(OUT/'native-v5/manifest.json')
assert r['source_sha256']==v.sha(ROOT/'integration/cam_coupling.py')
rows=[]

def cage(radius,low,high,start,move):
    if high<=low:raise ValueError('empty cylinder enclosure')
    origin=v.cq.Vector(start[0],start[1],low)
    if sum(x*x for x in move)==0:
        return v.n.single(v.cq.Solid.makeCylinder(radius,high-low,origin,v.cq.Vector(0,0,1)))
    result,method=swept_cylinder(origin,v.cq.Vector(0,0,1),radius,high-low,v.cq.Vector(*move))
    return result

for side in 'LR':
    sign=-1 if side=='L' else 1
    # Full global A-side tube reservation: every tube/collar/head fits this
    # radius and height range, including every allowed allocation of offsets.
    a=cage(1.4,.7,13.2,(sign*7.25,81.5),(sign*12.,0,0))
    for fixed in ('STUDY_A_FRAME','STUDY_A_BACK_PANEL'):
        value=v.common(a,p[fixed])
        rows.append({'side':side,'phase':'all prescribed extension/slide','moving_enclosure':'whole telescope radius1.4 global-height enclosure','fixed':fixed,'common_mm3':value})
    # B-relative long-slide envelopes at normal separation8.2. At total joint
    # offset8.5 with each<=2.9, each offset>=2.7 and the first two sum to5.6..5.8.
    # Split finite cylindrical carriers retain small flanges rather than falsely
    # treating a stepped head as a radius0.65 solid through the narrow neck.
    pieces=[('base',1.4,-7.5,-4.3),('stage1 including collar',1.15,-4.8,-1.4),
            ('stage2 shaft',.6,-1.9,1.5),('stage2 collar',.75,-1.9,-1.5),
            ('stage3 rod/collar',.35,1.,4.15),('head neck',.4,4.15,5.),
            ('head lower flange',.65,4.3,4.5),('head upper flange',.65,4.8,5.)]
    for label,radius,low,high in pieces:
        b=cage(radius,low,high,(sign*7.25,81.5),(sign*12.,-79.75,0))
        value=v.common(b,p['STUDY_B_SHELL'])
        rows.append({'side':side,'phase':'complete79.75mm long slide','moving_enclosure':label,'radius_mm':radius,'B_relative_Z_bounds_mm':[low,high],'fixed':'STUDY_B_SHELL','common_mm3':value})
    # During seating the follower stays at B-local Y=1.75, in the complementary
    # end step whose material starts at4.1. For arbitrary allowed joint offsets,
    # sum=.3+separation: stage1 top<=4.0; stage2 top<=4.1. The collar is lower.
    pieces=[('base',1.4,-7.5,3.9),('stage1 including collar',1.15,-4.8,4.),
            ('stage2 shaft',.6,-1.9,4.1),('stage2 collar',.75,-1.9,1.1),
            ('stage3 rod/collar',.35,1.,4.15),('head neck',.4,4.15,5.),
            ('head lower flange',.65,4.3,4.5),('head upper flange',.65,4.8,5.)]
    for label,radius,low,high in pieces:
        b=cage(radius,low,high,(sign*19.25,1.75),(0,0,0))
        value=v.common(b,p['STUDY_B_SHELL'])
        rows.append({'side':side,'phase':'complete8.2mm seating','moving_enclosure':label,'radius_mm':radius,'B_relative_Z_bounds_mm':[low,high],'fixed':'STUDY_B_SHELL','common_mm3':value})
    print('SIDE',side,'checks',len(rows),'positive',[x for x in rows if x['side']==side and x['common_mm3']>1e-7],flush=True)
assert all(v.sha(path)==value for path,value in hashes.items())
result={'source_sha256':r['source_sha256'],'input_sha256':hashes,'same_CAD_kernel':True,'candidate_builder_imported':False,
        'checks':rows,'passed':not any(x['common_mm3']>1e-7 for x in rows),
        'scope':'conservative continuous nominal telescope carriers versus revised A/B shells; not whole-scene continuous qualification',
        'joint_allocation_limits_used_mm':[.1,2.9],'sum_joint_offsets_equals_separation_plus_0p3':True,
        'guide_tilt_radial_play_force_and_PAWL_sequence_qualified':False,
        'included_in_481_unit_count':False,'candidate_go':False,'manufacturing_go':False}
(OUT/'telescope-shell-envelopes.json').write_text(json.dumps(result,indent=2)+'\n')
print('CONTINUOUS_TELESCOPE_SHELL_CHECKS',len(rows),'PASS',result['passed'],flush=True)
raise SystemExit(0 if result['passed'] else 1)
