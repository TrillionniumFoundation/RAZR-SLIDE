"""Independent native verification of body Y bearings and carrier relief.

Potential contact-direction rank is not simultaneous active contact or force
closure. Coupled motion preserves the unchanged inclined-slot equation; it
is a specified path, not an all-load/all-rotation reachable-set certificate.
"""
from pathlib import Path
import argparse,itertools,json,math,sys
import numpy as np
import cadquery as cq
import verify_pawl_lateral_guide as w
from translation_regions import sum_common_upper_bound
v=w.v
TOL=v.TOL


def relief(side):
    # Independent literal complete-cylinder reconstruction, not builder import.
    shape=v.box((10.5,19.2,5.3),(12.6,20.8,6.4))
    for z in (5.3,6.4):
        shape=shape.fuse(cq.Solid.makeCylinder(.8,2.1,cq.Vector(10.5,20,z),cq.Vector(1,0,0))).clean()
    clipped=v.single(shape.intersect(v.box((10.5,19.2,4.57),(12.6,20.8,7.13))).clean())
    return v.hand(clipped,side)


def expected_root(old,side):
    body=old
    for y0,y1 in ((17.9,18.075),(22.225,22.4)):
        part=v.hand(v.box((14.6,y0,4.5),(15.6,y1,7.3)),side)
        if v.common(part,old)<=TOL:raise ValueError('Y-bearing lacks root connection')
        body=body.fuse(part).clean()
    return v.single(body)


def native_y_faces(parts,side):
    body=parts[side+'_ROOT_OUTER'];body=body if side=='R' else body.mirror('YZ');rows=[]
    for y,ny in ((18.075,1.),(22.225,-1.)):
        faces=[]
        for f in body.Faces():
            if f.geomType()!='PLANE':continue
            b=f.BoundingBox();n=f.normalAt()
            actual=[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax,n.x,n.y,n.z]
            wanted=[14.6,15.6,y,y,4.5,7.3,0.,ny,0.]
            if max(abs(a-b) for a,b in zip(actual,wanted))<1e-6:faces.append(f)
        if len(faces)!=1 or abs(faces[0].Area()-2.8)>1e-6:raise ValueError('finite Y bearing plane not exact')
        rows.append({'y_mm':y,'normal_Y':ny,'x_bounds_mm':[14.6,15.6],'z_bounds_mm':[4.5,7.3],'native_face_area_mm2':faces[0].Area()})
    return rows


def coupled_lift(slot,u,dy,flank=0):
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in (u,dy,flank)):raise ValueError('finite real inputs required')
    if not 0<=u<=3 or abs(dy)>.08500001 or flank not in (-1,0,1):raise ValueError('outside explicit diagnostic domain')
    return slot['origin']+slot['slope']*(u-dy)+flank*slot['halfwidth']


