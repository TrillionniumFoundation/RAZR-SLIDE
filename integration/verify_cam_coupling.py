"""Builder-free native reimport of the finite transmission study (same CAD kernel).

Separate: groove-constrained output intervals; telescope joint limits; sampled
conditional whole assembly; missing PAWL actuation and unresolved relocking.
A reversible centerline trace is NOT a mechanically forced reverse trajectory.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import itertools
import json
import math
import sys
import tarfile
import tempfile
import cadquery as cq
import cam_contact_native as n
from cam_contact_profile import ContactProfile
from verify_contact_motion import PARTS

ROOT=Path(__file__).resolve().parents[1]
TOL=1e-7
K=12/79.75
R=.4
G=.425
X=7.25
YC=81.5
YO=77.5


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def vol(body):return n.whole_material(body,empty=True)[1]

def common(a,b):
    ab,bb=a.BoundingBox(),b.BoundingBox()
    if any(getattr(ab,k+'min')>getattr(bb,k+'max')+TOL or getattr(bb,k+'min')>getattr(ab,k+'max')+TOL for k in 'xyz'):return 0.
    value=vol(a.intersect(b))
    if value>min(vol(a),vol(b))+TOL:raise ValueError('impossible native common')
    return value


def cylinder(rad,z0,z1,x,y):
    return n.single(cq.Solid.makeCylinder(rad,z1-z0,cq.Vector(x,y,z0),cq.Vector(0,0,1)))


def equal(a,b):
    values=[vol(a.cut(b)),vol(b.cut(a))]
    if max(values)>TOL:raise ValueError('unaccounted native material difference')
    return values


def load(manifest):
    path=Path(manifest).resolve();r=json.loads(path.read_text());p={};hashes={str(path):sha(path)}
    expected={s+'_'+role for s in 'LR' for role in ('B_CAM','X_GUIDE','CROSSHEAD','KEY_YOKE','ORIGINAL_KEY','TELESCOPE_1','TELESCOPE_2','TELESCOPE_3')}
    expected|={'STUDY_A_FRAME','STUDY_A_BACK_PANEL','STUDY_B_SHELL'}
    if set(r['exports'])!=expected:raise ValueError('missing/extra coupling part')
    for role,rec in r['exports'].items():
        rel=Path(rec['path']);f=path.parent/rel
        if rel.is_absolute() or len(rel.parts)!=1 or rel.name!=role+'.step' or f.is_symlink():raise ValueError('invalid native filename')
        if sha(f)!=rec['sha256']:raise ValueError('changed native bytes')
        values=[rec['volume_mm3'],*rec['bounds_mm']]
        if len(values)!=7 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in values):raise ValueError('nonfinite native certificate')
        roots=cq.importers.importStep(str(f)).vals()
        if len(roots)!=1:raise ValueError('extra STEP root')
        body=n.single(roots[0]);b=body.BoundingBox();bb=[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]
        if abs(vol(body)-values[0])>TOL or any(abs(x-y)>TOL for x,y in zip(bb,values[1:])):raise ValueError('native certificate differs')
        p[role]=body;hashes[str(f)]=sha(f)
    return r,p,hashes


def source_parts(hashes):
    source=ROOT/'engineering/mounted-mechanism-20261015';mp=source/'geometry-manifest.json';m=json.loads(mp.read_text());arc=source/m['archive']
    if sha(arc)!=m['archive_sha256']:raise ValueError('parent archive differs')
    hashes[str(mp)]=sha(mp);hashes[str(arc)]=sha(arc)
    roles={s+'_'+k for s in 'LR' for k in PARTS}
    roles|={f'{family}_{i}_M1x3_NOMINAL' for family in ('CARTRIDGE','FRAME') for i in range(4)}
    roles|={'A_FRAME','A_BACK_PANEL','B_SHELL','A_OUTER','B_OUTER'}
    p={};entries={x['path']:x for x in m['files']}
    with tarfile.open(arc,'r:gz') as t,tempfile.TemporaryDirectory(prefix='coupling-independent-') as td:
        for role in sorted(roles):
            name=role+'.step';data=t.extractfile(name).read();rec=entries[name]
            if len(data)!=rec['bytes'] or hashlib.sha256(data).hexdigest()!=rec['sha256']:raise ValueError('parent part changed')
            f=Path(td)/name;f.write_bytes(data);roots=cq.importers.importStep(str(f)).vals()
            if len(roots)!=1:raise ValueError('extra parent root')
            p[role]=n.single(roots[0])
    return p


def native_slot(body,normal,probe):
    """Identify the two actual straight inner faces using their native planes."""
    direction=cq.Vector(*normal).normalized();probe=cq.Vector(*probe);faces=[]
    for f in body.Faces():
        if f.geomType()!='PLANE':continue
        nv=f.normalAt()
        if abs(abs(nv.dot(direction))-1)>1e-8:continue
        distance=abs(nv.dot(probe.sub(f.Center())))
        if abs(distance-G)<1e-7:
            faces.append({'normal':nv.toTuple(),'point':f.Center().toTuple(),'distance_mm':distance,'area_mm2':f.Area()})
    if len(faces)!=2:raise ValueError('two finite native groove walls not found')
    if cq.Vector(*faces[0]['normal']).dot(cq.Vector(*faces[1]['normal']))>-.999999:raise ValueError('groove walls not opposed')
    return faces


def prototype(p,s,d,offsets=None,dx=0.,dq=0.):
    q=K*s;z=8.2-d;j=[.1+z/3]*3 if offsets is None else list(offsets)
    if len(j)!=3 or any(v<.1-TOL or v>2.9+TOL for v in j) or abs(sum(j)-.3-z)>1e-7:raise ValueError('invalid telescope allocation')
    result={}
    for side in 'LR':
        sign=-1 if side=='L' else 1
        result[side+'_B_CAM']=p[side+'_B_CAM'].translate((0,s,z))
        result[side+'_X_GUIDE']=p[side+'_X_GUIDE']
        result[side+'_CROSSHEAD']=p[side+'_CROSSHEAD'].translate((sign*(q+dx),0,0))
        result[side+'_KEY_YOKE']=p[side+'_KEY_YOKE'].translate((0,q+dq,0))
        for i in range(1,4):result[f'{side}_TELESCOPE_{i}']=p[f'{side}_TELESCOPE_{i}'].translate((sign*(X+q+dx),YC,.7+sum(j[:i])))
    return result


def inspect_contacts(p):
    records=[];limits=[];planes={}
    for side in 'LR':
        sign=-1 if side=='L' else 1
        planes[side+'_cam']=native_slot(p[side+'_B_CAM'],(sign,K,0),(sign*(X+6),YC-79.75/2,4.65))
        planes[side+'_yoke']=native_slot(p[side+'_KEY_YOKE'],(sign,1,0),(sign*(X+6),YO-6,1.4))
        for s,d in ((0.,0.),(39.875,0.),(79.75,0.),(79.75,8.2)):
            q=K*s;ext=8.2-d
            for which,body,center,z0,z1,scale in (
                ('B_cam',p[side+'_B_CAM'].translate((0,s,ext)),(sign*(X+q),YC),4.52+ext,4.78+ext,math.hypot(1,K)),
                ('KEY_yoke',p[side+'_KEY_YOKE'].translate((0,q,0)),(sign*(X+q),YO),1.22,1.58,math.sqrt(2))):
                gap=cylinder(R,z0,z1,*center).distance(body)
                if abs(gap-(G-R))>1e-6:raise ValueError('nominal groove clearance differs')
                for flank in (-1,1):
                    x=center[0]+sign*flank*(G-R)*scale
                    pin=cylinder(R,z0,z1,x,center[1]);touch=pin.distance(body);hit=common(pin,body)
                    beyond=cylinder(R,z0,z1,x+sign*flank*.01,center[1]);penetration=common(beyond,body)
                    if touch>1e-6 or hit>TOL or penetration<=TOL:raise ValueError('native flank does not constrain the follower')
                    records.append({'side':side,'slide':s,'descent':d,'groove':which,'flank':flank,'touch_distance_mm':touch,'common_mm3':hit,'overtravel_01mm_common_mm3':penetration})
        for i in range(1,4):
            if i==1:
                parent=p[side+'_CROSSHEAD'];origin=(sign*X,YC,.7)
            else:
                parent=p[f'{side}_TELESCOPE_{i-1}'];origin=(0,0,0)
            for offset in (.1,2.9,.09,2.91):
                child=p[f'{side}_TELESCOPE_{i}'].translate((origin[0],origin[1],origin[2]+offset))
                v=common(parent,child);allowed=offset in (.1,2.9)
                if (allowed and v>TOL) or (not allowed and v<=TOL):raise ValueError('telescopic collar/floor limit not implemented')
                limits.append({'side':side,'joint':i,'offset_mm':offset,'common_mm3':v,'at_permitted_limit':allowed})
    return {'native_wall_planes':planes,'flank_tests':records,'joint_limit_tests':limits}


def scene(p,old,profiles,s,d):
    pr=prototype(p,s,d);q=K*s
    parts={s+'_'+k:old[s+'_'+k] for s in 'LR' for k in PARTS}
    parts.update({k:b for k,b in old.items() if k.startswith(('CARTRIDGE_','FRAME_'))})
    for side in 'LR':
        sign=-1 if side=='L' else 1
        parts[side+'_KEY']=pr.pop(side+'_KEY_YOKE');parts[side+'_PAWL']=parts[side+'_PAWL'].translate((0,0,1.1))
        pr.pop(side+'_B_CAM');pr.pop(side+'_X_GUIDE')
        for i in (0,1):
            profile=profiles[side][i];delta=profile.evaluate(q)[0]-profile.evaluate(0)[0]
            parts[f'{side}_STOP_{i}']=parts[f'{side}_STOP_{i}'].translate((sign*delta,0,0))
            name=f'{side}_SPRING_{i}_OD_TOL_ENVELOPE';b=old[name].BoundingBox()
            low=b.xmin+min(0,sign*delta);high=b.xmax+max(0,sign*delta)
            parts[name]=n.single(cq.Solid.makeCylinder(.43,high-low,cq.Vector(low,(b.ymin+b.ymax)/2,(b.zmin+b.zmax)/2),cq.Vector(1,0,0)))
    parts.update(pr);parts['A_FRAME']=p['STUDY_A_FRAME'];parts['A_BACK_PANEL']=p['STUDY_A_BACK_PANEL']
    parts['B_SHELL']=p['STUDY_B_SHELL'].translate((0,s,8.2-d))
    if len(parts)!=65:raise ValueError('conditional full scene participant count differs')
    return parts


def verify(manifest,output):
    output=Path(output)
    if output.exists():raise ValueError('new result required')
    r,p,hashes=load(manifest);old=source_parts(hashes)
    for side in 'LR':
        equal(old[side+'_KEY'],p[side+'_ORIGINAL_KEY'])
        if vol(old[side+'_KEY'].cut(p[side+'_KEY_YOKE']))>TOL:raise ValueError('original KEY was trimmed')
    profiles={};f=ROOT/'engineering/thin-mechanism-20261015/native-verification.json.gz'
    data=json.loads(gzip.decompress(f.read_bytes()));hashes[str(f)]=sha(f)
    fields=('pin_radius','floor_height','floor_corner_q','ramp_slope','pin_q','lower_stop_height','q_max')
    for side in 'LR':profiles[side]=[ContactProfile(**{k:v['profile'][k] for k in fields}) for v in data['sides'][side]['contacts']]
    arm_return_checks=[]
    half=(G-R)*(math.hypot(1,K)+math.sqrt(2))
    for side in 'LR':
        b=old[side+'_PAWL'].BoundingBox()
        sweep=n.single(cq.Solid.makeBox(b.xmax-b.xmin,b.ymax-b.ymin,b.zmax-b.zmin+1.1,cq.Vector(b.xmin,b.ymin,b.zmin)))
        added=p[side+'_KEY_YOKE'].cut(p[side+'_ORIGINAL_KEY'])
        for q in (0.,half,12.):
            value=common(added.translate((0,q,0)),sweep)
            if value>TOL:raise ValueError('new output arm blocks the complete PAWL return envelope')
            arm_return_checks.append({'side':side,'KEY_Y_mm':q,'added_arm_PAWL_sweep_common_mm3':value})
    contacts=inspect_contacts(p);print('CONTACTS',len(contacts['flank_tests']),'LIMITS',len(contacts['joint_limit_tests']),flush=True)
    allocations=[]
    for d,examples in ((0.,[(2.9,2.9,2.7),(2.7,2.9,2.9)]),(4.1,[(.1,1.4,2.9),(2.9,1.4,.1)]),(8.2,[(.1,.1,.1)])):
        for j in examples:
            bodies=prototype(p,79.75,d,j);bad=[]
            for a,b in itertools.combinations(bodies,2):
                v=common(bodies[a],bodies[b])
                if v>TOL:bad.append([a,b,v])
            allocations.append({'descent':d,'joint_offsets_mm':j,'positive_pairs':bad})
    trace=[(0.,0.),(.1,0.),(2.,0.),(5.,0.),(40.,0.),(79.75,0.),(79.75,4.1),(79.75,8.2)]
    rows=[];failed=[]
    for s,d in trace:
        parts=scene(p,old,profiles,s,d);pairs=[]
        for a,b in itertools.combinations(sorted(parts),2):
            v=common(parts[a],parts[b]);pairs.append({'a':a,'b':b,'common_mm3':v})
        bad=[v for v in pairs if v['common_mm3']>TOL]
        rows.append({'slide_mm':s,'normal_descent_mm':d,'KEY_centerline_Y_mm':K*s,'participants':65,'pairs':pairs,'positive_pairs':bad})
        failed.extend([{'slide':s,'descent':d,**v} for v in bad])
        print('NATIVE_POSE',s,d,'PAIRS',len(pairs),'BAD',bad,flush=True)
    # Material accounting is recomputed on actual shell bodies, not trusted from the manifest.
    changes={}
    for name in ('A_FRAME','A_BACK_PANEL','B_SHELL'):
        a,b=old[name],p['STUDY_'+name];lost,added=vol(a.cut(b)),vol(b.cut(a))
        if abs(vol(a)-lost+added-vol(b))>TOL:raise ValueError('shell material accounting mismatch')
        changes[name]={'removed_mm3':lost,'added_mm3':added}
    if any(sha(f)!=v for f,v in hashes.items()):raise ValueError('inputs changed during reimport')
    if 'cam_coupling' in sys.modules:raise ValueError('candidate generator imported')
    half=(G-R)*(math.hypot(1,K)+math.sqrt(2));allocation_failures=[x for x in allocations if x['positive_pairs']]
    result={'source_sha256':r['source_sha256'],'verifier_sha256':sha(__file__),'input_sha256':hashes,
            'native_STEP_files':len(p),'added_arm_return_checks':arm_return_checks,'contacts':contacts,'unequal_extension_trials':allocations,
            'conditional_whole_assembly_poses':rows,'shell_material_changes':changes,
            'unique_forward_pose_count':len(trace),'reverse_centerline_parameter_trace':list(reversed(trace)),
            'reverse_native_shapes_reused_by_exact_rigid_pose_not_recomputed':True,
            'whole_continuous_phone_clearance_proved':False,'centerline_is_not_unique_driven_output':True,
            'output_uncertainty_halfwidth_mm':half,'reversal_lost_motion_mm':2*half,
            'stow_output_band_mm':[-half,half],'open_output_band_mm':[12-half,12+half],
            'failure_pairs':failed,'passed':not failed and not allocation_failures,
            'nominal_pass_does_not_close_backlash_or_PAWL_sequence':True,
            'PAWL_already_parked_and_STOP_restoring_force_are_boundary_conditions':True,
            'telescopic_equal_split_not_required_but_not_all_allocations_native_sampled':True,
            'same_CAD_kernel':True,'candidate_builder_imported':False,
            'real_component_installation_and_lock_release_not_qualified':True,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print('RESULT',result['passed'],'RETURN_LOST_MOTION',2*half,flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=verify(a.manifest,a.output);raise SystemExit(0 if r['passed'] else 1)
