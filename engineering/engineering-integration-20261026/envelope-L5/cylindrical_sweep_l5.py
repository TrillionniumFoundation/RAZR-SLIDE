"""Named L5 source-bound axial-section sweep. Not wired into S4 or V4.

The continuous set argument is disk/annulus Minkowski addition by a segment,
then independent Z interval addition. Native BREP realization and Boolean
values remain ordinary CAD numerics, not a formal interval-kernel certificate.
"""
from fractions import Fraction as F
from pathlib import Path
import ast
import hashlib
import itertools
import math
import time

from exact_xy_support_l5 import certified_bridge, support_certificate

TOL=1e-7
SCHEMA='razr-L5-whole-axial-section-sweep-v1'
SECTION_SOURCE='engineering/product-integration-20261018/physical-test-followon-20261019/captured_follower_assembly.py'
SECTION_SHA='d3ccd367ef791b90296ec09011e5368bd17a93da4fc2c6fd999e252133dca259'
CAM_SHA='4a3bf1d2b86d31fa8e3d60d3412e15548bf42287ed95d756798f3d88c6c4e631'


def require(ok,message):
    if not ok:raise ValueError(message)


def round_bound(value,upper):
    value=F(value);result=float(value);got=F.from_float(result)
    if (got<value if upper else got>value):
        result=math.nextafter(result,math.inf if upper else -math.inf)
    require(math.isfinite(result),'nonfinite directed parameter endpoint')
    return result


def source_sections(root):
    path=Path(root)/SECTION_SOURCE;data=path.read_bytes()
    require(hashlib.sha256(data).hexdigest()==SECTION_SHA,'axial-section source changed')
    require(hashlib.sha256((Path(root)/'integration/cam_coupling.py').read_bytes()).hexdigest()==CAM_SHA,'native cam source changed')
    module=ast.parse(data)
    function=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='source_geometry')
    # Only the already-reviewed constant table builder runs here; the owning
    # worker separately executes the real unchanged complete S4 factory.
    values={};exec(compile(ast.Module(body=[function],type_ignores=[]),'<pinned axial section table>','exec'),values)
    return values['source_geometry']()[2]