def contact_records(new,base):
    rows=[];ranks=[];old_edges=[]
    for side in 'LR':
        faces=native_y_faces(new,side);s=v.slot_range(new[side+'_TAB']);xfaces=w.native_lands(new[side+'_ROOT_OUTER'],new[side+'_OLD_COVER'],side)
        # Recover matching PAWL body faces rather than assuming the part name.
        pawn=new[side+'_PAWL'] if side=='R' else new[side+'_PAWL'].mirror('YZ')
        for y,normal in ((18.15,-1),(22.15,1)):
            found=[f for f in pawn.Faces() if f.geomType()=='PLANE' and abs(f.normalAt().y-normal)<1e-6 and abs(f.BoundingBox().ymin-y)<TOL and abs(f.BoundingBox().ymax-y)<TOL and f.BoundingBox().xmin<=14.6 and f.BoundingBox().xmax>=15.6 and f.BoundingBox().zmin<=3.6+TOL and f.BoundingBox().zmax>=6.2-TOL]
            if len(found)!=1:raise ValueError('matching original PAWL face missing')
        areas=[]
        for u in (0.,3.):
            for sign in (-1,1):
                for flank in (-1,1):
                    dy=sign*.075;z=coupled_lift(s,u,dy,flank)
                    at=new[side+'_PAWL'].translate((0,dy,z));overdy=sign*.085
                    beyond=new[side+'_PAWL'].translate((0,overdy,coupled_lift(s,u,overdy,flank)))
                    root=new[side+'_ROOT_OUTER'];distance=at.distance(root);hit=v.common(at,root);over=v.common(beyond,root)
                    if distance>1e-6 or hit>TOL or over<=TOL:raise ValueError('Y boundary does not stop at actual body')
                    area=max(0.,min(7.3,6.2+z)-max(4.5,3.6+z))
                    if area<1.66:raise ValueError('actual bearing overlap lost')
                    areas.append(area)
                    rows.append({'side':side,'tab_mm':u,'dy_mm':dy,'flank':flank,'PAWL_lift_mm':z,'native_distance_mm':distance,'common_mm3':hit,'beyond_dy_mm':overdy,'beyond_common_mm3':over,'available_geometric_overlap_area_mm2':area})
            for dy in (-.05,.05):
                z=coupled_lift(s,u,dy);hits=[]
                for role in ('PAWL','SHOULDER_PIN_NOMINAL'):
                    moved=new[side+'_'+role].translate((0,dy,z))
                    for target in ('A_BACK_PANEL',side+'_ROOF'):
                        before=v.common(moved,base[target]);after=v.common(moved,new[target])
                        if after>TOL:raise ValueError('old pin-edge interference remains')
                        hits.append({'moving':role,'fixed':target,'old_mm3':before,'new_mm3':after})
                if not any(r['old_mm3']>TOL for r in hits):raise ValueError('prior actual edge witness lost')
                old_edges.append({'side':side,'tab_mm':u,'dy_mm':dy,'pairs':hits})
        matrix=[]
        for f in xfaces:
            for z in (4.75,6.):
                y=sum(f['y_interval_mm'])/2;nx=f['normal_X'];matrix.append([nx,0,0,0,(z-5.3)*nx,-(y-20.15)*nx])
        for f in faces:
            for x,z in itertools.product((14.7,15.5),(4.75,6.)):
                ny=f['normal_Y'];matrix.append([0,ny,0,-(z-5.3)*ny,0,(x-15.1)*ny])
        rank=int(np.linalg.matrix_rank(matrix))
        if rank!=5 or np.any(np.array(matrix)[:,2]):raise ValueError('potential normal-direction basis differs')
        ranks.append({'side':side,'Y_faces':faces,'possible_normal_matrix_vxyz_wxyz':matrix,'rank':rank,
                      'remaining_null_direction':'Z translation','not_active_or_force_closure':True,
                      'minimum_geometric_overlap_mm2':min(areas),
                      'one_N_divided_by_area_MPa_not_a_stress_solution':1/min(areas)})
    return {'body_contact_rows':rows,'prior_pin_edge_witnesses':old_edges,'direction_records':ranks}


def carrier_envelope(slot):
    # Minkowski sum of a complete X-cylinder and a center rectangle. The center
    # rectangle includes the entire correlated u/dy/flank family conservatively.
    d=.075;zlo=5.3+slot['lower']-slot['slope']*d;zhi=5.3+slot['upper']+slot['slope']*d
    yl,yh=20-d,20+d;r=.65;x0,x1=10.8,13.6
    body=v.box((x0,yl-r,zlo),(x1,yh+r,zhi)).fuse(v.box((x0,yl,zlo-r),(x1,yh,zhi+r))).clean()
    for y,z in itertools.product((yl,yh),(zlo,zhi)):
        body=body.fuse(cq.Solid.makeCylinder(r,x1-x0,cq.Vector(x0,y,z),cq.Vector(1,0,0))).clean()
    return v.single(body)


def whole_material_enclosure_checks(rows):
    """Aggregate material pieces for each side and fixed target separately."""
    expected={name for name,_,_ in v.COVERS[:3]}|{'round_carrier'}
    groups={}
    for row in rows:groups.setdefault((row['side'],row['fixed']),[]).append(row)
    if not groups:raise ValueError('complete enclosure comparisons required')
    result=[]
    for (side,fixed),pieces in sorted(groups.items()):
        if len(pieces)!=len(expected) or {row['piece'] for row in pieces}!=expected:
            raise ValueError('complete enclosure piece inventory required')
        upper=sum_common_upper_bound(row['common_mm3'] for row in pieces)
        result.append({'side':side,'fixed':fixed,'pieces':sorted(expected),
            'common_upper_bound_mm3':upper,'common_upper_bound_is_sum_not_union_volume':True,
            'whole_material_enclosure_clear':upper<=TOL})
    return result


