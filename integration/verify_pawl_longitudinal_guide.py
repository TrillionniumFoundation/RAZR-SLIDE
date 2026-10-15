"""Independent body-first Y guide readback with slot-coupled translation.

A bounded first-order guide model is NOT finite-rotation capture or active
force closure. Full mode reuses the existing frozen 79-part replay/assembly
machinery; subset mode never claims those results. All old collar collisions
are retained as negative witnesses. No candidate generator is imported.
"""
from pathlib import Path
import argparse,itertools,json,math,sys
import numpy as np
from scipy.optimize import linprog
import cadquery as cq
import verify_pawl_lateral_guide as v

TOL=v.TOL
Y_GAP=.08
X_GAP=.05


def capsule_x(x0,x1,y,z0,z1,radius):
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in (x0,x1,y,z0,z1,radius)) or x1<=x0 or z1<=z0 or radius<=0:
        raise ValueError('invalid axial capsule')
    a=cq.Solid.makeCylinder(radius,x1-x0,cq.Vector(x0,y,z0),cq.Vector(1,0,0))
    b=cq.Solid.makeCylinder(radius,x1-x0,cq.Vector(x0,y,z1),cq.Vector(1,0,0))
    return v.v.single(a.fuse(b).fuse(v.v.box((x0,y-radius,z0),(x1,y+radius,z1))).clean())


def reconstruct(base):
    p=dict(base);panel=base['A_BACK_PANEL'];tools={}
    for side in 'LR':
        root=base[side+'_ROOT_OUTER']
        for lo,hi in [((14.4,17.85,4.5),(16.3,18.07,7.3)),((14.4,22.23,4.5),(16.3,22.45,7.3))]:
            root=root.fuse(v.v.hand(v.v.box(lo,hi),side)).clean()
        p[side+'_ROOT_OUTER']=v.v.single(root)
        tools[side]=[v.v.hand(capsule_x(a,b,20.,5.3,6.4,.78),side) for a,b in [(10.70,11.055),(12.145,12.50)]]
        for role in ('ROOF','GUIDE_REFERENCE'):
            body=base[side+'_'+role]
            for tool in tools[side]:body=body.cut(tool).clean()
            p[side+'_'+role]=v.v.single(body)
        for tool in tools[side]:panel=panel.cut(tool).clean()
    p['A_BACK_PANEL']=v.v.single(panel)
    return p,tools


def y_faces(root,side):
    shape=root if side=='R' else root.mirror('YZ');rows=[]
    for y,ny in [(18.07,1.),(22.23,-1.)]:
        found=[]
        for i,face in enumerate(shape.Faces()):
            if face.geomType()!='PLANE':continue
            b=face.BoundingBox();n=face.normalAt()
            vals=(b.ymin-y,b.ymax-y,b.xmin-14.4,b.xmax-16.3,b.zmin-4.5,b.zmax-7.3,n.x,n.y-ny,n.z)
            if max(abs(q) for q in vals)<=1e-6:found.append((i,face))
        if len(found)!=1:raise ValueError('complete finite native Y bearing face absent')
        i,f=found[0];rows.append({'face_index':i,'y_mm':y,'normal_Y':ny,'X_mm':[14.4,16.3],'Z_mm':[4.5,7.3],'area_mm2':f.Area()})
    return rows