def plan(target,spec,sections):
    a,b=target['a'],target['b']
    require(a=='B_SHELL' and b[0] in 'LR','fixed full B shell and named side required')
    side=b[0];suffix=b[2:];sign=-1 if side=='L' else 1
    table={'TELESCOPE_2':'TUBE_2_OPEN_BOTTOM','TELESCOPE_3':'CORE_STEM',
           'TELESCOPE_3_CAM_LOWER_FLANGE':'CAM_LOWER_FLANGE',
           'TELESCOPE_3_CAM_UPPER_FLANGE':'CAM_UPPER_FLANGE'}
    require(suffix in table,'unrepresented whole material role')
    require(spec['moving']=={'kind':'complete_rigid_material','material':a} and
            spec['fixed']=={'kind':'complete_rigid_material','material':b},'whole rigid source operands differ')
    lo,hi=map(F,target['q_interval_exact']);require(0<=lo<=hi<=12,'finite source q domain changed')
    law=spec['relative_law'];wanted=[F(-sign),F(319,48),F(0)]
    require(list(map(F,law['q_xyz']))==wanted,'source q/slide relation changed')
    require(not any(F(v) for v in law['height_x']+law['flank_z']),'unrepresented height/flank dependence')
    joint=[F(0)]*4
    if suffix=='TELESCOPE_2':joint[0 if side=='L' else 2]=joint[1 if side=='L' else 3]=F(-1)
    require(list(map(F,law['joint_z']))==joint,'independent joint projection changed')
    expected_coefficients=[[float(x) for x in wanted]]
    expected_intervals=[[float(lo),float(hi)]]
    zlo=zhi=F(0)
    if suffix=='TELESCOPE_2':
        values=[-v[0]-v[1]+F(17,3) for v in set(itertools.permutations((F('2.7'),F('2.9'),F('2.9'))))]
        bounds=(min(values),max(values))
        expected_coefficients.append([0.,0.,1.]);expected_intervals.append([float(x) for x in bounds])
        zlo,zhi=-bounds[1],-bounds[0]
    require(spec['coefficients']==expected_coefficients and spec['parameter_intervals']==expected_intervals,
            'complete original numerical specification differs')
    joint0=float(F(17,6))
    origin=(sign*7.25,81.5,.7+sum([joint0]*(2 if suffix=='TELESCOPE_2' else 3)))
    direction=(-wanted[0],-wanted[1])
    exact_ends=[(F.from_float(origin[0])+direction[0]*q,F.from_float(origin[1])+direction[1]*q) for q in (lo,hi)]
    ends=[tuple(float(v) for v in point) for point in exact_ends]
    binary_direction=tuple(-F.from_float(v) for v in spec['coefficients'][0][:2])
    binary_ends=[tuple(F.from_float(origin[i])+binary_direction[i]*q for i in range(2)) for q in (lo,hi)]
    ideal_error=max(sum(abs(F.from_float(v)-exact) for v,exact in zip(point,raw)) for point,raw in zip(ends,exact_ends))
    binary_error=max(sum(abs(F.from_float(v)-exact) for v,exact in zip(point,raw)) for point,raw in zip(ends,binary_ends))
    center_error=max(ideal_error,binary_error)
    rows=[]
    for outer,inner,start,end in sections[table[suffix]]:
        require(0<=inner<outer and start<end,'invalid complete source annular interval')
        low=F.from_float(origin[2])+F.from_float(start)+zlo
        high=F.from_float(origin[2])+F.from_float(end)+zhi
        rows.append({'source_section':[outer,inner,start,end],
            'carrier_z_exact':[str(low),str(high)],
            'carrier_z_native':[round_bound(low,False),round_bound(high,True)],
            'outer_native_radius':round_bound(F.from_float(outer)+center_error,True),
            'inner_removal_native_radius':max(0.,round_bound(F.from_float(inner)-center_error,False))})
    return {'role':b,'source_table_key':table[suffix],'source_sections':sections[table[suffix]],
        'native_q0_origin_mm':list(origin),'native_source_q0_joint_operation':'float(Fraction(17,6)) explicit verify_slide_native reference',
        'prototype_None_default_joint_branch_used':False,
        'reverse_q_xy_exact':list(map(str,direction)),'source_q_interval_exact':[str(lo),str(hi)],
        'reverse_independent_Z_interval_exact':[str(zlo),str(zhi)],
        'centerline_endpoints_exact':[[str(v) for v in p] for p in exact_ends],
        'centerline_endpoints_native':[list(p) for p in ends],
        'recorded_binary64_coefficients_as_exact_affine_endpoints':[[str(v) for v in p] for p in binary_ends],
        'source_ideal_centerline_L1_endpoint_error_exact':str(ideal_error),
        'original_binary64_coefficient_centerline_L1_endpoint_error_exact':str(binary_error),
        'both_continuous_affine_centerlines_covered_by_endpoint_convexity':True,
        'machine_transform_implementation_interval_certificate':False,
        'centerline_endpoint_L1_rounding_bound_exact':str(center_error),'layers':rows,
        'source_parameter_arithmetic_outward':True,'native_curve_surface_Boolean_interval_certified':False,
        'nominal_zero_KEY_crosshead_offsets_only':True,'SEATING_or_independent_5D_not_covered':True}


def compare(p,a,b):
    values=[p.volume(a.cut(b)),p.volume(b.cut(a))]
    require(all(math.isfinite(v) and 0<=v<=TOL for v in values),'whole material identity failed')
    return {'a_minus_b_mm3':values[0],'b_minus_a_mm3':values[1]}


def static_common(p,guard,a,b):
    original=p.strict_common(a,b);value=original['common_mm3']
    if value<=TOL:
        raw={'disposition':'clear','method':'identical_relative_pose','region_count':1,
             'maximum_region_common_mm3':value,'common_upper_bound_mm3':value,
             'common_upper_bound_is_sum_not_union_volume':True}
    else:
        raw={'disposition':'unresolved_enclosure_overlap','method':'identical_relative_pose',
             'positive_enclosure_common_mm3':value,'examined_region_common_sum_mm3':value,
             'regions_examined':1,'total_region_count':1,'collision_proved':False}
    guard.validate_frame(raw)
    return {'strict_common':original,'original_static_carrier_postguard_record':raw,
            'guard_scope_is_static_carrier_not_dynamic_identical_pose':True}


