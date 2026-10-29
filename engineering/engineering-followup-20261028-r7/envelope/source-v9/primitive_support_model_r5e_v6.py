"""Exact primitive-model covers; native membership deliberately remains open.

This producer helper does not import CAD or evaluate floating-point trig.
The independent checker must not import this module.
"""
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import json
from math import factorial

IDENTITY=[['1','0','0','0'],['0','1','0','0'],['0','0','1','0']]


def need(ok,message):
    if not ok:raise ValueError(message)


def q(value):return F(value['exact']) if isinstance(value,dict) else F(value)
def vec(value):return tuple(map(q,value))
def box(value):return [tuple(map(F,part)) for part in value]
def enc(values):return [str(v) for v in values]
def encbox(value):return [enc(part) for part in value]
def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def dot(a,b):return sum((u*v for u,v in zip(a,b)),F(0))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def add(a,b):return (a[0]+b[0],a[1]+b[1])
def scale(c,a):return (min(c*a[0],c*a[1]),max(c*a[0],c*a[1]))
def multiply(a,b):
    values=[x*y for x in a for y in b];return min(values),max(values)


def project(normal,ranges):
    result=(F(0),F(0))
    for value,part in zip(normal,ranges):result=add(result,scale(value,part))
    return result


@lru_cache(maxsize=2048)
def centre_polynomials(centre):
    need(abs(centre)<=8,'Taylor centre outside preregistered finite range')
    sine=F(0);cosine=F(0);sterm=centre;cterm=F(1);square=centre*centre
    for k in range(24):
        sine+=sterm;cosine+=cterm
        if k<23:
            sterm=-sterm*square/((2*k+2)*(2*k+3))
            cterm=-cterm*square/((2*k+1)*(2*k+2))
    error=abs(centre)**48/factorial(48)
    return sine,cosine,error


def angular_record(domain):
    a,b=domain;need(a<=b,'ordered original angular domain required')
    centre=F(((a+b)/2*65536).__floor__(),65536)
    sine,cosine,error=centre_polynomials(centre)
    return {'U_interval_exact':enc(domain),'dyadic_centre_exact':str(centre),
            'actual_offset_interval_exact':enc((a-centre,b-centre)),
            'Maclaurin_sin_exact':str(sine),'Maclaurin_cos_exact':str(cosine),
            'degree_47_Lagrange_error_exact':str(error),'Taylor_term_count':24,
            'centre_grid_denominator':65536,'original_angular_endpoints_replaced':False}


def trig_range(A,B,record):
    sine=F(record['Maclaurin_sin_exact']);cosine=F(record['Maclaurin_cos_exact']);error=F(record['degree_47_Lagrange_error_exact'])
    s=(sine-error,sine+error);c=(cosine-error,cosine+error)
    offset=tuple(map(F,record['actual_offset_interval_exact']));h=max(map(abs,offset))
    value=add(scale(A,c),scale(B,s));slope=add(scale(-A,s),scale(B,c))
    remainder=(abs(A)+abs(B))*h*h/2
    return add(add(value,multiply(slope,offset)),(-remainder,remainder))


def cylinder_domains(face):
    surface=face['local_surface'];domains=[tuple(map(q,surface[name])) for name in ['U_interval','V_interval']]
    need(all(a<=b for a,b in domains),'ordered source surface domains required')
    need(face['wires'],'complete original wires required')
    for wire in face['wires']:
        need(wire['location']['matrix_3x4_exact']==IDENTITY and wire['edge_occurrences'],'complete identity wire required')
        for occurrence in wire['edge_occurrences']:
            need(occurrence['location']['matrix_3x4_exact']==IDENTITY and occurrence['edge_index'] is not None,'complete identity occurrence required')
            curve=occurrence['pcurve'];need(curve['type']=='GeomAbs_CurveType.GeomAbs_Line','non-Line pcurve keeps original whole face')
            origin,direction=vec(curve['origin_exact']),vec(curve['direction_exact'])
            need(len(origin)==len(direction)==2,'two-dimensional complete Line pcurve required')
            a,b=q(curve['first_parameter']),q(curve['last_parameter']);need(a<=b,'ordered actual Line parameters required')
            for k in range(2):
                values=[origin[k]+direction[k]*t for t in (a,b)]
                domains[k]=(min(domains[k][0],*values),max(domains[k][1],*values))
    return domains