def first_order_bounds(matrix,gaps):
    A=np.asarray(matrix,dtype=float);b=np.asarray(gaps,dtype=float)
    if A.ndim!=2 or A.shape[1]!=6 or b.shape!=(A.shape[0],) or not np.all(np.isfinite(A)) or not np.all(np.isfinite(b)) or np.any(b<0):
        raise ValueError('finite six-column guide inequalities required')
    axes=[0,1,3,4,5];reduced=A[:,axes];results=[]
    for i in range(5):
        unit=np.zeros(5);unit[i]=1
        low=linprog(unit,A_ub=reduced,b_ub=b,bounds=[(None,None)]*5,method='highs')
        high=linprog(-unit,A_ub=reduced,b_ub=b,bounds=[(None,None)]*5,method='highs')
        if low.status==3 or high.status==3:
            results.append({'axis':axes[i],'status':'unbounded','lower_status':low.status,'upper_status':high.status});continue
        if not low.success or not high.success:raise ValueError('guide LP did not solve')
        if max(np.max(reduced@low.x-b),np.max(reduced@high.x-b))>1e-8:raise ValueError('LP residual invalid')
        results.append({'axis':axes[i],'status':'bounded_first_order_only','lower':float(low.fun),'upper':float(-high.fun)})
    return {'rank':int(np.linalg.matrix_rank(A)),'remaining_nominal_axial_column_zero':bool(np.max(np.abs(A[:,2]))<1e-12),'bounds':results,
            'scope':'linearized finite-patch impenetrability with known gaps, rotations in radians; NOT certified finite coupled motions or force closure',
            'actual_contacts_active_at_centered_pose':False,'preload_stiffness_load_rating':None}


def guide_directions(parts,side):
    xfaces=v.native_lands(parts[side+'_ROOT_OUTER'],parts[side+'_OLD_COVER'],side);yf=y_faces(parts[side+'_ROOT_OUTER'],side)
    rows=[];gaps=[];locations=[];origin=np.array([15.1,20.15,5.3])
    # The rectangle points stay inside actual overlapping guide faces throughout
    # the nominal coupled axial interval. Signs point from body toward wall.
    for face in xfaces:
        normal=np.array([-face['normal_X'],0.,0.])
        for y in face['y_interval_mm']:
            for z in (4.8,6.1):
                point=np.array([13.6 if normal[0]<0 else 16.6,y,z]);arm=point-origin
                rows.append([*normal,*np.cross(arm,normal)]);gaps.append(.05);locations.append(point.tolist())
    for face in yf:
        normal=np.array([0.,-face['normal_Y'],0.])
        for x in face['X_mm']:
            for z in (4.8,6.1):
                point=np.array([x,18.15 if normal[1]<0 else 22.15,z]);arm=point-origin
                rows.append([*normal,*np.cross(arm,normal)]);gaps.append(.08);locations.append(point.tolist())
    estimate=first_order_bounds(rows,gaps)
    if estimate['rank']!=5 or not estimate['remaining_nominal_axial_column_zero'] or any(x['status']=='unbounded' for x in estimate['bounds']):
        raise ValueError('unwanted guide direction not bounded even in first order')
    return {'side':side,'Y_native_faces':yf,'X_native_faces':xfaces,'sample_points_in_fixed_patches_R':locations,
            'normal_inequalities_vxyz_wxyz':rows,'nominal_gaps_mm':gaps,'linearized_model':estimate,
            'directions_are_not_simultaneously_loaded_contacts':True}


def nominal_move(parts,side,u,dx,dy,flank=0):
    if type(u) not in (int,float) or not math.isfinite(u) or not 0<=u<=3:raise ValueError('manual travel outside bounds')
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in (dx,dy,flank)) or flank not in (-1,0,1):raise ValueError('invalid rigid offsets/flank')
    spec=v.v.slot_range(parts[side+'_TAB']);z=spec['origin']+spec['slope']*(u-dy)+flank*spec['halfwidth']
    sign=-1 if side=='L' else 1
    return {role:parts[side+'_'+role].translate((sign*dx,dy,z)) for role in ('PAWL','SHOULDER_PIN_NOMINAL')},z


