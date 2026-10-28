"""Independent reconstruction of V5 conditional trim-model boundary and partition certificates.

The producer/refiner is not imported. The earlier separate certificate checker
is reused only for complete-boundary channel inequalities and blocked records.
"""
import argparse
from collections import Counter
from fractions import Fraction as Q
import gzip
import hashlib
import importlib.util
from itertools import product
import json
from pathlib import Path
import resource
import time
import traceback


def need(ok,message):
    if not ok:raise ValueError(message)


def require_conditional_scope(record):
    need(record['conditional_trim_model_only'] is True and record['native_trim_class_membership_verified'] is False and
         record['inner_wire_hole_semantics_verified_for_native'] is False and record['original_raw_gate_reclassified'] is False and
         record['full_continuous_G2'] is False,'conditional-model scope must not become native or original raw qualification')


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def bound(record,parent=None):
    path=Path(record['path']) if parent is None else parent/record['path']
    need(path.stat().st_size==record['bytes'] and digest(path)==record['sha256'],'input identity differs');return path


def load_checker(contract):
    path=bound(contract['base_verifier_source']);spec=importlib.util.spec_from_file_location('r5e_v5_separate_channel_checker',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def complete_phase(producer,contract,baseline,selection):
    phase=contract['expected_phase'];need(producer['phase']==phase,'actual phase differs')
    expected=[tuple(x) for x in contract['expected_case_frames']]
    actual=[(r['case_id'],r['frame']) for r in producer['frames']]
    original=[(r['case_id'],r['frame']) for r in baseline['frames']]
    need(len(actual)==len(set(actual)) and len(expected)==len(set(expected)),'duplicate frame')
    need(actual==expected,'missing, extra or reordered frame')
    if phase=='all_trim_model_frames':need(actual==original and len(actual)==16,'all original16 frames required')
    elif phase=='single_trim_model_cell':
        selected=(selection['case_id'],selection['frame'])
        need(actual==expected==[selected] and selected in original,'exact original selected case/frame required')
    else:raise ValueError('unexpected verification phase')


def phase_controls(producer,contract,baseline,selection):
    rows=[]
    for name,changes in [('missing-frame',{'frames':producer['frames'][:-1]}),
                         ('duplicate-frame',{'frames':producer['frames']+[producer['frames'][0]]}),
                         ('incorrect-phase',{'phase':'preflight_trim_model'})]:
        error=None
        try:complete_phase(dict(producer,**changes),contract,baseline,selection)
        except ValueError as exc:error=str(exc)
        need(error is not None,'bad phase control accepted');rows.append({'name':name,'actual_rejected':True,'reason':error})
    return rows


def root_coverage(frame,certificate,expected_indices):
    need(frame['root_original_cell_indices']==expected_indices and
         [r['original_cell_index'] for r in certificate['roots']]==expected_indices and
         frame['root_count']==len(expected_indices),
         'missing, extra, duplicate or reordered original root cells')


def root_controls(frame,certificate,expected_indices):
    rows=[]
    for name,roots in [('omitted-original-root',certificate['roots'][:-1]),
                       ('duplicate-original-root',certificate['roots']+[certificate['roots'][0]])]:
        error=None
        try:root_coverage(frame,dict(certificate,roots=roots),expected_indices)
        except ValueError as exc:error=str(exc)
        need(error is not None,'bad root coverage accepted');rows.append({'name':name,'actual_rejected':True,'reason':error})
    return rows


def verify_tree(base,tree,root,sources,limits):
    nodes=tree['nodes'];need(nodes and all(type(n['id']) is int and n['id']==i for i,n in enumerate(nodes)),'contiguous explicit tree identities')
    stack=[(0,root,0)];seen=set();kept=Q(0);removed=Q(0);splits=leaves=excluded=checked=0;depth_max=0
    sample=None;split_sample=None;reasons={}
    while stack:
        index,cell,depth=stack.pop();need(index not in seen and 0<=index<len(nodes),'duplicate, cyclic or missing tree node');seen.add(index)
        node=nodes[index];value=base.signed_measure(cell);depth_max=max(depth_max,depth)
        need(depth<=limits['maximum_depth'],'path depth budget exceeded')
        if node['kind']=='split':
            axis=node['axis'];need(type(axis) is int and 0<=axis<3,'split axis')
            point=Q(node['cut_exact']);need(cell[axis][0]<point<cell[axis][1],'split strictly inside parent required')
            w=node['cut_source'];s,i,k,e=w['material_side'],w['piece_index'],w['axis'],w['endpoint']
            need(type(s) is int and 0<=s<len(sources) and type(i) is int and 0<=i<len(sources[s][0]),'cut source piece index')
            need(type(k) is int and k==axis and type(e) is int and e in (0,1),'cut source coordinate')
            need(point==sources[s][0][i][axis][e],'cut is not a registered trim-model boundary endpoint')
            child=node['children'];need(type(child) is list and len(child)==2 and all(type(x) is int and index<x<len(nodes) for x in child) and child[0]!=child[1],'two distinct forward child indices required')
            a=list(cell);b=list(cell);a[axis]=(cell[axis][0],point);b[axis]=(point,cell[axis][1])
            av,bv=base.signed_measure(a),base.signed_measure(b)
            need(av+bv==value and Q(node['parent_positive_directed_volume_exact'])==value,'parent directed volume conservation')
            need(list(map(Q,node['children_positive_directed_volumes_exact']))==[av,bv],'child directed volumes differ')
            need(node['closed_cut_plane_retained_as_zero_volume_carrier'] is True,'closed cut carrier omitted')
            stack.extend([(child[1],b,depth+1),(child[0],a,depth+1)]);splits+=1
            if split_sample is None:split_sample=(index,cell)
        elif node['kind']=='excluded':
            need(Q(node['positive_directed_volume_exact'])==value,'excluded leaf volume differs')
            checked+=base.check_exclusion(node['certificate'],cell,sources);removed+=value;leaves+=1;excluded+=1
            if sample is None:sample=(node['certificate'],cell)
        elif node['kind']=='retained':
            need(Q(node['positive_directed_volume_exact'])==value and node['actual_material_interference_claimed'] is False,'retained full directed volume/scope differs')
            reason=node['reason'];need(reason in ['tiny_exact_volume_retained','global_predicate_budget_retained','path_depth_limit_retained','global_split_limit_retained','no_registered_model_boundary_endpoint_inside_cell'],'unregistered retention reason')
            if reason=='tiny_exact_volume_retained':need(value<=Q(limits['tiny_retained_volume_exact']),'tiny retained leaf threshold differs')
            if reason=='path_depth_limit_retained':need(depth==limits['maximum_depth'],'incorrect path-depth stop')
            if 'actual_channel_observation' in node:
                observation=node['actual_channel_observation']
                need(observation['excluded_open_interior'] is False and observation['actual_material_interference_claimed'] is False,'retained observation overclaims material collision')
                if not observation.get('search_stopped_at_predicate_budget'):base.check_blocked(observation,cell,sources)
            kept+=value;leaves+=1;reasons[reason]=reasons.get(reason,0)+1
        else:raise ValueError('unknown partition tree disposition')
    need(len(seen)==len(nodes),'unreachable or unvisited tree node')
    need(kept+removed==base.signed_measure(root),'root volume not conserved')
    need(kept==Q(tree['retained_sum_exact']) and removed==Q(tree['excluded_open_sum_exact']),'tree sums differ')
    need(leaves==tree['total_leaf_count'] and excluded==tree['excluded_leaf_count'] and leaves-excluded==tree['retained_leaf_count'],'tree leaf counts differ')
    need(reasons==tree['retained_reason_counts'] and depth_max==tree['maximum_depth_reached'],'tree stop/depth metadata differs')
    need(tree['all_closed_cut_planes_and_root_boundaries_retained'] is True,'closed zero-volume carriers omitted')
    need(len(nodes)==2*splits+1 and leaves==splits+1,'full binary partition topology count')
    return {'kept':kept,'removed':removed,'nodes':len(nodes),'splits':splits,'leaves':leaves,'excluded_leaves':excluded,
            'checked_boundary_pieces':checked,'sample_exclusion':sample,'sample_split':split_sample,'depth':depth_max}


def reject_tree_mutation(base,tree,root,sources,limits,name,alter):
    changed=json.loads(json.dumps(tree));alter(changed)
    error=None
    try:verify_tree(base,changed,root,sources,limits)
    except (ValueError,IndexError,KeyError,TypeError) as exc:error=str(exc)
    need(error is not None,'corrupt partition accepted: '+name)
    return {'name':name,'actual_rejected':True,'reason':error}


def split_controls(base,tree,root,sources,limits):
    checked=verify_tree(base,tree,root,sources,limits)
    need(checked['sample_split'] is not None,'split mutation requires an actual eligible split')
    selected,parent=checked['sample_split']
    edits=[
        ('omitted-partition-child',lambda t:t['nodes'][selected].update(children=t['nodes'][selected]['children'][:1])),
        ('duplicated-partition-child',lambda t:t['nodes'][selected].update(children=[t['nodes'][selected]['children'][0]]*2)),
        ('cut-on-parent-boundary',lambda t:t['nodes'][selected].update(cut_exact=str(parent[t['nodes'][selected]['axis']][0]))),
        ('discarded-closed-cut-plane',lambda t:t['nodes'][selected].update(closed_cut_plane_retained_as_zero_volume_carrier=False)),
        ('incorrect-positive-directed-volume',lambda t:t['nodes'][selected].update(parent_positive_directed_volume_exact='0')),
    ]
    return [reject_tree_mutation(base,tree,root,sources,limits,name,edit) for name,edit in edits]


def leaf_controls(base,tree,root,sources,limits):
    # These controls remain applicable even when the real tree has no split or
    # no excluded leaf. Their scope is an existing positive leaf, not a claim
    # that the producer observed exclusion or tiny-volume retention.
    verify_tree(base,tree,root,sources,limits)
    leaf=min((n for n in tree['nodes'] if n['kind']!='split'),
             key=lambda n:Q(n['positive_directed_volume_exact']))
    index=leaf['id'];need(Q(leaf['positive_directed_volume_exact'])>0,'positive control leaf required')
    rows=[
        reject_tree_mutation(base,tree,root,sources,limits,'omitted-allocated-leaf-node',
                             lambda t:t['nodes'].pop(index)),
        reject_tree_mutation(base,tree,root,sources,limits,'discarded-smallest-selected-tree-leaf-volume',
                             lambda t:t['nodes'][index].update(positive_directed_volume_exact='0')),
    ]
    for row in rows:
        row.update(original_leaf_id=index,original_leaf_kind=leaf['kind'],
                   original_leaf_reason=leaf.get('reason'),
                   original_positive_volume_exact=leaf['positive_directed_volume_exact'])
    return rows


def encode_box(box):
    return [[str(a),str(b)] for a,b in box]


def ranges(value,dimension):
    need(type(value) is list and len(value)==dimension,'registered box dimension')
    result=[]
    for interval in value:
        need(type(interval) is list and len(interval)==2,'two interval endpoints required')
        a,b=map(Q,interval);need(a<=b,'reversed exact interval');result.append((a,b))
    return tuple(result)


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def identity_location(location):
    return [[Q(v) for v in row] for row in location['matrix_3x4_exact']]==[
        [Q(1),Q(0),Q(0),Q(0)],[Q(0),Q(1),Q(0),Q(0)],[Q(0),Q(0),Q(1),Q(0)]]


def load_trim_source(contract,baseline,original_report_identity):
    with gzip.open(bound(contract['trim_source_bundle']),'rt') as stream:bundle=json.load(stream)
    need(bundle['schema']=='razr-r5e-original-planar-trim-source-projection-v5','trim source schema')
    need(bundle['native_trim_class_membership_verified'] is False and bundle['new_mathematical_qualification'] is False and
         bundle['original_pcurve_values_changed'] is False and bundle['new_native_operations']==0,'source projection overclaims qualification')
    need(bundle['original_public_R4_report_identity']=={k:original_report_identity[k] for k in ('bytes','sha256')},
         'source bundle original public report differs')
    inventory=[r for r in baseline['input_identities'] if r['path']==bundle['original_native_inventory_relative_path']]
    need(len(inventory)==1 and bundle['original_native_inventory_identity']=={k:inventory[0][k] for k in ('bytes','sha256')},
         'source bundle original native inventory identity differs')
    records={}
    for record in bundle['records']:
        key=(record['input']['case_id'],record['input']['material_id']);need(key not in records,'duplicate source material')
        need(record['full_original_face_records_unchanged'] is True,'changed original face source')
        faces=record['candidate_faces'];need(len({f['face_index'] for f in faces})==len(faces),'duplicate candidate face')
        for candidate in faces:
            face=candidate['complete_original_face']
            need(face['index']==candidate['face_index'] and canonical_sha(face)==candidate['complete_original_face_canonical_sha256'],
                 'complete original face identity differs')
            indices=candidate['candidate_inner_wire_indices'];need(indices and len(set(indices))==len(indices),'candidate wire identities')
            available={w['index'] for w in face['wires']};need(set(indices)<=available,'candidate wire absent from complete source')
        records[key]=record
    bindings={}
    for item in bundle['frame_bindings']:
        key=(item['case_id'],item['frame']);need(key not in bindings,'duplicate source frame binding');bindings[key]=item
    original=[(r['case_id'],r['frame']) for r in baseline['frames']]
    need(list(bindings)==original and len(bindings)==16 and len(records)==32,'complete original16/32 source projection required')
    used={tuple(key) for item in bindings.values() for key in item['moving_and_fixed_material_keys']}
    need(used==set(records),'source material/frame projection coverage differs')
    return records,bindings


def independent_hole(wire):
    """Exact line endpoints and a conditional corner-closure model only."""
    need(wire['is_outer'] is False and identity_location(wire['location']),'registered inner wire with identity location required')
    occurrences=wire['edge_occurrences'];need(len(occurrences)==4,'four complete line occurrences required')
    segments=[];vertical=[];horizontal=[]
    for index,occurrence in enumerate(occurrences):
        need(identity_location(occurrence['location']),'identity occurrence location required')
        curve=occurrence['pcurve'];need(curve['type']=='GeomAbs_CurveType.GeomAbs_Line','nonlinear inner wire is unsupported')
        direction=tuple(map(Q,curve['direction_exact']));origin=tuple(map(Q,curve['origin_exact']))
        need(direction in ((Q(1),Q(0)),(Q(-1),Q(0)),(Q(0),Q(1)),(Q(0),Q(-1))) and len(origin)==2,
             'axis-unit UV line required')
        lo,hi=Q(curve['first_parameter']['exact']),Q(curve['last_parameter']['exact']);need(lo<hi,'positive line parameter span')
        a=tuple(origin[k]+direction[k]*lo for k in range(2));b=tuple(origin[k]+direction[k]*hi for k in range(2))
        orientation=occurrence['orientation']
        need(orientation in ('TopAbs_Orientation.TopAbs_FORWARD','TopAbs_Orientation.TopAbs_REVERSED'),'unregistered occurrence orientation')
        if orientation.endswith('REVERSED'):a,b=b,a
        segments.append((a,b))
        (vertical if direction[0]==0 else horizontal).append(a[0] if direction[0]==0 else a[1])
    need(len(vertical)==len(horizontal)==2 and len(set(vertical))==len(set(horizontal))==2,'two distinct sides per UV axis')
    u0,u1=sorted(vertical);v0,v1=sorted(horizontal);corners=[(u0,v0),(u1,v0),(u1,v1),(u0,v1)]
    arrows=[];delta=Q(0);offsets=[]
    for a,b in segments:
        side=[i for i,c in enumerate(corners) if (c[0]==a[0] if a[0]==b[0] else c[1]==a[1])]
        need(len(side)==2,'segment does not lie on an ideal side')
        endpoint_indices=[];pair_offsets=[]
        for endpoint in (a,b):
            distances=[max(abs(endpoint[k]-corners[i][k]) for k in range(2)) for i in side]
            need(distances[0]!=distances[1],'ambiguous endpoint-to-corner assignment')
            corner=side[0] if distances[0]<distances[1] else side[1]
            endpoint_indices.append(corner);delta=max(delta,min(distances))
            pair_offsets.append(tuple(endpoint[k]-corners[corner][k] for k in range(2)))
        need(endpoint_indices[0]!=endpoint_indices[1],'degenerate ideal directed edge')
        arrows.append(endpoint_indices);offsets.append(pair_offsets)
    need(Counter(a for a,b in arrows)==Counter(range(4)) and Counter(b for a,b in arrows)==Counter(range(4)),
         'ideal corner in/out degree differs')
    successor=dict(arrows);cycle=[0]
    for _ in range(4):cycle.append(successor[cycle[-1]])
    need(cycle[-1]==0 and len(set(cycle[:-1]))==4,'single four-corner directed cycle required')
    signed_twice_area=sum(corners[a][0]*corners[b][1]-corners[b][0]*corners[a][1] for a,b in arrows)
    need(abs(signed_twice_area)==2*(u1-u0)*(v1-v0),'ideal cycle winding is not plus/minus one')
    need(4*delta<min(u1-u0,v1-v0),'corner uncertainty boxes are not separated')
    core=((u0+delta,u1-delta),(v0+delta,v1-delta))
    squares=[((u-delta,u+delta),(v-delta,v+delta)) for u,v in corners]
    return {'wire_index':wire['index'],
            'oriented_segments_exact':[{'occurrence_index':i,'start_exact':[str(x) for x in a],
                                       'end_exact':[str(x) for x in b]} for i,(a,b) in enumerate(segments)],
            'ideal_rectangle_exact':encode_box(((u0,u1),(v0,v1))),
            'directed_corner_indices':arrows,'uniform_corner_radius_exact':str(delta),
            'corner_squares_exact':[encode_box(square) for square in squares],
            'hole_core_exact':encode_box(core),'cycle_corner_indices':cycle,
            'native_closure_class_membership_verified':False,'inner_wire_hole_semantics_verified_for_native':False},offsets


def plane_parameters(face,stationary):
    plane=face['local_surface'];need(plane['type']=='GeomAbs_SurfaceType.GeomAbs_Plane','planar source required')
    need(identity_location(face['location']),'identity face location required')
    origin=tuple(map(Q,plane['origin_exact']));x=tuple(map(Q,plane['X_exact']));y=tuple(map(Q,plane['Y_exact']))
    need(len(origin)==len(x)==len(y)==3,'three-dimensional plane coefficients required')
    chosen=None
    for a,b in ((0,1),(0,2),(1,2)):
        determinant=x[a]*y[b]-x[b]*y[a]
        if determinant:
            chosen=(a,b);inverse=((y[b]/determinant,-y[a]/determinant),(-x[b]/determinant,x[a]/determinant));break
    need(chosen is not None,'rank-two plane required')
    centered=[(stationary[k][0]-origin[k],stationary[k][1]-origin[k]) for k in chosen]
    outer=[]
    for row in inverse:
        low=high=Q(0)
        for coefficient,interval in zip(row,centered):
            values=[coefficient*v for v in interval];low+=min(values);high+=max(values)
        outer.append((low,high))
    return origin,x,y,chosen,inverse,tuple(outer)


def verify_uv_coverage(outer,cores,patches):
    """Finite exact endpoint strata, including edges/points; no sampling.

    Membership in every closed patch/open core is constant on each Cartesian
    stratum because all rectangle endpoints are grid coordinates. A required
    stratum is checked by interval containment, not by a numerical probe.
    """
    coordinates=[set(outer[k]) for k in range(2)]
    for core in cores:
        need(all(outer[k][0]<core[k][0]<core[k][1]<outer[k][1] for k in range(2)),
             'hole core must be strictly inside projected outer rectangle')
        for k in range(2):coordinates[k].update(core[k])
    for patch in patches:
        need(all(outer[k][0]<=patch[k][0]<=patch[k][1]<=outer[k][1] and
                 set(patch[k])<=coordinates[k] for k in range(2)),'UV patch escapes registered exact endpoint arrangement')
    strata=[]
    for values in coordinates:
        ordered=sorted(values);axis=[]
        for index,value in enumerate(ordered):
            axis.append((value,value))
            if index+1<len(ordered):axis.append((value,ordered[index+1]))
        strata.append(axis)
    def inside_open(part,core):
        return all(core[k][0]<a<core[k][1] if a==b else core[k][0]<=a<b<=core[k][1]
                   for k,(a,b) in enumerate(part))
    def inside_closed(part,patch):
        return all(patch[k][0]<=a<=b<=patch[k][1] for k,(a,b) in enumerate(part))
    def on_core_boundary(part,core):
        return inside_closed(part,core) and any(a==b and a in core[k] for k,(a,b) in enumerate(part))
    required=0
    for part in product(*strata):
        if not any(inside_open(part,core) for core in cores) or any(on_core_boundary(part,core) for core in cores):
            need(any(inside_closed(part,patch) for patch in patches),'UV closed coverage or a zero-dimensional carrier omitted')
            required+=1
    return {'exact_strata_checked':len(strata[0])*len(strata[1]),'required_closed_strata_covered':required,
            'closed_boundary_strata_included':True,'sampling_used':False}


def map_patch_to_stationary(uv,stationary,origin,x,y):
    result=[]
    for k in range(3):
        u=[x[k]*v for v in uv[0]];v=[y[k]*w for w in uv[1]]
        lo=max(stationary[k][0],origin[k]+min(u)+min(v))
        hi=min(stationary[k][1],origin[k]+max(u)+max(v))
        if lo>hi:return None
        result.append((lo,hi))
    return tuple(result)


def verify_boundary_refinement(proof,old,boundary,records,bindings,limits):
    need(boundary['schema']=='razr-r5e-conditional-planar-trim-boundary-v5','boundary refinement schema')
    need(boundary['conditional_trim_model_only'] is True and boundary['native_trim_class_membership_verified'] is False and
         boundary['inner_wire_hole_semantics_verified_for_native'] is False,'conditional trim-model scope must remain explicit')
    key=(old['case_id'],old['frame']);binding=bindings[key]
    need(binding['original_R4_raw_proof_identity']==old['proof'] and
         binding['original_full_D']==proof['full_remaining_displacement_box_exact'],'trim source frame identity or full D differs')
    cover=proof['complete_raw_boundary_slab_cover'];d=ranges(proof['full_remaining_displacement_box_exact'],3)
    actual_sources=boundary['sources'];need(type(actual_sources) is list and len(actual_sources)==2,'both complete material boundaries required')
    source_results=[];summary={'original_edges_vertices_preserved':0,'applied_faces':0,'unapplied_faces_preserved':0,
                               'hole_core_certificates_verified':0,'exact_UV_strata_checked':0,'new_boundary_pieces':0}
    for side,(source,input_name,piece_name,whole_name) in enumerate(zip(actual_sources,('moving_input','fixed_input'),
            ('first_complete_boundary_boxes','second_complete_boundary_boxes'),('first_whole_support_box_exact','second_whole_support_box_exact'))):
        material=tuple(binding['moving_and_fixed_material_keys'][side]);record=records[material]
        need(source['material_key']==list(material) and record['input']==proof[input_name],'original material identity differs')
        original=cover[piece_name]
        need(source['original_complete_piece_count']==len(original) and source['original_whole_support_box_exact']==cover[whole_name],
             'complete original boundary or whole box changed')
        counts=Counter(p['kind'] for p in original)
        need(all(counts[kind]==record['original_complete_boundary_counts'][plural]
                 for kind,plural in [('face','faces'),('edge','edges'),('vertex','vertices')]),'source complete boundary counts differ')
        candidates={f['face_index']:f for f in record['candidate_faces']}
        certificates=source['face_certificates'];need(len(certificates)==len(candidates),'candidate face certificate coverage differs')
        by_piece={};seen_faces=set();replacement={}
        for ci,certificate in enumerate(certificates):
            face_index=certificate['face_index'];index=certificate['original_piece_index']
            need(type(index) is int and 0<=index<len(original) and face_index in candidates and face_index not in seen_faces and
                 index not in by_piece,'duplicate or invalid original face mapping')
            piece=original[index];need(piece['kind']=='face' and piece['index']==face_index,'nonface boundary replacement')
            candidate=candidates[face_index];face=candidate['complete_original_face'];seen_faces.add(face_index);by_piece[index]=ci
            need(certificate['source_face_canonical_sha256']==candidate['complete_original_face_canonical_sha256'],'source face identity differs')
            need(type(certificate['applied']) is bool,'explicit face application status required')
            if not certificate['applied']:
                need(type(certificate['face_refinement_not_applied_reason']) is str and certificate['face_refinement_not_applied_reason'],
                     'conservative fallback reason required');summary['unapplied_faces_preserved']+=1;continue
            need(certificate['original_pcurve_values_changed'] is False and certificate['closed_hole_core_boundaries_retained'] is True and
                 certificate['native_trim_class_membership_verified'] is False and certificate['inner_wire_hole_semantics_verified_for_native'] is False,
                 'applied face scope or closed core carriers differ')
            original_box=ranges(piece['box_exact'],3)
            stationary=tuple((a-d[k][0],b-d[k][1]) if side==0 else (a,b) for k,(a,b) in enumerate(original_box))
            need(all(a<=b for a,b in stationary),'original moving face cannot be unswept by complete D')
            need(certificate['stationary_original_boundary_box_exact']==encode_box(stationary),'stationary original face differs')
            origin,x,y,axes,inverse,outer=plane_parameters(face,stationary)
            need(certificate['projection_axes']==list(axes) and
                 certificate['inverse_rows_exact']==[[str(v) for v in row] for row in inverse] and
                 certificate['uv_outer_box_exact']==encode_box(outer),'exact plane projection differs')
            wires={w['index']:w for w in face['wires']};holes=certificate['holes']
            need([h['wire_index'] for h in holes]==candidate['candidate_inner_wire_indices'],'complete candidate hole order differs')
            cores=[]
            for hole in holes:
                expected,offsets=independent_hole(wires[hole['wire_index']])
                for name,value in expected.items():need(hole[name]==value,'source-derived hole certificate differs: '+name)
                need(hole['endpoint_corner_offsets_exact']==[[[str(v) for v in offset] for offset in pair] for pair in offsets],
                     'actual endpoint-to-corner signed offsets differ')
                cores.append(ranges(expected['hole_core_exact'],2));summary['hole_core_certificates_verified']+=1
            patches=[ranges(p,2) for p in certificate['uv_closed_patch_boxes_exact']]
            need(len(patches)<=limits['maximum_uv_patches_per_face'],'registered UV patch capacity exceeded')
            coverage=verify_uv_coverage(outer,cores,patches);summary['exact_UV_strata_checked']+=coverage['exact_strata_checked']
            empty=[];retained=[];stationary_boxes=[];swept=[]
            for ui,uv in enumerate(patches):
                mapped=map_patch_to_stationary(uv,stationary,origin,x,y)
                if mapped is None:empty.append(ui);continue
                retained.append(ui);stationary_boxes.append(mapped)
                swept.append(tuple((a+d[k][0],b+d[k][1]) if side==0 else (a,b) for k,(a,b) in enumerate(mapped)))
            need(certificate['empty_uv_patch_indices']==empty and certificate['retained_uv_patch_indices']==retained,
                 'empty/nonempty UV patch partition differs')
            need(certificate['stationary_patch_boxes_exact']==[encode_box(p) for p in stationary_boxes] and
                 certificate['swept_patch_boxes_exact']==[encode_box(p) for p in swept],
                 'patch mapping, original-box intersection, or complete-D sweep differs')
            replacement[index]=[(ui,box) for ui,box in zip(retained,swept)];summary['applied_faces']+=1
        need(seen_faces==set(candidates),'candidate face lost')
        expected_pieces=[]
        for index,piece in enumerate(original):
            if index in replacement:
                for ui,box in replacement[index]:expected_pieces.append({'original_piece_index':index,'kind':piece['kind'],'index':piece['index'],
                       'replacement':'trim_patch','face_certificate_index':by_piece[index],'uv_patch_index':ui,'box_exact':encode_box(box)})
            else:
                expected_pieces.append({'original_piece_index':index,'kind':piece['kind'],'index':piece['index'],
                                        'replacement':'unchanged','box_exact':piece['box_exact']})
                if piece['kind'] in ('edge','vertex'):summary['original_edges_vertices_preserved']+=1
        need(len(source['pieces'])==len(expected_pieces)<=limits['maximum_boundary_pieces_per_material'],'complete replacement piece count/capacity differs')
        for declared,expected in zip(source['pieces'],expected_pieces):
            for name,value in expected.items():need(declared[name]==value,'replacement lineage or exact boundary box differs: '+name)
        boxes=[ranges(p['box_exact'],3) for p in expected_pieces];need(boxes,'nonempty complete boundary required')
        whole=tuple((min(p[k][0] for p in boxes),max(p[k][1] for p in boxes)) for k in range(3))
        need(source['whole_exact']==encode_box(whole),'new complete boundary hull differs')
        source_results.append((boxes,whole));summary['new_boundary_pieces']+=len(boxes)
    need(boundary['applied_face_count']==summary['applied_faces'] and boundary['applied_inner_wire_count']==summary['hole_core_certificates_verified'] and
         boundary['retained_original_face_count_after_rejection']==summary['unapplied_faces_preserved'],'trim refinement counts differ')
    summary.update(conditional_trim_model_only=True,native_trim_class_membership_verified=False,
                   inner_wire_hole_semantics_verified_for_native=False,original_raw_gate_reclassified=False)
    return source_results,summary


def boundary_controls(proof,old,boundary,records,bindings,limits):
    """Corrupt copies of actual conditional boundary certificates only."""
    applied=[(s,i) for s,source in enumerate(boundary['sources'])
             for i,face in enumerate(source['face_certificates']) if face['applied']]
    need(applied,'real applied-face controls require an eligible face')
    side,index=applied[0];rows=[]
    def reject(name,edit,locator):
        copied=json.loads(json.dumps(boundary));edit(copied);error=None
        try:verify_boundary_refinement(proof,old,copied,records,bindings,limits)
        except (ValueError,IndexError,KeyError,TypeError) as exc:error=str(exc)
        need(error is not None,'corrupt actual trim boundary accepted: '+name)
        rows.append({'name':name,'status':'executed','actual_rejected':True,'reason':error,
                     'actual_certificate_locator':locator,'original_case_id':old['case_id'],
                     'original_frame':old['frame'],'original_inputs_modified':False})
    def corrupt_core(copied):
        hole=copied['sources'][side]['face_certificates'][index]['holes'][0]
        # Expanding one real core endpoint would remove additional UV material.
        hole['hole_core_exact'][0][0]=str(Q(hole['hole_core_exact'][0][0])-1)
    locator={'material_side':side,'face_certificate_index':index,'hole_index':0}
    reject('expanded-actual-hole-core-endpoint',corrupt_core,locator)
    reject('omitted-actual-closed-UV-patches',
           lambda c:c['sources'][side]['face_certificates'][index].update(uv_closed_patch_boxes_exact=[]),
           {'material_side':side,'face_certificate_index':index})
    preserved=[(s,i) for s,source in enumerate(boundary['sources']) for i,piece in enumerate(source['pieces'])
               if piece['replacement']=='unchanged' and piece['kind'] in ('edge','vertex')]
    if preserved:
        es,ei=preserved[0]
        reject('omitted-actual-original-edge-or-vertex',lambda c:c['sources'][es]['pieces'].pop(ei),
               {'material_side':es,'piece_index':ei,'kind':boundary['sources'][es]['pieces'][ei]['kind']})
    else:
        rows.append({'name':'omitted-actual-original-edge-or-vertex','status':'not_applicable',
                     'actual_rejected':False,'reason':'No actual preserved edge or vertex piece exists.'})
    mapped=[(s,i) for s,i in applied if boundary['sources'][s]['face_certificates'][i]['swept_patch_boxes_exact']]
    if mapped:
        ms,mi=mapped[0]
        displacement=ranges(proof['full_remaining_displacement_box_exact'],3)
        axis=next((k for k in range(3) if ms==0 and displacement[k][0]!=displacement[k][1]),0)
        def corrupt_sweep(copied):
            patch=copied['sources'][ms]['face_certificates'][mi]['swept_patch_boxes_exact'][0]
            step=displacement[axis][1]-displacement[axis][0] if ms==0 else Q(0)
            patch[axis][1]=str(Q(patch[axis][1])-(step if step>0 else Q(1)))
        reject('incorrect-actual-swept-patch-endpoint',corrupt_sweep,
               {'material_side':ms,'face_certificate_index':mi,'retained_patch_list_index':0,'axis':axis})
    else:
        rows.append({'name':'incorrect-actual-swept-patch-endpoint','status':'not_applicable',
                     'actual_rejected':False,'reason':'No actual nonempty mapped patch exists.'})
    need(len(rows)==4 and all((r['status']=='executed' and r['actual_rejected'] is True) or
         (r['status']=='not_applicable' and r['actual_rejected'] is False) for r in rows),
         'actual trim control dispositions incomplete')
    return rows


def analytic_controls(base,limits):
    """Mandatory synthetic analytic controls, independent of real case success.

    A closed rectangular solid's complete boundary is its six closed faces.
    The target [2,3] x [0,1] x [0,1] lies outside the first complete solid
    [0,1]^3. A second complete solid supplies a registered exact cut endpoint.
    Both positive cases and all rejection mutations use the same verifier as
    real certificates. None is a measurement or an original-case gate pass.
    """
    def six_faces(bounds):
        faces=[]
        for axis in range(3):
            for end in (0,1):
                face=list(bounds);value=bounds[axis][end];face[axis]=(value,value)
                faces.append(tuple(face))
        return faces
    unit=((Q(0),Q(1)),)*3
    root=((Q(2),Q(3)),(Q(0),Q(1)),(Q(0),Q(1)))
    tiny=Q(limits['tiny_retained_volume_exact']);delta=tiny/2;point=Q(2)+delta
    second=((point,Q(4)),(Q(0),Q(1)),(Q(0),Q(1)))
    sources=[(six_faces(unit),unit),(six_faces(second),second)]
    def exterior(target):
        channel=list(target);channel[0]=(target[0][0],target[0][1]+1)
        return {'excluded_open_interior':True,'material_side':0,'axis':0,'end':1,
                'open_channel_exact':encode_box(channel),'complete_piece_separation_codes':'000000',
                'boundary_piece_count':6,'closed_cell_boundary_retained_as_zero_volume_carrier':True,
                'whole_closed_cell_disjoint_claimed':False}
    whole=base.signed_measure(root);certificate=exterior(root)
    single={'nodes':[{'id':0,'kind':'excluded','positive_directed_volume_exact':str(whole),'certificate':certificate}],
            'retained_sum_exact':'0','excluded_open_sum_exact':str(whole),'total_leaf_count':1,
            'excluded_leaf_count':1,'retained_leaf_count':0,'retained_reason_counts':{},'maximum_depth_reached':0,
            'all_closed_cut_planes_and_root_boundaries_retained':True}
    first=verify_tree(base,single,root,sources,limits)
    need(first['kept']==0 and first['removed']==1 and first['checked_boundary_pieces']==6,
         'complete-box analytic positive control failed')
    left=list(root);right=list(root);left[0]=(Q(2),point);right[0]=(point,Q(3))
    lv,rv=base.signed_measure(left),base.signed_measure(right)
    split={'nodes':[
        {'id':0,'kind':'split','axis':0,'cut_exact':str(point),
         'cut_source':{'material_side':1,'piece_index':0,'axis':0,'endpoint':0},'children':[1,2],
         'parent_positive_directed_volume_exact':str(whole),
         'children_positive_directed_volumes_exact':[str(lv),str(rv)],
         'closed_cut_plane_retained_as_zero_volume_carrier':True},
        {'id':1,'kind':'retained','reason':'tiny_exact_volume_retained',
         'positive_directed_volume_exact':str(lv),'actual_material_interference_claimed':False},
        {'id':2,'kind':'excluded','positive_directed_volume_exact':str(rv),'certificate':exterior(right)}],
        'retained_sum_exact':str(lv),'excluded_open_sum_exact':str(rv),'total_leaf_count':2,
        'excluded_leaf_count':1,'retained_leaf_count':1,'retained_reason_counts':{'tiny_exact_volume_retained':1},
        'maximum_depth_reached':1,'all_closed_cut_planes_and_root_boundaries_retained':True}
    second_result=verify_tree(base,split,root,sources,limits)
    need(second_result['kept']==delta>0 and second_result['removed']+delta==1 and second_result['splits']==1,
         'exact partition/tiny retained analytic positive control failed')
    channel_bad=base.negative_controls(certificate,root,sources)
    expected={'omitted-complete-boundary-piece','overclaim-closed-cell-disjointness',
              'channel-does-not-reach-known-exterior','false-separating-coordinate'}
    need(len(channel_bad)==4 and {x['name'] for x in channel_bad}==expected and
         all(x['actual_rejected'] is True for x in channel_bad),'all four analytic channel rejections required')
    split_bad=split_controls(base,split,root,sources,limits)
    leaf_bad=leaf_controls(base,split,root,sources,limits)
    need(len(split_bad)==5 and len(leaf_bad)==2 and all(x['actual_rejected'] is True for x in split_bad+leaf_bad),
         'analytic partition/leaf rejections required')
    return {'schema':'razr-r5e-mandatory-analytic-checker-controls-v5','execution_kind':'synthetic_analytic_control',
            'qualifies_original_or_trim_model_case':False,'real_case_result_changed':False,
            'source_closed_boxes_exact':[encode_box(unit),encode_box(second)],'source_complete_face_counts':[6,6],
            'complete_box_positive':{'verified':True,'root_box_exact':encode_box(root),'positive_volume_exact':'1',
                                     'excluded_open_volume_exact':'1','complete_boundary_pieces_verified':6},
            'exact_split_positive':{'verified':True,'split_exact':str(point),'positive_child_volumes_exact':[str(lv),str(rv)],
                                    'tiny_leaf_retained_in_full':True,'retained_sum_exact':str(delta),
                                    'all_closed_carriers_retained':True},
            'channel_negative_controls':channel_bad,'split_negative_controls':split_bad,'leaf_negative_controls':leaf_bad,
            'mandatory_controls_completed':True}


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();contract=json.loads(args.contract.read_text())
    need(digest(__file__)==contract['verifier_sha256'],'registered V5 verifier identity')
    base=load_checker(contract);args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    report={'schema':'razr-r5e-independent-trim-model-verification-v5','execution_completed':False,
            'producer_code_imported':False,'trim_producer_or_helper_imported':False,
            'contract_sha256':digest(args.contract),'verified_producer_report':contract['producer_report'],
            'frames':[],'phase_negative_controls':[],'root_coverage_negative_controls':[],
            'channel_negative_controls':[],'split_negative_controls':[],'leaf_negative_controls':[],
            'boundary_refinement_negative_controls':[],
            'mandatory_analytic_controls':None,'real_case_control_applicability':{},
            'conditional_trim_model_only':True,'native_trim_class_membership_verified':False,
            'inner_wire_hole_semantics_verified_for_native':False,'original_raw_gate_reclassified':False,
            'native_Common_called':False,'native_material_semantics_verified':False,
            'compiled_error_verified':False,'full_continuous_G2':False,'all_blockers_closed':False}
    def save():
        report['seconds']=time.monotonic()-start
        report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        producer_path=bound(contract['producer_report']);producer=json.loads(producer_path.read_text())
        need(producer['execution_completed'] and producer['schema']=='razr-r5e-trim-model-conditioned-refinement-v5',
             'complete registered V5 producer required')
        require_conditional_scope(producer)
        need(producer['source_report_identity']==contract['r4_report'] and producer['capacity']==contract['capacity'],
             'actual producer original source or registered capacity differs')
        controller=json.loads(bound(contract['producer_owned_supervision']).read_text())
        need(controller['completed'] and controller['worker_started'] and controller['worker_exit_code']==0 and
             controller['resource_stop'] is None,'producer owned resource qualification absent')
        need(controller['limits']['registered_math_contract_sha256']==producer['contract_sha256'],'producer actual contract differs')
        need(Path(controller['limits']['worker_output_directory']).resolve()==producer_path.parent.resolve(),
             'actual producer output binding differs')
        baseline=json.loads(bound(producer['source_report_identity']).read_text())
        selection=json.loads(bound(contract['real_retained_cell_selection']).read_text())
        need(producer['real_retained_cell_selection']==contract['real_retained_cell_selection'],
             'actual selected-cell source identity differs')
        complete_phase(producer,contract,baseline,selection)
        report['phase_negative_controls']=phase_controls(producer,contract,baseline,selection)
        report['expected_phase']=contract['expected_phase'];report['expected_case_frames']=contract['expected_case_frames']
        old_by={(r['case_id'],r['frame']):r for r in baseline['frames']}
        bridge_json=json.loads(bound(contract['public_input_bridge']).read_text())
        need(producer['public_input_bridge']==contract['public_input_bridge'],'producer/verifier public bridge differs')
        need(bridge_json['source_commit']=='c5f6606924937d716b007cd3ffa8e54df8ecfa5d' and len(bridge_json['files'])==19 and
             all(r['decoded_json_equal'] and not r['changed_strings'] for r in bridge_json['files']),
             'unchanged complete public bridge required')
        bridge={r['path']:r for r in bridge_json['files']};need(len(bridge)==19,'duplicate public bridge path')
        limits=producer['capacity']
        need(limits['maximum_splits']==4096 and limits['maximum_depth']==24 and limits['maximum_boundary_box_tests']==12000000 and
             Q(limits['tiny_retained_volume_exact'])==Q(1e-7)/100000 and limits['maximum_uv_patches_per_face']==1024 and
             limits['maximum_boundary_pieces_per_material']==4096,'registered finite trim/refinement policy differs')
        need(producer['trim_source_bundle']==contract['trim_source_bundle'],'producer/verifier trim source differs')
        need(producer['trim_model_source']==contract['trim_model_source'],'producer conditional model source differs')
        bound(contract['trim_model_source'])
        records,bindings=load_trim_source(contract,baseline,producer['source_report_identity'])
        report['trim_source_bundle']=contract['trim_source_bundle']
        report['verified_trim_source_bundle']=contract['trim_source_bundle']
        report['registered_trim_model_source_not_imported']=contract['trim_model_source']
        # Always execute known analytic positive cases and all four channel
        # rejections. Real case success is never a prerequisite for these.
        report['mandatory_analytic_controls']=analytic_controls(base,limits)
        save()
        all_splits=all_nodes=all_leaves=all_excluded=all_applied_faces=all_holes=all_fallback_faces=0
        for row in producer['frames']:
            require_conditional_scope(row)
            key=(row['case_id'],row['frame']);old=old_by[key];entry=bridge['support-v4/'+old['proof']['path']]
            need(row['original_raw_proof_identity']==old['proof'] and
                 entry['raw_identity']=={k:old['proof'][k] for k in ('bytes','sha256')},'raw source mapping differs')
            need({k:row['source_proof'][k] for k in ('bytes','sha256')}==entry['public_identity'],'actual public source identity differs')
            with gzip.open(bound(row['source_proof']),'rt') as stream:proof=json.load(stream)
            need(canonical_sha(proof)==entry['public_canonical_json_sha256'],'decoded public source differs')
            need(row['original_remaining_displacement_box_exact']==proof['full_remaining_displacement_box_exact']==
                 old['full_remaining_displacement_box_exact'],'complete original D differs')
            need(row['trim_source_bundle']==contract['trim_source_bundle'],'frame trim source bundle differs')
            with gzip.open(bound(row['certificate'],producer_path.parent),'rt') as stream:certificate=json.load(stream)
            need(certificate['schema']=='razr-r5e-trim-model-conditioned-tree-v5','registered V5 model certificate schema')
            need(certificate['frame']=={k:v for k,v in row.items() if k!='certificate'},'certificate frame header differs from actual report')
            sources,boundary_audit=verify_boundary_refinement(proof,old,certificate['boundary_refinement'],records,bindings,limits)
            need(row['model_boundary_applied_face_count']==boundary_audit['applied_faces'] and
                 row['model_boundary_applied_inner_wire_count']==boundary_audit['hole_core_certificates_verified'] and
                 row['model_boundary_retained_original_face_count_after_rejection']==boundary_audit['unapplied_faces_preserved'],
                 'actual frame conditional boundary counts differ')
            all_applied_faces+=boundary_audit['applied_faces'];all_holes+=boundary_audit['hole_core_certificates_verified']
            all_fallback_faces+=boundary_audit['unapplied_faces_preserved']
            if not report['boundary_refinement_negative_controls'] and boundary_audit['applied_faces']:
                report['boundary_refinement_negative_controls']=boundary_controls(
                    proof,old,certificate['boundary_refinement'],records,bindings,limits)
            need(row['source_piece_counts']==[len(s[0]) for s in sources],'actual rebuilt piece count differs')
            old_cells=proof['complete_raw_boundary_slab_cover']['combined']['positive_cells']
            expected_indices=[selection['original_raw_cell_index']] if contract['expected_phase']=='single_trim_model_cell' else list(range(len(old_cells)))
            if contract['expected_phase']=='single_trim_model_cell':
                chosen=old_cells[expected_indices[0]]
                need(selection['actual_V3_cell']['excluded_open_interior'] is False and
                     selection['actual_V3_cell']['box_exact']==chosen['box_exact'] and
                     Q(selection['actual_V3_cell']['positive_directed_volume_exact'])==Q(chosen['positive_directed_volume_exact']) and
                     selection['source_row_original_D']==proof['full_remaining_displacement_box_exact'],
                     'selected original real retained cell or full D changed')
            root_coverage(row,certificate,expected_indices)
            if not report['root_coverage_negative_controls']:
                report['root_coverage_negative_controls']=root_controls(row,certificate,expected_indices)
            kept=Q(0);removed=Q(0);checked=0;splits=leaves=nodes=excluded=0;max_depth=0
            for root_record,index in zip(certificate['roots'],expected_indices):
                old_cell=old_cells[index]
                need(root_record['root_box_exact']==old_cell['box_exact'] and
                     Q(root_record['root_directed_volume_exact'])==Q(old_cell['positive_directed_volume_exact']),
                     'original positive root changed')
                root=base.box(root_record['root_box_exact']);tree=root_record['tree']
                stats=verify_tree(base,tree,root,sources,limits)
                kept+=stats['kept'];removed+=stats['removed'];checked+=stats['checked_boundary_pieces']
                splits+=stats['splits'];nodes+=stats['nodes'];leaves+=stats['leaves'];excluded+=stats['excluded_leaves']
                max_depth=max(max_depth,stats['depth'])
                if not report['channel_negative_controls'] and stats['sample_exclusion']:
                    sample,cell=stats['sample_exclusion'];report['channel_negative_controls']=base.negative_controls(sample,cell,sources)
                if not report['split_negative_controls'] and stats['sample_split']:
                    report['split_negative_controls']=split_controls(base,tree,root,sources,limits)
                if not report['leaf_negative_controls']:
                    report['leaf_negative_controls']=leaf_controls(base,tree,root,sources,limits)
            need(kept==Q(row['retained_leaf_sum_exact']) and removed==Q(row['excluded_open_leaf_sum_exact']) and
                 kept+removed==Q(row['original_root_sum_exact']),'frame exact directed sums differ')
            need(row['all_closed_cut_planes_and_original_cell_boundaries_retained'] is True,'frame zero-volume carrier lost')
            selected=kept
            if contract['expected_phase']=='all_trim_model_frames':
                need(kept+removed==Q(proof['complete_raw_boundary_slab_cover']['combined']['sum_directed_volume_exact']),
                     'complete original root sum differs')
                selected=min(kept,Q(old['coarse_whole_support_upper_exact_mm3']))
                need(selected<=Q(old['conditional_complete_material_intersection_upper_exact_mm3']) and
                     old['original_min_volume_plus_TOL_gate_passed'] is True,'inherited numerical upper sanity bound differs')
            need(row['original_R4_min_volume_plus_TOL_gate_passed']==old['original_min_volume_plus_TOL_gate_passed'],
                 'historical original R4 sanity result changed')
            need(selected==Q(row['trim_model_conditional_upper_exact_mm3']) and
                 row['trim_model_conditional_clearance_gate_passed']==(selected<=Q(1e-7)),
                 'conditional model bound or unchanged threshold differs')
            need(splits==row['exact_splits_this_frame'] and leaves==row['total_leaf_count'] and
                 max_depth==row['maximum_depth_reached'],'actual tree metadata differs')
            all_splits+=splits;all_nodes+=nodes;all_leaves+=leaves;all_excluded+=excluded
            report['frames'].append({'case_id':key[0],'frame':key[1],'original_roots_verified':len(expected_indices),
                'exact_tree_nodes_verified':nodes,'exact_splits_verified':splits,
                'all_retained_and_excluded_leaves_verified':leaves,'actual_excluded_leaf_count':excluded,
                'complete_boundary_piece_separations_checked':checked,'trim_model_conditional_upper_exact_mm3':str(selected),
                'trim_model_conditional_clearance_gate_passed':selected<=Q(1e-7),
                'original_R4_raw_clearance_gate_passed_unchanged':old['original_clearance_gate_passed'],
                'original_raw_gate_reclassified':False,'native_trim_class_membership_verified':False,
                'conditional_trim_model_only':True,'independent_boundary_refinement':boundary_audit})
            save()
        need(all_splits==producer['counters']['splits']<=limits['maximum_splits'] and
             all_nodes==producer['counters']['tree_nodes_visited'],'global actual tree count differs')
        need(producer['counters']['boundary_box_tests']<=limits['maximum_boundary_box_tests'],
             'actual predicate counter exceeds registered budget')
        need(producer['applied_face_occurrences_across_frames']==all_applied_faces and
             producer['applied_inner_wire_occurrences_across_frames']==all_holes and
             producer['retained_original_face_occurrences_after_rejection']==all_fallback_faces,
             'actual complete-phase conditional model counts differ')
        for label,eligible,rows,required_count,reason in [
            ('channel_mutations',all_excluded,report['channel_negative_controls'],4,'No actual excluded leaf exists in these completed case certificates.'),
            ('split_mutations',all_splits,report['split_negative_controls'],5,'No actual split exists in these completed case certificates.'),
            ('leaf_mutations',all_leaves,report['leaf_negative_controls'],2,'No actual positive leaf exists.')]:
            if eligible:
                need(len(rows)==required_count and all(r['actual_rejected'] is True for r in rows),
                     'applicable real-case rejection controls incomplete: '+label)
            else:need(not rows,'inapplicable real-case controls falsely claimed executed: '+label)
            report['real_case_control_applicability'][label]={'status':'executed' if eligible else 'not_applicable',
                'actual_eligible_count':eligible,'reason':None if eligible else reason,
                'analytic_controls_are_separate':True}
        boundary_rows=report['boundary_refinement_negative_controls']
        need((all_applied_faces>0 and len(boundary_rows)==4) or (all_applied_faces==0 and not boundary_rows),
             'real applied-face control applicability differs')
        report['real_case_control_applicability']['boundary_refinement_mutations']={
            'status':'executed' if all_applied_faces else 'not_applicable','actual_applied_face_count':all_applied_faces,
            'actual_rejected_controls':sum(r['actual_rejected'] is True for r in boundary_rows),
            'individual_missing_targets_recorded_as_not_applicable':True,
            'reason':None if all_applied_faces else 'No actual applied trim face exists in these completed certificates.'}
        need(all_leaves>0 and report['mandatory_analytic_controls']['mandatory_controls_completed'] is True and
             len(report['phase_negative_controls'])==3 and len(report['root_coverage_negative_controls'])==2,
             'mandatory analytic/coverage controls incomplete')
        passes=sum(r['trim_model_conditional_clearance_gate_passed'] for r in report['frames'])
        need(passes==producer['trim_model_conditional_clearance_passes'],'producer/independent conditional model gates differ')
        report.update(total_tree_nodes_verified=all_nodes,total_splits_verified=all_splits,total_leaves_verified=all_leaves,
                      total_actual_excluded_leaves_verified=all_excluded,trim_model_conditional_clearance_passes=passes,
                      applied_face_occurrences_verified=all_applied_faces,applied_inner_wire_occurrences_verified=all_holes,
                      retained_original_face_occurrences_after_rejection_verified=all_fallback_faces)
        need(digest(__file__)==contract['verifier_sha256'] and digest(Path(contract['base_verifier_source']['path']))==
             contract['base_verifier_source']['sha256'] and digest(args.contract)==report['contract_sha256'] and
             digest(bound(contract['trim_source_bundle']))==contract['trim_source_bundle']['sha256'],
             'verifier source, source bundle or contract changed')
        bound(contract['producer_report']);bound(contract['producer_owned_supervision'])
        report['execution_completed']=True
    except BaseException as exc:
        report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};raise
    finally:
        save();print(json.dumps({k:report.get(k) for k in ['execution_completed','trim_model_conditional_clearance_passes',
              'total_tree_nodes_verified','seconds','peak_RSS_bytes','failure']}),flush=True)


if __name__=='__main__':main()
