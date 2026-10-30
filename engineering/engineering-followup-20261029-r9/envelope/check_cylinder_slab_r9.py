"""Independent exact checker for cylinder/slab conditional channel bounds.

No producer import, no CAD kernel and no floating-point arithmetic.
"""
from collections import Counter
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import sys

R8=Path(__file__).resolve().parents[2]/'engineering-followup-20261029-r8/independent-review'
sys.path.insert(0,str(R8))
import quadric_checker_r8 as math
from read_depth24_actual_r8 import need, measure, channel_of, validate_old_code


def project(normal,B):
    values=[math.inner(normal,p) for p in product(*B)]
    return min(values),max(values)


def source_record(material,piece):
    return material['boundary']['faces' if piece['kind']=='face' else 'edges'][piece['index']]


def verify_channels(result,B,sources,materials,D,counts):
    order=list(product(range(2),range(3),range(2)))
    observations=result['observations']
    need(0<len(observations)<=12,'complete_channel_prefix')
    need([(o['material_side'],o['axis'],o['end']) for o in observations]==order[:len(observations)],'original_channel_order')
    for observation in observations:
        side=observation['material_side'];source=sources[side];channel=channel_of(B,math.bounds(source['known_whole_exact']),observation['axis'],observation['end'])
        need(math.bounds(observation['channel_exact'])==channel,'full_exterior_channel')
        shift=D if side==0 else ((F(0),F(0)),)*3
        codes=observation['codes'];claims={c['piece_index']:c for c in observation['new_claims']}
        need(len(codes)==len(source['pieces']),'all_source_pieces_covered')
        need(len(claims)==len(observation['new_claims']),'unique_piece_claims')
        used=set();unknown=[];counts['channels']+=1
        for index,(code,piece) in enumerate(zip(codes,source['pieces'])):
            counts['pieces']+=1
            if code=='?':unknown.append(index);continue
            if code in '01234567':validate_old_code(piece,channel,code);continue
            need(index in claims,'source_claim_present');claim=claims[index];used.add(index)
            need(claim['material_key']==source['material_key'] and math.bounds(claim['channel_exact'])==channel,'claim_material_channel')
            need(code=={'quadric':'Q','plane':'P','line':'L','empty_closed_intersection':'E'}[claim['code']],'claim_code')
            if code=='E':
                carrier=math.bounds(piece['box_exact']);need(any(max(carrier[k][0],channel[k][0])>min(carrier[k][1],channel[k][1]) for k in range(3)),'empty_closed_intersection')
            else:
                if code=='Q':need(claim['classification'] in ('below_radius','above_radius'),'strict_quadric_required_for_exclusion')
                native=materials[tuple(source['material_key'])]
                math.verify_source_claim(claim,source_record(native,piece),piece,shift)
            counts['new_'+claim['code']]+=1
        need(unknown==observation['unresolved_piece_indices'],'complete_unresolved_census')
        need(used==set(claims),'all_claims_consumed')
        need(observation['failure']==(None if not unknown else {'piece_index':unknown[0]}),'retained_failure_identity')
    return observations


def verify_cylinder(candidate,observation,source,material,D):
    indices=observation['unresolved_piece_indices']
    need(indices and candidate['piece_index'] in indices,'cylinder_seed_in_complete_unresolved_set')
    record=source_record(material,source['pieces'][candidate['piece_index']])
    need(source['pieces'][candidate['piece_index']]['kind']=='face','cylinder_face_source')
    basis=math.original_basis(record)
    need('local_surface' in record and record['local_surface']['type']=='GeomAbs_SurfaceType.GeomAbs_Cylinder','exact_cylinder_source_type')
    for index in indices:
        piece=source['pieces'][index];need(piece['kind']=='face','all_remaining_pieces_cylinder_faces')
        other=source_record(material,piece)
        need(other['local_surface']['type']=='GeomAbs_SurfaceType.GeomAbs_Cylinder','remaining_cylinder_type')
        need(math.original_basis(other)==basis,'same_complete_cylinder_locus')
    O,a,b,r=math.duals(basis)
    shift=D if observation['material_side']==0 else ((F(0),F(0)),)*3
    need(math.bounds(candidate['source_shift_exact'])==shift,'full_cylinder_displacement')
    C=math.bounds(observation['channel_exact']);S=tuple((C[k][0]-shift[k][1]-O[k],C[k][1]-shift[k][0]-O[k]) for k in range(3))
    axis=observation['axis'];normal=tuple(2*(a[axis]*a[k]+b[axis]*b[k]) for k in range(3));low,high=project(normal,S)
    direction=1 if observation['end'] else -1
    need(candidate['derivative_exact']==[str(low),str(high)] and candidate['outward_direction']==direction,'exact_outward_cylinder_derivative')
    need(low>=0 if direction==1 else high<=0,'outward_radial_monotonicity')
    return basis,shift