def capsule(cq,p,ends,radius,z0,z1,emit=None,label_prefix='capsule',audit=None):
    require(radius>0 and z1>z0 and all(math.isfinite(v) for xy in ends for v in xy),'invalid capsule dimensions')
    a,b=ends;delta=[F.from_float(y)-F.from_float(x) for x,y in zip(a,b)]
    exact_length2=sum(x*x for x in delta);length=math.hypot(*(float(x) for x in delta))
    height=round_bound(F.from_float(z1)-F.from_float(z0),True)
    def cylinder(r,point):return cq.Solid.makeCylinder(r,height,cq.Vector(*point,z0),cq.Vector(0,0,1))
    def export(label,body,positive=True):return emit(label_prefix+'-'+label,body,positive) if emit is not None else None
    base={'centerline_endpoints_native':list(map(list,ends)),'centerline_delta_exact':list(map(str,delta)),
        'centerline_length_squared_exact':str(exact_length2),
        'native_centerline_length_mm':length,'requested_native_Z_interval':[z0,z1],
        'directed_native_extrusion_height_mm':height,
        'extrusion_height_outward_arithmetic_excess_exact':str(F.from_float(height)-(F.from_float(z1)-F.from_float(z0))),
        'native_curve_surface_Boolean_interval_certified':False}
    if audit is not None:
        audit.update(base);base=audit
    if exact_length2<F(1,10**10):
        # Triangle inequality covers the full exact centerline, including tiny
        # nonzero displacements. No equality/length tolerance drops a movement.
        l1=sum(abs(x) for x in delta)
        inflation=round_bound(F.from_float(radius)+l1,True)
        raw=cylinder(inflation,a);raw_record=export('short-disk',raw,False);result=p.single(raw)
        base.update({'method':'short_segment_containing_disk',
            'centerline_L1_length_bound_exact':str(l1),'native_radius_mm':inflation,
            'zero_displacement_exact':exact_length2==0,'nonzero_displacement_not_dropped':True,
            'whole_short_disk_BREP':raw_record})
        p.whole_material(result)
        return result,base
    points,proof=certified_bridge(ends,radius)
    pts=[cq.Vector(x,y,z0) for x,y in points]
    raw_bridge=cq.Solid.extrudeLinear(cq.Wire.makePolygon(pts,close=True),[],cq.Vector(0,0,height))
    base['XY_bridge_support']=proof;base['bridge_BREP']=export('bridge',raw_bridge,False)
    bridge=p.single(raw_bridge)
    native=[tuple(v.Center().toTuple()) for v in bridge.Vertices()]
    xy=sorted(set((v[0],v[1]) for v in native))
    require(len(native)==8 and len(bridge.Edges())==12 and len(bridge.Faces())==6,
            'native rounded bridge does not have complete hexahedral topology')
    require(all(f.geomType()=='PLANE' for f in bridge.Faces()),'native bridge has unrepresented curved face')
    require(set(xy)==set(points),'native bridge XY vertices differ from certified rounded coordinates')
    zchecks=[]
    for x,y in points:
        zs=sorted(v[2] for v in native if v[:2]==(x,y))
        zchecks.append({'XY':[x,y],'native_Z_vertices':zs,
            'full_directed_Z_interval_contained':len(zs)==2 and zs[0]<=z0 and zs[1]>=z1})
    require(all(r['full_directed_Z_interval_contained'] for r in zchecks),'native bridge Z extent shrank')
    native_proof=support_certificate(ends,radius,points)
    require(native_proof['continuous_rectangle_contained'],'actual native XY rectangle support failed')
    base['native_bridge_topology']={'vertex_count':len(native),'edge_count':len(bridge.Edges()),
        'face_count':len(bridge.Faces()),'all_faces_planar':True,'native_vertex_XY_equals_certified_quad':True,
        'native_Z_vertex_checks':zchecks,'native_vertices':[list(v) for v in native],
        'signed_volume_mm3':p.volume(bridge),'whole_valid_positive_checked':True}
    raw_disks=[cylinder(radius,point) for point in ends]
    base['endpoint_disk_BREPs']=[export('endpoint-'+str(i),body,False) for i,body in enumerate(raw_disks)]
    disks=[p.single(body) for body in raw_disks]
    # Same fuse/clean/one-positive-solid sequence as original p.fuse, with the
    # returned final shape retained before its unchanged final validation.
    raw_result=bridge
    for body in disks:
        p.single(body);raw_result=raw_result.fuse(body)
    raw_result=raw_result.clean();base['prevalidation_union_BREP']=export('assembled-union',raw_result,False)
    result=p.single(raw_result);base['component_containment_checks']=[]
    for label,body in [('bridge',bridge),('endpoint-0',disks[0]),('endpoint-1',disks[1])]:
        difference=body.cut(result);difference_record=export(label+'-difference',difference,False)
        leaves,outside=p.whole_material(difference,empty=True)
        base['component_containment_checks'].append({'component':label,'outside_mm3':outside,
            'difference_has_no_solid_material':not leaves and outside==0.,
            'actual_difference_BREP':difference_record})
        require(0<=outside<=TOL,'actual capsule Boolean omitted an entire supplied component')
    require(math.fsum(x['outside_mm3'] for x in base['component_containment_checks'])<=TOL,
            'summed capsule component loss exceeds original material gate')
    p.whole_material(result)
    base.update({'method':'positive_disk_capsule_prism','native_radius_mm':radius,
        'continuous_planar_bridge_support_certificate_passed':True,
        'native_component_containment_checks_are_numerical_not_interval':True})
    return result,base


