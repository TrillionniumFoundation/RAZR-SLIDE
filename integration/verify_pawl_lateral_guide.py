"""Native opposed-land contact and integration check, without builder imports.

The geometric pure-X travel limit is NOT a full coupled six-DOF limit, preload,
friction, stiffness or a vendor tolerance. Existing rigid-error envelopes are
rechecked and now have 0.02mm minimum gap at these intentional bearing lands,
rather than reusing the previous 0.05mm nonbearing certificate.
"""
from pathlib import Path
import argparse
import itertools
import json
import math
import sys
import numpy as np
import cadquery as cq
import verify_root_clearance as v

TOL=v.TOL


def reconstruct(old,side,*,spine=True):
    if type(spine) is not bool:
        raise ValueError('explicit spine flag required')
    additions=[]
    for x0,x1 in ((13.4,13.55),(16.65,16.85)):
        for y0,y1 in ((18.3,19.),(21.3,22.)):
            additions.append(v.hand(v.box((x0,y0,4.5),(x1,y1,7.3)),side))
    if spine:
        additions.append(v.hand(v.box((16.8,17.8,4.5),(17.,23.2,7.3)),side))
    body=old
    for part in additions:body=body.fuse(part).clean()
    return body,additions


def native_lands(root,side):
    shape=root if side=='R' else root.mirror('YZ');rows=[]
    for x,nx in ((13.55,1.),(16.65,-1.)):
        for y0,y1 in ((18.3,19.),(21.3,22.)):
            matches=[]
            for face in shape.Faces():
                if face.geomType()!='PLANE':continue
                b=face.BoundingBox();n=face.normalAt()
                vals=(b.xmin-x,b.xmax-x,b.ymin-y0,b.ymax-y1,b.zmin-4.5,b.zmax-7.3,n.x-nx,n.y,n.z)
                if max(abs(q) for q in vals)<1e-6:matches.append(face)
            if len(matches)!=1:raise ValueError('one complete finite planar bearing face required')
            rows.append({'x_mm':x,'y_interval_mm':[y0,y1],'z_interval_mm':[4.5,7.3],
                         'normal_X':nx,'area_mm2':matches[0].Area()})
    return rows


def contact_checks(new,base):
    rows=[];directions=[]
    for side in 'LR':
        lands=native_lands(new[side+'_ROOT_OUTER'],side)
        # Original rectangular guide block has complete opposing X faces.
        block=(new[side+'_PAWL'] if side=='R' else new[side+'_PAWL'].mirror('YZ'))
        for x in (13.6,16.6):
            faces=[f for f in block.Faces() if f.geomType()=='PLANE' and
                   abs(f.BoundingBox().xmin-x)<TOL and abs(f.BoundingBox().xmax-x)<TOL and
                   f.BoundingBox().ymin<=18.15+TOL and f.BoundingBox().ymax>=22.15-TOL and
                   f.BoundingBox().zmin<=3.6+TOL and f.BoundingBox().zmax>=6.2-TOL]
            if len(faces)!=1:raise ValueError('complete original PAWL guide face missing')
        slot=v.slot_range(new[side+'_TAB']);sgn=-1 if side=='L' else 1
        minimum_z_overlap=min(min(7.3,6.2+z)-max(4.5,3.6+z) for z in (slot['lower'],slot['upper']))
        if minimum_z_overlap<=1.69:raise ValueError('finite bearing lost during complete slot range')
        for lift in (slot['lower'],slot['origin'],slot['origin']+1.5*slot['slope'],slot['upper']):
            for sign in (-1,1):
                at=new[side+'_PAWL'].translate((sgn*sign*.05,0,lift))
                beyond=new[side+'_PAWL'].translate((sgn*sign*.06,0,lift))
                d=at.distance(new[side+'_ROOT_OUTER']);hit=v.common(at,new[side+'_ROOT_OUTER'])
                over=v.common(beyond,new[side+'_ROOT_OUTER']);old=v.common(beyond,base[side+'_ROOT_OUTER'])
                if d>1e-6 or hit>TOL or over<=TOL or old>TOL:
                    raise ValueError('intended new stop or old travel witness not reproduced')
                rows.append({'side':side,'PAWL_lift_mm':lift,'outward_sign':sign,
                             'contact_X_mm':sign*.05,'at_contact_distance_mm':d,'at_contact_common_mm3':hit,
                             'at_0p06_new_common_mm3':over,'at_0p06_previous_common_mm3':old})
        # These are possible normal constraint directions when contact occurs.
        # They do not imply active contact/preload at the centered clearance pose.
        matrix=[]
        for land in lands:
            for z in (4.75,6.):
                y=sum(land['y_interval_mm'])/2;nx=land['normal_X']
                matrix.append([nx,0.,0.,0.,(z-5.3)*nx,-(y-20.15)*nx])
        rank=int(np.linalg.matrix_rank(np.array(matrix)))
        if rank!=3:raise ValueError('bearing normal directions changed')
        directions.append({'side':side,'native_faces':lands,'minimum_overlap_over_full_slot_mm':minimum_z_overlap,
            'possible_contact_direction_matrix_vxyz_wxyz':matrix,'direction_matrix_rank':rank,
            'unconstrained_by_these_lands_alone':['Y translation','Z intended translation','rotation about X'],
            'not_an_active_contact_or_force_closure_claim':True})
    return {'native_contact_rows':rows,'land_direction_records':directions,
            'pure_X_nominal_interval_mm':[-.05,.05],
            'scope':'same orientation and overlapping guide block; combined rotations and guide tolerances not bounded'}