def verify_slab(candidate,observation,source,material,D):
    n=math.vector(candidate['normal_exact']);need(len(n)==3 and any(n),'nonzero_projection_normal')
    direction=1 if observation['end'] else -1
    need(n[observation['axis']]*direction<0,'outward_slab_projection_decreases')
    shift=D if observation['material_side']==0 else ((F(0),F(0)),)*3
    need(math.bounds(candidate['source_shift_exact'])==shift,'full_slab_displacement')
    records=candidate['piece_projections'];indices=observation['unresolved_piece_indices']
    need(indices and [r['piece_index'] for r in records]==indices,'all_unresolved_piece_projections')
    lower=[]
    ds=project(n,shift)
    for claim,index in zip(records,indices):
        piece=source['pieces'][index]
        if claim['method']=='original_complete_carrier':
            lo,hi=project(n,math.bounds(piece['box_exact']))
        else:
            original=source_record(material,piece)
            need(original['location']['matrix_3x4_exact']==math.IDENTITY,'projection_source_placement')
            if claim['method']=='exact_plane':
                need(piece['kind']=='face','plane_projection_kind');d=original['local_surface']
                need(d==original['native_global_surface'] and d['type']=='GeomAbs_SurfaceType.GeomAbs_Plane','original_plane_projection_source')
                need(math.inner(n,math.vector(d['X_exact']))==math.inner(n,math.vector(d['Y_exact']))==0,'plane_normal_annihilates_both_axes')
                base=math.inner(n,math.vector(d['origin_exact']));lo,hi=base+ds[0],base+ds[1]
            elif claim['method']=='complete_original_line':
                need(piece['kind']=='edge','line_projection_kind');d=original['local_curve']
                need(d==original['native_global_curve'] and d['type']=='GeomAbs_CurveType.GeomAbs_Line','original_line_projection_source')
                t0,t1=math.rational(d['first_parameter']),math.rational(d['last_parameter']);need(t0<=t1,'complete_line_parameter_domain')
                origin,direction=math.vector(d['origin_exact']),math.vector(d['direction_exact'])
                values=[math.inner(n,tuple(origin[k]+t*direction[k] for k in range(3))) for t in (t0,t1)]
                lo,hi=min(values)+ds[0],max(values)+ds[1]
            else:raise ValueError('unknown_piece_projection_method')
        need(F(claim['lower_exact'])==lo and F(claim['upper_exact'])==hi,'whole_piece_projection_bounds')
        lower.append(lo)
    L=min(lower);need(F(candidate['lower_exact'])==L,'minimum_complete_boundary_projection')
    return n,L


def verify_combination(claim,B,basis,shift,n,L):
    O,X,Y,Z=(math.vector(basis[k]) for k in ('origin','X','Y','Z'))
    radius=F(basis['radius']);det=math.inner(X,math.wedge(Y,Z));need(det!=0,'invertible_original_cylinder_basis')
    w=tuple(v/det for v in math.wedge(X,Y))
    need((math.inner(w,X),math.inner(w,Y),math.inner(w,Z))==(0,0,1),'axial_dual_identity')
    S=tuple((B[k][0]-shift[k][1]-O[k],B[k][1]-shift[k][0]-O[k]) for k in range(3))
    axial=project(w,S);need(claim['axial_parameter_interval_exact']==list(map(str,axial)),'complete_axial_box_interval')
    radial2=math.inner(n,X)**2+math.inner(n,Y)**2
    need(F(claim['support_sqrt_radicand_exact'])==radial2,'original_radial_support_radicand')
    sq=F(claim['support_sqrt_upper_exact']);need(sq>=0 and sq*sq>=radial2,'outward_support_square_root')
    axial_support=max(math.inner(n,Z)*a for a in axial)
    need(F(claim['axial_support_upper_exact'])==axial_support,'exact_axial_support')
    U=math.inner(n,O)+radius*sq+axial_support+project(n,shift)[1]
    need(F(claim['cylinder_support_upper_exact'])==U and F(claim['slab_lower_exact'])==L,'full_cylinder_and_slab_supports')
    positive=max(F(0),U-L);need(F(claim['positive_projection_width_exact'])==positive,'positive_projection_width')
    axis=claim['slice_axis'];need(type(axis) is int and 0<=axis<3 and n[axis]!=0,'nonzero_fubini_slice_axis')
    area=F(1)
    for k in range(3):
        if k!=axis:area*=B[k][1]-B[k][0]
    need(F(claim['other_axes_area_exact'])==area,'full_transverse_box_area')
    bound=min(measure(B),positive*area/abs(n[axis]))
    need(F(claim['bound_exact'])==bound and 0<=bound<=measure(B),'conservative_positive_volume_bound')
    return bound


def verify(result,B,sources,materials,D,counts):
    observations=verify_channels(result,B,sources,materials,D,counts)
    if result['kind']=='complete_exterior_channel':
        index=result['selected_channel'];need(index==len(observations)-1 and not observations[index]['unresolved_piece_indices'],'complete_excluding_channel')
        bound=F(0)
    elif result['kind']=='cylinder_slab_upper_bound':
        need(len(observations)==12,'all_channels_in_family_search')
        ci,si=result['cylinder_channel'],result['slab_channel']
        need(type(ci) is int and type(si) is int and 0<=ci<12 and 0<=si<12,'selected_family_channels')
        c,s=observations[ci],observations[si];need(c['material_side']!=s['material_side'],'two_distinct_materials')
        cs,ss=sources[c['material_side']],sources[s['material_side']]
        basis,shift=verify_cylinder(result['cylinder'],c,cs,materials[tuple(cs['material_key'])],D)
        normal,L=verify_slab(result['slab'],s,ss,materials[tuple(ss['material_key'])],D)
        bound=verify_combination(result['combination'],B,basis,shift,normal,L)
        counts['cylinder_slab_bounds']+=1
    elif result['kind']=='unresolved_full_box':
        need(len(observations)==12,'all_unresolved_channels_preserved');bound=measure(B)
        counts['unresolved_full_boxes']+=1
    else:raise ValueError('unknown_volume_bound_kind')
    need(F(result['bound_exact'])==bound,'reported_cell_bound')
    return bound