def evaluate(shell,telescope,spec,target,*,root,cq,p,guard,emit,budget_check,
             preserve_annular_holes=False,audit=None):
    start=time.monotonic();audit={} if audit is None else audit
    budget_check();p.whole_material(shell);p.whole_material(telescope)
    geometry=plan(target,spec,source_sections(root));audit['source_motion_and_sections']=geometry
    origin=geometry['native_q0_origin_mm'];layers=[];audit['layers']=layers;whole=[]
    for i,row in enumerate(geometry['layers']):
        budget_check();r,inner,z0,z1=row['source_section']
        material=p.single(cq.Solid.makeCylinder(r,z1-z0,cq.Vector(origin[0],origin[1],origin[2]+z0),cq.Vector(0,0,1)))
        if inner:
            hole=cq.Solid.makeCylinder(inner,z1-z0,cq.Vector(origin[0],origin[1],origin[2]+z0),cq.Vector(0,0,1))
            material=p.single(material.cut(hole).clean())
        whole.append(material);entry={'index':i,'source_section':row['source_section'],
            'reconstructed_layer_BREP':emit('layer-'+str(i),material)};layers.append(entry)
        # Slice the actual whole input using the same axial boundaries. The
        # global union comparison below detects any material outside this box.
        slab=p.box((origin[0]-r-1,origin[1]-r-1,origin[2]+z0),
                   (origin[0]+r+1,origin[1]+r+1,origin[2]+z1))
        actual=p.single(telescope.intersect(slab))
        entry['actual_layer_BREP']=emit('actual-layer-'+str(i),actual)
        entry['actual_layer_native_bounds_mm']=list(p.bounds(actual))
        entry['native_bounds_are_not_interval_certificates']=True
        entry['actual_layer_identity']=compare(p,actual,material)
    rebuilt=p.fuse(whole);audit['complete_reconstructed_BREP']=emit('whole-reconstructed',rebuilt)
    audit['complete_input_identity']=compare(p,telescope,rebuilt)
    missing=telescope.cut(rebuilt);missing_record=emit('whole-source-omission',missing,False)
    missing_solids,missing_volume=p.whole_material(missing,empty=True)
    audit['whole_source_omission']={'signed_volume_mm3':missing_volume,
        'actual_difference_has_no_solid_material':not missing_solids and missing_volume==0.,
        'actual_difference_BREP':missing_record,
        'one_per_pose_volume_error_budget_not_a_swept_union_volume':True}
    require(missing_volume<=TOL,'complete source omission exceeds original material identity gate')
    for key in ('a_minus_b_mm3','b_minus_a_mm3'):
        value=math.fsum(row['actual_layer_identity'][key] for row in layers)
        require(value<=TOL,'summed layer identity exceeds original whole-material gate')
    checks=[];carriers=[];audit['carrier_checks']=checks
    for i,row in enumerate(geometry['layers']):
        budget_check();t=time.monotonic();ends=geometry['centerline_endpoints_native']
        actual_bounds=layers[i]['actual_layer_native_bounds_mm']
        dzlo,dzhi=map(F,geometry['reverse_independent_Z_interval_exact'])
        z0=round_bound(min(F(row['carrier_z_exact'][0]),F.from_float(actual_bounds[4])+dzlo),False)
        z1=round_bound(max(F(row['carrier_z_exact'][1]),F.from_float(actual_bounds[5])+dzhi),True)
        partial_construction={};audit.setdefault('capsule_construction_attempts',[]).append({'layer_index':i,'construction':partial_construction})
        try:
            carrier,construction=capsule(cq,p,ends,row['outer_native_radius'],z0,z1,emit=emit,label_prefix='layer-'+str(i),audit=partial_construction)
        except Exception as exc:
            audit['construction_failure']={'layer_index':i,'failure_type':type(exc).__name__,
                'partial_bridge_audit':getattr(exc,'partial_bridge_audit',None)}
            raise
        construction['annular_inner_hole_filled_for_conservative_cover']=True
        inner=row['inner_removal_native_radius']
        if preserve_annular_holes and inner>0:
            delta=[F.from_float(b)-F.from_float(a) for a,b in zip(*ends)]
            if sum(v*v for v in delta)<4*F.from_float(inner)**2:
                disks=[p.single(cq.Solid.makeCylinder(inner,z1-z0,cq.Vector(*xy,z0),cq.Vector(0,0,1))) for xy in ends]
                lens=p.single(disks[0].intersect(disks[1]))
                construction['removed_inner_lens_BREP']=emit('inner-lens-'+str(i),lens)
                carrier=p.single(carrier.cut(lens).clean())
                construction['annular_inner_hole_filled_for_conservative_cover']=False
            else:construction['inner_endpoint_disks_have_no_positive_volume_intersection']=True
        p.whole_material(carrier);carriers.append(carrier)
        entry={'layer_index':i,'construction':construction,'carrier_z_native_with_actual_bound_union':[z0,z1],
               'carrier_BREP':emit('carrier-'+str(i),carrier),
               'construction_seconds':time.monotonic()-t};checks.append(entry)
        budget_check();t=time.monotonic()
        try:
            entry['static']=static_common(p,guard,carrier,shell)
        except Exception as exc:
            entry['original_Common_failure_type']=type(exc).__name__
            try:
                followup=carrier.intersect(shell)
                entry['followup_Common_BREP']=emit('layer-'+str(i)+'-Common',followup,False)
                entry['followup_is_new_operation_not_original_failed_Common']=True
            except Exception as followup_exc:
                entry['followup_Common_failure_type']=type(followup_exc).__name__
            raise
        entry['Common_seconds']=time.monotonic()-t
        if entry['static']['strict_common']['common_mm3']>TOL:
            followup=carrier.intersect(shell)
            entry['positive_Common_BREP']=emit('layer-'+str(i)+'-Common',followup,False)
            followup_volume=p.volume(followup)
            require(abs(followup_volume-entry['static']['strict_common']['common_mm3'])<=TOL,
                    'retained new Common differs from original checked Common')
            entry['retained_Common_is_new_recomputed_operation']=True
    # Common is summed over every full layer, never reset per fragment.
    from translation_regions import sum_common_upper_bound
    carrier_sum=sum_common_upper_bound(row['static']['strict_common']['common_mm3'] for row in checks)
    component_losses=[x for row in checks for x in row['construction'].get('component_containment_checks',[])]
    component_omission_sum=math.fsum(x['outside_mm3'] for x in component_losses)
    upper=sum_common_upper_bound([carrier_sum,missing_volume,component_omission_sum])
    strict_containment=bool(audit['whole_source_omission']['actual_difference_has_no_solid_material']
        and all(x['difference_has_no_solid_material'] for x in component_losses))
    audit['whole_pair_volume_error_budget']={'carrier_Common_sum_mm3':carrier_sum,
        'whole_source_omission_once_mm3':missing_volume,'capsule_component_omission_sum_mm3':component_omission_sum,
        'complete_per_pose_Common_upper_bound_mm3':upper,
        'source_omission_counted_once_per_pose_not_as_swept_union_volume':True,
        'strict_set_containment_demonstrated_by_native_empty_differences':strict_containment}
    carrier_union=p.fuse(carriers);audit['complete_carrier_union_BREP']=emit('carrier-union',carrier_union)
    audit['fused_union_is_corroboration_not_used_for_primary_sum_bound']=True
    audit['finite_whole_material_containment_checks']=[]
    qlo,qhi=map(F,target['q_interval_exact']);dx,dy=map(F,geometry['reverse_q_xy_exact'])
    dzlo,dzhi=map(F,geometry['reverse_independent_Z_interval_exact'])
    for q in sorted({qlo,(qlo+qhi)/2,qhi}):
        for dz in sorted({dzlo,(dzlo+dzhi)/2,dzhi}):
            budget_check();actual=p.single(telescope.translate((float(dx*q),float(dy*q),float(dz))))
            outside=p.volume(actual.cut(carrier_union))
            audit['finite_whole_material_containment_checks'].append({'q_exact':str(q),'Z_exact':str(dz),'outside_mm3':outside})
            require(0<=outside<=TOL,'actual whole input escaped the continuous carrier')
    audit['finite_checks_do_not_substitute_for_continuous_argument']=True
    lo=F(target['q_interval_exact'][0]);dx,dy=map(F,geometry['reverse_q_xy_exact'])
    dz=F(geometry['reverse_independent_Z_interval_exact'][0])
    negative=p.single(telescope.translate((float(dx*lo),float(dy*lo),float(dz))))
    audit['negative_control_BREP']=emit('negative-intruding-complete-input',negative)
    negative_values=[static_common(p,guard,carrier,negative) for carrier in carriers]
    negative_sum=sum_common_upper_bound(row['strict_common']['common_mm3'] for row in negative_values)
    require(negative_sum>TOL,'deliberate actual-input penetration negative control did not reject')
    audit['negative_control']={'checks':negative_values,'sum_mm3':negative_sum,
        'scope':'complete moving input deliberately held within its own sweep, not a physical B-shell collision'}
    budget_check()
    return {'schema':SCHEMA,'method':'whole_axial_sections_capsule_translation_sweep',
        'disposition':('clear' if strict_containment else 'unresolved_source_containment') if upper<=TOL else 'unresolved_enclosure_overlap',
        'original_per_pose_volume_predicate_disposition':'clear' if upper<=TOL else 'unresolved_enclosure_overlap',
        'strict_set_containment_status':'native_empty_difference_controls_passed' if strict_containment else 'unresolved_nonempty_omission',
        'pair':[target['a'],target['b']],'source_q_interval_exact':target['q_interval_exact'],
        'original_volume_gate_mm3':TOL,'common_upper_bound_mm3':upper,
        'common_upper_bound_is_sum_not_union_volume':True,'actual_whole_source_reconstruction_passed':True,
        'complete_original_pair_all_layers_count':len(checks),'original_static_postguards_passed':True,
        'negative_control_passed':True,'analytic_continuous_cover_argument':'whole source annuli, full centerline segment and independent Z interval; optional endpoint-inner-disk lens removal',
        'audit':audit,'elapsed_seconds':time.monotonic()-start,
        'native_geometric_operations_executed':True,'formal_interval_CAD_certificate':False,
        'sampled_checks_are_not_continuous_proof':True,'full_11781_pair_execution':False,
        'independent_5D_or_SEATING_domain_proved':False,'K3_candidate_qualification':False,
        'physical_qualification':False,'candidate_go':False,'manufacturing_go':False}