def face_projection(candidate,stationary,displacement,limits):
    face=candidate['complete_original_face'];surface=face['local_surface']
    need(canonical(face)==candidate['complete_original_face_canonical_sha256'],'complete original face digest differs')
    need(face['index']==candidate['face_index'],'original face index differs')
    need(face['location']['matrix_3x4_exact']==IDENTITY,'nonidentity original face placement unsupported')
    for wire in face['wires']:
        need(wire['location']['matrix_3x4_exact']==IDENTITY,'nonidentity original wire placement unsupported')
        for occurrence in wire['edge_occurrences']:
            need(occurrence['location']['matrix_3x4_exact']==IDENTITY and occurrence['edge_index'] is not None,'complete identity occurrence required')
    O,X,Y=map(vec,[surface['origin_exact'],surface['X_exact'],surface['Y_exact']])
    need(len(O)==len(X)==len(Y)==3,'three-dimensional source primitive required')
    if surface['type']=='GeomAbs_SurfaceType.GeomAbs_Plane':
        n=cross(X,Y);need(any(n),'singular source plane')
        need(dot(n,X)==dot(n,Y)==0,'exact affine normal identity failed')
        value=dot(n,O);bounds=add((value,value),project(n,displacement))
        return {'applied':True,'primitive':'plane','stationary_original_box_exact':encbox(stationary),
                'plane_normal_exact':enc(n),'plane_stationary_support_exact':str(value),
                'full_D_support_exact':enc(project(n,displacement)),
                'pieces':[{'parameter_patch_index':None,'box_exact':encbox([(stationary[k][0]+displacement[k][0],stationary[k][1]+displacement[k][1]) for k in range(3)]),
                           'additional_slabs':[{'normal_exact':enc(n),'bounds_exact':enc(bounds),'source':'exact_affine_plane'}]}],
                'original_pcurve_values_changed':False,'native_primitive_semantics_verified':False}
    need(surface['type']=='GeomAbs_SurfaceType.GeomAbs_Cylinder','unsupported original primitive retained')
    Z=vec(surface['axis_exact']);radius=q(surface['radius']);need(len(Z)==3 and radius>0,'positive original cylinder radius required')
    determinant=dot(X,cross(Y,Z));need(determinant!=0,'singular stored cylinder basis')
    domains=cylinder_domains(face);u,v=domains
    need(u[0]<u[1],'positive full angular interval required')
    count=limits['cylinder_angular_patch_count'];need(count==64,'fixed angular patch count differs')
    yz,zx=cross(Y,Z),cross(Z,X);patches=[];pieces=[]
    for index in range(count):
        angular=(u[0]+(u[1]-u[0])*index/count,u[0]+(u[1]-u[0])*(index+1)/count)
        trig=angular_record(angular);mapped=[]
        for k in range(3):
            radial=scale(radius,trig_range(X[k],Y[k],trig))
            mapped.append(add(add((O[k],O[k]),scale(Z[k],v)),radial))
        clipped=[(max(mapped[k][0],stationary[k][0]),min(mapped[k][1],stationary[k][1])) for k in range(3)]
        row={'parameter_patch_index':index,'trigonometric_certificate':trig,
             'stationary_unclipped_box_exact':encbox(mapped),'stationary_clipped_box_exact':encbox(clipped),
             'closed_parameter_endpoints_retained':True}
        empty=next((k for k,(a,b) in enumerate(clipped) if a>b),None)
        row['empty_axis']=empty
        if empty is not None:patches.append(row);continue
        A=F(trig['Maclaurin_cos_exact']);B=F(trig['Maclaurin_sin_exact'])
        n=tuple((A*yz[k]+B*zx[k])/determinant for k in range(3))
        need(any(n) and dot(n,X)==A and dot(n,Y)==B and dot(n,Z)==0,'exact radial dual-basis identity failed')
        radial=scale(radius,trig_range(A,B,trig));centre=dot(n,O)
        stationary_slab=add((centre,centre),radial);D_support=project(n,displacement)
        slab=add(stationary_slab,D_support)
        swept=[(clipped[k][0]+displacement[k][0],clipped[k][1]+displacement[k][1]) for k in range(3)]
        row.update(radial_normal_exact=enc(n),radial_dual_coordinates_exact=enc((A,B,F(0))),
                   radial_stationary_support_exact=enc(stationary_slab),full_D_support_exact=enc(D_support),
                   swept_box_exact=encbox(swept),radial_swept_support_exact=enc(slab))
        patches.append(row)
        pieces.append({'parameter_patch_index':index,'box_exact':encbox(swept),
                       'additional_slabs':[{'normal_exact':enc(n),'bounds_exact':enc(slab),'source':'exact_cylinder_patch_radial_support'}]})
    need(pieces,'no nonempty closed cylinder patch; original face retained')
    return {'applied':True,'primitive':'cylinder','stationary_original_box_exact':encbox(stationary),
            'complete_source_UV_domains_exact':encbox(domains),'basis_determinant_exact':str(determinant),
            'angular_patch_count':count,'patches':patches,'pieces':pieces,
            'original_pcurve_values_changed':False,'closed_angular_seams_and_endpoints_retained':True,
            'native_primitive_semantics_verified':False}