def complete_envelopes(new):
    rows=[];coverage=[]
    for side in 'LR':
        sp=v.slot_range(new[side+'_TAB']);lower=sp['lower']-sp['slope']*.075;upper=sp['upper']+sp['slope']*.075
        pieces=[];original=None
        for label,a,b in v.COVERS[:3]:
            original_piece=v.hand(v.box(a,b),side);original=original_piece if original is None else original.fuse(original_piece)
            pieces.append((label,v.hand(v.box((a[0],a[1]-.075,a[2]+lower),(b[0],b[1]+.075,b[2]+upper)),side)))
        cyl=v.hand(cq.Solid.makeCylinder(.65,2.8,cq.Vector(10.8,20,5.3),cq.Vector(1,0,0)),side)
        original=original.fuse(cyl).clean()
        uncovered={r:v.vol(new[side+'_'+r].cut(original)) for r in ('PAWL','SHOULDER_PIN_NOMINAL')}
        if any(x>TOL for x in uncovered.values()):raise ValueError('complete moving material not covered')
        coverage.append({'side':side,'uncovered_mm3':uncovered})
        pieces.append(('round_carrier',v.hand(carrier_envelope(sp),side)))
        for name,b in pieces:
            for target in (side+'_ROOT_INNER',side+'_ROOT_OUTER',side+'_OLD_COVER','A_BACK_PANEL',side+'_ROOF'):
                hit=v.common(b,new[target]);distance=b.distance(new[target])
                if hit>TOL:raise ValueError('full coupled control envelope intersects '+target)
                rows.append({'side':side,'piece':name,'fixed':target,'common_mm3':hit,'distance_mm':distance})
    combined=whole_material_enclosure_checks(rows)
    if any(not row['whole_material_enclosure_clear'] for row in combined):
        raise ValueError('complete coupled control material enclosure is not cleared')
    return {'coverage':coverage,'comparisons':rows,'whole_material_comparisons':combined,
            'complete_nominal_u_and_Y_and_slot_flanks':True,
            'specified_correlated_translation_family_no_rotation_or_process_errors':True,'intentional_body_contact_included':True}