def body_contacts(parts,old):
    contacts=[];old_collisions=[]
    for side in 'LR':
        spec=v.v.slot_range(parts[side+'_TAB'])
        for u in (0.,1.5,3.):
            for flank in (-1,1):
                for sign in (-1,1):
                    moved,z=nominal_move(parts,side,u,0.,sign*.08,flank);root=parts[side+'_ROOT_OUTER'];body=moved['PAWL']
                    distance=body.distance(root);hit=v.v.common(body,root)
                    over,_=nominal_move(parts,side,u,0.,sign*.09,flank);beyond=v.v.common(over['PAWL'],root)
                    if distance>1e-6 or hit>TOL or beyond<=TOL:raise ValueError('actual Y body stop not present')
                    pclear=[]
                    for moving,s in moved.items():
                        for fixed in ('A_BACK_PANEL',side+'_ROOF'):
                            d=s.distance(parts[fixed]);vhit=v.v.common(s,parts[fixed])
                            if vhit>TOL or d<.025:raise ValueError('collar still bears before intended body guide')
                            pclear.append({'moving':moving,'fixed':fixed,'gap_mm':d,'common_mm3':vhit})
                    contacts.append({'side':side,'u_mm':u,'flank':flank,'Y_contact_mm':sign*.08,'PAWL_Z_mm':z,
                                     'body_root_gap_mm':distance,'at_contact_common_mm3':hit,'at_0p09_common_mm3':beyond,'collar_clearance':pclear})
            for sign in (-1,1):
                moved,z=nominal_move(old,side,u,0.,sign*.08,0)
                hit=sum(v.v.common(s,old['A_BACK_PANEL']) for s in moved.values())
                if hit<=TOL:raise ValueError('old shoulder-to-panel obstruction lost')
                old_collisions.append({'side':side,'u_mm':u,'Y_mm':sign*.08,'combined_original_panel_common_mm3':hit,
                                       'not_actual_admissible_old_freeplay':True})
    return {'Y_body_contact_and_overtravel':contacts,'original_collar_obstructions':old_collisions,
            'center_Z_changes_by_minus_slot_slope_times_Y':True}


def complete_translation_envelopes(parts):
    rows=[];collars=[];coverage=[]
    for side in 'LR':
        s=v.v.slot_range(parts[side+'_TAB']);loz=s['lower']-s['slope']*.08;hiz=s['upper']+s['slope']*.08
        union=None
        for name,lo,hi in v.v.COVERS:
            b=v.v.hand(v.v.box(lo,hi),side);union=b if union is None else union.fuse(b)
        lost=v.v.vol(parts[side+'_PAWL'].cut(union));pbox=v.v.hand(v.v.box((10.8,19.35,4.65),(13.3,20.65,5.95)),side)
        plost=v.v.vol(parts[side+'_SHOULDER_PIN_NOMINAL'].cut(pbox))
        if max(lost,plost)>TOL:raise ValueError('moving material omitted')
        coverage.append({'side':side,'PAWL_omitted_mm3':lost,'pin_omitted_mm3':plost})
        for name,lo,hi in (*v.v.COVERS,('pin',(10.8,19.35,4.65),(13.3,20.65,5.95))):
            low=[lo[0]-.05,lo[1]-.08,lo[2]+loz];high=[hi[0]+.05,hi[1]+.08,hi[2]+hiz]
            cage=v.v.hand(v.v.box(low,high),side)
            for role in ('ROOT_INNER','ROOT_OUTER','OLD_COVER'):
                fixed=parts[side+'_'+role];hit=v.v.common(cage,fixed)
                if hit>TOL:raise ValueError('complete coupled-translation superset hits root/cover')
                rows.append({'side':side,'cover':name,'fixed':role,'common_mm3':hit,'gap_mm':cage.distance(fixed),'R_bounds':[low,high]})
        # Exact original outer cylindrical carriers + radial Minkowski bound.
        # All Y variation and the correlated axial offset fit inside this disk.
        inflation=math.hypot(.08,s['slope']*.08+s['halfwidth'])
        carriers=[]
        for name,x0,x1,radius in [('head',10.8,11.,.65),('shaft',11.,13.3,.4),('socket',12.2,13.8,.65)]:
            carriers.append(v.v.hand(capsule_x(x0,x1,20.,5.3,5.300001,radius),side))
            cage=v.v.hand(capsule_x(x0-.05,x1+.05,20.,5.3+s['origin'],5.3+s['origin']+3*s['slope'],radius+inflation),side)
            for role in ('A_BACK_PANEL',side+'_ROOF'):
                fixed=parts[role];hit=v.v.common(cage,fixed);gap=cage.distance(fixed)
                if hit>TOL or gap<.02:raise ValueError('collar full-range enclosure rejected')
                collars.append({'side':side,'carrier':name,'fixed':role,'radial_inflation_mm':inflation,'common_mm3':hit,'gap_mm':gap})
        # Original head+shaft cover all native pin; socket carrier plus body/neck/
        # tongue supersets covers full PAWL (no selected fragments discarded).
        combined=carriers[0].fuse(carriers[1]);pinlost=v.v.vol(parts[side+'_SHOULDER_PIN_NOMINAL'].cut(combined))
        pawl_cover=carriers[2]
        for name,lo,hi in v.v.COVERS:
            if name!='socket':pawl_cover=pawl_cover.fuse(v.v.hand(v.v.box(lo,hi),side))
        blost=v.v.vol(parts[side+'_PAWL'].cut(pawl_cover))
        if max(pinlost,blost)>TOL:raise ValueError('cylindrical carrier loses moving native material')
    return {'whole_material_coverage':coverage,'root_cover_checks':rows,'collar_panel_roof_checks':collars,
            'X_mm':[-.05,.05],'Y_mm':[-.08,.08],'Z_from_entire_slot_plus_correlated_Y':True,
            'intentional_guide_tangency_allowed_not_a_positive_process_margin':True,
            'finite_rotations_or_feature_errors_not_included':True}


