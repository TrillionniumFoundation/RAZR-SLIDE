"""Independent reconstruction and bounded-interface checks for relieved roots.

Complete box supersets cover the entire original PAWL and shoulder pin across
all nominal slot heights plus a specified rigid relative-error box. This is
not a full manufacturing-size tolerance, freely floating mechanism, load,
friction, fatigue or all-phone error proof. Full mode rechecks the real prior
79-part scene and affected assembly/moving-STOP paths with all new roots.
"""
from pathlib import Path
import argparse, hashlib, itertools, json, math, sys
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from verify_catalogue_roof_joint import read, vol, common, equal

TOL=1e-7
ROOT=Path(__file__).resolve().parents[1]
ERROR=(.03,.05,.02)
COVERS=(('body',(13.6,18.15,3.6),(16.6,22.15,6.2)),
        ('neck',(13.6,16.125,4.04),(14.1,18.15,4.36)),
        ('tongue',(14.1,16.05,4.1),(29.95,16.65,4.2)),
        ('socket',(12.2,19.35,4.65),(13.6,20.65,5.95)))


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def box(lo,hi):
    if len(lo)!=3 or len(hi)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in (*lo,*hi)) or any(y<=x for x,y in zip(lo,hi)):
        raise ValueError('invalid bounded region')
    return cq.Solid.makeBox(*(b-a for a,b in zip(lo,hi)),cq.Vector(*lo))

def hand(s,side):
    if side not in 'LR' or len(side)!=1:raise ValueError('invalid side')
    return s.mirror('YZ') if side=='L' else s

def single(s):
    if len(s.Solids())!=1 or not s.isValid() or vol(s)<=0:raise ValueError('not one complete connected positive solid')
    return s


def load_new(path):
    path=Path(path).resolve();m=json.loads(path.read_text());parts={};h={str(path):sha(path)}
    roles=('ROOF_SCREW_0_M1_NOMINAL','ROOF_SCREW_1_M1_NOMINAL','PAWL','SHOULDER_PIN_NOMINAL',
           'TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','ROOF','GUIDE_REFERENCE','ROOT_OUTER','ROOT_INNER')
    if set(m['exports'])!={s+'_'+k for s in 'LR' for k in roles}|{'A_BACK_PANEL'}:
        raise ValueError('missing or extra root-clearance participant')
    for key,r in m['exports'].items():
        rel=Path(r['path']);f=path.parent/rel
        if rel.parts!=(key+'.step',) or f.is_symlink() or sha(f)!=r['sha256']:raise ValueError('native file identity mismatch')
        vals=[r['volume_mm3'],*r['bounds_mm']]
        if len(vals)!=7 or any(type(v) not in (int,float) or not math.isfinite(v) for v in vals):raise ValueError('invalid finite certificate')
        roots=cq.importers.importStep(str(f)).vals()
        if len(roots)!=1:raise ValueError('extra native root')
        body=single(roots[0]);b=body.BoundingBox();actual=[vol(body),b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]
        if any(abs(a-b)>TOL for a,b in zip(vals,actual)):raise ValueError('certificate differs from actual solid')
        parts[key]=body;h[str(f)]=sha(f)
    return m,parts,h


def read_mount(path):
    path=Path(path).resolve();m=json.loads(path.read_text());p={};h={str(path):sha(path)}
    for side in 'LR':
        for role in ('ROOT_INNER','KEY'):
            key=side+'_'+role;r=m['exports'][key];f=path.parent/r['path']
            if Path(r['path']).parts!=(key+'.step',) or f.is_symlink() or sha(f)!=r['sha256']:raise ValueError('bad mounted source')
            vals=cq.importers.importStep(str(f)).vals()
            if len(vals)!=1:raise ValueError('extra mount root')
            p[key]=single(vals[0]);h[str(f)]=sha(f)
    return p,h


