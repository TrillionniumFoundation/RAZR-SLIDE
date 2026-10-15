from pathlib import Path
import json,math,sys
from OCP.BRepAdaptor import BRepAdaptor_Surface
ROOT=Path('/home/qian-qi/RAZR-SLIDE-coupling-20261015')
OUT=Path('/tmp/razr-coupling-20261015')
sys.path.insert(0,str(ROOT/'integration'))
import verify_cam_coupling as v
meta,p,inputs=v.load(OUT/'native-v5/manifest.json')
assert meta['source_sha256']==v.sha(ROOT/'integration/cam_coupling.py')

def end_centers(body,radius):
    found=[]
    for face in body.Faces():
        if face.geomType()!='CYLINDER':continue
        c=BRepAdaptor_Surface(face.wrapped).Cylinder()
        if abs(c.Radius()-radius)>1e-8:continue
        a=c.Axis().Direction()
        if abs(abs(a.Z())-1)>1e-8:raise ValueError('groove cylinder axis differs')
        pt=c.Location();xy=[pt.X(),pt.Y()]
        if not any(math.dist(xy,x)<1e-8 for x in found):found.append(xy)
    if len(found)!=2:raise ValueError('finite two-end groove not identified')
    return sorted(found,key=lambda x:x[1])

rows=[]
for side in 'LR':
    sign=-1 if side=='L' else 1
    cam=end_centers(p[side+'_B_CAM'],.425)
    yoke=end_centers(p[side+'_KEY_YOKE'],.425)
    c0,c1=cam;k=-sign*(c1[0]-c0[0])/(c1[1]-c0[1])
    y0,y1=yoke;m=-sign*(y1[0]-y0[0])/(y1[1]-y0[1])
    if abs(k-12/79.75)>1e-9 or abs(m-1)>1e-9:raise ValueError('actual native groove ratio differs')
    # Project the two endpoint centerline positions on the finite native groove
    # segment. Their affine projection bounds every centerline position between.
    def progress(point,ends):
        a,b=ends;dx,dy=b[0]-a[0],b[1]-a[1]
        return ((point[0]-a[0])*dx+(point[1]-a[1])*dy)/(dx*dx+dy*dy)
    a=[sign*7.25,81.5];b=[sign*(7.25+12),81.5-79.75]
    first=sorted([progress(a,cam),progress(b,cam)])
    second=sorted([progress([sign*7.25,77.5],yoke),progress([sign*(7.25+12),77.5-12],yoke)])
    if not 0<first[0]<first[1]<1 or not 0<second[0]<second[1]<1:raise ValueError('centerline overruns finite groove')
    length1=math.dist(*cam);length2=math.dist(*yoke)
    margins=[min(first[0],1-first[1])*length1,min(second[0],1-second[1])*length2]
    if min(margins)<=.4:raise ValueError('endpoint span does not enclose full nominal pin radius')
    half=.025*(math.hypot(1,k)+math.sqrt(1+m*m))/m
    rows.append({'side':side,'native_cam_end_centers_xy_mm':cam,'native_yoke_end_centers_xy_mm':yoke,
                 'native_first_groove_slope':k,'native_second_groove_slope':m,
                 'derived_output_input_ratio':k/m,'first_centerline_parameter_range':first,
                 'second_centerline_parameter_range':second,'nominal_centerline_end_distances_mm':margins,
                 'whole_linear_centerline_span_inside_finite_grooves':True,
                 'slot_only_output_halfband_mm':half,
                 'does_not_certify_clearance_of_all_phone_parts_or_guides':True})
assert all(v.sha(path)==h for path,h in inputs.items())
result={'source_sha256':meta['source_sha256'],'native_manifest_sha256':v.sha(OUT/'native-v5/manifest.json'),
        'input_sha256':inputs,'candidate_builder_imported':False,'same_CAD_kernel':True,'rows':rows,
        'scope':'geometric straight-groove nominal centerline span; not whole-scene continuous clearance, force, play or release sequence',
        'included_in_481_unit_count':False,'candidate_go':False,'manufacturing_go':False}
(OUT/'native-groove-span.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(rows),flush=True)