def build_boundary(base_boundary,frame,projection,limits):
    records={(r['input']['case_id'],r['input']['material_id']):r for r in projection['records']}
    binding=next(f for f in projection['frame_bindings'] if (f['case_id'],f['frame'])==(frame['case_id'],frame['frame']))
    need(binding['original_full_D']==frame['original_remaining_displacement_box_exact'],'original full D differs')
    displacement=box(binding['original_full_D']);zero=[(F(0),F(0))]*3
    result={'schema':'razr-r5e-source-primitive-boundary-refinement-v6','conditional_primitive_support_model_only':True,
            'native_primitive_semantics_verified':False,'native_trim_class_membership_verified':False,
            'original_raw_gate_reclassified':False,'sources':[]}
    rebuilt=[];planes=cylinders=fallbacks=0
    for side,old_source in enumerate(base_boundary['sources']):
        key=tuple(old_source['material_key']);record=records[key]
        need(list(key)==binding['moving_and_fixed_material_keys'][side],'original material/frame binding differs')
        candidates={f['face_index']:f for f in record['candidate_faces']};shift=displacement if side==0 else zero
        rows=[];new=[];face_certificates=[];seen=set()
        for base_index,old in enumerate(old_source['pieces']):
            prefix={'base_V5_piece_index':base_index,'original_piece_index':old['original_piece_index'],
                    'kind':old['kind'],'index':old['index'],'preserved_V5_replacement':old['replacement']}
            candidate=candidates.get(old['index']) if old['kind']=='face' else None
            if candidate is None:
                row=dict(prefix,replacement='unchanged',box_exact=old['box_exact'],additional_slabs=[])
                rows.append(row);new.append({'box':box(row['box_exact']),'additional_slabs':[]});continue
            need(old['replacement']=='unchanged' and old['index'] not in seen,'registered primitive must be one unchanged original V5 piece')
            seen.add(old['index']);old_box=box(old['box_exact'])
            stationary=[(old_box[k][0]-shift[k][0],old_box[k][1]-shift[k][1]) for k in range(3)]
            fixed={'face_index':old['index'],'base_V5_piece_index':base_index,
                   'source_face_canonical_sha256':candidate['complete_original_face_canonical_sha256']}
            try:certificate=dict(fixed,**face_projection(candidate,stationary,shift,limits))
            except ValueError as exc:certificate=dict(fixed,applied=False,retained_original_face_reason=str(exc))
            ci=len(face_certificates);face_certificates.append(certificate)
            if not certificate['applied']:
                fallbacks+=1;row=dict(prefix,replacement='unchanged',box_exact=old['box_exact'],additional_slabs=[])
                rows.append(row);new.append({'box':old_box,'additional_slabs':[]});continue
            if certificate['primitive']=='plane':planes+=1
            else:cylinders+=1
            for item in certificate['pieces']:
                row=dict(prefix,replacement='plane_slab' if certificate['primitive']=='plane' else 'cylinder_patch',
                         face_certificate_index=ci,**item)
                rows.append(row)
                new.append({'box':box(item['box_exact']),'additional_slabs':[
                    (vec(s['normal_exact']),tuple(map(F,s['bounds_exact']))) for s in item['additional_slabs']],
                    'slab_source':item['additional_slabs'][0]['source'] if item['additional_slabs'] else None})
        need(seen==set(candidates),'registered actual blocking face omitted')
        need(len(rows)<=limits['maximum_boundary_pieces_per_material'],'registered complete material piece capacity exceeded')
        result['sources'].append({'material_key':list(key),'base_V5_piece_count':len(old_source['pieces']),
            'known_whole_exact':old_source['whole_exact'],'pieces':rows,'face_certificates':face_certificates})
        rebuilt.append({'whole':box(old_source['whole_exact']),'pieces':new})
    result.update(applied_plane_count=planes,applied_cylinder_count=cylinders,retained_original_faces_after_rejection=fallbacks)
    return rebuilt,result