def bounded_error(new):
    slots={s:v.slot_range(new[s+'_TAB']) for s in 'LR'}
    raw=v.error_envelopes(new,slots)
    # Deliberate new bearing face consumes 0.03mm of the old nonbearing margin.
    # Do not misrepresent the old all_envelopes_clear (>0.049) flag as passing.
    rows=raw['rows'];minimum=min(r['distance_mm'] for r in rows)
    if any(r['common_mm3']>TOL for r in rows) or minimum<.02-1e-6:
        raise ValueError('new 0.02mm bearing-error envelope margin failed')
    return {'whole_material_cover':raw['whole_original_material_covered'],'rows':rows,
        'old_0p05_margin_rule_passes':raw['all_envelopes_clear'],
        'new_0p02_margin_rule_passes':True,'minimum_distance_mm':minimum,
        'relative_rigid_error_xyz_mm':[.03,.05,.02],
        'reduced_margin_is_intentional_and_not_a_process_or_rotation_qualification':True}


def verify(baseline,manifest,output,*,full=False):
    output=Path(output)
    if output.exists():raise ValueError('new result required')
    _,base,h=v.load_new(baseline);meta,new,h2=v.load_new(manifest);h.update(h2)
    if meta['baseline_manifest_sha256']!=v.sha(baseline):raise ValueError('wrong baseline')
    changed={s+'_ROOT_OUTER' for s in 'LR'}
    for name in set(base)-changed:v.equal(base[name],new[name])
    material=[]
    for side in 'LR':
        name=side+'_ROOT_OUTER';expected,_=reconstruct(base[name],side)
        v.single(expected);v.equal(expected,new[name])
        incomplete,_=reconstruct(base[name],side,spine=False)
        if len(incomplete.Solids())!=3:raise ValueError('floating-land negative witness lost')
        loss=v.vol(base[name].cut(new[name]));gain=v.vol(new[name].cut(base[name]))
        if loss>TOL or abs(v.vol(base[name])+gain-v.vol(new[name]))>TOL:
            raise ValueError('original root material was lost')
        material.append({'side':side,'removed_mm3':loss,'added_mm3':gain,
                         'without_spine_components':3,'with_spine_components':1})
    contacts=contact_checks(new,base);error=bounded_error(new)
    print('NATIVE_LANDS',8,'CONTACT_ROWS',len(contacts['native_contact_rows']),
          'ERROR_MARGIN',error['minimum_distance_mm'],flush=True)
    integration={};failures=[]
    if full:
        import verify_endpoint_joint_pawl as e
        parent,prior,old,profiles=e.v.parent_native(h);slots={s:e.native_slot(new[s+'_TAB']) for s in 'LR'}
        def scene(slide,descent,tabs,dx=0.):
            p=e.scene(new,parent,prior,old,profiles,slots,slide,descent,tabs)
            for side in 'LR':
                p[side+'_ROOT_INNER']=new[side+'_ROOT_INNER']
                p[side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=new[side+'_ROOT_OUTER']
                if dx:
                    sign=-1 if side=='L' else 1
                    for role in ('PAWL','SHOULDER_PIN_NOMINAL'):p[side+'_'+role]=p[side+'_'+role].translate((sign*dx,0,0))
            if len(p)!=79:raise ValueError('incomplete original phone scene')
            return p
        roots={s+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS' for s in 'LR'}
        selected=roots|{s+'_'+r for s in 'LR' for r in ('PAWL','SHOULDER_PIN_NOMINAL')}
        states=[]
        cases=[(0.,0.,(0.,0.),0.),(0.,0.,(3.,3.),0.),(40.,0.,(3.,3.),0.),(79.75,8.2,(3.,3.),0.)]
        cases += [(0.,0.,(u,u),dx) for u in (0.,3.) for dx in (-.05,.05)]
        for i,(slide,descent,tabs,dx) in enumerate(cases):
            p=scene(slide,descent,tabs,dx);rows=e.v.w.pairs(p,None if i==0 else selected)
            bad=[r for r in rows if r['common_mm3']>TOL];failures+=bad
            states.append({'slide_mm':slide,'descent_mm':descent,'tabs_mm':tabs,'outward_X_shift_mm':dx,'participants':79,'pairs':rows,'bad':bad})
            print('SCENE',i,len(rows),'BAD',bad,flush=True)
            if i==0:home=p
        paths=[]
        for side in 'LR':
            gain=new[side+'_ROOT_OUTER'].cut(base[side+'_ROOT_OUTER'])
            supports={side+'_ADDED_GUIDANCE_'+str(i):v.single(s) for i,s in enumerate(gain.Solids())}
            for i in (0,1):
                profile=profiles[side][i];delta=profile.lower_stop_height-profile.floor_height-profile.pin_radius
                paths.append(e.v.motion(side+'_STOP_'+str(i),old[f'{side}_STOP_{i}'],((-1 if side=='L' else 1)*delta,0,0),supports))
        root_closure=[e.v.root_closure_check(new,s) for s in 'LR']
        detachable={s+'_'+k for s in 'LR' for k in e.v.INSERT_ROLES}
        installed={k:b for k,b in home.items() if k not in detachable|{'A_FRAME','B_SHELL'}};assembly=[];prev=e.frozen(h)
        for side in 'LR':
            for name,vec in e.v.plan(side):
                proof=e.roof_motion_partition(name,home[name],prev[name],vec,installed) if name.endswith('_ROOF') else e.v.motion(name,home[name],vec,installed)
                assembly.append(proof);installed[name]=home[name]
                print('ASSEMBLY',name,'BAD',len(proof['failed']),flush=True)
        outside={k:e.v.vol(home[k].cut(old['A_OUTER'])) for k in roots}
        failures += [x for x in paths+assembly if x['failed']]
        failures += [x for x in root_closure if not x['result']['all_regions_clear']]
        failures += [{'outside_A':k,'mm3':x} for k,x in outside.items() if x>TOL]
        integration={'scenes':states,'STOP_paths_against_added_material':paths,'root_closure':root_closure,
                     'assembly':assembly,'outside_A_mm3':outside,
                     'assembly_requires_detached_backpanel_and_prior_temporary_holding':True}
    if any(v.sha(f)!=x for f,x in h.items()):raise ValueError('input changed during native check')
    if 'pawl_lateral_guide' in sys.modules:raise ValueError('candidate builder imported')
    result={'source_sha256':meta['source_sha256'],'reader_sha256':v.sha(__file__),'input_sha256':h,
        'scope':'complete prior scene plus conditional lateral bearing checks' if full else 'isolated native-template subset',
        'native_templates':23,'unchanged_templates':21,'material':material,'contacts':contacts,
        'bounded_error':error,'integration':integration,'failures':failures,'passed':not failures,
        'candidate_builder_imported':False,'same_CAD_kernel_family':True,
        'not_full_six_DOF_freeplay_force_stiffness_or_friction_qualification':True,
        'opposed_lands_do_not_supply_preload_or_detent':True,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('RESULT',result['passed'],flush=True);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--full',action='store_true')
    a=p.parse_args();r=verify(a.baseline,a.manifest,a.output,full=a.full)
    raise SystemExit(0 if r['passed'] else 1)
