"""Independent nominal nut-seat verification; threads remain specified, not solved.

Keeps every original physical participant and adds four nuts. Checks actual
frame shoulders, finite nut antirotation, pre-B assembly, changed interfaces,
and selected rigid deck paths. Smooth bore CAD cannot prove screw/nut axial
engagement: that missing geometry is kept as an explicit negative control.
"""
from pathlib import Path
import argparse,json,math,sys
import cadquery as cq
import verify_panel_shear_key as p
v=p.v
e=p.e
TOL=v.TOL
ROOT=Path(__file__).resolve().parents[1]
CENTERS=((-34.8,50.),(34.8,50.),(-34.8,70.),(34.8,70.))


def cyl(r,z0,z1,x,y):return v.single(cq.Solid.makeCylinder(r,z1-z0,cq.Vector(x,y,z0)))


def hexagon(af,z0,z1,x,y):
    # Literal vertex construction independent of candidate generator.
    a=af/(2*math.sqrt(3));b=af/2
    vertices=[(x+2*a,y),(x+a,y+b),(x-a,y+b),(x-2*a,y),(x-a,y-b),(x+a,y-b)]
    return v.single(cq.Workplane('XY',origin=(0,0,z0)).polyline(vertices).close().extrude(z1-z0).val())


def load(manifest,base):
    path=Path(manifest).resolve();m=json.loads(path.read_text());h={str(path):v.sha(path)};new={}
    expected=set(base)|{'A_FRAME'}|{f'FRAME_{i}_{role}' for i in range(4) for role in ('M1x3_NOMINAL','NUT_SHNS_M1_NOMINAL')}
    if set(m['exports'])!=expected:raise ValueError('missing/extra native participant')
    for name,row in m['exports'].items():
        rel=Path(row['path']);f=path.parent/rel
        if rel.is_absolute() or len(rel.parts)!=1 or rel.name!=name+'.step' or f.is_symlink():raise ValueError('invalid native path')
        if v.sha(f)!=row['sha256']:raise ValueError('native bytes differ')
        values=[row['volume_mm3'],*row['bounds_mm']]
        if len(values)!=7 or any(type(x) not in (int,float) or not math.isfinite(x) for x in values):raise ValueError('invalid native size record')
        roots=cq.importers.importStep(str(f)).vals()
        if len(roots)!=1:raise ValueError('extra STEP roots')
        body=v.single(roots[0]);b=body.BoundingBox();bounds=[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]
        if abs(v.vol(body)-values[0])>TOL or max(abs(a-b) for a,b in zip(bounds,values[1:]))>TOL:raise ValueError('native shape record differs')
        h[str(f)]=v.sha(f);new[name]=body
    return m,new,h


def scene(new,base,parent,prior,old,profiles,slots,args,dx=0.):
    if type(dx) not in (int,float) or not math.isfinite(dx) or abs(dx)>.020000001:raise ValueError('only declared deck X family')
    state=p.w.scene(base,parent,prior,old,profiles,slots,*args)
    moving,fixed=p.shift_deck(state,dx);fixed['A_FRAME']=new['A_FRAME']
    for i in range(4):
        for role in ('M1x3_NOMINAL','NUT_SHNS_M1_NOMINAL'):
            k=f'FRAME_{i}_{role}';fixed[k]=new[k]
    whole={**moving,**fixed}
    if len(moving)!=73 or len(fixed)!=10 or len(whole)!=83:raise ValueError('incomplete83-part assembly')
    return whole,moving,fixed


def check_rows(rows):return [r for r in rows if r['common_mm3']>TOL]


def nut_route_cages(x,y):
    # Back-panel aperture -> inside cavity above boss -> into seat.
    # Bare frame and already placed nuts only; no hidden through-front opening.
    x0=31. if x>0 else -31.
    return [hexagon(2.5,-5.,5.3,x0,y),
            v.box((min(x0,x)-2.5/math.sqrt(3),y-1.25,4.5),(max(x0,x)+2.5/math.sqrt(3),y+1.25,5.3)),
            hexagon(2.5,2.55,5.3,x,y)]


