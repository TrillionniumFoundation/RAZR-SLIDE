"""Builder-free native STEP readback of the empty-shell study, same CAD kernel.

Checks complete roots, same local outer extents, all three installed B poses,
material accounting and declared full-motion enclosures. Does not certify
hardware, dimensions of OEM parts, or occupancy by omitted phone components.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
import cadquery as cq
from straight_envelope import TOL, single, whole_material


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def vol(shape):
    return whole_material(shape,empty=True)[1]


def difference(a,b):
    values=[vol(a.cut(b)),vol(b.cut(a))]
    if max(values)>TOL:
        raise ValueError('reimported material differs')
    return values


def readback(report_path, output):
    report_path=Path(report_path).resolve();output=Path(output).resolve()
    r=json.loads(report_path.read_text());inputs={str(report_path):sha(report_path)};parts={}
    expected={f'{kind}_{side}_{part}' for kind in ('rectangular_negative','stepped') for side in 'AB' for part in ('outer','cavity','shell')}
    expected|={f'{kind}_{pose}_B_shell' for kind in ('rectangular_negative','stepped') for pose in ('STOW','PREDOCK','OPEN_SEATED')}
    expected|={'slide_outer_superset','seat_lap_superset','seat_body_superset'}
    if set(r['exports'])!=expected:
        raise ValueError('missing or extra native participants')
    for name,meta in r['exports'].items():
        rel=Path(meta['path'])
        if rel.is_absolute() or len(rel.parts)!=1 or rel.name!=name+'.step':
            raise ValueError('unexpected STEP filename')
        path=report_path.parent/rel
        if path.is_symlink() or sha(path)!=meta['sha256']:
            raise ValueError('native STEP bytes changed')
        roots=cq.importers.importStep(str(path)).vals()
        if len(roots)!=1:
            raise ValueError('extra native root')
        if len(meta['bounds_xyz_mm'])!=6 or any(not math.isfinite(v) for v in meta['bounds_xyz_mm']):
            raise ValueError('invalid bounds certificate')
        body=single(roots[0]);b=body.BoundingBox()
        bb=[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]
        if not math.isfinite(meta['volume_mm3']) or abs(vol(body)-meta['volume_mm3'])>TOL or any(abs(x-y)>TOL for x,y in zip(bb,meta['bounds_xyz_mm'])):
            raise ValueError('native size/volume certificate differs')
        parts[name]=body;inputs[str(path)]=sha(path)
    d=r['dimensions'];w,h,t=[d[k] for k in ('width_mm','height_mm','thickness_mm')]
    c,wall,y,z=[d[k] for k in ('study_clearance_mm','study_wall_mm','slide_mm','normal_seating_mm')]
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in d.values()):
        raise ValueError('invalid dimensions')
    half=(t-c)/2;lap=h-y+c
    if not (h>y and z-t>=c-TOL and half>wall and min(w,y-c,t)>2*wall):
        raise ValueError('invalid overlap study')
    def box(x0,x1,y0,y1,z0,z1):
        return single(cq.Solid.makeBox(x1-x0,y1-y0,z1-z0,cq.Vector(x0,y0,z0)))
    outer_a=box(-w/2,w/2,0,y-c,0,t).fuse(box(-w/2,w/2,y-c,h,0,half)).clean()
    outer_b=box(-w/2,w/2,lap,h,0,t).fuse(box(-w/2,w/2,0,lap,half+c,t)).clean()
    expected_shapes={
        'rectangular_negative_A_outer':box(-w/2,w/2,0,h,0,t),
        'rectangular_negative_B_outer':box(-w/2,w/2,0,h,0,t),
        'rectangular_negative_A_cavity':box(-w/2+wall,w/2-wall,wall,h-wall,wall,t-wall),
        'rectangular_negative_B_cavity':box(-w/2+wall,w/2-wall,wall,h-wall,wall,t-wall),
        'stepped_A_outer':outer_a,'stepped_B_outer':outer_b,
        'stepped_A_cavity':box(-w/2+wall,w/2-wall,wall,y-c-wall,wall,t-wall),
        'stepped_B_cavity':box(-w/2+wall,w/2-wall,lap+wall,h-wall,wall,t-wall),
        'slide_outer_superset':box(-w/2,w/2,0,h+y,z,z+t),
        'seat_lap_superset':box(-w/2,w/2,y,y+lap,half+c,t+z),
        'seat_body_superset':box(-w/2,w/2,y+lap,y+h,0,t+z)}
    comparisons={k:difference(parts[k],v) for k,v in expected_shapes.items()}
    for kind in ('rectangular_negative','stepped'):
        for side in 'AB':
            k=f'{kind}_{side}';cavity=parts[k+'_cavity'];outer=parts[k+'_outer']
            if vol(cavity.cut(outer))>TOL:
                raise ValueError('cavity outside declared outer')
            comparisons[k+'_shell']=difference(parts[k+'_shell'],outer.cut(cavity))
    poses=[]
    for kind in ('rectangular_negative','stepped'):
        for pose,move in {'STOW':(0,0,z),'PREDOCK':(0,y,z),'OPEN_SEATED':(0,y,0)}.items():
            k=f'{kind}_{pose}_B_shell'
            comparisons[k]=difference(parts[k],parts[kind+'_B_shell'].translate(move))
            value=vol(parts[kind+'_A_shell'].intersect(parts[k]))
            poses.append({'variant':kind,'pose':pose,'shell_common_mm3':value})
            previous=next(x for x in r['poses'] if x['variant']==kind and x['pose']==pose)
            if abs(value-previous['shell_common_mm3'])>TOL:
                raise ValueError('pose common differs')
            if kind=='stepped' and value>TOL:
                raise ValueError('stepped study collision')
            if kind=='rectangular_negative' and pose=='OPEN_SEATED' and value<=TOL:
                raise ValueError('lost rectangular negative control')
    continuous={k:vol(parts['stepped_A_outer'].intersect(parts[k])) for k in ('slide_outer_superset','seat_lap_superset','seat_body_superset')}
    if any(v>TOL for v in continuous.values()):
        raise ValueError('full-motion enclosure collides')
    if any(sha(path)!=value for path,value in inputs.items()):
        raise ValueError('input changed during readback')
    if 'phone_layout' in sys.modules:
        raise ValueError('candidate builder imported')
    result={'complete_STEP_files':len(parts),'native_positive_solids':len(parts),'comparisons':comparisons,
            'poses':poses,'continuous_enclosure_common_mm3':continuous,'input_sha256':inputs,
            'same_kernel_not_cross_engine':True,'candidate_builder_imported':False,'passed':True,
            'only_empty_project_owned_shells':True,'actual_phone_fit':'unknown',
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=readback(a.report,a.output);print(json.dumps({k:r[k] for k in ('complete_STEP_files','passed','candidate_builder_imported','actual_phone_fit')}))