def verify(baseline,manifest,output,full=False):
    output=Path(output)
    if output.exists():raise ValueError('new output required')
    _,old,h=v.load_new(baseline);meta,new,h2=v.load_new(manifest);h.update(h2)
    if meta['baseline_manifest_sha256']!=v.v.sha(baseline):raise ValueError('wrong baseline')
    expected,_=reconstruct(old);changed={'A_BACK_PANEL'}|{s+'_'+k for s in 'LR' for k in ('ROOT_OUTER','GUIDE_REFERENCE','ROOF')}
    material=[]
    for key in new:
        v.v.equal(new[key],expected[key])
        if key not in changed:v.v.equal(new[key],old[key])
        else:
            loss=v.v.vol(old[key].cut(new[key]));gain=v.v.vol(new[key].cut(old[key]))
            if abs(v.v.vol(old[key])-loss+gain-v.v.vol(new[key]))>TOL:raise ValueError('material balance')
            material.append({'part':key,'removed_mm3':loss,'added_mm3':gain})
    directions=[guide_directions(new,s) for s in 'LR'];contact=body_contacts(new,old);envelopes=complete_translation_envelopes(new)
    original_error=v.bounded_error(new)
    print('Y_CONTACTS',len(contact['Y_body_contact_and_overtravel']),'BODY_ENVELOPES',len(envelopes['root_cover_checks']),'COLLAR_ENVELOPES',len(envelopes['collar_panel_roof_checks']),flush=True)
    full_result={};failures=[]
    if full:
        import verify_endpoint_joint_pawl as e
        parent,prior,mounted,profiles=e.v.parent_native(h);slots={s:e.native_slot(new[s+'_TAB']) for s in 'LR'}
        def scene(slide,descent,tabs,dx=0.,dy=0.,flank=0):
            p=e.scene(new,parent,prior,mounted,profiles,slots,slide,descent,tabs,(flank,flank))
            for side,u in zip('LR',tabs):
                p[side+'_ROOT_INNER']=new[side+'_ROOT_INNER'];p[side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=new[side+'_ROOT_OUTER'];p[side+'_OLD_COVER']=new[side+'_OLD_COVER']
                sign=-1 if side=='L' else 1
                for role in ('PAWL','SHOULDER_PIN_NOMINAL'):p[side+'_'+role]=p[side+'_'+role].translate((sign*dx,dy,-slots[side]['slope']*dy))
            if len(p)!=79:raise ValueError('lost full scene participant')
            return p
        selected={'A_BACK_PANEL'}|{s+'_'+k for s in 'LR' for k in ('ROOT_OUTER_CONNECTED_ALL_FRAGMENTS','PAWL','SHOULDER_PIN_NOMINAL','ROOF')}
        cases=[(0.,0.,(0.,0.),0.,0.,0),(0.,0.,(3.,3.),0.,0.,0),(40.,0.,(3.,3.),0.,0.,0),(79.75,8.2,(3.,3.),0.,0.,0)]
        cases += [(0.,0.,(u,u),0.,dy,flank) for u in (0.,3.) for dy in (-.08,.08) for flank in (-1,1)]
        cases += [(0.,0.,(u,u),dx,dy,0) for u in (0.,3.) for dx,dy in itertools.product((-.05,.05),(-.08,.08))]
        cases += [(slide,descent,(3.,3.),dx,dy,flank) for slide,descent in ((5.,0.),(40.,0.),(79.75,0.),(79.75,8.2)) for dx,dy,flank in itertools.product((-.05,.05),(-.08,.08),(-1,1))]
        states=[]
        for i,args in enumerate(cases):
            p=scene(*args);checks=e.v.w.pairs(p,None if i==0 else selected);bad=[x for x in checks if x['common_mm3']>TOL];failures+=bad
            states.append({'case':list(args),'participants':len(p),'checks':checks,'bad':bad});print('FULL_SCENE',i,'BAD',bad,flush=True)
            if i==0:home=p
        detachable={s+'_'+k for s in 'LR' for k in e.v.INSERT_ROLES};installed={k:b for k,b in home.items() if k not in detachable|{'A_FRAME','B_SHELL'}}
        original_service=e.frozen(h);assembly=[]
        for side in 'LR':
            for role,vector in e.v.plan(side):
                # New collar relief removes material from the previous roof:
                # proving its parent's complete sweep is a conservative certificate.
                swept=old[role] if role.endswith('_ROOF') else home[role]
                if role.endswith('_ROOF'):
                    if v.v.vol(home[role].cut(swept))>TOL:raise ValueError('roof not a subset of prior roof')
                    check=e.roof_motion_partition(role,swept,original_service[role],vector,installed)
                else:check=e.v.motion(role,swept,vector,installed)
                assembly.append(check);installed[role]=home[role];failures+=check['failed']
        stop=[]
        for side in 'LR':
            gain=new[side+'_ROOT_OUTER'].cut(old[side+'_ROOT_OUTER']);pieces={side+'_Y_LAND_'+str(i):v.v.single(b) for i,b in enumerate(gain.Solids())}
            for i in (0,1):
                pr=profiles[side][i];delta=pr.lower_stop_height-pr.floor_height-pr.pin_radius
                proof=e.v.motion(side+'_STOP_'+str(i),mounted[side+'_STOP_'+str(i)],((-1 if side=='L' else 1)*delta,0,0),pieces)
                stop.append(proof);failures+=proof['failed']
        closures=[e.v.root_closure_check(new,s) for s in 'LR']
        if any(not x['result']['all_regions_clear'] for x in closures):failures.append({'root_closure':'failed'})
        full_result={'scenes':states,'assembly':assembly,'STOP_paths':stop,'root_closures':closures}
    if any(v.v.sha(p)!=x for p,x in h.items()):raise ValueError('inputs changed')
    if 'pawl_longitudinal_guide' in sys.modules:raise ValueError('candidate builder imported')
    result={'source_sha256':meta['source_sha256'],'reader_sha256':v.v.sha(__file__),'input_sha256':h,'native_templates':len(new),
            'unchanged_templates':len(new)-len(changed),'material':material,'contact_geometry':contact,'guide_directions':directions,
            'continuous_coupled_translation_envelopes':envelopes,'previous_rigid_error_interface_recheck':original_error,
            'full_native':full_result,'failures':failures,'passed':not failures,'full_mode_executed':full,
            'same_CAD_kernel_family':True,'candidate_builder_imported':False,'no_finite_rotation_load_preload_wear_or_manufacturing_qualification':True,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('RESULT',result['passed'],'FULL',full,flush=True);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--full',action='store_true')
    a=p.parse_args();r=verify(a.baseline,a.manifest,a.output,a.full);raise SystemExit(0 if r['passed'] else 1)