def verify(baseline,manifest,output,*,full=False):
    output=Path(output)
    if output.exists():raise ValueError('new report path required')
    bm,base,h=p.w.w.w.load_new(baseline);meta,new,h2=load(manifest,base);h.update(h2)
    if meta['baseline_manifest_sha256']!=v.sha(baseline) or bm['source_sha256']!=v.sha(ROOT/'integration/panel_shear_key.py'):raise ValueError('wrong native/source baseline')
    parent,prior,old,profiles=e.v.parent_native(h);slots={s:e.native_slot(base[s+'_TAB']) for s in 'LR'}
    oldscene=p.w.scene(base,parent,prior,old,profiles,slots);original_frame=oldscene['A_FRAME'];expected=original_frame
    for name in base:v.equal(base[name],new[name])
    for i,(x,y) in enumerate(CENTERS):
        expected=expected.cut(hexagon(2.56,2.55,4.4,x,y)).cut(cyl(.55,1.1,4.4,x,y)).clean()
        name=f'FRAME_{i}_NUT_SHNS_M1_NOMINAL'
        v.equal(new[name],hexagon(2.5,2.55,3.35,x,y).cut(cyl(.5,2.4,3.5,x,y)))
        v.equal(new[f'FRAME_{i}_M1x3_NOMINAL'],oldscene[f'FRAME_{i}_M1x3_NOMINAL'])
    v.equal(new['A_FRAME'],expected);frame=new['A_FRAME']
    loss=v.vol(original_frame.cut(frame));gain=v.vol(frame.cut(original_frame))
    if gain>TOL or abs(v.vol(original_frame)-loss-v.vol(frame))>TOL:raise ValueError('frame material changed outside declared pockets')
    contacts=[];motion=[];thread_negatives=[]
    for i,(x,y) in enumerate(CENTERS):
        name=f'FRAME_{i}_NUT_SHNS_M1_NOMINAL';nut=new[name];screw=new[f'FRAME_{i}_M1x3_NOMINAL']
        seat=p.w.planar_contacts(nut,{'A_FRAME':frame})
        bottom=[r for r in seat if r['normal_into_cover'][2]>.999999]
        if not bottom or sum(r['area_mm2'] for r in bottom)<4.4:raise ValueError('finite nut bearing shoulder missing')
        old_hit=v.common(nut,original_frame);hit=v.common(nut,frame);down=v.common(nut.translate((0,0,-.01)),frame)
        if old_hit<=TOL or hit>TOL or down<=TOL:raise ValueError('seat does not reject old body and prevent downward nut passage')
        rotations=[]
        for angle in (-5.,5.):
            value=v.common(nut.rotate((x,y,0),(x,y,1),angle),frame)
            if value<=TOL:raise ValueError('finite antirotation witness missing')
            rotations.append({'angle_degrees':angle,'common_mm3':value})
        contacts.append({'index':i,'old_unpocketed_nut_common_mm3':old_hit,'installed_nut_frame_common_mm3':hit,'downward_0p01mm_common_mm3':down,'bearing_patches':bottom,'rotation_obstructions':rotations})
        # Screw extraction through a smooth bore MUST remain unqualified. It is
        # intentionally not treated as a native axial-retention pass.
        reverse_screw=v.single(cyl(.5,.45,3.55,x,y).fuse(cyl(.9,0.,.55,x,y)).clean())
        missing=v.common(reverse_screw,nut)
        if missing>TOL:raise ValueError('unexpected collision in documented smooth-bore omission')
        thread_negatives.append({'index':i,'pure_screw_axial_extraction_0p1mm_vs_smooth_nut_mm3':missing,'native_thread_retention_proved':False,'requires_actual_M1x0p25_thread_engagement':True})
        # Exact union of the hexagonal nut translated vertically; hole filled
        # only for the insertion cage, before the screw is installed.
        straight=hexagon(2.5,2.55,11.35,x,y)
        old_path=v.common(straight,frame)
        actual_hit=v.common(nut.translate((0,0,4.8)),frame)
        if old_path<=TOL or actual_hit<=TOL:raise ValueError('front-skin insertion negative witness lost')
        values=[v.common(cage,frame) for cage in nut_route_cages(x,y)]
        if any(value>TOL for value in values):raise ValueError('bare-frame dogleg nut insertion obstructed')
        motion.append({'index':i,'rejected_straight8mm_enclosure_common_mm3':old_path,
                       'rejected_actual_nut_at_z7p35_common_mm3':actual_hit,
                       'bare_frame_three_segment_common_mm3':values,'all_segments_complete_supersets':True})
    print('NUT_SEATS',len(contacts),'THREAD_OMISSION_NEGATIVES',len(thread_negatives),flush=True)
    failures=[];integration={}
    home,_,_=scene(new,base,parent,prior,old,profiles,slots,(0.,0.,0.,0.,0.))
    if full:
        states=[];shifts=[];selected={'A_FRAME'}|{f'FRAME_{i}_NUT_SHNS_M1_NOMINAL' for i in range(4)}
        cases=[(s,d,u,c,z) for s,d,u in ((0.,0.,0.),(0.,0.,3.),(40.,0.,3.),(79.75,8.2,3.)) for c,z in ((0.,0.),(.02,.07))]
        for index,args in enumerate(cases):
            whole,_,_=scene(new,base,parent,prior,old,profiles,slots,args)
            rows=e.v.w.pairs(whole,None if index==0 else selected);bad=check_rows(rows);failures+=bad
            states.append({'args':args,'participants':83,'pairs':rows,'bad':bad});print('STATE',index,len(rows),'BAD',bad,flush=True)
            for dx in (-.02,.02):
                whole,moving,fixed=scene(new,base,parent,prior,old,profiles,slots,args,dx)
                rows=p.cross_pairs(moving,fixed);bad=check_rows(rows);failures+=bad
                shifts.append({'state':index,'dx':dx,'moving':73,'fixed':10,'pairs':rows,'bad':bad});print('DECK',index,dx,'BAD',bad,flush=True)
        # Frame and loose nuts preassembled with B removed. Nuts inserted first;
        # then the unchanged nominal screws enter from the rear. Actual helical
        # engagement is prescribed by the catalogue interface, not this cage.
        nuts={f'FRAME_{i}_NUT_SHNS_M1_NOMINAL' for i in range(4)};screws={f'FRAME_{i}_M1x3_NOMINAL' for i in range(4)}
        installed={'A_FRAME':frame};assembly=[]
        for i,(x,y) in enumerate(CENTERS):
            name=f'FRAME_{i}_NUT_SHNS_M1_NOMINAL'
            for segment,cage in enumerate(nut_route_cages(x,y)):
                rows=[{'fixed':k,'common_mm3':v.common(cage,b)} for k,b in installed.items()];bad=check_rows(rows);failures+=bad
                assembly.append({'name':name,'segment':segment,'method':'complete_bare_frame_dogleg_superset','checks':rows,'failed':bad})
                print('NUT_INSERT',i,segment,'BAD',bad,flush=True)
            installed[name]=home[name]
        # Joint screw approach is a separate verified assembly stage, conditional
        # on the inherited deck being installed; no whole-deck admission claimed.
        installed={k:b for k,b in home.items() if k not in screws|{'B_SHELL'}}
        for i,(x,y) in enumerate(CENTERS):
            name=f'FRAME_{i}_M1x3_NOMINAL'
            cage=v.single(cyl(.5,-7.45,3.55,x,y).fuse(cyl(.9,-7.9,.55,x,y)).clean())
            rows=[{'fixed':k,'common_mm3':v.common(cage,b)} for k,b in installed.items()];bad=check_rows(rows);failures+=bad
            assembly.append({'name':name,'method':'complete_nominal_head_shank_rear8mm_translation_envelope_NOT_thread_insertion','checks':rows,'failed':bad});installed[name]=home[name]
            print('SCREW_APPROACH',i,'BAD',bad,flush=True)
        # Added nuts are inside the old frame material; prove this explicitly.
        # It allows inherited paths avoiding the entire old frame to be reused
        # only where their original motion/anchor conditions remain identical.
        envelope_containment={k:v.vol(home[k].cut(original_frame)) for k in nuts}
        if any(x>TOL for x in envelope_containment.values()):failures.append({'new_nut_outside_old_frame':envelope_containment})
        paths=[]
        for index in (0,7):
            _,moving,fixed=scene(new,base,parent,prior,old,profiles,slots,cases[index],-.02)
            for name,body in moving.items():
                if name=='A_BACK_PANEL':
                    core={k:b for k,b in fixed.items() if k not in nuts};row=p.panel_motion_with_exact_screw_voids(body,(.04,0,0),core)
                    # Nuts' entire X sweep stays high above the panel: exact hex
                    # prisms translated along X are conservatively boxed here.
                    for nutname in nuts:
                        b=fixed[nutname].BoundingBox();cage=v.box((b.xmin-.04,b.ymin,b.zmin),(b.xmax,b.ymax,b.zmax));hit=v.common(body,cage)
                        item={'fixed':nutname,'common_mm3':[hit],'clear':hit<=TOL,'method':'complete_inverse_nut_box_superset'};row['checks'].append(item)
                        if hit>TOL:row['failed'].append(item)
                else:row=e.v.motion(name,body,(.04,0,0),fixed)
                failures+=row['failed'];paths.append(row)
            print('WHOLE_X',index,'FAILED',sum(len(x['failed']) for x in paths),flush=True)
        integration={'states':states,'deck_shifts':shifts,'pre_B_nut_and_screw_approach':assembly,'nuts_inside_old_frame_mm3':envelope_containment,'whole_deck_X_paths':paths,'old_control_and_complete_upstream_assembly_not_rerun':True,'nut_installation_before_backpanel_and_B':True,'temporary_nut_retention_until_screw_engagement_required':True}
    if v.vol(frame.cut(old['A_OUTER']))>TOL:raise ValueError('modified frame outside old outer')
    if any(v.sha(f)!=value for f,value in h.items()):raise ValueError('source inputs changed during verification')
    if 'frame_nut_anchor' in sys.modules:raise ValueError('candidate builder imported')
    result={'source_sha256':meta['source_sha256'],'reader_sha256':v.sha(__file__),'input_sha256':h,'templates':34,'physical_parts':83,'original25_templates_unchanged':True,'frame_material_removed_mm3':loss,'frame_material_added_mm3':gain,
            'seat_contacts':contacts,'frame_only_nut_paths':motion,'smooth_bore_thread_omission':thread_negatives,'integration':integration,'failure_pairs':failures,'passed':not failures,
            'scope':'nominal catalogue nut seats and explicit assembly paths, NOT helical thread retention or full product release',
            'screw_nut_thread_connection_specified_not_native_verified':True,'actual_torque_preload_thread_capacity_and_frame_strength_qualified':False,'unfastened_nut_upward_capture':False,'frame_held_fixed':True,'same_CAD_kernel':True,'candidate_builder_imported':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('FRAME_NUT_RESULT',result['passed'],flush=True);return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--full',action='store_true')
    a=ap.parse_args();r=verify(a.baseline,a.manifest,a.output,full=a.full);raise SystemExit(0 if r['passed'] else 1)
