"""Independent native readback of revised slot and roof-joint geometry.

Original lower/upper root-collision witnesses remain negative controls. New
ideal-slot bounds are checked, not clamped to root stops. No thread strength,
full machining tolerance, friction, detent or automatic lock is certified.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
import tarfile
import tempfile
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
import verify_serviceable_pawl as v
from translation_regions import sum_common_upper_bound

ROOT=Path(__file__).resolve().parents[1]
TOL=1e-7


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen(h):
    folder=ROOT/'engineering/serviceable-pawl-20261015';gm=folder/'geometry-v2-manifest.json'
    meta=json.loads(gm.read_text());arc=folder/meta['archive'];mp=folder/'V2_NATIVE_MANIFEST.json'
    if sha(arc)!=meta['archive_sha256']:raise ValueError('prior serviceable archive changed')
    h.update({str(f):sha(f) for f in (gm,arc,mp)})
    with tempfile.TemporaryDirectory(prefix='endpoint-parent-') as td,tarfile.open(arc,'r:gz') as t:
        dest=Path(td);seen=set()
        for rec in meta['files']:
            rel=Path(rec['path'])
            if rel.is_absolute() or len(rel.parts)!=1 or str(rel) in seen:raise ValueError('unsafe or repeated prior member')
            seen.add(str(rel));member=t.getmember(str(rel))
            if not member.isfile():raise ValueError('nonregular native member')
            data=t.extractfile(member).read()
            if len(data)!=rec['bytes'] or hashlib.sha256(data).hexdigest()!=rec['sha256']:raise ValueError('prior member differs')
            (dest/rel).write_bytes(data)
        (dest/'manifest.json').write_bytes(mp.read_bytes());_,old,_=v.load(dest/'manifest.json')
    return old


def cylinders(body,radius,axis):
    result=[]
    for face in body.Faces():
        if face.geomType()!='CYLINDER':continue
        cylinder=BRepAdaptor_Surface(face.wrapped).Cylinder();direction=cylinder.Axis().Direction()
        direction=(direction.X(),direction.Y(),direction.Z())
        if abs(cylinder.Radius()-radius)>1e-7 or abs(abs(direction[axis])-1)>1e-7:continue
        p=cylinder.Location();b=face.BoundingBox()
        result.append({'origin':[p.X(),p.Y(),p.Z()],'low':[b.xmin,b.ymin,b.zmin],'high':[b.xmax,b.ymax,b.zmax]})
    return result


def native_slot(tab):
    faces=cylinders(tab,.425,0);centers=sorted({(round(r['origin'][1],9),round(r['origin'][2],9)) for r in faces})
    if len(centers)!=2:raise ValueError('exactly two finite native slot ends required')
    a,b=centers;slope=-(b[1]-a[1])/(b[0]-a[0]);origin=a[1]+(20.-a[0])*(-slope)-5.3
    if abs(slope-1.06/3)>1e-7 or abs(origin-.02)>1e-7:raise ValueError('native slot datum or rise differs')
    half=.025*math.hypot(1,slope)
    if a[0]+.025>=17. or b[0]-.025<=20.:raise ValueError('finite slot does not contain all requested working centers')
    return {'slope':slope,'origin':origin,'halfwidth':half,'end_centers_yz_mm':centers,
            'global_slot_only_bounds_mm':[origin-half,origin+3*slope+half],
            'finite_straight_flanks_within_retained_endcaps':True}


def roof_overlap(parts,side,index):
    x=(-1 if side=='L' else 1)*11.6;y=(14.5,29.6)[index]
    def axis_faces(name):
        return [r for r in cylinders(parts[name],.5,2) if abs(r['origin'][0]-x)<1e-7 and abs(r['origin'][1]-y)<1e-7]
    holes=axis_faces(side+'_ROOF');shanks=axis_faces(f'{side}_ROOF_SCREW_{index}_M1_NOMINAL')
    if len(holes)!=1 or len(shanks)!=1:raise ValueError('joint native bore/shank identity ambiguous')
    lo=max(holes[0]['low'][2],shanks[0]['low'][2]);hi=min(holes[0]['high'][2],shanks[0]['high'][2])
    if hi<=lo:raise ValueError('missing axial mating envelope')
    return {'side':side,'index':index,'lower_mm':lo,'upper_mm':hi,'nominal_axial_overlap_mm':hi-lo,
            'nominal_pitch_mm':.25,'equivalent_pitch_count_not_effective_threads':(hi-lo)/.25,
            'helical_threads_and_chamfer_runout_unmodeled':True}


def scene(new,parent,prior,old,profiles,slots,slide,descent,tabs,flanks=(0,0),key_offset=0.):
    p=v.scene(new,parent,prior,old,profiles,slide,descent,tabs)
    if key_offset:
        shifted=v.w.scene(parent,prior,old,profiles,slide,descent,tabs,key_offset=key_offset)
        for side in 'LR':
            for role in ('KEY','CROSSHEAD','STOP_0','STOP_1','SPRING_0_OD_TOL_ENVELOPE','SPRING_1_OD_TOL_ENVELOPE','TELESCOPE_1','TELESCOPE_2','TELESCOPE_3'):
                p[side+'_'+role]=shifted[side+'_'+role]
    for side,u,flank in zip('LR',tabs,flanks):
        s=slots[side];z=s['origin']+s['slope']*u+flank*s['halfwidth']
        for role in ('PAWL','SHOULDER_PIN_NOMINAL'):p[side+'_'+role]=new[side+'_'+role].translate((0,0,z))
    return p


def roof_motion_partition(label,body,base,vector,fixed):
    # This is an exact MATERIAL partition, not a sampled path or omitted part.
    if v.vol(base.cut(body))>TOL:raise ValueError('roof partition lost original material')
    added=body.cut(base);leaves=v.w.v.n.whole_material(added)[0]
    if len(leaves)!=2:raise ValueError('two complete added joint bosses required')
    rebuilt=base
    for part in leaves:rebuilt=rebuilt.fuse(part).clean()
    difference=v.w.v.equal(body,rebuilt)
    components=[v.motion(label+'_PART_'+str(i),part,vector,fixed) for i,part in enumerate([base,*leaves])]
    combined=[]
    for name in sorted(fixed):
        rows=[next(r for r in c['checks'] if r['fixed']==name) for c in components]
        values=[x for r in rows for x in r['common_mm3']]
        upper=sum_common_upper_bound(values)
        combined.append({'fixed':name,'method':'exact_whole_material_partition_then_complete_sweeps',
            'common_mm3':values,'common_upper_bound_mm3':upper,
            'common_upper_bound_is_sum_not_union_volume':True,'clear':upper<=TOL})
    return {'label':label,'translation_mm':vector,'partition_components':3,'whole_material_difference_mm3':difference,
            'component_proofs':components,'checks':combined,'failed':[x for x in combined if not x['clear']]}


def verify(manifest,output):
    output=Path(output)
    if output.exists():raise ValueError('new result path required')
    sources={str(Path(f).resolve()):sha(f) for f in (__file__,sum_common_upper_bound.__code__.co_filename)}
    meta,new,h=v.load(manifest);h.update(sources);prev=frozen(h);parent,prior,old,profiles=v.parent_native(h)
    changed_templates={'A_BACK_PANEL'}|{s+'_'+k for s in 'LR' for k in ('TAB','ROOF','GUIDE_REFERENCE')}
    for name in sorted(set(new)-changed_templates):v.w.v.equal(new[name],prev[name])
    slots={side:native_slot(new[side+'_TAB']) for side in 'LR'}
    material={name:{'removed_mm3':v.vol(prev[name].cut(new[name])),'added_mm3':v.vol(new[name].cut(prev[name]))} for name in sorted(changed_templates)}
    # Native joint overlap comparison, keeping the entire original screw exact.
    joints=[]
    for side in 'LR':
        for i,y in enumerate((14.5,29.6)):
            before=roof_overlap(prev,side,i);after=roof_overlap(new,side,i)
            if abs(before['nominal_axial_overlap_mm']-.25)>TOL or abs(after['nominal_axial_overlap_mm']-1.25)>TOL:raise ValueError('joint axial reservation differs')
            joints.append({'before':before,'after':after})
        # The new top joint is confined to four specific cylinder pockets/bosses.
        x=(-1 if side=='L' else 1)*11.6;expected=prev[side+'_ROOF'];expected_guide=prev[side+'_GUIDE_REFERENCE']
        for y in (14.5,29.6):
            outer=v.w.v.cylinder(.8,5.7,6.8,x,y);inner=v.w.v.cylinder(.5,5.6,7.1,x,y)
            expected=expected.fuse(outer.cut(inner)).clean()
            expected_guide=expected_guide.cut(v.w.v.cylinder(.85,5.65,6.8,x,y)).clean()
        v.w.v.equal(new[side+'_ROOF'],expected);v.w.v.equal(new[side+'_GUIDE_REFERENCE'],expected_guide)
    expected_panel=prev['A_BACK_PANEL']
    for side in 'LR':
        for y in (14.5,29.6):expected_panel=expected_panel.cut(v.w.v.cylinder(.85,5.65,6.8,(-1 if side=='L' else 1)*11.6,y)).clean()
    v.w.v.equal(new['A_BACK_PANEL'],expected_panel)
    changed={'A_BACK_PANEL'}|{s+'_'+k for s in 'LR' for k in ('PAWL','SHOULDER_PIN_NOMINAL','TAB','ROOF')}
    allrows=[];failed=[];keyhalf=(v.w.v.G-v.w.v.R)*(math.hypot(1,v.w.v.K)+math.sqrt(2))
    home=scene(new,parent,prior,old,profiles,slots,0.,0.,(0.,0.))
    initial=v.w.pairs(home);bad=[x for x in initial if x['common_mm3']>TOL];failed+=bad
    allrows.append({'name':'HOME','all_pairs':True,'pairs':initial,'bad':bad});print('HOME',len(initial),'BAD',bad,flush=True)
    for u in (0.,1.5,3.):
        for flank in (-1,1):
            p=scene(new,parent,prior,old,profiles,slots,0.,0.,(u,u),(flank,flank),keyhalf)
            rows=v.w.pairs(p,changed);bad=[x for x in rows if x['common_mm3']>TOL];failed+=bad
            allrows.append({'name':'COMBINED_SLOT_EXTREME','tab_mm':u,'flank':flank,'KEY_positive_play_mm':keyhalf,'pairs':rows,'bad':bad});print('SLOT',u,flank,'BAD',bad,flush=True)
    for slide,descent in ((5.,0.),(40.,0.),(79.75,0.),(79.75,8.2)):
        for flank in (-1,1):
            p=scene(new,parent,prior,old,profiles,slots,slide,descent,(3.,3.),(flank,flank))
            rows=v.w.pairs(p,changed);bad=[x for x in rows if x['common_mm3']>TOL];failed+=bad
            allrows.append({'name':'RELEASED_SLOT_EXTREME','slide':slide,'descent':descent,'flank':flank,'pairs':rows,'bad':bad});print('RELEASE',slide,descent,flank,'BAD',bad,flush=True)
    # Continuous full axial envelope for each PAWL/socket/pin, not three samples.
    motion=[]
    for side in 'LR':
        lower,upper=slots[side]['global_slot_only_bounds_mm']
        fixed={k:b for k,b in home.items() if k not in {side+'_PAWL',side+'_SHOULDER_PIN_NOMINAL',side+'_TAB','A_FRAME','B_SHELL'}}
        for role in ('PAWL','SHOULDER_PIN_NOMINAL'):
            body=new[side+'_'+role].translate((0,0,lower))
            motion.append(v.motion(side+'_'+role+'_FULL_SLOT_RANGE',body,(0,0,upper-lower),fixed))
    # Preserve real obstruction of the unmodified parent at its old slot extremes.
    negatives=[]
    previous_half=.025*math.hypot(1,1.1/3.)
    for side in 'LR':
        for name,z,root in [('LOWER',-previous_half,old[side+'_ROOT_INNER']),('UPPER',1.1+previous_half,prev[side+'_ROOT_OUTER'])]:
            hit=v.common(prev[side+'_PAWL'].translate((0,0,z)),root)
            if hit<=TOL:raise ValueError('prior endpoint failure not reproduced')
            negatives.append({'side':side,'old_endpoint':name,'PAWL_shift_mm':z,'common_mm3':hit})
    # Counterforce witness at closed state versus released state, not load rating.
    retention=[]
    for side in 'LR':
        for u in (0.,3.):
            for flank in (-1,1):
                spec=slots[side];lift=spec['origin']+spec['slope']*u+flank*spec['halfwidth']
                hit=v.common(prior[side+'_KEY_YOKE'].translate((0,keyhalf+.3,0)),new[side+'_PAWL'].translate((0,0,lift)))
                if (u==0 and hit<=TOL) or (u==3 and hit>TOL):raise ValueError('new slot loses closed obstruction or release')
                retention.append({'side':side,'tab':u,'flank':flank,'KEY_offset_plus_attempt_mm':keyhalf+.3,'common_mm3':hit})
    # The same fourteen body-insertion steps are rechecked against changed roof/pockets.
    detachable={s+'_'+k for s in 'LR' for k in v.INSERT_ROLES}
    installed={k:b for k,b in home.items() if k not in detachable|{'A_FRAME','B_SHELL'}};assembly=[]
    for side in 'LR':
        for role,withdrawal in v.plan(side):
            check=roof_motion_partition(role,home[role],prev[role],withdrawal,installed) if role.endswith('_ROOF') else v.motion(role,home[role],withdrawal,installed)
            assembly.append(check);installed[role]=home[role]
            print('INSERT',role,'BAD',len(check['failed']),flush=True)
    # Shoulder tools follow the revised closed PAWL datum; other tools are unchanged.
    tools=[]
    for side in 'LR':
        z=slots[side]['origin'];blade=v.box((.8,19.92,4.85+z),(10.89,20.08,5.75+z))
        if side=='L':blade=blade.mirror('YZ')
        targets=[(side+'_SHOULDER_PIN_NOMINAL',blade)];x=(-1 if side=='L' else 1)*11.6
        for role,y,width in [('PAD_SCREW_M06_NOMINAL',24.5,.40),('ROOF_SCREW_0_M1_NOMINAL',14.5,.65),('ROOF_SCREW_1_M1_NOMINAL',29.6,.65)]:
            targets.append((side+'_'+role,v.box((x-width,y-.08,-10.),(x+width,y+.08,.19))))
        for name,blade in targets:
            checks=[{'fixed':k,'common_mm3':v.common(blade,b)} for k,b in installed.items()]
            tools.append({'target':name,'checks':checks,'failed':[x for x in checks if x['common_mm3']>TOL]})
    closure=[v.motion('FRAME_CLOSE_'+name,home[name],(0,0,-20.),{'A_FRAME':home['A_FRAME']}) for name in sorted(changed)]
    outside={k:v.vol(home[k].cut(old['A_OUTER'])) for k in changed}
    failures={'scene':failed,'full_axial_slot_envelope':[x for x in motion if x['failed']],
              'assembly':[x for x in assembly if x['failed']],'tools':[x for x in tools if x['failed']],
              'frame_closure':[x for x in closure if x['failed']],'outside_A':{k:x for k,x in outside.items() if x>TOL}}
    if any(sha(f)!=x for f,x in h.items()):raise ValueError('input bytes changed during test')
    if any(k in sys.modules for k in ('endpoint_joint_pawl','serviceable_pawl','pawl_actuator','cam_coupling')):raise ValueError('candidate generator imported')
    result={'source_sha256':meta['source_sha256'],'reader_sha256':sha(__file__),'input_sha256':h,'native_templates':len(new),'unchanged_template_count':len(new)-len(changed_templates),'native_slots':slots,'native_joint_overlaps':joints,'material':material,'scene_checks':allrows,'full_axial_slot_envelopes':motion,'old_negative_controls':negatives,'retention_release_checks':retention,'assembly_stages':assembly,'tool_checks':tools,'frame_closure':closure,'failures':failures,'passed':not any(failures.values()),'same_CAD_kernel':True,'candidate_builder_imported':False,
            'scope':'selected ideal slot clearance extremes and full PAWL axial range, deeper nominal joint reservation; not full manufacturing tolerances or forced motion',
            'negative_KEY_play_branch_not_extended':True,'no_guide_lateral_play_thermal_deflection_or_preload_proof':True,
            'thread_material_grade_torque_fatigue_pullout_qualified':False,'automatic_return_detent_or_OPEN_lock_implemented':False,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('ENDPOINT_JOINT_RESULT',result['passed'],{k:len(x) for k,x in failures.items()},flush=True);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=verify(a.manifest,a.output);raise SystemExit(0 if r['passed'] else 1)
