"""Exact boundary cover for an explicitly conditional planar trim realization.

Native membership in the hole/closure model is deliberately not established.
All original pcurve endpoints, edges, vertices and displacement intervals stay.
"""
from fractions import Fraction as F
import hashlib
import json

IDENTITY=[['1','0','0','0'],['0','1','0','0'],['0','0','1','0']]


def need(ok,message):
    if not ok:raise ValueError(message)


def q(x):return F(x['exact']) if isinstance(x,dict) else F(x)
def vec(x):return tuple(map(q,x))
def encbox(x):return [[str(v) for v in interval] for interval in x]
def box(x):return [tuple(map(F,interval)) for interval in x]
def canonical(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def affine_interval(coefficients,ranges,constant=F(0)):
    lo=hi=constant
    for a,(u,v) in zip(coefficients,ranges):
        x,y=a*u,a*v;lo+=min(x,y);hi+=max(x,y)
    return lo,hi


def hole_certificate(wire):
    need(not wire['is_outer'] and len(wire['edge_occurrences'])==4,'four-occurrence inner wire required')
    need(wire['location']['matrix_3x4_exact']==IDENTITY,'nonidentity wire location unsupported')
    constants=[[],[]];segments=[];constant_axes=[]
    for i,occ in enumerate(wire['edge_occurrences']):
        need(occ['location']['matrix_3x4_exact']==IDENTITY,'nonidentity pcurve occurrence location unsupported')
        curve=occ['pcurve'];need(curve['type'].endswith('GeomAbs_Line'),'non-Line pcurve outside registered class')
        origin,direction=vec(curve['origin_exact']),vec(curve['direction_exact'])
        need(len(origin)==len(direction)==2 and direction in [(F(1),F(0)),(F(-1),F(0)),(F(0),F(1)),(F(0),F(-1))], 'exact axial UV line required')
        first,last=q(curve['first_parameter']),q(curve['last_parameter']);need(first<last,'positive actual pcurve parameter interval')
        endpoints=[tuple(origin[k]+t*direction[k] for k in range(2)) for t in (first,last)]
        orientation=occ['orientation'].split('.')[-1]
        need(orientation in ['TopAbs_FORWARD','TopAbs_REVERSED'],'unsupported occurrence orientation')
        if orientation=='TopAbs_REVERSED':endpoints.reverse()
        constant_axis=0 if direction[0]==0 else 1
        constants[constant_axis].append(origin[constant_axis])
        constant_axes.append(constant_axis)
        segments.append({'occurrence_index':i,'start_exact':[str(v) for v in endpoints[0]],'end_exact':[str(v) for v in endpoints[1]]})
    need(all(len(values)==2 and len(set(values))==2 for values in constants),'two distinct constant sides per coordinate required')
    rectangle=[tuple(sorted(values)) for values in constants]
    (ul,ur),(vb,vt)=rectangle
    corners=[(ul,vb),(ur,vb),(ur,vt),(ul,vt)]
    assigned=[];radius=F(0);offsets=[]
    for row,constant_axis in zip(segments,constant_axes):
        endpoints=[vec(row['start_exact']),vec(row['end_exact'])];ids=[];edge_offsets=[]
        for point in endpoints:
            allowed=[i for i,corner in enumerate(corners) if corner[constant_axis]==point[constant_axis]]
            need(len(allowed)==2,'actual segment not on exactly one auxiliary rectangle side')
            distances=[max(abs(point[k]-corners[i][k]) for k in range(2)) for i in allowed]
            smallest=min(distances);need(distances.count(smallest)==1,'ambiguous endpoint-to-corner correspondence')
            index=allowed[distances.index(smallest)];ids.append(index);radius=max(radius,smallest)
            edge_offsets.append([str(point[k]-corners[index][k]) for k in range(2)])
        need(ids[0]!=ids[1] and ((ids[0]-ids[1])%4 in (1,3)),'ideal directed side must join adjacent distinct corners')
        assigned.append(ids);offsets.append(edge_offsets)
    need(sorted(a for a,b in assigned)==list(range(4)) and sorted(b for a,b in assigned)==list(range(4)), 'ideal sides do not give one predecessor/successor per corner')
    following=dict(assigned);cycle=[0]
    for unused in range(4):cycle.append(following[cycle[-1]])
    need(cycle[-1]==0 and len(set(cycle[:-1]))==4,'ideal sides are not one four-corner cycle')
    need(4*radius<min(ur-ul,vt-vb),'endpoint-corner neighborhoods are too large or degenerate')
    core=[(ul+radius,ur-radius),(vb+radius,vt-radius)]
    squares=[[(u-radius,u+radius),(v-radius,v+radius)] for u,v in corners]
    return {'wire_index':wire['index'],'oriented_segments_exact':segments,'ideal_rectangle_exact':encbox(rectangle),
            'directed_corner_indices':assigned,'endpoint_corner_offsets_exact':offsets,
            'uniform_corner_radius_exact':str(radius),'corner_squares_exact':[encbox(s) for s in squares],
            'hole_core_exact':encbox(core),'cycle_corner_indices':cycle,
            'native_closure_class_membership_verified':False,'inner_wire_hole_semantics_verified_for_native':False,
            'original_pcurve_endpoints_replaced':False}


def subtract_open_core(rectangle,core):
    # A zero-area rectangle is an explicitly retained closed carrier.
    if any(a==b for a,b in rectangle):return [rectangle]
    (a,b),(c,d)=rectangle;(u0,u1),(v0,v1)=core
    lo,hi=max(a,u0),min(b,u1);bottom,top=max(c,v0),min(d,v1)
    if lo>=hi or bottom>=top:return [rectangle]
    # Covers rectangle minus open core; all prior and cut closed boundaries stay.
    return [[(a,lo),(c,d)],[(hi,b),(c,d)],[(lo,hi),(c,bottom)],[(lo,hi),(top,d)]]


def refine_face(face_record,stationary,displacement,limits):
    face=face_record['complete_original_face']
    need(canonical(face)==face_record['complete_original_face_canonical_sha256'],'complete original face digest differs')
    need(face['location']['matrix_3x4_exact']==IDENTITY,'nonidentity face placement unsupported')
    surface=face['local_surface'];need(surface['type'].endswith('GeomAbs_Plane'),'nonplanar face outside class')
    origin,X,Y=map(vec,[surface['origin_exact'],surface['X_exact'],surface['Y_exact']])
    chosen=None
    for j,k in [(0,1),(0,2),(1,2)]:
        det=X[j]*Y[k]-X[k]*Y[j]
        if det!=0:
            chosen=(j,k);inverse=[(Y[k]/det,-Y[j]/det),(-X[k]/det,X[j]/det)];break
    need(chosen is not None,'singular stored plane tangents')
    j,k=chosen;translated=[(stationary[t][0]-origin[t],stationary[t][1]-origin[t]) for t in chosen]
    outer=[affine_interval(row,translated) for row in inverse]
    need(all(a<b for a,b in outer),'positive projected stationary face domain required')
    wires={w['index']:w for w in face['wires']};holes=[];patches=[outer]
    for index in face_record['candidate_inner_wire_indices']:
        need(index in wires,'candidate wire missing from full original face')
        hole=hole_certificate(wires[index]);core=box(hole['hole_core_exact'])
        need(all(outer[t][0]<core[t][0]<core[t][1]<outer[t][1] for t in range(2)), 'hole core not strictly within projected full face box')
        holes.append(hole);new=[]
        for rectangle in patches:new.extend(subtract_open_core(rectangle,core))
        # Explicit zero-width carriers preserve this whole closed core boundary
        # even if it lies inside another core. Later subtractions keep these.
        (a,b),(c,d)=core
        new.extend([[(a,a),(c,d)],[(b,b),(c,d)],[(a,b),(c,c)],[(a,b),(d,d)]])
        need(len(new)<=limits['maximum_uv_patches_per_face'],'registered UV patch capacity exceeded')
        patches=new
    need(holes,'no admitted inner hole')
    retained=[];empty=[];stationary_boxes=[];swept=[]
    for index,rectangle in enumerate(patches):
        mapped=[affine_interval((X[t],Y[t]),rectangle,origin[t]) for t in range(3)]
        clipped=[(max(mapped[t][0],stationary[t][0]),min(mapped[t][1],stationary[t][1])) for t in range(3)]
        if any(a>b for a,b in clipped):empty.append(index);continue
        retained.append(index);stationary_boxes.append(clipped)
        swept.append([(clipped[t][0]+displacement[t][0],clipped[t][1]+displacement[t][1]) for t in range(3)])
    need(retained,'face refinement would discard every closed boundary patch')
    return {'applied':True,'projection_axes':list(chosen),'inverse_rows_exact':[[str(v) for v in row] for row in inverse],
            'stationary_original_boundary_box_exact':encbox(stationary),'uv_outer_box_exact':encbox(outer),'holes':holes,
            'uv_closed_patch_boxes_exact':[encbox(r) for r in patches],'retained_uv_patch_indices':retained,'empty_uv_patch_indices':empty,
            'stationary_patch_boxes_exact':[encbox(r) for r in stationary_boxes],'swept_patch_boxes_exact':[encbox(r) for r in swept],
            'original_pcurve_values_changed':False,'closed_hole_core_boundaries_retained':True,
            'native_trim_class_membership_verified':False,'inner_wire_hole_semantics_verified_for_native':False}


def build_boundary(base,proof,trim_bundle,limits):
    old_sources=base.source_records(proof,stationary=False)
    by={(r['input']['case_id'],r['input']['material_id']):r for r in trim_bundle['records']}
    frame=next(r for r in trim_bundle['frame_bindings'] if (r['case_id'],r['frame'])==(proof['case_id'],proof['frame']))
    need(frame['original_full_D']==proof['full_remaining_displacement_box_exact'],'source bundle full D differs')
    displacement=base.decode(proof['full_remaining_displacement_box_exact']);zero=[(F(0),F(0))]*3
    scope={'schema':'razr-r5e-conditional-planar-trim-boundary-v5','conditional_trim_model_only':True,
           'native_trim_class_membership_verified':False,'inner_wire_hole_semantics_verified_for_native':False,'sources':[]}
    rebuilt=[];applied_faces=applied_holes=rejected_faces=0
    for side,label in enumerate(['moving_input','fixed_input']):
        inp=proof[label];key=(inp['case_id'],inp['material_id']);source=by[key]
        need(list(key)==frame['moving_and_fixed_material_keys'][side] and source['input']['sha256']==inp['sha256'],'whole material source mapping differs')
        face_candidates={r['face_index']:r for r in source['candidate_faces']}
        shift=displacement if side==0 else zero
        old=old_sources[side];new_pieces=[];certificates=[];rows=[]
        for index,(identity,old_box) in enumerate(zip(old['identities'],old['pieces'])):
            face_record=face_candidates.get(identity['index']) if identity['kind']=='face' else None
            if face_record is None:
                rows.append(dict(original_piece_index=index,kind=identity['kind'],index=identity['index'],replacement='unchanged',box_exact=encbox(old_box)))
                new_pieces.append(old_box);continue
            stationary=[(old_box[t][0]-shift[t][0],old_box[t][1]-shift[t][1]) for t in range(3)]
            fixed={'face_index':identity['index'],'original_piece_index':index,'source_face_canonical_sha256':face_record['complete_original_face_canonical_sha256']}
            try:certificate=dict(fixed,**refine_face(face_record,stationary,shift,limits))
            except ValueError as exc:
                certificate=dict(fixed,applied=False,face_refinement_not_applied_reason=str(exc))
            ci=len(certificates);certificates.append(certificate)
            if not certificate['applied']:
                rejected_faces+=1;rows.append(dict(original_piece_index=index,kind=identity['kind'],index=identity['index'],replacement='unchanged',box_exact=encbox(old_box)))
                new_pieces.append(old_box);continue
            applied_faces+=1;applied_holes+=len(certificate['holes'])
            for uv_index,new_box in zip(certificate['retained_uv_patch_indices'],certificate['swept_patch_boxes_exact']):
                rows.append(dict(original_piece_index=index,kind=identity['kind'],index=identity['index'],replacement='trim_patch',
                                 face_certificate_index=ci,uv_patch_index=uv_index,box_exact=new_box))
                new_pieces.append(box(new_box))
        need(len(new_pieces)<=limits['maximum_boundary_pieces_per_material'],'registered material boundary-piece capacity exceeded')
        whole=[(min(r[t][0] for r in new_pieces),max(r[t][1] for r in new_pieces)) for t in range(3)]
        need(all(old['whole'][t][0]<=whole[t][0]<=whole[t][1]<=old['whole'][t][1] for t in range(3)),'model boundary grew beyond old support')
        scope['sources'].append({'material_key':list(key),'original_complete_piece_count':len(old['pieces']),
                                 'original_whole_support_box_exact':encbox(old['whole']),'pieces':rows,'whole_exact':encbox(whole),
                                 'face_certificates':certificates})
        rebuilt.append({'pieces':new_pieces,'whole':whole})
    scope['applied_face_count']=applied_faces;scope['applied_inner_wire_count']=applied_holes;scope['retained_original_face_count_after_rejection']=rejected_faces
    return rebuilt,scope
