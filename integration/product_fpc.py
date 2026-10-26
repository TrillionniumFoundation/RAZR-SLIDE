"""Build an identified 26-channel flex coupon and a constant-length route study.

Both endpoints use product_assembly's current world coordinates. The electrical
coupon has owned continuity nets only. Material, phone fit and life are reported
separately; no unmeasured OEM signal is assigned to a test trace.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

from product_interfaces import CONFIG, ENDPOINT, ROOT, bind_endpoint, load_config, positive, sha


def material_return_sections(a, b, length_mm, count, width_mm, thickness_mm):
    """G2 planar return with prescribed arc-length parameter and +X width.

    The turn angle is pi*(3u^2-2u^3); curvature is zero at each straight join.
    Its length is solved from the actual Z lane separation, not a fit spline.
    """
    a,b=np.asarray(a,float),np.asarray(b,float)
    if abs(a[0]-b[0])>1e-9 or b[2]-a[2]<=0:
        raise ValueError('this Y-Z return requires same X and positive Z lane separation')
    width=positive(width_mm,'width');thickness=positive(thickness_mm,'thickness')
    x,w=leggauss(96)
    def turn_integral(u):
        q=(x+1)*u/2
        angle=np.pi*(3*q*q-2*q*q*q)
        return np.array([np.dot(w,np.cos(angle)),np.dot(w,np.sin(angle))])*u/2
    integral=turn_integral(1.)
    bend_length=(b[2]-a[2])/integral[1]
    straight_A=(length_mm-bend_length+b[1]-a[1])/2
    straight_B=length_mm-bend_length-straight_A
    if min(straight_A,straight_B)<0: raise ValueError('negative fixed-material straight section')
    arc_join=a+np.array([0,straight_A,0])
    samples=np.linspace(0,length_mm,count)
    # Preserve equal material stations and also insert the exact joins for finite solids.
    stations=np.unique(np.r_[samples,straight_A+bend_length*np.linspace(0,1,33)])
    center=[];tangent=[];normal_s=[];curvature=[]
    for distance in stations:
        if distance<=straight_A:
            point=a+np.array([0,distance,0]);angle=0.;rate=0.
        elif distance>=straight_A+bend_length:
            rest=distance-straight_A-bend_length
            point=arc_join+np.array([0,0,b[2]-a[2]])+np.array([0,-rest,0]);angle=np.pi;rate=0.
        else:
            u=(distance-straight_A)/bend_length
            iy,iz=turn_integral(u);point=arc_join+np.array([0,bend_length*iy,bend_length*iz])
            angle=np.pi*(3*u*u-2*u*u*u);rate=np.pi*(6*u-6*u*u)/bend_length
        t=np.array([0,np.cos(angle),np.sin(angle)])
        center.append(point);tangent.append(t);curvature.append(rate)
        normal_s.append(np.array([0,-np.cos(angle),-np.sin(angle)])*rate)
    center,tangent,normal_s=np.array(center),np.array(tangent),np.array(normal_s)
    widths=np.tile([1.,0.,0.],(len(stations),1));normal=np.cross(widths,tangent)
    uv=np.array([[-width/2,-thickness/2],[width/2,-thickness/2],[width/2,thickness/2],[-width/2,thickness/2]])
    corners=center[:,None,:]+uv[None,:,0,None]*widths[:,None,:]+uv[None,:,1,None]*normal[:,None,:]
    longitudinal=tangent[:,None,:]+uv[None,:,1,None]*normal_s[:,None,:]
    jac=np.sum(longitudinal*tangent[:,None,:],axis=2)
    sections={'s':stations,'u':stations/length_mm,'center':center,'tangent':tangent,'width_axis':widths,'normal':normal,'corners':corners,'jacobian':jac,'curvature_per_mm':np.array(curvature),'twist_rad_per_mm':np.zeros(len(stations)),'corner_axial_stretch':np.linalg.norm(longitudinal,axis=2)-1,'width_derivative':np.zeros_like(widths),'normal_derivative':normal_s}
    min_radius=bend_length/(1.5*np.pi)
    result={'length_analytic_mm':straight_A+bend_length+straight_B,'target_mm':length_mm,'length_error_mm':straight_A+bend_length+straight_B-length_mm,'straight_A_mm':straight_A,'straight_B_mm':straight_B,'G2_turn_length_mm':bend_length,'Z_lane_separation_mm':b[2]-a[2],'analytic_minimum_centerline_radius_mm':min_radius,'analytic_minimum_material_jacobian':1-thickness/(2*min_radius),'arc_integral_96':integral.tolist(),'same_equal_s_material_samples_plus_exact_join_sections':True}
    return sections,result


def route_pose(config, slide_mm, descent_mm):
    from product_assembly import b_transform
    r=config['route_study'];a=np.array(r['A_anchor_local_mm'],float)
    b=np.array(r['B_anchor_local_mm'],float)+np.array(b_transform(slide_mm,descent_mm))
    sections,length=material_return_sections(a,b,r['fixed_free_material_length_mm'],r['stations'],r['width_mm'],r['thickness_mm'])
    report={'slide_mm':slide_mm,'descent_mm':descent_mm,'A_endpoint_world_mm':a.tolist(),'B_endpoint_world_mm':b.tolist(),**length,'material_station_count':len(sections['s']),'positive_sampled_jacobian':bool(np.min(sections['jacobian'])>0),'max_sampled_abs_twist_rad_per_mm':0.,'end_tangents':sections['tangent'][[0,-1]].tolist(),'end_width_axes':sections['width_axis'][[0,-1]].tolist(),'G2_endpoint_curvature_zero':True,'material_model':'fixed +X width; exact arc-length parameter; G2 Y-Z turn plus straight tails; finite width and thickness','not_a_supplier_fatigue_or_full_motion_clearance_qualification':True}
    return sections,report


def finite_material_solid(corners):
    """Native solid of this precise triangular finite material surface.

    No OCC corrected-Frenet sweep or independent section transport is used.
    The finite tessellation is explicit and is not an exact smooth envelope.
    """
    import cadquery as cq
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
    from OCP.TopoDS import TopoDS
    data = np.asarray(corners, float)
    if data.ndim != 3 or data.shape[1:] != (4, 3) or not np.isfinite(data).all():
        raise ValueError('invalid finite material mesh')
    # All current route material sections have the same +X width. Extrude
    # the actual Y-Z section polygon so no independent sweep frame can drift.
    if not np.allclose(data[:,1]-data[:,0],data[0,1]-data[0,0],atol=1e-9):
        raise ValueError('planar fixed-width finite solid required')
    vector=data[0,1]-data[0,0]
    vertices=np.concatenate([data[:,0],data[::-1,3]],axis=0)
    wire=cq.Wire.makePolygon([cq.Vector(*v) for v in vertices],close=True)
    solid=cq.Solid.extrudeLinear(wire,[],cq.Vector(*vector))
    if not solid.isValid() or len(solid.Solids())!=1 or solid.Volume()<=0:
        raise ValueError('finite material extrusion is not one valid positive solid')
    return solid,{'station_sections':len(data),'native_volume_mm3':solid.Volume(),'native_transport_same_as_material_station_vertices':True,'construction':'finite section polygon extruded over actual width','smooth_between_station_clearance_proved':False}


def _box(lo, hi):
    import cadquery as cq
    return cq.Solid.makeBox(*(b-a for a, b in zip(lo, hi)), cq.Vector(*lo))


def local_endpoint_parts(config,end):
    """Complete research endpoint stack, own two boards, connector reservation,
    flex/stiffener, jaws and fasteners. B uses longitudinal screw ears to keep
    its entire fixture width at 12 mm. No fixture is asserted installed.
    """
    import cadquery as cq
    if end not in ('A','B'):raise ValueError('unknown end')
    c=config['coupon'];w=c['width_mm'];length=c['end_stiffener_length_mm'];tf=c['finished_flex_thickness_assumption_mm'];ts=c['stiffener_thickness_mm']
    sy= -1 if end=='A' else 1
    # Reverse the B local thickness placement: both PCBs remain below world-Z flex.
    sz=1 if end=='A' else -1
    def box(x0,x1,y0,y1,z0,z1):
        ys=sorted([sy*y0,sy*y1]);zs=sorted([sz*z0,sz*z1]);return _box((x0,ys[0],zs[0]),(x1,ys[1],zs[1]))
    def cylinder(x,y,z,height,radius):
        return cq.Solid.makeCylinder(radius,height,cq.Vector(x,sy*y,min(sz*z,sz*(z+height))))
    parts={'tail':box(-w/2,w/2,0,length,-tf/2,tf/2),'stiffener':box(-w/2,w/2,0,length,-tf/2-ts,-tf/2)}
    jaw_w=20 if end=='A' else 12
    gy1=6 if end=='A' else 21
    upper=box(-jaw_w/2,jaw_w/2,1,gy1,.05,.85)
    lower=box(-jaw_w/2,jaw_w/2,1,gy1,-1.65,-.25)
    fasteners=[(-8,3.5),(8,3.5)] if end=='A' else [(0,15),(0,19)]
    for i,(x,y) in enumerate(fasteners,1):
        hole=cylinder(x,y,-2,4,1.1);upper=upper.cut(hole);lower=lower.cut(hole)
        parts[f'M2_clamp_screw_{i}']=cylinder(x,y,-1.6,2.45,1.)
        parts[f'M2_clamp_head_{i}']=cylinder(x,y,.85,.6,1.75)
    parts['upper_jaw']=upper;parts['lower_jaw']=lower
    # DS/DP front faces oppose with the supplier nominal 0.6 mm mating gap.
    pcb_low=box(-6,6,.5,12.5,-3.85,-3.05)
    pcb_high=box(-6,6,.5,12.5,-2.45,-1.65)
    for i,(x,y) in enumerate([(-5,1.8),(5,1.8),(-5,11.2),(5,11.2)],1):
        hole=cylinder(x,y,-4,3,.7);pcb_low=pcb_low.cut(hole);pcb_high=pcb_high.cut(hole)
        parts[f'M1_board_shaft_{i}']=cylinder(x,y,-3.85,2.2,.5)
        parts[f'M1_board_head_{i}']=cylinder(x,y,-4.25,.4,.9)
    parts['mini_DP_PCB']=pcb_low;parts['mini_DS_PCB']=pcb_high
    parts['mated_BM28_reservation']=box(-3.5,3.5,5.55,7.45,-3.05,-2.45)
    # A conservative installed jumper volume reserves actual insulated wires
    # between the mini board probe rows and the exposed tail solder window.
    # It is deliberately not counted as routed OEM circuitry or an absent obstacle.
    parts['static_26wire_transfer_reservation']=box(-5.3,5.3,.5,12.5,-1.65,-.3)
    return parts


def place_endpoint(parts, sections, end):
    import cadquery as cq
    index = 0 if end == 'A' else -1
    w, t, n, origin = (sections[k][index] for k in ('width_axis', 'tangent', 'normal', 'center'))
    rotation = np.column_stack([w, t, n])
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-10) or np.linalg.det(rotation) < .999999:
        raise ValueError('endpoint frame is not a proper rigid transformation')
    from OCP.gp import gp_Trsf
    trsf=gp_Trsf()
    trsf.SetValues(*np.column_stack([rotation,origin]).ravel().tolist())
    return {end+'_'+key: shape.moved(cq.Location(trsf)) for key,shape in parts.items()}


def coupon_geometry(config):
    c = config['coupon']
    width, length = positive(c['width_mm'], 'width'), positive(c['length_mm'], 'length')
    count = c['trace_count']
    pitch = positive(c['trace_pitch_mm'], 'trace pitch')
    track = positive(c['trace_width_mm'], 'trace width')
    pad = positive(c['pad_width_mm'], 'pad width')
    if track >= pitch or pad >= pitch or (count-1)*pitch+max(pad, track) >= width:
        raise ValueError('coupon copper does not fit with positive trace/edge clearance')
    if not math.isclose(length, c['free_length_mm']+2*c['end_stiffener_length_mm'], abs_tol=1e-9):
        raise ValueError('free and stiffened material lengths disagree')
    y = c['pad_center_y_mm']
    if y-c['pad_length_mm']/2 <= 0 or y+c['pad_length_mm']/2 >= c['coverlay_opening_end_mm']:
        raise ValueError('pad is not inside its exposed end window')
    rows = [{'net': f'C{i+1:02}', 'x_mm': width/2+(i-(count-1)/2)*pitch,
             'A_y_mm': y, 'B_y_mm': length-y} for i in range(count)]
    return rows, {'channels': count, 'width_mm': width, 'length_mm': length,
                  'trace_clearance_mm': pitch-track, 'pad_clearance_mm': pitch-pad,
                  'edge_clearance_mm': (width-(count-1)*pitch-pad)/2,
                  'rigid_end_mm': c['end_stiffener_length_mm'],
                  'free_material_mm': c['free_length_mm'],
                  'selected_finished_material_stack': False,
                  'USB_impedance_or_power_rating': None}


def coupon_pcb(config):
    c = config['coupon']
    rows, _ = coupon_geometry(config)
    lines = ['(kicad_pcb (version 20221018) (generator "razr_product_fpc_coupon")',
             f'(general (thickness {c["finished_flex_thickness_assumption_mm"]})) (paper "A4")',
             '(layers (0 "F.Cu" signal) (31 "B.Cu" signal) (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user) (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))',
             '(setup (stackup (layer "F.Mask" (type "Top Solder Mask") (thickness .010)) (layer "F.Cu" (type "copper") (thickness .018)) (layer "dielectric 1" (type "core") (thickness .062) (material "FLEX_REFERENCE_REQUEST_UNCONFIRMED")) (layer "B.Cu" (type "copper") (thickness 0)) (layer "B.Mask" (type "Bottom Solder Mask") (thickness .010)) (copper_finish "None") (dielectric_constraints no)) (pad_to_mask_clearance 0)) (net 0 "")']
    for i, row in enumerate(rows, 1):
        lines.append(f'(net {i} "{row["net"]}")')
    for end in ('A', 'B'):
        lines.append(f'(footprint "RAZR_FLEX:END26_{end}" (layer "F.Cu") (at 0 0) (attr smd)',)
        lines.append(f'(fp_text reference "J{end}" (at 6 {7 if end == "A" else c["length_mm"]-7}) (layer "F.Fab") (effects (font (size .8 .8) (thickness .1))))')
        lines.append('(fp_text value "OWNED_CONTINUITY_END" (at 6 0) (layer "F.Fab") hide (effects (font (size .8 .8) (thickness .1))))')
        for i, row in enumerate(rows, 1):
            lines.append(f'(pad "{i}" smd rect (at {row["x_mm"]:.6f} {row[end+"_y_mm"]:.6f}) (size {c["pad_width_mm"]} {c["pad_length_mm"]}) (layers "F.Cu" "F.Mask") (net {i} "{row["net"]}"))')
        lines.append(')')
    for i, row in enumerate(rows, 1):
        lines.append(f'(segment (start {row["x_mm"]:.6f} {row["A_y_mm"]:.6f}) (end {row["x_mm"]:.6f} {row["B_y_mm"]:.6f}) (width {c["trace_width_mm"]}) (layer "F.Cu") (net {i}))')
    w, h = c['width_mm'], c['length_mm']
    for a, b in [((0, 0), (w, 0)), ((w, 0), (w, h)), ((w, h), (0, h)), ((0, h), (0, 0))]:
        lines.append(f'(gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (layer "Edge.Cuts") (width .05))')
    lines.append(')')
    return '\n'.join(lines)+'\n'


def coupon_netlist(config):
    rows, _ = coupon_geometry(config)
    return '(export (version "E") (design (source "product_fpc.py") (tool "RAZR owned coupon"))\n'+\
        '(components (comp (ref "JA") (value "CONTINUITY_END26")) (comp (ref "JB") (value "CONTINUITY_END26")))\n(nets\n'+\
        '\n'.join(f'(net (code "{i}") (name "{r["net"]}") (node (ref "JA") (pin "{i}")) (node (ref "JB") (pin "{i}")))' for i, r in enumerate(rows, 1))+'\n))\n'


def dxf_rectangles(rectangles):
    out = ['0', 'SECTION', '2', 'HEADER', '9', '$INSUNITS', '70', '4', '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES']
    for layer, x0, y0, x1, y1 in rectangles:
        for a, b in [((x0,y0),(x1,y0)), ((x1,y0),(x1,y1)), ((x1,y1),(x0,y1)), ((x0,y1),(x0,y0))]:
            out += ['0', 'LINE', '8', layer, '10', str(a[0]), '20', str(a[1]), '30', '0', '11', str(b[0]), '21', str(b[1]), '31', '0']
    return '\n'.join(out+['0', 'ENDSEC', '0', 'EOF'])+'\n'


def export_coupon(config, output):
    import cadquery as cq
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows, facts = coupon_geometry(config)
    endpoint = bind_endpoint()
    (output/'continuity26.kicad_pcb').write_text(coupon_pcb(config))
    (output/'continuity26.net').write_text(coupon_netlist(config))
    project = {'board': {'design_settings': {'defaults': {}, 'rules': {'min_clearance': 0.1,
                'min_track_width': 0.1, 'min_hole_clearance': 0.25, 'min_copper_edge_clearance': 0.5}}},
               'meta': {'filename': 'continuity26.kicad_pro', 'version': 1},
               'text_variables': {'SCOPE': '26 continuity nets, no OEM assignments, unqualified requested flex stack'}}
    project['net_settings']={'classes':[{'name':'Default','clearance':.1,'track_width':.15,'via_diameter':.6,'via_drill':.3,'diff_pair_width':.15,'diff_pair_gap':.1,'diff_pair_via_gap':.25}], 'meta':{'version':3}}
    (output/'continuity26.kicad_pro').write_text(json.dumps(project, indent=2)+'\n')
    c = config['coupon']
    w, length, stiff = c['width_mm'], c['length_mm'], c['end_stiffener_length_mm']
    rectangles = [('FLEX_OUTLINE',0,0,w,length), ('STIFFENER_A',0,0,w,stiff),
                  ('STIFFENER_B',0,length-stiff,w,length),
                  ('COVERLAY_END_A_OPEN',0,0,w,c['coverlay_opening_end_mm']),
                  ('COVERLAY_END_B_OPEN',0,length-c['coverlay_opening_end_mm'],w,length)]
    (output/'coupon-cut-and-stiffener.dxf').write_text(dxf_rectangles(rectangles))
    with (output/'conductor-schedule.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['net', 'x_mm', 'A_y_mm', 'B_y_mm', 'mini_DS_probe', 'mini_DP_probe', 'frozen_R2_DS_probe', 'frozen_R2_DP_probe', 'OEM_signal'])
        writer.writeheader()
        for row, mapping in zip(rows, endpoint['mapping']):
            if row['net'] != mapping['net']:
                raise ValueError('coupon/BM28 identity mismatch')
            writer.writerow({**row, 'mini_DS_probe': 'TP'+row['net'][1:], 'mini_DP_probe': 'TP'+row['net'][1:], 'frozen_R2_DS_probe': mapping['DS_testpoint'], 'frozen_R2_DP_probe': mapping['DP_testpoint'], 'OEM_signal': ''})
    export_rows = []
    for end in ('A', 'B'):
        for name, shape in local_endpoint_parts(config, end).items():
            if not shape.isValid() or len(shape.Solids()) != 1 or shape.Volume() <= 0:
                raise ValueError('invalid endpoint fabrication body')
            path = output/f'{end}_{name}.step'
            cq.exporters.export(shape, str(path))
            if 'jaw' in name:
                cq.exporters.export(shape, str(output/f'{end}_{name}.stl'))
            reopened = cq.importers.importStep(str(path)).val()
            if not reopened.isValid() or len(reopened.Solids()) != 1 or abs(reopened.Volume()-shape.Volume()) > 1e-6:
                raise ValueError('endpoint STEP export differs from source')
            export_rows.append({'path': path.name, 'sha256': sha(path), 'volume_mm3': shape.Volume()})
    result = {'schema': 'razr-flex-coupon-source-v1', **facts, 'definition': c,
              'endpoint_exports': export_rows, 'native_KiCad_DRC_executed': False,
              'native_KiCad_Gerber_export_executed': False,
              'copper_artwork_file': 'continuity26.kicad_pcb',
              'mechanical_cut_file': 'coupon-cut-and-stiffener.dxf',
              'static_endpoint_source': 'electrical/mini-endpoints (new routed boards); exact J1 frozen from '+str(ENDPOINT),
              'motion_life_or_phone_electrical_qualification': False,
              'prototype_artwork_and_clamp_solids_defined': True,
              'supplier_finished_stackup_confirmation_required': True,
              'phone_fixture_fabrication_go': False, 'manufacturing_go': False}
    (output/'coupon-source-report.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def travel_manual_state(slide,descent):
    from dataclasses import asdict
    from product_motion import Pose
    return asdict(Pose(slide=slide,descent=descent,left_tab=3.,right_tab=3.))


def current_shared_scene(slide,descent,manual_state=None):
    from product_assembly import product_scene,registered_components
    import oled_storage
    state=manual_state or travel_manual_state(slide,descent)
    from product_motion import Pose
    Pose(**state)
    if state['slide']!=slide or state['descent']!=descent:raise ValueError('manual and material pose disagree')
    scene,metadata=product_scene(slide_mm=slide,descent_mm=descent,left_tab_mm=state['left_tab'],right_tab_mm=state['right_tab'],open_hold=state['hold_screws']>0,open_support=state['support_insert'])
    if state['hold_screws']==1:scene.pop('R_OPEN_HOLD_M1_NOMINAL')
    metadata={**metadata,'exact_manual_state':state,'installed_mechanical_parts':len(scene)}
    scene.update(registered_components(slide_mm=slide,descent_mm=descent))
    oled,oled_meta=oled_storage.geometry(slide_mm=slide,descent_mm=descent)
    scene['OLED_GEOMETRIC_TRIAL']=oled
    metadata={**metadata,'registered_product_allocations_included':True,'finite_OLED_included':True,'OLED_metadata':oled_meta}
    return scene,metadata


def shape_witness(shape,scene,*,first_failure=True):
    """Native positive common rejects the pose; an AABB overlap never proves collision."""
    from product_assembly import bounds
    box=bounds(shape);rows=[]
    for name,obstacle in scene.items():
        b=bounds(obstacle);gap=max(b[0]-box[1],box[0]-b[1],b[2]-box[3],box[2]-b[3],b[4]-box[5],box[4]-b[5])
        if gap>1e-7:continue
        try:
            common=shape.intersect(obstacle);solids=common.Solids()
            if any(not s.isValid() or s.Volume()<=0 for s in solids):raise ValueError('invalid common solid')
            volume=sum(s.Volume() for s in solids)
            if volume>min(shape.Volume(),obstacle.Volume())+1e-5:raise ValueError('common exceeds participant')
            if volume>1e-7:
                rows.append({'part':name,'native_common_mm3':volume,'interference':True,'AABB_alone_used_to_reject':False})
                if first_failure:break
        except Exception as exc:
            rows.append({'part':name,'native_evaluation_failed':True,'error':str(exc),'interference':True,'positive_collision_proved':False})
            if first_failure:break
    return {'scene_participants':len(scene),'first_decisive_rejection_only':first_failure,'failures':rows,'sampled_pose_clear':not rows,'clearance_distance_or_continuous_pass_proven':False}


def shared_scene_collisions(shape,slide,descent):
    scene,metadata=current_shared_scene(slide,descent)
    return {'scene_metadata':metadata,**shape_witness(shape,scene)}


def motion_poses():
    forward=[('SLIDE',float(s),0.) for s in np.linspace(0,79.75,17)]
    forward += [('SEAT',79.75,float(d)) for d in np.linspace(0,8.2,9)[1:]]
    return forward+[('RETURN_'+phase,s,d) for phase,s,d in reversed(forward[:-1])]


def export_motion(config,output,*,native=False,phone_scene=False):
    import cadquery as cq
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    input_paths=[Path(__file__),CONFIG,ROOT/'integration/product_interfaces.py',ROOT/'integration/product_assembly.py',ROOT/'integration/product_motion.py',ROOT/'design/product_geometry.json',ROOT/'integration/oled_storage.py']
    input_snapshot={str(path.relative_to(ROOT)):sha(path) for path in input_paths}
    rows=[];arrays={};cache={};extremes={(0.,0.):'STOW',(79.75,0.):'PREDOCK',(79.75,8.2):'OPEN_SEATED'}
    local_parts={e:local_endpoint_parts(config,e) for e in ('A','B')}
    for i,(phase,slide,descent) in enumerate(motion_poses()):
        sections,report=route_pose(config,slide,descent)
        key=(slide,descent);name=f'{i:03}_{phase}'
        arrays[name+'_s']=sections['s'];arrays[name+'_corners']=sections['corners']
        report.update(index=i,phase=phase,manual_state=travel_manual_state(slide,descent))
        if key in cache:
            previous=cache[key]
            if not np.array_equal(sections['corners'],previous['corners']):raise ValueError('reverse material state differs')
            report.update(native=previous['native'],phone_scene=previous['phone_scene'],reverse_same_material_and_obstacles_verified=True,reused_native_geometry_evaluation_for_identical_pose=True)
        elif native:
            material,native_report=finite_material_solid(sections['corners'])
            parts={'finite_material':material}
            for end in ('A','B'):parts.update(place_endpoint(local_parts[end],sections,end))
            full=cq.Compound.makeCompound(list(parts.values()))
            native_report['complete_assembly_part_count']=len(parts)
            if key in extremes:
                path=output/(extremes[key]+'_full_endpoint_and_material.step');cq.exporters.export(full,str(path))
                reread=cq.importers.importStep(str(path)).val()
                if len(reread.Solids())!=len(parts) or any(not q.isValid() or q.Volume()<=0 for q in reread.Solids()):raise ValueError('full STEP reread failed')
                native_report.update(path=path.name,sha256=sha(path),reimport_valid_positive_solids=len(reread.Solids()))
            collision={}
            if phone_scene:
                scene,meta=current_shared_scene(slide,descent)
                collision={'factory':'integration/product_assembly.py:product_scene','scene_participants':len(scene),'registered_product_allocations_included':True,'finite_OLED_included':True,'material':shape_witness(material,scene),'A_complete_endpoint':shape_witness(cq.Compound.makeCompound([v for k,v in parts.items() if k.startswith('A_')]),scene),'B_complete_endpoint':shape_witness(cq.Compound.makeCompound([v for k,v in parts.items() if k.startswith('B_')]),scene)}
                collision['sampled_complete_pose_clear']=all(collision[k]['sampled_pose_clear'] for k in ('material','A_complete_endpoint','B_complete_endpoint'))
            report.update(native=native_report,phone_scene=collision)
            cache[key]={'corners':sections['corners'],'native':native_report,'phone_scene':collision,'parts':parts}
            print(json.dumps({'motion_pose':i,'slide_mm':slide,'descent_mm':descent,'clear':collision.get('sampled_complete_pose_clear'),'radius_mm':report['analytic_minimum_centerline_radius_mm']}),flush=True)
        rows.append(report)
        # Atomic checkpoint after each actually completed native pose.
        checkpoint=output/'motion-progress.json';checkpoint.write_text(json.dumps({'completed_poses':rows,'all_motion_completed':False},indent=2)+'\n')
    np.savez_compressed(output/'material-stations.npz',**arrays)
    from product_motion import manual_program
    program=manual_program();manual_rows=[]
    if native and phone_scene:
        for i,state in enumerate(program['poses']):
            slide,descent=state['slide'],state['descent'];parts=cache[(slide,descent)]['parts']
            scene,meta=current_shared_scene(slide,descent,state)
            checks={'material':shape_witness(parts['finite_material'],scene),'A_complete_endpoint':shape_witness(cq.Compound.makeCompound([v for k,v in parts.items() if k.startswith('A_')]),scene),'B_complete_endpoint':shape_witness(cq.Compound.makeCompound([v for k,v in parts.items() if k.startswith('B_')]),scene)}
            manual_rows.append({'index':i,'state':state,'mechanical_participants':meta['installed_mechanical_parts'],'all_participants':len(scene),'checks':checks,'sampled_complete_pose_clear':all(r['sampled_pose_clear'] for r in checks.values())})
    # Actual installation path attempt: complete endpoint rigidly lowered from +Z
    # into the declared world station. No clearance means no assembly approval.
    install=[]
    if native and phone_scene:
        sections,_=route_pose(config,0,0);scene,_=current_shared_scene(0,0,program['poses'][0])
        for end in ('A','B'):
            installed=place_endpoint(local_parts[end],sections,end)
            body=cq.Compound.makeCompound(list(installed.values()))
            path=[]
            for offset in [12.,9.,6.,3.,0.]:
                witness=shape_witness(body.translate((0,0,offset)),scene)
                path.append({'translation_world_Z_mm':offset,**witness})
            install.append({'endpoint':end,'candidate_path':'straight -Z insertion from +12mm; closed current scene retained','samples':path,'assembly_path_accepted':False,'requires_disassembly_access_or_new_mounting_bosses':True})
    rejected=sum(bool(r.get('phone_scene')) and not r['phone_scene'].get('sampled_complete_pose_clear',False) for r in rows)
    if any(sha(ROOT/name)!=digest for name,digest in input_snapshot.items()):raise ValueError('source or scene input changed during complete motion evaluation')
    result={'input_sha256':input_snapshot,'exact_bounds_api':'product_assembly.bounds/AddOptimal(useTriangulation=False)','manual_program':program,'manual_program_states':manual_rows,'manual_state_count':len(manual_rows),'manual_program_all_states_rejected':all(not r['sampled_complete_pose_clear'] for r in manual_rows),'schema':'razr-product-flex-material-study-v2','source_sha256':sha(Path(__file__)),'config_sha256':sha(CONFIG),'common_scene_api':config['route_study']['common_scene_api'],'shared_scene_source_sha256':sha(ROOT/'integration/product_assembly.py'),'geometry_config_sha256':sha(ROOT/'design/product_geometry.json'),'OLED_source_sha256':sha(ROOT/'integration/oled_storage.py'),'fixed_free_material_length_mm':config['route_study']['fixed_free_material_length_mm'],'equal_material_base_station_count':config['route_study']['stations'],'all_phases_use_same_equal_s_material_labels':True,'pose_count':len(rows),'unique_native_pose_count':len(cache),'complete_forward_slide_seating_and_reverse_sampled':True,'pose_step_mm':{'slide':79.75/16,'descent':8.2/8},'poses':rows,'rejected_complete_pose_count':rejected,'installation_path_attempts':install,'material_artifact_sha256':sha(output/'material-stations.npz'),'native_export_executed':native,'current_phone_scene_checked':phone_scene,'all_motion_clearance_proven':False,'smooth_interpose_swept_volume_proven':False,'supplier_dynamic_qualified':False,'actual_endpoints_installed':False,'candidate_go':False,'manufacturing_go':False,'qualification_boundary':'negative candidate result; sample spacing is never used as continuous clearance or fatigue certification'}
    (output/'motion-report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def _balanced_expression(text, start):
    depth, quoted, escaped = 0, False, False
    for i in range(start, len(text)):
        ch=text[i]
        if quoted:
            if escaped: escaped=False
            elif ch=='\\': escaped=True
            elif ch=='"': quoted=False
        elif ch=='"': quoted=True
        elif ch=='(': depth+=1
        elif ch==')':
            depth-=1
            if depth==0: return text[start:i+1]
    raise ValueError('incomplete native footprint')


def mini_endpoint_pcb(side):
    """New routed 12 x 12 mm board, exact original owned J1 footprint."""
    from product_interfaces import sexp, children
    if side not in ('DP','DS'): raise ValueError('DP or DS required')
    source=(ROOT/ENDPOINT/f'endpoint_{side}.kicad_pcb').read_text()
    start=source.index('(footprint ')
    footprint=_balanced_expression(source,start)
    native=sexp(footprint)
    pads=children(native,'pad')
    header=source[:start].replace('razr_owned_coupon_r2','razr_product_mini_endpoint')
    mini_stack='(stackup (layer "F.SilkS" (type "Top Silk Screen")) (layer "F.Paste" (type "Top Solder Paste")) (layer "F.Mask" (type "Top Solder Mask") (thickness .010)) (layer "F.Cu" (type "copper") (thickness .035)) (layer "dielectric 1" (type "core") (thickness .710) (material "FR4_REQUEST_UNCONFIRMED")) (layer "B.Cu" (type "copper") (thickness .035)) (layer "B.Mask" (type "Bottom Solder Mask") (thickness .010)) (layer "B.Paste" (type "Bottom Solder Paste")) (layer "B.SilkS" (type "Bottom Silk Screen")) (copper_finish "None") (dielectric_constraints no))'
    header=header.replace('(setup (pad_to_mask_clearance 0))','(setup '+mini_stack+' (pad_to_mask_clearance 0))')
    lines=[header,footprint]
    routes=[]
    # Monotonic fanout keeps all copper outside the exact supplier land pattern.
    for pad in pads:
        pin=pad[1]
        if not pin.startswith('S_'): continue
        x,y=map(float,children(pad,'at')[0][1:3])
        net=int(children(pad,'net')[0][1]); name=children(pad,'net')[0][2]
        j=int(pin.rsplit('_',1)[1]); sign=-1 if y<0 else 1
        target=((j-5.5)*.7,sign*4.15)
        path=[(x,y),(x,sign*1.45),(target[0],sign*3.3),target]
        routes.append({'net':name,'site':pin,'target_xy_mm':list(target),'polyline_local_mm':[list(p) for p in path],'width_mm':.1})
    for pin,sgn in [('P_L',-1),('P_R',1)]:
        lands=[p for p in pads if p[1]==pin]
        net=int(children(lands[0],'net')[0][1]);name=children(lands[0],'net')[0][2]
        target=(sgn*4.8,0.)
        for pad in lands:
            x,y=map(float,children(pad,'at')[0][1:3])
            path=[(x,y),(sgn*3.25,y),(sgn*3.25,0.),target]
            routes.append({'net':name,'site':pin,'target_xy_mm':list(target),'polyline_local_mm':[list(p) for p in path],'width_mm':.12})
    seen=set()
    for row in routes:
        code=int(row['net'][1:]);path=row['polyline_local_mm']
        for a,b in zip(path,path[1:]):
            if a==b: continue
            lines.append(f'(segment (start {100+a[0]:.6f} {100+a[1]:.6f}) (end {100+b[0]:.6f} {100+b[1]:.6f}) (width {row["width_mm"]}) (layer "F.Cu") (net {code}))')
        if row['net'] in seen: continue
        seen.add(row['net']);x,y=row['target_xy_mm']
        sx,sy=(.6,1.2) if row['site'].startswith('P_') else (.45,1.2)
        pad_type='HAND_SOLDER_PAD_060x120' if row['site'].startswith('P_') else 'HAND_SOLDER_PAD_045x120'
        lines.append(f'(footprint "RAZR_RESEARCH:{pad_type}" (layer "F.Cu") (at {100+x:.6f} {100+y:.6f}) (attr smd) (fp_text reference "TP{code:02}" (at 0 0) (layer "F.Fab") hide (effects (font (size .5 .5) (thickness .08)))) (fp_text value "OWNED_{row["site"]}" (at 0 0) (layer "F.Fab") hide (effects (font (size .5 .5) (thickness .08)))) (pad "1" smd rect (at 0 0) (size {sx} {sy}) (layers "F.Cu" "F.Mask") (net {code} "{row["net"]}")))')
    for i,(x,y) in enumerate([(-5,-4.7),(5,-4.7),(-5,4.7),(5,4.7)],1):
        lines.append(f'(footprint "RAZR_RESEARCH:M1_NPTH" (layer "F.Cu") (at {100+x} {100+y}) (attr through_hole exclude_from_bom exclude_from_pos_files) (fp_text reference "H{i}" (at 0 0) (layer "F.Fab") hide (effects (font (size .5 .5) (thickness .08)))) (fp_text value "1.4mm_NPTH" (at 0 0) (layer "F.Fab") hide (effects (font (size .5 .5) (thickness .08)))) (pad "" np_thru_hole circle (at 0 0) (size 1.4 1.4) (drill 1.4) (layers "*.Cu" "*.Mask")))')
    for a,b in [((94,94),(106,94)),((106,94),(106,106)),((106,106),(94,106)),((94,106),(94,94))]:
        lines.append(f'(gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (layer "Edge.Cuts") (width .05))')
    lines.append(')')
    return '\n'.join(lines)+'\n',routes,hashlib.sha256(footprint.encode()).hexdigest()


def export_mini_endpoints(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    result={'schema':'razr-mini-endpoint-v1','dimensions_mm':[12,12,.8],'signal_assignment':'owned C01-C26 only, no manufacturer pin1 or OEM signals','boards':{},'prototype_electrical_or_dynamic_qualification':False}
    for side in ('DP','DS'):
        pcb,routes,footprint_sha=mini_endpoint_pcb(side)
        stem='mini_'+side
        (output/(stem+'.kicad_pcb')).write_text(pcb)
        project={'board':{'design_settings':{'rules':{'min_clearance':.1,'min_track_width':.1,'min_copper_edge_clearance':.5,'min_hole_clearance':.2}}},'meta':{'filename':stem+'.kicad_pro','version':1}}
        project['net_settings']={'classes':[{'name':'Default','clearance':.1,'track_width':.15,'via_diameter':.6,'via_drill':.3,'diff_pair_width':.15,'diff_pair_gap':.1,'diff_pair_via_gap':.25}], 'meta':{'version':3}}
        (output/(stem+'.kicad_pro')).write_text(json.dumps(project,indent=2)+'\n')
        (output/(stem+'-routes.json')).write_text(json.dumps(routes,indent=2)+'\n')
        from product_interfaces import pcb_pins
        pins,counts=pcb_pins(pcb.encode())
        if len(pins)!=52 or len(set(pins.values()))!=26: raise ValueError('mini board terminal identity incomplete')
        result['boards'][side]={'path':stem+'.kicad_pcb','sha256':sha(output/(stem+'.kicad_pcb')),'frozen_J1_footprint_sha256':footprint_sha,'unique_electrical_pins':len(pins),'owned_nets':len(set(pins.values())),**counts,'native_DRC_executed_here':False}
    (output/'mini-source-report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=CONFIG)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--coupon', action='store_true')
    parser.add_argument('--motion', action='store_true')
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--phone-scene', action='store_true')
    args = parser.parse_args()
    if args.phone_scene and not args.native:
        parser.error('--phone-scene requires --native')
    config = load_config(args.config)
    if args.coupon:
        export_mini_endpoints(args.output/'mini-endpoints')
        result = export_coupon(config, args.output/'coupon')
        print(json.dumps({'coupon_channels': result['channels'], 'mechanical_parts': len(result['endpoint_exports'])}))
    if args.motion:
        result = export_motion(config, args.output/'motion', native=args.native, phone_scene=args.phone_scene)
        print(json.dumps({'motion_poses': len(result['poses']), 'candidate_go': result['candidate_go']}))
