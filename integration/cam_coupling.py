"""Finite cam/yoke plus captured telescopic follower: an unqualified transmission study.

B's long inclined groove drives a transverse follower; a second diagonal groove
converts that translation into the original KEY's Y stroke. Three nested joints
absorb normal seating. Real groove clearance is retained, so centerline poses
are not a claim of uniquely driven motion or reliable endpoint relocking.
Original mounted components remain exact; all new interface geometry is a study.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import argparse
import hashlib
import json
import math
import tarfile
import tempfile
import cadquery as cq
import cam_contact_native as n

ROOT=Path(__file__).resolve().parents[1]
BASE='f9091d28eda1ddbeed73d931e283a16aef7ac8d0'
SOURCE=ROOT/'engineering/mounted-mechanism-20261015'
STROKE=79.75
SEATING=8.2
KEY_STROKE=12.
RATIO=KEY_STROKE/STROKE
X0=7.25
Y_CAM=81.5
Y_OUTPUT=77.5
PIN_RADIUS=.4
SLOT_RADIUS=.425
CLEARANCE=SLOT_RADIUS-PIN_RADIUS
STAGE_LENGTH=3.2
STAGE_MIN=.1
STAGE_MAX=2.9


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('finite numeric value required')
    return float(value)


def pose(slide,descent=0.):
    slide=number(slide);descent=number(descent)
    if not 0<=slide<=STROKE or not 0<=descent<=SEATING:
        raise ValueError('outside prescribed phone stroke')
    if descent>0 and slide!=STROKE:raise ValueError('normal seating precedes full slide')
    extension=SEATING-descent
    return {'B_Y_mm':slide,'B_Z_mm':extension,'nominal_KEY_Y_mm':RATIO*slide,
            'nominal_crosshead_outward_mm':RATIO*slide,
            'nominal_joint_offsets_mm':[STAGE_MIN+extension/3]*3,
            'equal_extension_allocation_is_not_mechanically_enforced':True}


def output_band(slide):
    slide=number(slide)
    if not 0<=slide<=STROKE:raise ValueError('invalid slide')
    half=CLEARANCE*(math.sqrt(1+RATIO*RATIO)+math.sqrt(2))
    center=RATIO*slide
    return {'center_mm':center,'lower_mm':center-half,'upper_mm':center+half,
            'reversal_lost_motion_mm':2*half,'unique_output_without_preload':False}


def stage_allocation(descent,offsets):
    p=pose(STROKE,descent)
    if not isinstance(offsets,(list,tuple)) or len(offsets)!=3:raise ValueError('three joints required')
    q=[number(x) for x in offsets]
    if any(x<STAGE_MIN-1e-9 or x>STAGE_MAX+1e-9 for x in q):raise ValueError('captured telescope joint overtravel')
    if abs(sum(q)-3*STAGE_MIN-p['B_Z_mm'])>1e-8:raise ValueError('head is not captured at B cam plane')
    return q


def one(body):return n.single(body)

def vol(body):return n.whole_material(body,empty=True)[1]

def box(a,b):
    if len(a)!=3 or len(b)!=3 or any(number(y)<=number(x) for x,y in zip(a,b)):raise ValueError('invalid box')
    return one(cq.Solid.makeBox(*(y-x for x,y in zip(a,b)),cq.Vector(*a)))

def cylinder(r,z0,z1,x=0.,y=0.):
    if number(r)<=0 or number(z1)<=number(z0):raise ValueError('invalid cylinder')
    return one(cq.Solid.makeCylinder(r,z1-z0,cq.Vector(x,y,z0),cq.Vector(0,0,1)))


def capsule(a,b,r,z0,z1):
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
    if length<=0:raise ValueError('distinct capsule endpoints required')
    vx,vy=-dy*r/length,dx*r/length
    points=[cq.Vector(a[0]+vx,a[1]+vy,z0),cq.Vector(a[0]-vx,a[1]-vy,z0),
            cq.Vector(b[0]-vx,b[1]-vy,z0),cq.Vector(b[0]+vx,b[1]+vy,z0)]
    wire=cq.Wire.makePolygon(points,close=True)
    bridge=one(cq.Solid.extrudeLinear(wire,[],cq.Vector(0,0,z1-z0)))
    return one(bridge.fuse(cylinder(r,z0,z1,*a)).fuse(cylinder(r,z0,z1,*b)).clean())


def handed(body,side):
    if side not in ('L','R'):raise ValueError('invalid side')
    return body if side=='R' else body.mirror('YZ')


@lru_cache(maxsize=64)
def parent(role):
    gm=json.loads((SOURCE/'geometry-manifest.json').read_text());arc=SOURCE/gm['archive']
    if sha(arc)!=gm['archive_sha256']:raise ValueError('mounted source archive changed')
    entry=next((x for x in gm['files'] if x['path']==role+'.step'),None)
    if entry is None:raise ValueError('unknown parent role')
    with tarfile.open(arc,'r:gz') as t:raw=t.extractfile(entry['path']).read()
    if len(raw)!=entry['bytes'] or hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('parent STEP differs')
    with tempfile.TemporaryDirectory(prefix='coupling-parent-') as td:
        p=Path(td)/'part.step';p.write_bytes(raw);roots=cq.importers.importStep(str(p)).vals()
    if len(roots)!=1:raise ValueError('extra parent root')
    return one(roots[0])


@lru_cache(maxsize=1)
def templates():
    result={}
    a=(X0+RATIO*(Y_CAM-1.),1.);b=(X0+RATIO*(Y_CAM-82.25),82.25)
    cam=capsule(a,b,.95,4.5,4.8).cut(capsule(a,b,SLOT_RADIUS,4.4,4.9)).clean()
    # Closed finite second groove; a connected output arm reaches the original KEY.
    c=(X0-.75,Y_OUTPUT+.75);d=(X0+12.75,Y_OUTPUT-12.75)
    yoke=capsule(c,d,1.1,1.2,1.6).cut(capsule(c,d,SLOT_RADIUS,1.1,1.7)).clean()
    arm=box((10.8,39.,1.2),(11.4,72.6,1.6))
    post=box((14.2,39.,1.2),(14.8,39.6,4.35))
    tab=one(box((14.2,15.8,4.05),(14.8,39.6,4.35)).fuse(box((10.8,39.,1.2),(14.8,39.6,1.6))).fuse(post).clean())
    yoke=one(yoke.fuse(arm).fuse(tab).clean())
    # All telescopic tubes have bottom floors and retaining top lips. Nested
    # collars bound the relative offset to [0.1,2.9], not an equality schedule.
    stages=[]
    for outer,bore,throat,collar in [(1.4,1.2,1.05,None),(1.,.8,.65,1.15),(.6,.4,.25,.75)]:
        body=cylinder(outer,0,STAGE_LENGTH)
        body=one(body.cut(cylinder(bore,.1,STAGE_LENGTH-.1)).cut(cylinder(throat,STAGE_LENGTH-.1,STAGE_LENGTH+.1)).clean())
        if collar is not None:body=one(body.fuse(cylinder(collar,0,.2).cut(cylinder(bore,.1,.3))).clean())
        stages.append(body)
    top=one(cylinder(.2,0,STAGE_LENGTH).fuse(cylinder(.35,0,.2)).clean())
    top=one(top.fuse(cylinder(.4,3.15,4.0)).fuse(cylinder(.65,3.3,3.5)).fuse(cylinder(.65,3.8,4.)).clean())
    stages.append(top)
    cross=box((X0-1.4,77.2,2.05),(X0+1.4,84.3,2.45))
    follower=one(cylinder(.4,1.,2.1,X0,Y_OUTPUT).fuse(cylinder(.65,1.,1.2,X0,Y_OUTPUT)).fuse(cylinder(.65,1.6,1.8,X0,Y_OUTPUT)).clean())
    cross=one(cross.fuse(follower).fuse(stages[0].translate((X0,Y_CAM,.7))).clean())
    cross=one(cross.cut(cylinder(1.2,.8,3.8,X0,Y_CAM)).cut(cylinder(1.05,3.8,4.0,X0,Y_CAM)).clean())
    # A physically shaped linear guide, still NOT fastened to the existing shell.
    rails=[box((5.3,76.7,1.8),(21.2,77.1,2.8)),box((5.3,84.4,1.8),(21.2,84.8,2.8)),
           box((5.3,76.7,2.5),(21.2,77.5,2.8)),box((5.3,84.0,2.5),(21.2,84.8,2.8)),
           box((5.3,76.7,1.8),(5.7,84.8,2.8)),box((20.8,76.7,1.8),(21.2,84.8,2.8))]
    guide=rails[0]
    for index in (4,1,2,3,5):guide=one(guide.fuse(rails[index]).clean())
    for side in 'LR':
        result[side+'_B_CAM']=one(handed(cam,side))
        result[side+'_X_GUIDE']=one(handed(guide,side))
        result[side+'_CROSSHEAD']=one(handed(cross,side))
        old=parent(side+'_KEY');extension=one(handed(yoke,side))
        if n.common(old,extension)<=1e-7:raise ValueError('output arm detached from original KEY')
        result[side+'_KEY_YOKE']=one(old.fuse(extension).clean())
        result[side+'_ORIGINAL_KEY']=old
        for index in range(1,4):result[f'{side}_TELESCOPE_{index}']=stages[index]
    return result


def state(slide,descent=0.,*,offsets=None):
    p=pose(slide,descent);q=p['nominal_KEY_Y_mm'];j=p['nominal_joint_offsets_mm'] if offsets is None else stage_allocation(descent,offsets)
    t=templates();bodies={}
    for side in 'LR':
        sign=-1 if side=='L' else 1
        bodies[side+'_B_CAM']=t[side+'_B_CAM'].translate((0,slide,p['B_Z_mm']))
        bodies[side+'_X_GUIDE']=t[side+'_X_GUIDE']
        bodies[side+'_CROSSHEAD']=t[side+'_CROSSHEAD'].translate((sign*q,0,0))
        bodies[side+'_KEY_YOKE']=t[side+'_KEY_YOKE'].translate((0,q,0))
        for i in range(1,4):
            bodies[f'{side}_TELESCOPE_{i}']=t[f'{side}_TELESCOPE_{i}'].translate((sign*(X0+q),Y_CAM,.7+sum(j[:i])))
    return bodies,p


def generate(output):
    out=Path(output).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('new external output required')
    out.mkdir(parents=True,exist_ok=False);exports={}
    all_shapes=dict(templates())
    shells,shell_detail=housing_study()
    all_shapes.update({"STUDY_"+k:v for k,v in shells.items()})
    for role,body in all_shapes.items():
        f=out/(role+'.step');cq.exporters.export(body,str(f));b=body.BoundingBox()
        exports[role]={'path':f.name,'sha256':sha(f),'volume_mm3':vol(body),'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]}
    result={'base_main':BASE,'source_sha256':sha(__file__),'exports':exports,
            'groove_pin_radius_mm':PIN_RADIUS,'groove_radius_mm':SLOT_RADIUS,
            'stroke_ratio':RATIO,'joint_offset_limits_mm':[STAGE_MIN,STAGE_MAX],
            'nominal_head_compensation_mm':SEATING,'output_band_at_stow':output_band(0.),
            'output_band_at_open':output_band(STROKE),
            'real_parent_KEY_material_preserved':True,'prototype_shell_mounts_and_cutouts_implemented':True,
            'shell_material_and_joints':shell_detail,
            'PAWL_release_hold_and_endpoint_relock_implemented':False,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result


@lru_cache(maxsize=1)
def housing_study():
    """Fixed project-owned reliefs and supports; never cut around a run-time pose.
    All removed/added shell material is accounted. This does not authorize an
    OEM cut or qualify installation, preload, seals or structural strength.
    """
    frame0=parent('A_FRAME');panel0=parent('A_BACK_PANEL');b0=parent('B_SHELL')
    frame,panel,b=frame0,panel0,b0
    joins=[]
    for side in 'LR':
        # Fixed rear overlap-pocket and thin output-yoke channel.
        for lo,hi in [((5.,76.5,.65),(21.6,85.,3.95)),((5.,65.,1.15),(21.6,92.,1.65))]:
            frame=one(frame.cut(handed(box(lo,hi),side)).clean())
        guide=templates()[side+'_X_GUIDE']
        for x0,x1 in ((5.3,5.7),(20.8,21.2)):
            guide=one(guide.fuse(handed(box((x0,84.5,1.8),(x1,86.,2.8)),side)).clean())
        joint=n.common(frame,guide)
        if joint<=1e-7:raise ValueError('crosshead guide has no connection to A frame')
        frame=one(frame.fuse(guide).clean());joins.append({'side':side,'interface':'X guide to frame','overlap_mm3':joint})
        for y in (56.,62.):
            pieces=[box((10.5,y,.60),(11.7,y+2,1.15)),
                    box((10.5,y,1.1),(10.75,y+2,1.9)),box((11.45,y,1.1),(11.7,y+2,1.9)),
                    box((10.5,y,1.65),(11.7,y+2,1.9))]
            guide=pieces[0]
            for part in pieces[1:]:guide=one(guide.fuse(part).clean())
            guide=one(handed(guide,side));joint=n.common(panel,guide)
            if joint<=1e-7:raise ValueError('Y guide detached from back panel')
            panel=one(panel.fuse(guide).clean());joins.append({'side':side,'interface':'Y guide to panel','overlap_mm3':joint})
        cam=templates()[side+'_B_CAM'];joint=n.common(b,cam)
        if joint<=1e-7:raise ValueError('B cam plate lacks shell connection')
        b=one(b.fuse(cam).clean());joins.append({'side':side,'interface':'cam to B shell','overlap_mm3':joint})
        a=(X0+RATIO*(Y_CAM-1.),1.);end=(X0+RATIO*(Y_CAM-82.25),82.25)
        # Preserve the cam's neck walls but open finite lower/upper head channels.
        for radius,low,high in ((.675,-.05,4.5),(SLOT_RADIUS,4.5,4.8),(.675,4.8,5.05)):
            b=one(b.cut(handed(capsule(a,end,radius,low,high),side)).clean())
    changes={}
    for name,old,new in [('A_FRAME',frame0,frame),('A_BACK_PANEL',panel0,panel),('B_SHELL',b0,b)]:
        removed=vol(old.cut(new));added=vol(new.cut(old))
        if abs(vol(old)-removed+added-vol(new))>1e-7:raise ValueError('shell material accounting differs')
        changes[name]={'old_volume_mm3':vol(old),'removed_mm3':removed,'added_mm3':added,'new_volume_mm3':vol(new)}
    return {'A_FRAME':frame,'A_BACK_PANEL':panel,'B_SHELL':b}, {'joints':joins,'material':changes,
            'fixed_declared_reliefs_not_pose_adaptive':True,'new_shell_geometry_is_not_released':True,
            'cam_head_assembly_and_actual_threads_not_designed':True}


def phone_scene(slide,descent=0.):
    """Conditional nominal contact branch: PAWL is already parked by an unmodeled actuator.
    Preserved spring solids are maximum material envelopes, not simulated coils.
    """
    import gzip
    from cam_contact_profile import ContactProfile
    prototype,p=state(slide,descent);shells,detail=housing_study();q=p['nominal_KEY_Y_mm']
    gm=json.loads((SOURCE/'geometry-manifest.json').read_text())
    names={x['path'][:-5] for x in gm['files'] if x['path'].endswith('.step')}
    names={x for x in names if (x.startswith(('L_','R_')) and not x.endswith('PARENT_ROOT_INNER')) or x.startswith(('CARTRIDGE_','FRAME_'))}
    parts={x:parent(x) for x in names}
    receipt=json.loads(gzip.decompress((ROOT/'engineering/thin-mechanism-20261015/native-verification.json.gz').read_bytes()))
    for side in 'LR':
        sign=-1 if side=='L' else 1
        parts[side+'_KEY']=prototype.pop(side+'_KEY_YOKE')
        parts[side+'_PAWL']=parts[side+'_PAWL'].translate((0,0,1.1))
        prototype.pop(side+'_X_GUIDE');prototype.pop(side+'_B_CAM')
        for i in (0,1):
            rec=receipt['sides'][side]['contacts'][i]['profile']
            keys=('pin_radius','floor_height','floor_corner_q','ramp_slope','pin_q','lower_stop_height','q_max')
            profile=ContactProfile(**{k:rec[k] for k in keys});delta=profile.evaluate(q)[0]-profile.evaluate(0)[0]
            parts[f'{side}_STOP_{i}']=parts[f'{side}_STOP_{i}'].translate((sign*delta,0,0))
            role=f'{side}_SPRING_{i}_OD_TOL_ENVELOPE';old=parts[role];bb=old.BoundingBox()
            low=bb.xmin+min(0,sign*delta);high=bb.xmax+max(0,sign*delta)
            parts[role]=one(cq.Solid.makeCylinder(.43,high-low,cq.Vector(low,(bb.ymin+bb.ymax)/2,(bb.zmin+bb.zmax)/2),cq.Vector(1,0,0)))
    parts.update(prototype);parts['A_FRAME']=shells['A_FRAME'];parts['A_BACK_PANEL']=shells['A_BACK_PANEL']
    parts['B_SHELL']=shells['B_SHELL'].translate((0,slide,p['B_Z_mm']))
    return parts,p,detail

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=generate(a.output);print(json.dumps({'exports':len(r['exports']),'output_band_at_stow':r['output_band_at_stow']}))


