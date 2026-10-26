"""A finite, constant-material-length OLED planar-storage geometry study.

One front leg, one 180-degree turn and one B-local planar return are modeled.
The width, thickness and 187.9 mm material length are explicit trial inputs,
not a selected, qualified OLED module. Source panel lengths are compared
without counting attached FPC/COF tails as more active or bendable OLED.

Full-path enclosures below are analytic sets for this two-stage motion family.
They do not prove material fatigue, guide forces, installed COF or touch fit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
import product_assembly as p
from straight_envelope import single, whole_material, fuse

ROOT=p.ROOT
TOL=1e-7


def specification(config=None):
    spec=dict((config or p.load_config())['oled_storage_study'])
    for key in ('width_mm','thickness_mm','B_return_z_mm','B_turn_center_y_mm',
                'total_material_length_mm','B_storage_y_min_mm'):
        if p.finite(spec[key])<=0:raise ValueError('positive OLED study dimension required')
    p.finite(spec['front_z_mm']);p.finite(spec['front_anchor_y_mm'])
    if spec['selected_module'] is not None or spec['thickness_is_not_supplier_finished_stack'] is not True:
        raise ValueError('this family is not a supplier-qualified module model')
    return spec


def state(slide_mm=0.,descent_mm=0.,spec=None,*,require_finite_tail=True):
    spec=spec or specification();_,s,z=p.b_transform(slide_mm,descent_mm)
    zf=spec['front_z_mm'];zr=spec['B_return_z_mm']+z
    r=(zr-zf)/2.;yc=spec['B_turn_center_y_mm']+s
    front=yc-spec['front_anchor_y_mm'];arc=math.pi*r
    tail=spec['total_material_length_mm']-front-arc
    if r<=spec['thickness_mm']/2 or front<=0:raise ValueError('invalid finite OLED bend geometry')
    if require_finite_tail and tail<=0:raise ValueError('selected material length cannot form the requested planar return')
    return {'slide_mm':s,'descent_mm':descent_mm,'B_translation_mm':[0.,s,z],
            'front_z_mm':zf,'return_z_mm':zr,'turn_y_mm':yc,'circle_z_mm':(zr+zf)/2,
            'radius_mm':r,'front_length_mm':front,'arc_length_mm':arc,'tail_length_mm':tail,
            'total_material_length_mm':front+arc+tail,
            'tail_end_B_y_mm':spec['B_turn_center_y_mm']-tail,
            'curve_max_B_y_mm':spec['B_turn_center_y_mm']+r+spec['thickness_mm']/2,
            'material_allowable_radius_known':False}


def material_station(station_mm,slide_mm=0.,descent_mm=0.,spec=None):
    """One permanent material coordinate, anchored at the A end, all poses."""
    spec=spec or specification();u=p.finite(station_mm);q=state(slide_mm,descent_mm,spec)
    if not 0<=u<=spec['total_material_length_mm']:raise ValueError('material coordinate outside the one fixed strip')
    if u<=q['front_length_mm']:
        point=[0.,spec['front_anchor_y_mm']+u,q['front_z_mm']];tangent=[0.,1.,0.];curvature=0.;region='front'
    elif u<=q['front_length_mm']+q['arc_length_mm']:
        angle=(u-q['front_length_mm'])/q['radius_mm']
        point=[0.,q['turn_y_mm']+q['radius_mm']*math.sin(angle),q['circle_z_mm']-q['radius_mm']*math.cos(angle)]
        tangent=[0.,math.cos(angle),math.sin(angle)];curvature=1/q['radius_mm'];region='turn'
    else:
        point=[0.,q['turn_y_mm']-(u-q['front_length_mm']-q['arc_length_mm']),q['return_z_mm']]
        tangent=[0.,-1.,0.];curvature=0.;region='planar_return'
    return {'material_station_mm':u,'point_mm':point,'unit_tangent':tangent,'curvature_per_mm':curvature,'region':region}


def half_cylinder(width,radius,y,z):
    body=single(cq.Solid.makeCylinder(radius,width,cq.Vector(-width/2,y,z),cq.Vector(1,0,0)))
    return single(body.intersect(p.box((-width/2-.1,y,z-radius-.1),(width/2+.1,y+radius+.1,z+radius+.1))).clean())


def turn_body(q,spec):
    w,t=spec['width_mm'],spec['thickness_mm']
    outer=half_cylinder(w,q['radius_mm']+t/2,q['turn_y_mm'],q['circle_z_mm'])
    inner=single(cq.Solid.makeCylinder(q['radius_mm']-t/2,w+.2,cq.Vector(-w/2-.1,q['turn_y_mm'],q['circle_z_mm']),cq.Vector(1,0,0)))
    return single(outer.cut(inner).clean())


def geometry(slide_mm=0.,descent_mm=0.,spec=None):
    spec=spec or specification();q=state(slide_mm,descent_mm,spec);w,t=spec['width_mm'],spec['thickness_mm']
    front=p.box((-w/2,spec['front_anchor_y_mm'],q['front_z_mm']-t/2),(w/2,q['turn_y_mm'],q['front_z_mm']+t/2))
    arc=turn_body(q,spec)
    tail=p.box((-w/2,q['turn_y_mm']-q['tail_length_mm'],q['return_z_mm']-t/2),(w/2,q['turn_y_mm'],q['return_z_mm']+t/2))
    body=fuse([front,arc,tail])
    expected=w*t*spec['total_material_length_mm']
    if abs(p.volume(body)-expected)>TOL:raise ValueError('finite OLED body loses fixed material volume')
    return body,{**q,'width_mm':w,'trial_thickness_mm':t,'volume_mm3':p.volume(body),
                 'expected_constant_volume_mm3':expected,'one_connected_solid':True,
                 'continuous_tangent_at_two_junctions':True,'curvature_jumps_at_junctions_not_a_fatigue_model':True,
                 'selected_supplier_module':False,'COF_and_full_stack_included':False}


def budget(spec=None):
    spec=spec or specification();s0=state(0,0,spec,require_finite_tail=False)
    pre=state(79.75,0,spec,require_finite_tail=False);opened=state(79.75,8.2,spec,require_finite_tail=False)
    # Slide raises front length monotonically, at constant radius. Seating
    # decreases radius monotonically with front length fixed. These extrema
    # therefore cover every pose of both stages and their reverse paths.
    minimum=pre['front_length_mm']+pre['arc_length_mm']
    capacity=spec['B_turn_center_y_mm']-spec['B_storage_y_min_mm']
    maximum=s0['front_length_mm']+s0['arc_length_mm']+capacity
    original_capacity=spec['B_turn_center_y_mm']-spec['original_full_depth_storage_min_mm']
    oldmax=s0['front_length_mm']+s0['arc_length_mm']+original_capacity
    return {'analytic_whole_two_stage_length_interval_mm':[minimum,maximum],
            'positive_tail_requires_strictly_more_than_lower_limit':True,
            'trial_material_length_mm':spec['total_material_length_mm'],
            'trial_inside_geometric_length_interval':minimum<spec['total_material_length_mm']<=maximum,
            'original_closed_lap_full_depth_cavity_interval_mm':[minimum,oldmax],
            'original_full_depth_cavity_family_feasible':minimum<oldmax,
            'minimum_extra_planar_storage_into_original_solid_lap_mm':max(0.,minimum-oldmax),
            'new_channel_has_not_proved_battery_capacity_or_material_qualification':True,
            'states':{'STOW':s0,'PREDOCK':pre,'OPEN_SEATED':opened},
            'proof':'monotone affine front length in slide and affine semicircle radius in seating; same swept sets for reverse',
            'topology_specific_not_global_OLED_impossibility':True}


def source_comparison(spec=None):
    spec=spec or specification();b=budget(spec);need=b['analytic_whole_two_stage_length_interval_mm'][0]
    sources=[('engineering/controlled-inputs-web-20261013-r6/candidate_facts.json','TOQ'),
             ('engineering/oled-orderable-module-search-20261013-r5/extracted-tdo-inputs.json','TDO')]
    rows=[]
    for rel,kind in sources:
        path=ROOT/rel;facts=json.loads(path.read_text())
        if kind=='TOQ':
            length,width=facts['mechanical']['summary_before_bending_mm'];model=facts['candidate_model']
            tail=facts['mechanical']['attached_FPC_height_typ_mm'];thickness={'finished_maximum_mm':None,'partial_layers_only_mm':.234}
        else:
            width,length,_=facts['dimension_inputs_for_research_only']['general_table_nominal_W_H_D_mm'];model=facts['supplier_module']
            tail=facts['dimension_inputs_for_research_only']['module_drawn_FPC_length_mm'];thickness={'finished_maximum_mm':None,'nominal_table_mm':.231,'catalogue_conflict_mm':.291}
        rows.append({'model':model,'source':rel,'source_sha256':p.sha(path),'panel_nominal_length_mm':length,
                     'panel_nominal_width_mm':width,'panel_length_deficit_for_this_family_mm':max(0.,need-length),
                     'attached_FPC_dimension_mm_not_OLED_length':tail,'thickness_scope':thickness,
                     'AA_physical_rectangle_not_inferred':True,'dynamic_radius_allowed_mm':None,'selected_for_product':False})
    return {'rows':rows,'trial_width_mm':spec['width_mm'],'trial_length_mm':spec['total_material_length_mm'],
            'finite_trial_strip_is_not_one_of_the_supplier_modules':True,'COF_FPC_is_not_added_display_length':True}


def changing_radius_cage(spec,*,frame):
    """Exact turn union for concentric-at-one-end nested half-disks.

    During seating the circles are internally tangent at one endpoint. Their
    outer disks grow by inclusion and their inner disks share the same order.
    Max outer minus min inner therefore encloses every intermediate strip.
    Width is finite, not a sampled centerline or an infinite surface.
    """
    qmax=state(79.75,0,spec);qmin=state(79.75,8.2,spec);w,t=spec['width_mm'],spec['thickness_mm']
    if frame=='B':
        for q in (qmax,qmin):
            q['turn_y_mm']-=q['B_translation_mm'][1];q['circle_z_mm']-=q['B_translation_mm'][2]
    elif frame!='A':raise ValueError('unknown relative frame')
    outer=half_cylinder(w,qmax['radius_mm']+t/2,qmax['turn_y_mm'],qmax['circle_z_mm'])
    inner=single(cq.Solid.makeCylinder(qmin['radius_mm']-t/2,w+.2,cq.Vector(-w/2-.1,qmin['turn_y_mm'],qmin['circle_z_mm']),cq.Vector(1,0,0)))
    return single(outer.cut(inner).clean())


def full_motion_cages(spec=None):
    spec=spec or specification();w,t=spec['width_mm'],spec['thickness_mm'];q=state(0,0,spec);pre=state(79.75,0,spec)
    outer_r=q['radius_mm']+t/2;inner_r=q['radius_mm']-t/2;yc=q['turn_y_mm'];zc=q['circle_z_mm']
    # For each Z, translating the original arc interval by [0,S] creates one
    # interval. A rectangle plus the final outer half disk, minus the initial
    # inner disk, is exactly that finite arc sweep.
    arc_slide=fuse([p.box((-w/2,yc,zc-outer_r),(w/2,yc+79.75,zc+outer_r)),half_cylinder(w,outer_r,yc+79.75,zc)])
    inner=single(cq.Solid.makeCylinder(inner_r,w+.2,cq.Vector(-w/2-.1,yc,zc),cq.Vector(1,0,0)))
    arc_slide=single(arc_slide.cut(inner).clean())
    A={
       'slide_turn_exact':arc_slide,
       'seat_turn_nested_disk_union':changing_radius_cage(spec,frame='A'),
       'front_all_motion':p.box((-w/2,spec['front_anchor_y_mm'],q['front_z_mm']-t/2),(w/2,pre['turn_y_mm'],q['front_z_mm']+t/2)),
       'return_slide_exact':p.box((-w/2,q['turn_y_mm']-q['tail_length_mm'],q['return_z_mm']-t/2),(w/2,pre['turn_y_mm'],q['return_z_mm']+t/2)),
    }
    opened=state(79.75,8.2,spec)
    # A complete rectangular superset of the short return leg during seating;
    # its lower Y is derived from the monotone moving material endpoint.
    low=min(pre['turn_y_mm']-pre['tail_length_mm'],opened['turn_y_mm']-opened['tail_length_mm'])
    A['return_seat_box_superset']=p.box((-w/2,low,opened['return_z_mm']-t/2),(w/2,pre['turn_y_mm'],pre['return_z_mm']+t/2))
    B={'turn_all_motion_nested_disk_union':changing_radius_cage(spec,frame='B'),
       'return_all_motion_exact':p.box((-w/2,q['tail_end_B_y_mm'],spec['B_return_z_mm']-t/2),(w/2,spec['B_turn_center_y_mm'],spec['B_return_z_mm']+t/2)),
       'front_all_motion_box_superset':p.box((-w/2,spec['front_anchor_y_mm']-79.75,spec['front_z_mm']-8.2-t/2),(w/2,spec['B_turn_center_y_mm'],spec['front_z_mm']+t/2))}
    return {'A':A,'B':B}


def relative_slide_turn(spec,travel):
    q=state(0,0,spec);w,t=spec['width_mm'],spec['thickness_mm'];r=q['radius_mm'];y,z=q['turn_y_mm'],q['circle_z_mm']
    if travel<=0:raise ValueError('positive relative slide required')
    outer=fuse([p.box((-w/2,y,z-r-t/2),(w/2,y+travel,z+r+t/2)),half_cylinder(w,r+t/2,y+travel,z)])
    inner=single(cq.Solid.makeCylinder(r-t/2,w+.2,cq.Vector(-w/2-.1,y,z),cq.Vector(1,0,0)))
    return single(outer.cut(inner).clean())


def verify_motion(spec=None):
    spec=spec or specification();cages=full_motion_cages(spec);home,meta=p.product_scene();native,_=p.native_scene()
    b=home['B_SHELL'].translate((0,0,-8.2));oldb=native['B_SHELL'].translate((0,0,-8.2))
    checks=[];negatives=[]
    for name,cage in cages['A'].items():
        for role in ('A_FRAME','A_BACK_PANEL','L_SIDE_GUIDE','R_SIDE_GUIDE'):
            row={'frame':'A','enclosure':name,'obstacle':role,**p.strict_common(cage,home[role])};checks.append(row)
        for role in ('A_FRAME','A_BACK_PANEL'):
            hit=p.strict_common(cage,native[role])
            if hit['common_mm3']>TOL:negatives.append({'frame':'A','enclosure':name,'original_obstacle':role,**hit})
    for name,cage in cages['B'].items():
        checks.append({'frame':'B','enclosure':name,'obstacle':'B_SHELL',**p.strict_common(cage,b)})
        hit=p.strict_common(cage,oldb)
        if hit['common_mm3']>TOL:negatives.append({'frame':'B','enclosure':name,'original_obstacle':'B_SHELL',**hit})
    config=p.load_config();allocations=p.registered_components(config)
    for row in config['components']:
        component=allocations[row['name']]
        if row['cabin']=='B':component=component.translate((0,0,-8.2))
        for name,cage in cages[row['cabin']].items():
            checks.append({'frame':row['cabin'],'enclosure':name,'obstacle':row['name'],
                           'provenance':row['source_kind'],**p.strict_common(cage,component)})
    endpoint_scenes=[p.product_scene(s,d,u,u)[0] for s,d,u in ((0.,0.,0.),(0.,0.,3.),(79.75,0.,3.),(79.75,8.2,3.))]
    # Fixed A parts lie at nonnegative Z while front is negative. Arc/return
    # cages are compared to every inherited and new A part, not only shells.
    for name,cage in cages['A'].items():
        for role,body in sorted(home.items()):
            if role in ('A_FRAME','A_BACK_PANEL','B_SHELL','L_SIDE_GUIDE','R_SIDE_GUIDE'):continue
            # Internal KEY/crosshead/stages move. Their endpoint bbox union is
            # an enclosing box only for the declared affine nominal path.
            ends=[p.bounds(scene[role]) for scene in endpoint_scenes]
            lo=[min(v[2*i] for v in ends) for i in range(3)];hi=[max(v[2*i+1] for v in ends) for i in range(3)]
            row={'frame':'A','enclosure':name,'obstacle':role,'obstacle_method':'nominal affine per-stage bounding-box superset',**p.strict_common(cage,p.box(lo,hi))}
            if row['common_mm3']>TOL and name=='slide_turn_exact':
                start,end=endpoint_scenes[1][role],endpoint_scenes[2][role]
                aa,bb=p.bounds(start),p.bounds(end);dy=bb[2]-aa[2]
                translated=start.translate((0,dy,0))
                if abs(dy)<79.75 and max(p.volume(end.cut(translated)),p.volume(translated.cut(end)))<=TOL:
                    # A simultaneous affine KEY/follower translation must not
                    # be turned into independent time variables. The relative
                    # arc sweep subtracts its Y travel and keeps the part fixed.
                    result=p.strict_common(relative_slide_turn(spec,79.75-dy),start)
                    row={'frame':'A','enclosure':name,'obstacle':role,'obstacle_method':'complete relative straight sweep; native rigid endpoint identity checked',
                         'rejected_independent_time_box_common_mm3':row['common_mm3'],'obstacle_slide_Y_mm':dy,**result}
            checks.append(row)
    failures=[r for r in checks if r['common_mm3']>TOL]
    return {'budget':budget(spec),'supplier_comparison':source_comparison(spec),'mechanical_configuration_sha256':p.sha(p.CONFIG),
            'mechanical_candidate_source_sha256':p.sha(p.__file__),'OLED_source_sha256':p.sha(__file__),
            'checks':checks,'rejected_enclosure_pairs':failures,'original_shell_negative_controls':negatives,
            'all_declared_enclosures_clear':not failures,'whole_slide_and_seat_and_reverse_covered':True,
            'scope':'finite trial OLED and exact/superset path families against modified shells, controls and nominal affine moving-part enclosures; slot centerline and nominal equal telescope allocation',
            'same_material_stations_across_all_poses':True,'telescope_non_nominal_joint_allocations_covered':False,
            'selected_module_fit_full_stack_COF_touch_and_strain_qualified':False,'candidate_go':False,'manufacturing_go':False}


def export(output,*,slide_mm=0.,descent_mm=0.):
    out=Path(output).resolve()
    if out.exists() or out==ROOT or ROOT in out.parents:raise ValueError('new external output directory required')
    body,meta=geometry(slide_mm,descent_mm);out.mkdir(parents=True);path=out/'OLED_GEOMETRIC_TRIAL.step';cq.exporters.export(body,str(path))
    result={'schema':'razr-oled-geometric-export-v1','source_sha256':p.sha(__file__),'configuration_sha256':p.sha(p.CONFIG),
            'geometry':meta,'exports':{'OLED_GEOMETRIC_TRIAL':{'path':path.name,'sha256':p.sha(path),'volume_mm3':p.volume(body),'bounds_mm':p.bounds(body)}},
            'source_comparison':source_comparison(),'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--slide',type=float,default=0.);ap.add_argument('--descent',type=float,default=0.);ap.add_argument('--verify-motion',action='store_true')
    a=ap.parse_args();r=export(a.output,slide_mm=a.slide,descent_mm=a.descent)
    if a.verify_motion:(a.output/'motion-report.json').write_text(json.dumps(verify_motion(),indent=2)+'\n')
    print(json.dumps({'material_length_mm':r['geometry']['total_material_length_mm'],'material_volume_mm3':r['geometry']['volume_mm3'],'candidate_go':False}))