def reconstruct(old,side,outer):
    # Independent literal construction, not calls into the new generator.
    windows=[((13.5,18.05,3.5),(16.7,22.25,7.4)),((13.5,16.02,3.94),(14.25,18.25,5.60)),
             ((14.,15.95,4.),(30.07,16.75,5.42)),((12.10,19.25,4.57),(13.85,20.75,7.15))]
    body=old
    for lo,hi in windows:body=body.cut(hand(box(lo,hi),side)).clean()
    cut=body
    if outer:
        if len(cut.Solids())!=3:raise ValueError('cut-only disconnection witness changed')
        for x in (22.55,27.70):
            for lo,hi in [((x,15.35,4.95),(x+.4,15.70,5.82)),((x,15.35,5.48),(x+.4,17.60,5.82)),((x,17.15,4.95),(x+.4,17.60,5.82))]:
                body=body.fuse(hand(box(lo,hi),side)).clean()
    single(body)
    if vol(cut.cut(body))>TOL:raise ValueError('cut material discarded')
    return body,cut


def slot_range(tab):
    ends=set()
    for f in tab.Faces():
        if f.geomType()!='CYLINDER':continue
        c=BRepAdaptor_Surface(f.wrapped).Cylinder();d=c.Axis().Direction();p=c.Location()
        if abs(c.Radius()-.425)<TOL and abs(abs(d.X())-1)<TOL:ends.add((round(p.Y(),9),round(p.Z(),9)))
    if len(ends)!=2:raise ValueError('ambiguous actual slot ends')
    a,b=sorted(ends);slope=-(b[1]-a[1])/(b[0]-a[0]);origin=a[1]-(20-a[0])*slope-5.3
    if abs(slope-1.06/3)>TOL or abs(origin-.02)>TOL:raise ValueError('prior manual slot changed')
    h=.025*math.hypot(1,slope)
    return {'origin':origin,'slope':slope,'halfwidth':h,'lower':origin-h,'upper':origin+3*slope+h}


def error_envelopes(parts,slots,error=ERROR):
    if len(error)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in error):raise ValueError('invalid relative-error box')
    rows=[];cover_receipts=[]
    for side in 'LR':
        union=None
        for _,lo,hi in COVERS:
            b=hand(box(lo,hi),side);union=b if union is None else union.fuse(b).clean()
        uncovered=vol(parts[side+'_PAWL'].cut(union))
        pinbox=hand(box((10.8,19.35,4.65),(13.3,20.65,5.95)),side)
        pin_uncovered=vol(parts[side+'_SHOULDER_PIN_NOMINAL'].cut(pinbox))
        if max(uncovered,pin_uncovered)>TOL:raise ValueError('finite proof cover omits original moving material')
        cover_receipts.append({'side':side,'PAWL_uncovered_mm3':uncovered,'pin_uncovered_mm3':pin_uncovered})
        for name,lo,hi in (*COVERS,('pin',(10.8,19.35,4.65),(13.3,20.65,5.95))):
            a=[lo[i]-error[i]+(slots[side]['lower'] if i==2 else 0) for i in range(3)]
            b=[hi[i]+error[i]+(slots[side]['upper'] if i==2 else 0) for i in range(3)]
            region=hand(box(a,b),side)
            for role in ('ROOT_INNER','ROOT_OUTER'):
                root=parts[side+'_'+role];hit=common(region,root);gap=region.distance(root)
                if not math.isfinite(gap) or gap<0:raise ValueError('invalid distance')
                rows.append({'side':side,'cover':name,'root':role,'relative_error_xyz_mm':error,
                             'envelope_R_bounds':[a,b],'common_mm3':hit,'distance_mm':gap,
                             'clear':hit<=TOL and gap>.049})
    return {'whole_original_material_covered':cover_receipts,'rows':rows,
        'minimum_envelope_to_root_distance_mm':min(r['distance_mm'] for r in rows),
        'all_envelopes_clear':all(r['clear'] for r in rows),
        'complete_error_box_and_axial_interval_not_pose_samples':True,
        'scope':'relative rigid translation at this interface only; not feature sizes, free play, force, rotation or other parts'}