def verify(baseline,manifest,output,*,full=False):
    out=Path(output)
    if out.exists():raise ValueError('new output required')
    sources={str(Path(f).resolve()):v.sha(f) for f in (__file__,sum_common_upper_bound.__code__.co_filename)}
    _,base,h=w.load_new(baseline);meta,new,h2=w.load_new(manifest);h.update(h2)
    h.update(sources)
    if meta['baseline_manifest_sha256']!=v.sha(baseline):raise ValueError('wrong baseline')
    changed={'A_BACK_PANEL'}|{s+'_'+r for s in 'LR' for r in ('ROOT_OUTER','ROOF','GUIDE_REFERENCE')}
    for name in set(base)-changed:v.equal(base[name],new[name])
    panel=base['A_BACK_PANEL'];materials=[]
    for side in 'LR':
        v.equal(expected_root(base[side+'_ROOT_OUTER'],side),new[side+'_ROOT_OUTER'])
        cutter=relief(side);panel=panel.cut(cutter).clean()
        for role in ('ROOF','GUIDE_REFERENCE'):v.equal(base[side+'_'+role].cut(cutter).clean(),new[side+'_'+role])
    v.equal(panel,new['A_BACK_PANEL'])
    for name in sorted(changed):
        lost=v.vol(base[name].cut(new[name]));gain=v.vol(new[name].cut(base[name]))
        if abs(v.vol(base[name])-lost+gain-v.vol(new[name]))>TOL:raise ValueError('unbalanced native material')
        if (name.endswith('ROOT_OUTER') and lost>TOL) or (not name.endswith('ROOT_OUTER') and gain>TOL):raise ValueError('wrong material-change direction')
        materials.append({'part':name,'removed_mm3':lost,'added_mm3':gain})
    contact=contact_records(new,base);envelopes=complete_envelopes(new);old_error=w.bounded_error(new)
    print('BODY_CONTACTS',len(contact['body_contact_rows']),'COMPLETE_ENVELOPES',len(envelopes['comparisons']),flush=True)
    integration={};failures=[]
    if full:
        import verify_endpoint_joint_pawl as e
        parent,prior,old,profiles=e.v.parent_native(h);slots={s:e.native_slot(new[s+'_TAB']) for s in 'LR'}
        def scene(slide,descent,u,dy=0.,flank=0,dx=0.):
            p=e.scene(new,parent,prior,old,profiles,slots,slide,descent,(u,u))
            for side in 'LR':
                p[side+'_ROOT_INNER']=new[side+'_ROOT_INNER'];p[side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=new[side+'_ROOT_OUTER'];p[side+'_OLD_COVER']=new[side+'_OLD_COVER']
                z=coupled_lift(slots[side],u,dy,flank)
                for role in ('PAWL','SHOULDER_PIN_NOMINAL'):p[side+'_'+role]=new[side+'_'+role].translate(((-1 if side=='L' else 1)*dx,dy,z))
            if len(p)!=79:raise ValueError('incomplete scene')
            return p
        selected={'A_BACK_PANEL'}|{s+'_'+r for s in 'LR' for r in ('ROOT_OUTER_CONNECTED_ALL_FRAGMENTS','ROOF','PAWL','SHOULDER_PIN_NOMINAL')}
        cases=[(0,0,0,0,0,0),(0,0,3,0,0,0),(40,0,3,0,0,0),(79.75,8.2,3,0,0,0)]
        cases += [(0,0,u,dy,f,0) for u,dy,f in itertools.product((0,3),(-.075,.075),(-1,1))]
        cases += [(0,0,u,sign*.075,0,sign*.05) for u,sign in itertools.product((0,3),(-1,1))]
        states=[]
        for i,args in enumerate(cases):
            p=scene(*args);rows=e.v.w.pairs(p,None if i==0 else selected);bad=[r for r in rows if r['common_mm3']>TOL];failures+=bad
            states.append({'coordinates_slide_descent_u_dy_flank_dx':args,'participants':len(p),'pairs':rows,'bad':bad});print('SCENE',i,len(rows),'BAD',bad,flush=True)
            if i==0:home=p
        paths=[]
        for side in 'LR':
            gain=new[side+'_ROOT_OUTER'].cut(base[side+'_ROOT_OUTER']);fixed={side+'_Y_LAND_'+str(i):v.single(b) for i,b in enumerate(gain.Solids())}
            for i in (0,1):
                profile=profiles[side][i];delta=profile.lower_stop_height-profile.floor_height-profile.pin_radius
                paths.append(e.v.motion(side+'_STOP_'+str(i),old[f'{side}_STOP_{i}'],((1 if side=='R' else -1)*delta,0,0),fixed))
        closures=[e.v.root_closure_check(new,s) for s in 'LR']
        detachable={s+'_'+r for s in 'LR' for r in e.v.INSERT_ROLES}
        installed={k:b for k,b in home.items() if k not in detachable|{'A_FRAME','B_SHELL'}};assembly=[];previous=e.frozen(h)
        for side in 'LR':
            for name,move in e.v.plan(side):
                if name.endswith('_ROOF'):
                    kept=v.single(previous[name].cut(relief(side)).clean())
                    proof=e.roof_motion_partition(name,home[name],kept,move,installed)
                else:proof=e.v.motion(name,home[name],move,installed)
                assembly.append(proof);installed[name]=home[name];print('ASSEMBLY',name,'BAD',len(proof['failed']),flush=True)
        outside={k:v.vol(home[k].cut(old['A_OUTER'])) for k in selected if k not in ('L_PAWL','R_PAWL','L_SHOULDER_PIN_NOMINAL','R_SHOULDER_PIN_NOMINAL')}
        failures += [x for p in paths+assembly for x in p['failed']]
        failures += [p for p in closures if not p['result']['all_regions_clear']]
        failures += [{'outside':k,'volume':x} for k,x in outside.items() if x>TOL]
        integration={'states':states,'STOP_paths':paths,'root_closures':closures,'assembly':assembly,'outside_A_mm3':outside}
    if any(v.sha(f)!=value for f,value in h.items()):raise ValueError('input changed during readback')
    if 'pawl_box_guide' in sys.modules:raise ValueError('builder imported')
    result={'source_sha256':meta['source_sha256'],'reader_sha256':v.sha(__file__),'input_sha256':h,'scope':'full79-part scenes plus body-bearing subset' if full else 'isolated25-template subset',
            'templates':len(new),'unchanged_templates':len(base)-len(changed),'material':materials,'contacts':contact,
            'coupled_control_envelopes':envelopes,'previous_rigid_error_envelopes':old_error,'integration':integration,'failures':failures,'passed':not failures,
            'candidate_builder_imported':False,'same_CAD_kernel_family':True,
            'actual_material_force_preload_stiffness_wear_or_process_qualified':False,
            'direction_rank_not_active_five_DOF_or_loaded_guide_certificate':True,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('RESULT',result['passed'],flush=True);return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--full',action='store_true')
    a=ap.parse_args();r=verify(a.baseline,a.manifest,a.output,full=a.full);raise SystemExit(0 if r['passed'] else 1)
