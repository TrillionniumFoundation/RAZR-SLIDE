"""One complete EP3 rearrangement, with a decisive single-U internal-path rejection.

The arithmetic mode needs no CAD. Native mode uses all split-scene participants
at three poses, complete endpoint pair matrices, and the union of two separate
outer prisms. Neither a clean pair matrix nor outer-prism containment certifies
an empty internal channel, intermediate motion, supplier fatigue or fabrication.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import traceback

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'design/product_routing_ep3.json'
POSES = [('STOW', 0., 0.), ('PREDOCK', 79.75, 0.), ('OPEN', 79.75, 8.2)]
TOL = 1e-7
GO_KEYS = ('candidate_go', 'fixture_fabrication_go', 'manufacturing_go',
           'supplier_dynamic_qualified', 'physical_hardware_test_executed',
           'full_cycle_internal_route_accepted')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_config(path=CONFIG):
    c = json.loads(Path(path).read_text())
    if c.get('schema') != 'razr-product-routing-ep3-v1':
        raise ValueError('unknown EP3 study')
    if any(c.get(k) is not False for k in GO_KEYS):
        raise ValueError('EP3 cannot grant a physical or full-motion release')
    expected = {'equal_finished_cabins': True, 'single_flexible_display': True,
                'independent_rear_display': False, 'OLED_storage_is_planar_in_B': True,
                'slide_mm': 79.75, 'normal_seating_mm': 8.2}
    if c.get('constraints') != expected:
        raise ValueError('fixed product constraints changed')
    fixed_route = {'A_anchor_local_mm': [0.,51.,1.45], 'B_anchor_local_mm': [0.,40.,4.85],
        'free_length_mm': 100., 'total_material_length_mm': 124.,
        'stiffened_length_each_end_mm': 12., 'width_mm': 12., 'thickness_assumption_mm': .1,
        'base_stations': 65, 'minimum_straight_request_mm': 3., 'STOW_material_head_limit_mm': 94.}
    fixed_end = {'parts_per_end': 20, 'boards_per_end': 2, 'PCB_dimensions_mm': [12.,12.,.8],
        'PCB_A_tail_coordinate_y_mm': [24.,36.], 'PCB_B_tail_coordinate_y_mm': [-14.,-2.],
        'DP_material_z_mm': [.3,1.1], 'DS_material_z_mm': [1.7,2.5], 'BM28_mated_gap_mm': .6,
        'stiffener_thickness_mm': .2, 'outer_stiffener_jaw_thickness_mm': .35,
        'inner_carrier_jaw_thickness_mm': .8, 'carrier_width_mm': 12.,
        'carrier_plate_material_z_mm': [2.9,3.3], 'board_support_ledge_thickness_mm': .2,
        'static_transfer_gap_thickness_mm': .55, 'M1_shaft_length_mm': 2.4,
        'M1_head_height_mm': .4, 'M2_shaft_length_mm': 1.4, 'M2_head_height_mm': .6,
        'M2_legacy_shaft_length_mm': 2.45}
    for key, value in fixed_route.items():
        if c['route'].get(key) != value:
            raise ValueError('EP3 native route declaration changed: '+key)
    for key, value in fixed_end.items():
        if c['endpoint'].get(key) != value:
            raise ValueError('EP3 native endpoint declaration changed: '+key)
    if c['endpoint'].get('joint_material_process_and_nominal_short_M2_selected') is not False or c['endpoint'].get('individual_static_conductors_routed') is not False:
        raise ValueError('geometric reservations cannot become qualified components')
    if c['domain']['finished_cabin_outer_bounds_local_mm'] != [-36.995,36.995,0.,94.25,-1.15,8.]:
        raise ValueError('outer domain differs from the current native body envelope')
    if c['domain']['actual_internal_cross_cabin_opening_defined'] is not False:
        raise ValueError('an actual internal opening has not been supplied')
    return c


def turn_constants(intervals=4096):
    """Numerical quadrature of a declared analytic turn; not interval arithmetic."""
    if type(intervals) is not int or intervals < 64 or intervals % 2:
        raise ValueError('even integration count >=64 required')
    def integrate(fn, end):
        h = end/intervals
        return h/3*math.fsum([fn(0.), fn(end), *[
            (4 if i % 2 else 2)*fn(i*h) for i in range(1,intervals)]])
    theta = lambda u: math.pi*(3*u*u-2*u*u*u)
    return {'I_sin_0_1': integrate(lambda u: math.sin(theta(u)),1.),
            'J_cos_0_half': integrate(lambda u: math.cos(theta(u)),.5),
            'Simpson_intervals': intervals,
            'formal_directed_rounding_certificate': False}


def pose_numbers(slide, descent, c=None):
    c = c or load_config()
    if not (0 <= slide <= 79.75 and 0 <= descent <= 8.2) or (descent > 0 and slide != 79.75):
        raise ValueError('outside ordered slide/seating program')
    r = c['route']; a = r['A_anchor_local_mm']; b = r['B_anchor_local_mm']
    constants = turn_constants()
    dz, dy = b[2]+8.2-descent-a[2], b[1]+slide-a[1]
    bend = dz/constants['I_sin_0_1']; length = r['free_length_mm']
    sa, sb = (length-bend+dy)/2, (length-bend-dy)/2
    return {'slide_mm':slide, 'descent_mm':descent, 'delta_Z_mm':dz, 'delta_Y_mm':dy,
        'turn_length_mm':bend, 'straight_A_mm':sa, 'straight_B_mm':sb,
        'turn_start_world_Y_mm':a[1]+sa,
        'finite_head_world_Y_mm':a[1]+sa+bend*constants['J_cos_0_half']+r['thickness_assumption_mm']/2,
        'minimum_centerline_radius_mm':bend/(1.5*math.pi),
        'minimum_finite_jacobian':1-r['thickness_assumption_mm']*1.5*math.pi/(2*bend),
        'length_sum_mm':sa+bend+sb}


def arithmetic_report(c=None):
    c = c or load_config(); r = c['route']; a,b = r['A_anchor_local_mm'],r['B_anchor_local_mm']
    constants = turn_constants(); st = pose_numbers(0,0,c); pre = pose_numbers(79.75,0,c)
    bend = st['turn_length_mm']; j = constants['J_cos_0_half']; straight = r['minimum_straight_request_mm']
    lo = pre['turn_length_mm']+abs(pre['delta_Y_mm'])+2*straight
    hi = 2*(r['STOW_material_head_limit_mm']-r['thickness_assumption_mm']/2
            -(a[1]+b[1])/2-bend*(j-.5))
    head = c['domain']['finished_cabin_outer_bounds_local_mm'][3]
    outside_length = pre['turn_start_world_Y_mm']-head
    foot_outer_lower = 21.
    foot_requested_lower = foot_outer_lower+c['domain']['B_endpoint_required_local_foot_request_mm']
    max_b_y = head-79.75-straight
    cavity = c['domain']['reference_return_guide_bottom_mm']-c['domain']['reference_floor_mm']
    usable = cavity-2*c['domain']['reference_normal_clearance_each_face_mm']
    return {'schema':'razr-ep3-arithmetic-v1', 'candidate_id':c['candidate_id'],
        'inputs_sha256':{'design/product_routing_ep3.json':sha(CONFIG),
                        'integration/product_routing_ep3.py':sha(__file__)},
        'turn':constants, 'poses':{name:pose_numbers(s,d,c) for name,s,d in POSES},
        'free_length_necessary_interval_mm':[lo,hi],
        'selected_free_length_in_necessary_interval':lo <= r['free_length_mm'] <= hi,
        'length_interval_derivation': 'L >= max(bend+abs(B_y+slide-A_y)+2*straight); L <= 2*(STOW_head-t/2-(A_y+B_y)/2-bend*(J-.5))',
        'length_interval_scope':'ordered full forward/reverse straight-length inequality plus STOW head bound; not internal clearance',
        'opposed_outer_jaw_reference_cavity':{
            'usable_height_after_two_normal_clearances_mm':usable,
            'old_outward_stack_each_mm':.05+.2+.8,
            'old_max_lane_difference_mm':usable-2*(.05+.2+.8),
            'EP3_outward_stack_each_mm':.05+.2+.35,
            'EP3_max_lane_difference_mm':usable-2*(.05+.2+.35),
            'reference_cavity_is_not_proved_empty':True,
            'requires_shortened_1_4mm_nominal_M2_not_original_2_45mm_shaft':True},
        'PREDOCK_single_U_internal_counterexample':{
            'A_low_straight_Z_interval_mm':[a[2]-.05,a[2]+.05],
            'B_outer_prism_min_Z_mm':-1.15+8.2,
            'A_outer_prism_max_Y_mm':head,
            'low_straight_end_Y_mm':pre['turn_start_world_Y_mm'],
            'outside_low_straight_length_mm':outside_length,
            'finite_low_straight_volume_outside_outer_union_mm3':outside_length*r['width_mm']*r['thickness_assumption_mm'],
            'minimum_turn_start_for_requested_straight_mm':b[1]+79.75+straight,
            'internal_B_anchor_upper_bound_mm':max_b_y,
            'B_endpoint_tail_extent_toward_local_minus_Y_mm':21.,
            'B_anchor_lower_bound_using_outer_prism_only_mm':foot_outer_lower,
            'outer_only_anchor_interval_shortfall_mm':foot_outer_lower-max_b_y,
            'B_anchor_lower_bound_with_wall_and_clearance_request_mm':foot_requested_lower,
            'wall_plus_clearance_request_mm':c['domain']['B_endpoint_required_local_foot_request_mm'],
            'requested_anchor_interval_shortfall_mm':foot_requested_lower-max_b_y,
            'scope':'fixed single +Y / -Y U family, retained complete B endpoint orientation and nonnegative physical end straight; alternative multi-turn/opening topologies are not disproved',
            'native_solid_checks_executed_here':False,
            'rejects_complete_forward_and_reverse_because_both_include_PREDOCK':True},
        'native_checks_executed':False, **{key:False for key in GO_KEYS}}


def candidate_interface_config(original, c):
    result = copy.deepcopy(original); r=c['route']
    result['coupon'].update(length_mm=r['total_material_length_mm'],free_length_mm=r['free_length_mm'])
    result['route_study'].update(A_anchor_local_mm=r['A_anchor_local_mm'],B_anchor_local_mm=r['B_anchor_local_mm'],
        fixed_free_material_length_mm=r['free_length_mm'],stations=r['base_stations'],
        width_mm=r['width_mm'],thickness_mm=r['thickness_assumption_mm'])
    return result


def ep3_local_parts(end, c=None):
    """20 complete positive bodies. Dimensions are fixed by load_config.

    The thin jaw is on the stiffener side, toward the cavity's outer face.
    The thicker jaw carries an explicit top plate, ledge and clearance-window
    web. The .2 mm ledge and short nominal M2 have no selected process/retention.
    """
    c=c or load_config()
    if end not in ('A','B'): raise ValueError('unknown endpoint')
    import cadquery as cq
    import product_assembly as p
    box=lambda x0,x1,y0,y1,z0,z1:p.box((x0,y0,z0),(x1,y1,z1))
    cyl=lambda x,y,z,h,r:cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z))
    y0,y1 = (24.,36.) if end=='A' else (-14.,-2.)
    parts={'tail':box(-6,6,0,12,-.05,.05),'stiffener':box(-6,6,0,12,-.25,-.05)}
    outer=box(-6,6,7,21,-.6,-.25)
    carrier=box(-6,6,7,21,.05,.85)
    plate=box(-6,6,min(y0,7),max(y1,21),2.9,3.3)
    web=box(-6,6,12.05,12.5,.8,3.3)
    if end=='A':
        ledge=box(-6,6,23.6,36,.1,.3)
        post=box(-6,6,23.6,23.8,.1,3.3)
    else:
        ledge=box(-6,6,-14,-1.6,.1,.3)
        post=box(-6,6,-1.8,-1.6,.1,3.3)
    carrier=carrier.fuse(plate).fuse(web).fuse(ledge).fuse(post)
    # A continuous finite transfer passes through explicit windows, not
    # through a missing carrier. .1 mm side/height requests remain nominal.
    carrier=carrier.cut(box(-5.4,5.4,min(y0,5),max(y1,6),1.1,1.75))
    for i,y in enumerate((15.,19.),1):
        hole=cyl(0,y,-1,4.5,1.1)
        outer,carrier=outer.cut(hole),carrier.cut(hole)
        parts[f'M2_clamp_screw_{i}']=cyl(0,y,-.55,1.4,1.)
        parts[f'M2_clamp_head_{i}']=cyl(0,y,.85,.6,1.75)
    dp=box(-6,6,y0,y1,.3,1.1); ds=box(-6,6,y0,y1,1.7,2.5)
    holes=[(-5,y0+1.3),(5,y0+1.3),(-5,y1-1.3),(5,y1-1.3)]
    for i,(x,y) in enumerate(holes,1):
        hole=cyl(x,y,0,3,.7)
        dp,ds=dp.cut(hole),ds.cut(hole)
        carrier=carrier.cut(cyl(x,y,.05,.3,.55))
        parts[f'M1_board_shaft_{i}']=cyl(x,y,.1,2.4,.5)
        parts[f'M1_board_head_{i}']=cyl(x,y,2.5,.4,.9)
    mid=(y0+y1)/2
    parts['mini_DP_PCB'],parts['mini_DS_PCB']=dp,ds
    parts['mated_BM28_reservation']=box(-3.5,3.5,mid-.95,mid+.95,1.1,1.7)
    if end=='A':
        transfer=box(-5.3,5.3,5.3,y1-.05,1.15,1.7)
        transfer=transfer.fuse(box(-5.3,5.3,5.25,5.5,.05,1.7))
        transfer=transfer.fuse(box(-5.3,5.3,0,5.5,.05,.25))
        for y in (15.,19.): transfer=transfer.cut(cyl(0,y,1.1,.7,1.85))
    else:
        transfer=box(-5.3,5.3,y0+.05,-1.3,1.15,1.7)
        transfer=transfer.fuse(box(-5.3,5.3,-1.5,-1.25,.05,1.7))
        transfer=transfer.fuse(box(-5.3,5.3,-1.4,5.5,.05,.25))
    transfer=transfer.cut(box(-3.7,3.7,mid-1.15,mid+1.15,1.1,1.75))
    for x,y in holes: transfer=transfer.cut(cyl(x,y,1.1,.7,.75))
    parts['outer_stiffener_jaw']=outer.clean()
    parts['inner_carrier_jaw']=carrier.clean()
    parts['static_26wire_transfer_reservation']=transfer.clean()
    # In A, material before the free section extends opposite +Y. In B,
    # material after the free section follows local +Y; proper end rotation
    # maps that to world -Y and maps material +Z to world -Z.
    if end=='A': parts={name:body.mirror('XZ') for name,body in parts.items()}
    if len(parts)!=20: raise ValueError('incomplete EP3 endpoint')
    for name,body in parts.items():
        if len(body.Solids())!=1 or not body.isValid() or body.Volume()<=0:
            raise ValueError('invalid EP3 endpoint body: '+end+' '+name)
    return parts


def outer_domains(scene):
    """Use two prisms, never their enclosing global box; verify native bounds."""
    import product_assembly as p
    b=p.bounds(scene['B_SHELL'])
    a_parts=[scene[k] for k in ('A_FRAME','A_BACK_PANEL','A_DISPLAY_SUPPORT')]
    boxes=[p.bounds(body) for body in a_parts]
    a=[min(v[2*i] for v in boxes) if side==0 else max(v[2*i+1] for v in boxes)
       for i in range(3) for side in range(2)]
    expected=load_config()['domain']['finished_cabin_outer_bounds_local_mm']
    if any(abs(x-y)>1e-7 for x,y in zip(a,expected)):
        raise ValueError('A native outer envelope changed')
    if any(abs((b[2*i+1]-b[2*i])-(a[2*i+1]-a[2*i]))>1e-7 for i in range(3)):
        raise ValueError('finished cabin outer extents are no longer equal')
    build=lambda v:p.box((v[0],v[2],v[4]),(v[1],v[3],v[5]))
    return [build(a),build(b)], {'A_bounds_mm':a,'B_bounds_mm':b,
        'domain':'union of two separate optimistic outer prisms; includes occupied material and unverified void',
        'passed_containment_would_only_be_necessary':True,
        'actual_internal_opening_or_tool_channel_proved':False}


def containment(parts, domains):
    import product_assembly as p
    rows=[]
    for name,body in sorted(parts.items()):
        try:
            residual=body
            for domain in domains: residual=residual.cut(domain)
            outside=p.volume(residual)
            if outside>p.volume(body)+TOL: raise ValueError('outside material exceeds original')
            rows.append({'part':name,'outside_outer_union_mm3':outside,'rejected':outside>TOL,
                         'method':'native sequential cuts by both distinct prisms'})
        except Exception as exc:
            rows.append({'part':name,'evaluation_failed':True,'error_type':type(exc).__name__,
                         'error':str(exc),'rejected':True})
    return {'parts':len(parts),'rows':rows,'failures':[r for r in rows if r['rejected']],
            'all_part_material_inside_outer_union':all(not r['rejected'] for r in rows),
            'internal_cavity_clearance_proved':False}


def predock_svg(corners, domain, witness, path):
    """Exact coordinate projection of the same finite polygon, in millimetres."""
    import html
    a,b=domain['A_bounds_mm'],domain['B_bounds_mm']
    scale=4.; X=lambda y:32+scale*y; Y=lambda z:122-scale*z
    rect=lambda box,color:f'<rect x="{X(box[2]):.5f}" y="{Y(box[5]):.5f}" width="{scale*(box[3]-box[2]):.5f}" height="{scale*(box[5]-box[4]):.5f}" fill="{color}" fill-opacity=".18" stroke="{color}"/>'
    vertices=list(corners[:,0])+list(corners[::-1,3])
    points=' '.join(f'{X(v[1]):.5f},{Y(v[2]):.5f}' for v in vertices)
    lo,hi=witness['Y_interval_mm']; zlo,zhi=witness['Z_interval_mm']
    text=(f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="250" viewBox="0 0 960 250">'
        '<rect width="960" height="250" fill="white"/>'
        '<g font-family="sans-serif" font-size="13" fill="#16202a">'
        '<text x="24" y="23">EP3 PREDOCK — Y-Z projection of finite geometry; necessary outer-envelope check</text>'
        +rect(a,'#2563eb')+rect(b,'#16a34a')
        +f'<polygon points="{points}" fill="#222" stroke="#222" stroke-width=".25"/>'
        +f'<rect x="{X(lo):.5f}" y="{Y(zhi):.5f}" width="{scale*(hi-lo):.5f}" height="{scale*(zhi-zlo):.5f}" fill="#e11d48"/>'
        +f'<text x="{X(12):.1f}" y="156">A outer prism: Y 0..94.25</text>'
        +f'<text x="{X(111):.1f}" y="45">B outer prism: Y 79.75..174</text>'
        +f'<text x="24" y="182">Outer-prism Y overlap = 14.5 mm; this is not an empty internal opening.</text>'
        +f'<text x="24" y="205">Red low straight: Y {lo:.5f}..{hi:.5f}, Z {zlo:.2f}..{zhi:.2f}; width out of view = 12 mm.</text>'
        +'<text x="24" y="228">Finite thickness = 0.10 mm. Candidate rejected; physical flex stack, loads and fabrication remain unqualified.</text>'
        '</g></svg>')
    Path(path).write_text(text+'\n')


def native_report(output, c=None):
    import cadquery as cq
    import product_assembly as p
    import product_fpc as f
    import product_interfaces as interfaces
    import product_routing_diagnostic as old
    import product_split_assembly as split
    import oled_storage
    c=c or load_config(); output=Path(output).resolve()
    if output.exists() or ROOT in output.parents: raise ValueError('new output outside source required')
    output.mkdir(parents=True)
    names=['integration/product_routing_ep3.py','design/product_routing_ep3.json',
        'integration/product_split_assembly.py','integration/product_assembly.py','integration/product_fpc.py',
        'integration/product_interfaces.py','integration/product_routing_diagnostic.py','design/product_routing_followup.json',
        'integration/oled_storage.py','integration/product_motion.py','integration/cam_coupling.py',
        'engineering/product-integration-20261018/physical-test-followon-20261019/captured_follower_assembly.py',
        'design/product_geometry.json','design/product_interfaces.json']
    before={name:sha(ROOT/name) for name in names}
    original=interfaces.load_config(); cfg=candidate_interface_config(original,c)
    local={end:ep3_local_parts(end,c) for end in ('A','B')}
    local_checks={end:old.native_pair_checks(parts) for end,parts in local.items()}
    endpoint_exports={}
    for end,parts in local.items():
        compound=cq.Compound.makeCompound(list(parts.values())); path=output/('EP3-'+end+'-complete.step')
        cq.exporters.export(compound,str(path)); reread=cq.importers.importStep(str(path)).val()
        if len(reread.Solids())!=20 or any(not s.isValid() or s.Volume()<=0 for s in reread.Solids()):
            raise ValueError('EP3 endpoint STEP readback failed')
        endpoint_exports[end]={'file':path.name,'sha256':sha(path),'parts':20,
            'bounds_mm':p.bounds(compound),'same_process_kernel_readback_positive_solids':20,
            'independent_process_readback_executed':False}
    # Frozen EP2 OPEN counterexample is executed from its own original input.
    old.load_config(); old_sections,_=f.route_pose(original,79.75,8.2)
    old_material,_=f.finite_material_solid(old_sections['corners'])
    old_b=f.place_endpoint(old.ep2_local_parts(original,'B'),old_sections,'B')
    negative=old.native_pair_checks({'finite_material':old_material},old_b)
    expected={'B_M2_clamp_screw_1':.314159265358978,'B_M2_clamp_screw_2':.314159265358978,
              'B_lower_jaw':16.039734577831304}
    actual={r['b']:r.get('common_mm3') for r in negative['failures']}
    if set(actual)!=set(expected) or any(actual[k] is None or abs(actual[k]-expected[k])>1e-6 for k in expected):
        raise ValueError('retained EP2 OPEN negative control changed')
    poses=[]
    for label,slide,descent in POSES:
        accessories=label=='OPEN'; tab=0. if label=='STOW' else 3.
        scene,meta=split.split_scene(slide,descent,tab,tab,open_hold=accessories,open_support=accessories)
        count=len(scene); expected_mechanical=115 if accessories else 108
        if count!=expected_mechanical: raise ValueError('split mechanical participant count changed')
        scene.update(p.registered_components(p.load_config(),slide,descent))
        scene['OLED_GEOMETRIC_TRIAL'],oled_meta=oled_storage.geometry(slide,descent)
        if len(scene)!=count+5: raise ValueError('component allocation or OLED omitted')
        sections,route=f.route_pose(cfg,slide,descent)
        material,finite=f.finite_material_solid(sections['corners'])
        placed={end:f.place_endpoint(local[end],sections,end) for end in ('A','B')}
        complete={'EP3_finite_material':material,**placed['A'],**placed['B']}
        internal={'A_to_B_endpoints':old.native_pair_checks(placed['A'],placed['B']),
            'material_to_A_endpoint':old.native_pair_checks({'finite_material':material},placed['A']),
            'material_to_B_endpoint':old.native_pair_checks({'finite_material':material},placed['B'])}
        external=old.native_pair_checks(complete,scene)
        domains,domain_meta=outer_domains(scene)
        domain_check=containment(complete,domains)
        row={'pose':label,'mechanical_participants':count,'external_participants':len(scene),
            'candidate_participants':len(complete),'combined_participants':len(scene)+len(complete),
            'scene':meta,'OLED':oled_meta,'route':route,'finite_material':finite,
            'internal':internal,'external':external,'outer_domain':domain_meta,'containment':domain_check,
            'all_declared_checks_clear_at_pose':all(v['no_positive_common_or_evaluation_error'] for v in [*internal.values(),external,*local_checks.values()]) and domain_check['all_part_material_inside_outer_union'],
            'internal_cavity_or_interpose_clearance_accepted':False}
        if label=='PREDOCK':
            r=c['route']; a=r['A_anchor_local_mm']; y0=domain_meta['A_bounds_mm'][3]; y1=a[1]+route['straight_A_mm']
            witness=p.box((-6,y0,a[2]-.05),(6,y1,a[2]+.05))
            common=p.strict_common(witness,material)['common_mm3']; outside=containment({'low_straight_witness':witness},domains)
            vol=p.volume(witness)
            if abs(common-vol)>1e-6 or abs(outside['rows'][0]['outside_outer_union_mm3']-vol)>1e-6:
                raise ValueError('analytic low-straight witness is not retained native material outside both prisms')
            row['low_straight_witness']={'Y_interval_mm':[y0,y1],'Z_interval_mm':[a[2]-.05,a[2]+.05],
                'width_mm':12.,'native_volume_mm3':vol,'native_common_with_finite_material_mm3':common,
                'native_volume_outside_both_prisms_mm3':outside['rows'][0]['outside_outer_union_mm3']}
            predock_svg(sections['corners'],domain_meta,row['low_straight_witness'],output/'EP3-PREDOCK-YZ.svg')
            row['projection']={'file':'EP3-PREDOCK-YZ.svg','sha256':sha(output/'EP3-PREDOCK-YZ.svg')}
        assembly=cq.Assembly(name='EP3_REJECTED_'+label)
        for name,body in sorted({**scene,**complete}.items()): assembly.add(body,name=name)
        path=output/(label+'-complete-EP3-REJECTED.step'); assembly.export(str(path))
        row['combined_STEP']={'file':path.name,'sha256':sha(path),'expected_solids':len(scene)+len(complete),
                              'independent_readback_executed':False}
        row['parts']={name:{'bounds_mm':p.bounds(body),'volume_mm3':p.volume(body)} for name,body in sorted(complete.items())}
        poses.append(row)
        (output/'progress.json').write_text(json.dumps({'completed_poses':poses,'completed':False},indent=2)+'\n')
        print(json.dumps({'pose':label,'external_pairs':external['pair_count'],
            'external_rejections':len(external['failures']),'outside_domain_parts':len(domain_check['failures']),
            'all_declared_checks_clear':row['all_declared_checks_clear_at_pose']}),flush=True)
    if before!={name:sha(ROOT/name) for name in names} or any(not p.source_unchanged(row['scene']) for row in poses):
        raise ValueError('native EP3 input changed during execution')
    result={'schema':'razr-ep3-native-three-pose-v1','candidate_id':c['candidate_id'],
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'input_sha256':before,'source_bytes_unchanged':True,'native_checks_executed':True,
        'pose_scope':'three decisive poses only; no sampled or continuous full-motion acceptance',
        'endpoint_exports':endpoint_exports,'endpoint_self_checks':local_checks,
        'retained_EP2_OPEN_negative_control':negative,'poses':poses,
        'fixed_free_material_length_mm':100.,'total_material_including_two_stiffened_ends_mm':124.,
        'actual_wire_stack_and_individual_conductors_selected':False,
        'actual_OLED_COF_material_or_end_fixture_selected':False,
        'stop_reason':'single-U PREDOCK finite low straight outside both cabin outer prisms; full cycle rejected',
        **{key:False for key in GO_KEYS}}
    (output/'native-report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True); parser.add_argument('--native',action='store_true')
    args=parser.parse_args(); out=args.output.resolve()
    if out.exists() or ROOT in out.parents: parser.error('new output outside source required')
    c=load_config(); out.mkdir(parents=True)
    (out/'arithmetic.json').write_text(json.dumps(arithmetic_report(c),indent=2)+'\n')
    # This cut pattern is a rejected geometric coupon proposal, not an order.
    from product_fpc import dxf_rectangles
    (out/'EP3-124mm-REJECTED-cut-pattern.dxf').write_text(dxf_rectangles([
        ('REJECTED_FLEX_OUTLINE',0,0,12,124),('STIFFENER_A',0,0,12,12),
        ('STIFFENER_B',0,112,12,124),('PAD_OPEN_A',0,0,12,6),('PAD_OPEN_B',0,118,12,124)]))
    if args.native:
        try: result=native_report(out/'native',c)
        except Exception as exc:
            (out/'native-execution-failure.json').write_text(json.dumps({'error_type':type(exc).__name__,
                'error':str(exc),'traceback':traceback.format_exc(),'completed_native_report':False,
                **{key:False for key in GO_KEYS}},indent=2)+'\n')
            raise
        print(json.dumps({'native_completed':True,'pose_count':len(result['poses']),
                          'candidate_go':False,'full_cycle_internal_route_accepted':False}))
    else: print(json.dumps({'arithmetic_completed':True,'native_executed':False,'candidate_go':False}))


if __name__=='__main__': main()