def verify(baseline,manifest,output,*,mount_manifest=None,full=False):
    output=Path(output)
    if output.exists():raise ValueError('new result required')
    _,base,h=read(baseline);meta,new,h2=load_new(manifest);h.update(h2)
    if meta['baseline_manifest_sha256']!=sha(baseline):raise ValueError('wrong baseline identity')
    scenes=[];full_checks={};old_sources={}
    if full:
        import verify_endpoint_joint_pawl as e
        parent,prior,old,profiles=e.v.parent_native(h)
        original_inner={s+'_ROOT_INNER':old[s+'_ROOT_INNER'] for s in 'LR'}
        keys={s:prior[s+'_KEY_YOKE'] for s in 'LR'}
    else:
        if mount_manifest is None:raise ValueError('subset mode requires exact mounted inputs')
        mounted,h2=read_mount(mount_manifest);h.update(h2);original_inner={s+'_ROOT_INNER':mounted[s+'_ROOT_INNER'] for s in 'LR'}
        keys={s:mounted[s+'_KEY'] for s in 'LR'}
    for name in set(base)-{'L_ROOT_OUTER','R_ROOT_OUTER'}:equal(base[name],new[name])
    materials=[]
    for side in 'LR':
        for role,is_outer in [('ROOT_OUTER',True),('ROOT_INNER',False)]:
            key=side+'_'+role;oldroot=base[key] if is_outer else original_inner[key]
            expected,cut=reconstruct(oldroot,side,is_outer);identity=equal(expected,new[key])
            loss=vol(oldroot.cut(new[key]));gain=vol(new[key].cut(oldroot))
            if abs(vol(oldroot)-loss+gain-vol(new[key]))>TOL:raise ValueError('material accounting mismatch')
            materials.append({'part':key,'removed_mm3':loss,'added_mm3':gain,'components_after_cuts':len(cut.Solids()),
                              'original_cut_fragments_retained_mm3':vol(cut),'cut_fragment_loss_mm3':vol(cut.cut(new[key])),
                              'reconstructed_material_difference_mm3':identity,'new_components':len(new[key].Solids())})
    slots={s:slot_range(new[s+'_TAB']) for s in 'LR'}
    envelopes=error_envelopes(new,slots)
    if not envelopes['all_envelopes_clear']:raise ValueError('bounded interface envelope rejected')
    old_witness=[];repaired=[]
    for side in 'LR':
        lift=slots[side]['origin']+slots[side]['halfwidth']
        for dy in (-.02,.02):
            moved=new[side+'_PAWL'].translate((0,dy,lift));before=common(moved,base[side+'_ROOT_OUTER']);after=common(moved,new[side+'_ROOT_OUTER'])
            if before<=TOL or after>TOL:raise ValueError('original process witness not reproduced/repaired')
            old_witness.append({'side':side,'dy_mm':dy,'before_mm3':before,'after_mm3':after})
    # Test the preserved contact interface under the bounded relative-translation
    # scenario. This is not a force model or a complete reachable-set proof.
    retention=[];keyhalf=.025*(math.hypot(1,12/79.75)+math.sqrt(2))
    for side in 'LR':
        for u in (0.,3.):
            for flank in (-1,1):
                for signs in itertools.product((-1,1),repeat=3):
                    err=tuple(s*x for s,x in zip(signs,ERROR));sp=slots[side]
                    z=sp['origin']+u*sp['slope']+flank*sp['halfwidth']+err[2]
                    pawl=new[side+'_PAWL'].translate((err[0],err[1],z));key=keys[side].translate((0,keyhalf+.3,0))
                    hit=common(pawl,key)
                    ok=hit>TOL if u==0 else hit<=TOL
                    retention.append({'side':side,'tab_mm':u,'slot_flank':flank,'error_xyz_mm':err,'common_mm3':hit,'expected':('block' if u==0 else 'release'),'passed':ok})
    if full:
        changed={s+'_'+k for s in 'LR' for k in ('ROOT_INNER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS')}
        for i,(slide,descent,tabs) in enumerate([(0.,0.,(0.,0.)),(0.,0.,(3.,3.)),(40.,0.,(3.,3.)),(79.75,8.2,(3.,3.))]):
            p=e.scene(base,parent,prior,old,profiles,slots,slide,descent,tabs)
            for side in 'LR':
                p[side+'_ROOT_INNER']=new[side+'_ROOT_INNER'];p[side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=new[side+'_ROOT_OUTER']
            pairs=e.v.w.pairs(p,None if i==0 else changed);bad=[r for r in pairs if r['common_mm3']>TOL]
            scenes.append({'slide_mm':slide,'descent_mm':descent,'tabs':tabs,'participants':len(p),'pairs':pairs,'bad':bad})
            print('SCENE',i,len(pairs),'BAD',bad,flush=True)
            if i==0:home=p
        # Complete STOP translation against the new ribs/root material.
        stop_paths=[]
        for side in 'LR':
            sign=-1 if side=='L' else 1
            for i in (0,1):
                profile=profiles[side][i];delta=profile.lower_stop_height-(profile.floor_height+profile.pin_radius)
                if delta>0:raise ValueError('unexpected STOP motion direction')
                gain=new[side+'_ROOT_OUTER'].cut(base[side+'_ROOT_OUTER'])
                supports={side+'_ADDED_SUPPORT_'+str(j):single(b) for j,b in enumerate(gain.Solids())}
                if not supports:raise ValueError('new support material omitted')
                stop_paths.append(e.v.motion(side+'_STOP_'+str(i)+'_AGAINST_ADDED_SUPPORT',old[f'{side}_STOP_{i}'],(sign*delta,0,0),supports))
        closures=[e.v.root_closure_check(new,s) for s in 'LR']
        detachable={s+'_'+k for s in 'LR' for k in e.v.INSERT_ROLES}
        installed={k:b for k,b in home.items() if k not in detachable|{'A_FRAME','B_SHELL'}};assembly=[]
        prev=e.frozen(h)
        for side in 'LR':
            for name,vec in e.v.plan(side):
                proof=e.roof_motion_partition(name,home[name],prev[name],vec,installed) if name.endswith('_ROOF') else e.v.motion(name,home[name],vec,installed)
                assembly.append(proof);installed[name]=home[name]
                print('INSERT',name,len(proof['failed']),flush=True)
        outside={k:e.v.vol(home[k].cut(old['A_OUTER'])) for k in changed}
        full_checks={'STOP_full_translation':stop_paths,'earlier_root_closure':closures,'assembly':assembly,'changed_root_outside_A_mm3':outside}
    if any(sha(f)!=v for f,v in h.items()):raise ValueError('input changed during independent readback')
    if 'root_clearance' in sys.modules:raise ValueError('candidate builder imported')
    failures={'retention':[r for r in retention if not r['passed']],
        'scenes':[r for r in scenes if r['bad']],
        'stop_paths':[r for r in full_checks.get('STOP_full_translation',[]) if r['failed']],
        'root_closure':[r for r in full_checks.get('earlier_root_closure',[]) if not r['result']['all_regions_clear']],
        'assembly':[r for r in full_checks.get('assembly',[]) if r['failed']],
        'outside_A':{k:v for k,v in full_checks.get('changed_root_outside_A_mm3',{}).items() if v>TOL}}
    result={'source_sha256':meta['source_sha256'],'reader_sha256':sha(__file__),'input_sha256':h,
        'native_templates':len(new),'scope':'full prior scene plus bounded root-interface proof' if full else 'isolated root/interface subset only',
        'unchanged_catalogue_templates':len(base)-2,'material':materials,'actual_slots':slots,
        'bounded_interface_envelopes':envelopes,'original_error_witnesses_and_repair':old_witness,
        'retention_release_corner_checks':retention,'scene_checks':scenes,'full_checks':full_checks,
        'failures':failures,'passed':not any(failures.values()),'candidate_builder_imported':False,'same_CAD_kernel':True,
        'relative_error_scenario_not_process_or_full_free_play_qualification':True,
        'new_support_strength_and_guidance_contact_preload_qualified':False,
        'actual_materials_threads_detents_electronics_not_qualified':True,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('RESULT',result['passed'],{k:len(v) for k,v in failures.items()},flush=True);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--mount-manifest',type=Path);p.add_argument('--full',action='store_true')
    a=p.parse_args();r=verify(a.baseline,a.manifest,a.output,mount_manifest=a.mount_manifest,full=a.full);raise SystemExit(0 if r['passed'] else 1)
