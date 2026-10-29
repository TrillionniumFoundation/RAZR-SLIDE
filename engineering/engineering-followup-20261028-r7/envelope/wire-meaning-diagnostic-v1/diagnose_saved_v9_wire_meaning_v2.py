"""Finite source-curve/contact and conditional winding diagnosis of four saved targets.

This standalone diagnostic imports no producer, helper, or native CAD code.
It does not qualify a bounded face, change a source carrier, or run refinement.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
from functools import lru_cache
import gzip
import hashlib
import json
from math import factorial
from pathlib import Path
import resource
import signal
import sys
import time
import traceback


IDENTITY = [['1','0','0','0'],['0','1','0','0'],['0','0','1','0']]
PREDICATES = ('clip_endpoint_inequalities', 'source_line_target_inequalities',
              'circle_witness_inequalities', 'homotopy_point_inequalities',
              'winding_predicates', 'target_binding_inequalities')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def ident(path):
    p=Path(path).resolve(); h=hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576), b''):
            h.update(block)
    return {'path':str(p), 'bytes':p.stat().st_size, 'sha256':h.hexdigest()}


def same(a,b): return all(a[k]==b[k] for k in ('bytes','sha256'))
def canonical(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def q(x): return F(x['exact']) if isinstance(x,dict) else F(x)
def vec(x): return tuple(map(q,x))
def box(x): return tuple(tuple(map(F,row)) for row in x)
def encpoint(x): return [str(v) for v in x]
def encbox(x): return [encpoint(row) for row in x]
def dot(a,b): return sum((x*y for x,y in zip(a,b)),F(0))
def interval_add(a,b): return a[0]+b[0],a[1]+b[1]
def interval_scale(c,a): return min(c*a[0],c*a[1]),max(c*a[0],c*a[1])
def interval_multiply(a,b):
    v=[x*y for x in a for y in b]
    return min(v),max(v)


def interval_project(n,ranges):
    result=(F(0),F(0))
    for coefficient,interval in zip(n,ranges):
        result=interval_add(result,interval_scale(coefficient,interval))
    return result


def load(row,compressed=False):
    need(same(ident(row['path']),row),'registered input changed')
    if compressed:
        with gzip.open(row['path'],'rb') as stream: raw=stream.read(67108865)
    else:
        need(row['bytes']<=67108864,'registered input byte cap exceeded')
        raw=Path(row['path']).read_bytes()
    need(len(raw)<=67108864,'registered decoded input cap exceeded')
    return json.loads(raw)


def charge(counters,name,amount=1):
    need(name in PREDICATES,'registered predicate category required')
    counters[name]+=amount
    need(sum(counters[k] for k in PREDICATES)<=100000,'registered 100000 exact-predicate diagnostic cap exceeded')


def unique_adjacent(points):
    out=[]
    for p in points:
        if not out or out[-1]!=p: out.append(p)
    if len(out)>1 and out[-1]==out[0]: out.pop()
    return out


def clip_polygon(vertices,normal,bound,counters):
    if not vertices:return []
    out=[]
    for previous,current in zip(vertices[-1:]+vertices[:-1],vertices):
        pv,cv=dot(normal,previous),dot(normal,current)
        charge(counters,'clip_endpoint_inequalities',2)
        pin,cin=pv<=bound,cv<=bound
        if pin!=cin:
            need(cv!=pv,'crossing edge has nonzero exact denominator')
            t=(bound-pv)/(cv-pv)
            need(0<=t<=1,'closed clipping parameter outside edge')
            p=tuple(previous[k]+t*(current[k]-previous[k]) for k in range(2))
            need(dot(normal,p)==bound,'exact clipping equation differs')
            out.append(p)
        if cin:out.append(current)
    out=unique_adjacent(out)
    need(len(out)<=16,'registered at most sixteen active halfplanes exceeded')
    return out


def hull(points):
    return tuple((min(p[k] for p in points),max(p[k] for p in points)) for k in range(2)) if points else None


def rectangle_constraints(bounds):
    return [((F(1),F(0)),bounds[0][1]),((-F(1),F(0)),-bounds[0][0]),
            ((F(0),F(1)),bounds[1][1]),((F(0),-F(1)),-bounds[1][0])]


def saved_cover_intersection(vertices,piece,counters):
    constraints=rectangle_constraints(box(piece['box_exact']))
    need(len(piece['additional_slabs'])<=1,'original at-most-one UV support slab required')
    for s in piece['additional_slabs']:
        n=vec(s['normal_exact']); low,high=map(F,s['bounds_exact'])
        constraints.extend([(n,high),(tuple(-v for v in n),-low)])
    need(len(constraints)<=6,'fixed original piece halfplane count exceeded')
    out=list(vertices)
    for n,b in constraints:out=clip_polygon(out,n,b,counters)
    bounds=hull(out)
    return {'intersects_closed_target':bool(out), 'intersection_hull_exact':encbox(bounds) if bounds else None,
            'nonempty_zero_width_retained':bool(bounds and any(a==b for a,b in bounds))}


def line_target_interval(origin,direction,domain,constraints,counters):
    low,high=domain
    for n,b in constraints:
        coefficient=dot(n,direction); remaining=b-dot(n,origin)
        charge(counters,'source_line_target_inequalities',6)
        if coefficient==0:
            if remaining<0:return None
        elif coefficient>0:
            high=min(high,remaining/coefficient)
        else:
            low=max(low,remaining/coefficient)
        if low>high:return None
    return low,high


@lru_cache(maxsize=1024)
def trig_point(t):
    """Degree-63 Taylor polynomials; both remainders bounded by |t|^64/64!."""
    need(abs(t)<=8,'original fixed angular range exceeded')
    sine=F(0);cosine=F(0);st=t;ct=F(1);square=t*t
    for k in range(32):
        sine+=st;cosine+=ct
        if k<31:
            st=-st*square/((2*k+2)*(2*k+3))
            ct=-ct*square/((2*k+1)*(2*k+2))
    error=abs(t)**64/factorial(64)
    return (sine-error,sine+error),(cosine-error,cosine+error),error


def trig_linear_range(A,B,domain):
    centre=(domain[0]+domain[1])/2
    sine,cosine,error=trig_point(centre)
    offset=(domain[0]-centre,domain[1]-centre)
    value=interval_add(interval_scale(A,cosine),interval_scale(B,sine))
    derivative=interval_add(interval_scale(-A,sine),interval_scale(B,cosine))
    remainder=(abs(A)+abs(B))*max(map(abs,offset))**2/2
    return interval_add(interval_add(value,interval_multiply(derivative,offset)),(-remainder,remainder))


def circle_box(curve,domain):
    O,X,Y=vec(curve['center_exact']),vec(curve['X_exact']),vec(curve['Y_exact']);radius=q(curve['radius'])
    need(radius>0 and X[0]*Y[1]-X[1]*Y[0]!=0,'complete regular original Circle required')
    return tuple(interval_add((O[k],O[k]),interval_scale(radius,trig_linear_range(X[k],Y[k],domain))) for k in range(2))


def source_endpoint_box(curve,t):
    if curve['type'].split('.')[-1]=='GeomAbs_Line':
        O,V=vec(curve['origin_exact']),vec(curve['direction_exact'])
        return tuple((O[k]+t*V[k],O[k]+t*V[k]) for k in range(2))
    return circle_box(curve,(t,t))


def midpoint(bounds):return tuple((a+b)/2 for a,b in bounds)


def point_box_disjoint(point,bounds,counters):
    charge(counters,'homotopy_point_inequalities',4)
    return any(point[k]<bounds[k][0] or point[k]>bounds[k][1] for k in range(2))


def polygon_winding(segments,point,counters):
    need(segments and all(segments[i][1]==segments[(i+1)%len(segments)][0] for i in range(len(segments))),
         'complete exactly closed rational representative required')
    winding=0;boundary=[]
    for i,(a,b) in enumerate(segments):
        cross=(b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0])
        charge(counters,'winding_predicates',15)
        if cross==0 and all(min(a[k],b[k])<=point[k]<=max(a[k],b[k]) for k in range(2)):
            boundary.append(i)
        if a[1]<=point[1]<b[1] and cross>0:winding+=1
        if b[1]<=point[1]<a[1] and cross<0:winding-=1
    return {'integer':winding,'representative_boundary_segment_indices':boundary}


def classify_source_wire(face,model,point,counters):
    need(len(face['wires'])==len(model['wire_certificates'])==1,'registered single original outer wire required')
    wire=face['wires'][0];wc=model['wire_certificates'][0]
    need(wire['is_outer'] is True and wc['original_is_outer'] is True,'selected original outer-wire identity differs')
    need(wire['location']['matrix_3x4_exact']==IDENTITY and wc['original_orientation']==wire['orientation'],
         'complete original wire orientation/location differs')
    occurrences=wire['edge_occurrences'];successors=wc['successor_indices'];count=len(occurrences)
    need(wc['source_occurrence_count']==count and len(successors)==count and sorted(successors)==list(range(count)),
         'full original occurrence/successor census differs')
    pieces=model['uv_boundary_pieces'];source_parts={};endpoint_boxes={};homotopy=[];source_line_contacts=[]
    for oi,occurrence in enumerate(occurrences):
        need(occurrence['location']['matrix_3x4_exact']==IDENTITY,'complete original identity occurrence required')
        orientation=occurrence['orientation'].split('.')[-1]
        need(orientation in ('TopAbs_FORWARD','TopAbs_REVERSED'),'unsupported original occurrence orientation')
        curve=occurrence['pcurve'];kind=curve['type'].split('.')[-1]
        domain=(q(curve['first_parameter']),q(curve['last_parameter']))
        need(domain[0]<=domain[1] and kind in ('GeomAbs_Line','GeomAbs_Circle'),'complete original ordered Line/Circle domain required')
        source=[(i,p) for i,p in enumerate(pieces) if p['occurrence_index']==oi and p['kind']!='closure']
        expected=1 if kind=='GeomAbs_Line' else 64
        need(len(source)==expected and all(p['source_edge_index']==occurrence['edge_index'] and p['wire_index']==wire['index'] for _,p in source),
             'source occurrence/full-piece binding differs')
        parts=[];endboxes=[]
        for patch,(pi,piece) in enumerate(source):
            patch_domain=domain if expected==1 else (domain[0]+(domain[1]-domain[0])*patch/64,domain[0]+(domain[1]-domain[0])*(patch+1)/64)
            need(piece['parameter_interval_exact']==encpoint(patch_domain) and piece['kind']==('line' if expected==1 else 'circle_patch'),
                 'complete original parameter patch identity differs')
            if expected==64:need(piece['parameter_patch_index']==patch,'fixed original angular patch ordering differs')
            a_box,b_box=(source_endpoint_box(curve,t) for t in patch_domain)
            a,b=midpoint(a_box),midpoint(b_box)
            if kind=='GeomAbs_Line':
                O,V=vec(curve['origin_exact']),vec(curve['direction_exact'])
                exact_box=tuple(interval_add((O[k],O[k]),interval_scale(V[k],domain)) for k in range(2))
                n=(-V[1],V[0]);value=dot(n,O)
                need(piece['box_exact']==encbox(exact_box) and piece['additional_slabs']==[{'normal_exact':encpoint(n),'bounds_exact':[str(value),str(value)],'source':'exact_pcurve_line'}],
                     'original exact Line carrier differs')
                cover=None
            else:
                bound=circle_box(curve,patch_domain)
                cover=tuple((min(bound[k][0],a_box[k][0],b_box[k][0]),max(bound[k][1],a_box[k][1],b_box[k][1])) for k in range(2))
            parts.append({'start':a,'end':b,'source_piece_index':pi,'kind':piece['kind'],'cover':cover,
                          'source_edge_index':occurrence['edge_index'],'parameter_interval_exact':encpoint(patch_domain)})
            endboxes.append((a_box,b_box))
        if orientation=='TopAbs_REVERSED':
            parts=[dict(p,start=p['end'],end=p['start']) for p in reversed(parts)]
            endpoints=(endboxes[-1][1],endboxes[0][0])
        else:endpoints=(endboxes[0][0],endboxes[-1][1])
        source_parts[oi]=parts;endpoint_boxes[oi]=endpoints
    ordered=[];seen=set();oi=0;gap_rows=[]
    for _ in range(count):
        need(oi not in seen,'source successor has early cycle');seen.add(oi)
        parts=source_parts[oi];ordered.extend(parts);nxt=successors[oi]
        join=wc['join_certificates'][oi]
        need(join['terminal_occurrence_index']==oi and join['initial_occurrence_index']==nxt,'original source join identity differs')
        gap=box(join['closed_gap_box_exact'])
        end_box,start_box=endpoint_boxes[oi][1],endpoint_boxes[nxt][0]
        need(all(gap[k][0]<=end_box[k][0]<=end_box[k][1]<=gap[k][1] and gap[k][0]<=start_box[k][0]<=start_box[k][1]<=gap[k][1] for k in range(2)),
             'independent original endpoint interval not contained in original closed-gap carrier')
        closures=[(i,p) for i,p in enumerate(pieces) if p['kind']=='closure' and p['occurrence_index']==oi]
        need(len(closures)==1 and closures[0][1]['box_exact']==join['closed_gap_box_exact'] and
             closures[0][1]['successor_occurrence_index']==nxt,'complete original closure-piece identity differs')
        ordered.append({'start':parts[-1]['end'],'end':source_parts[nxt][0]['start'],'source_piece_index':closures[0][0],
                        'kind':'closure','cover':gap,'source_edge_index':occurrences[oi]['edge_index'],'parameter_interval_exact':None})
        gap_rows.append({'terminal_occurrence_index':oi,'initial_occurrence_index':nxt,'source_closed_gap_box_exact':encbox(gap),
                         'independent_endpoint_intervals_contained':True})
        oi=nxt
    need(oi==0 and len(seen)==count and len(ordered)==len(pieces),'complete one-cycle original wire traversal differs')
    obstructed=[]
    for entry in ordered:
        if entry['cover'] is not None:
            disjoint=point_box_disjoint(point,entry['cover'],counters)
            if not disjoint:obstructed.append(entry['source_piece_index'])
            homotopy.append({'source_piece_index':entry['source_piece_index'],'kind':entry['kind'],
                             'independent_convex_homotopy_box_exact':encbox(entry['cover']),
                             'query_point_strictly_outside_box':disjoint})
    result=polygon_winding([(p['start'],p['end']) for p in ordered],point,counters)
    certified=not obstructed and not result['representative_boundary_segment_indices']
    return {'original_wire_index':wire['index'],'original_is_outer':True,'original_inner_wire_count':0,
            'original_wire_orientation':wire['orientation'],'source_occurrence_count':count,'complete_source_piece_count':len(pieces),
            'rational_representative_vertices_exact':[encpoint(p['start']) for p in ordered],
            'source_piece_traversal_indices':[p['source_piece_index'] for p in ordered],
            'convex_homotopy_records':homotopy,'source_gap_containment':gap_rows,
            'representative_winding':result,'homotopy_point_obstruction_piece_indices':obstructed,
            'source_curve_and_all_original_gap_realizations_winding_certified':certified,
            'certified_winding_integer':result['integer'] if certified else None,
            'simple_source_wire_proved':False,'native_trimmed_region_membership_proved':False,
            'point_geometric_interpretation':('nonzero outer-wire winding; interior only under simple-wire filling premise' if result['integer']!=0
                                               else 'zero outer-wire winding; no inner wire in original source') if certified
                                              else 'unresolved: query touches representative or a convex homotopy/gap cover'}


def circle_parameter_witness(curve,t,constraints,counters):
    bounds=circle_box(curve,(t,t));checks=[];inside=True;strict=True
    for n,b in constraints:
        projected=interval_project(n,bounds);charge(counters,'circle_witness_inequalities',2)
        contained=projected[1]<=b
        inside=inside and contained
        if any(n):strict=strict and projected[1]<b
        checks.append({'normal_exact':encpoint(n),'upper_exact':str(b),'point_projection_interval_exact':encpoint(projected),
                       'entire_interval_satisfies_closed_constraint':contained})
    return {'original_parameter_exact':str(t),'independent_source_curve_point_box_exact':encbox(bounds),
            'degree_63_Taylor_remainder_exact':str(trig_point(t)[2]),'complete_target_constraint_checks':checks,
            'certified_actual_source_curve_point_in_closed_target':inside,
            'certified_strict_against_all_nonconstant_target_constraints':inside and strict,
            'negative_outcome_means':None if inside else 'this fixed parameter is not a certified witness; curve/target separation is not implied'}


def analytic_controls(counters):
    zero=F(0);one=F(1)
    vertices=[(zero,zero),(one,zero),(one,one),(zero,one)]
    segments=list(zip(vertices,vertices[1:]+vertices[:1]));inside=(F(1,2),F(1,2))
    rows=[]
    for name,s,p,expected,boundary in [('square-positive-winding',segments,inside,1,False),
         ('square-negative-winding',[(b,a) for a,b in reversed(segments)],inside,-1,False),
         ('square-exterior-zero',segments,(F(2),F(1,2)),0,False),
         ('closed-square-boundary',segments,(zero,F(1,2)),1,True)]:
        r=polygon_winding(s,p,counters)
        need(r['integer']==expected and bool(r['representative_boundary_segment_indices'])==boundary,'synthetic winding control failed: '+name)
        rows.append({'name':name,'execution_kind':'synthetic_analytic_diagnostic','passed':True,'result':r})
    constraints=rectangle_constraints(((zero,zero),(zero,zero)))
    r=line_target_interval((zero,zero),(one,zero),(-one,one),constraints,counters)
    need(r==(zero,zero),'closed zero-dimensional Line contact must be retained')
    rows.append({'name':'closed-point-Line-contact','execution_kind':'synthetic_analytic_diagnostic','passed':True,'parameter_interval_exact':encpoint(r)})
    r=line_target_interval((zero,one),(one,zero),(-one,one),constraints,counters)
    need(r is None,'strictly separated Line control failed')
    rows.append({'name':'strict-Line-separation','execution_kind':'synthetic_analytic_diagnostic','passed':True})
    curve={'center_exact':['0','0'],'X_exact':['1','0'],'Y_exact':['0','1'],'radius':'1'}
    r=circle_parameter_witness(curve,zero,rectangle_constraints(((one,one),(zero,zero))),counters)
    need(r['certified_actual_source_curve_point_in_closed_target'],'closed exact Circle endpoint control failed')
    rows.append({'name':'closed-Circle-point-contact','execution_kind':'synthetic_analytic_diagnostic','passed':True,'result':r})
    need(not point_box_disjoint(inside,((zero,one),(zero,one)),counters),'point inside uncertain closure must remain unresolved')
    rows.append({'name':'uncertain-closure-not-certified','execution_kind':'synthetic_analytic_diagnostic','passed':True})
    return rows


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();contract=json.loads(args.contract.read_text())
    need(sys.flags.isolated==1 and sys.flags.no_site==1 and sys.flags.optimize==0,'isolated unoptimized entry required')
    need(contract['schema']=='razr-r7e-wire-meaning-diagnostic-contract-v2' and same(ident(__file__),contract['source']),
         'registered standalone diagnostic identity differs')
    need(contract['wall_seconds']==60 and contract['address_space_bytes']==536870912 and contract['maximum_exact_predicates']==100000,
         'original finite diagnostic resource registration differs')
    need(not args.output.exists(),'new diagnostic output directory required');args.output.mkdir(parents=True)
    started=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('registered 60-second wire-meaning diagnostic cap')));signal.alarm(60)
    counters=Counter({k:0 for k in PREDICATES})
    report={'schema':'razr-r7e-saved-v9-wire-meaning-diagnostic-v2','started_utc':datetime.now(timezone.utc).isoformat(),
            'completed':False,'source':ident(__file__),'contract':ident(args.contract),'new_scientific_qualification':False,
            'original_V9_owned_verification_passed':False,'original_first_u_gate_reached':False,'native_operations':0,
            'producer_or_helper_imported':False,'full_material_searches':0,'new_refinement_nodes':0,
            'native_trimmed_region_membership_proved':False,'all_blockers_closed':False,'full_continuous_G2':False,'targets':[]}
    try:
        inputs=contract['inputs'];before={k:ident(v['path']) for k,v in inputs.items()}
        need(all(same(before[k],v) for k,v in inputs.items()),'complete registered source/input identity differs')
        prior_contract=load(inputs['prior_diagnostic_contract']);prior=load(inputs['prior_diagnostic_report'])
        need(same(prior['source'],inputs['prior_diagnostic_source']) and same(prior['contract'],inputs['prior_diagnostic_contract']) and prior['completed'],
             'actual original correlation diagnostic binding differs')
        for key,row in prior_contract['inputs'].items():
            need(same(row,inputs[key]) and same(prior['source_input_identities'][key],inputs[key]),'all prior original input bindings must remain exact')
        controller=load(inputs['actual_V9_checker_controller'])
        need(controller['completed'] is False and controller['worker_exit_code']==0 and controller['failure']==prior['actual_V9_verifier_owned_failure']==
             {'type':'RuntimeError','message':"still-running owned child RSS unavailable: KeyError: 'VmRSS'"},'original owned failure must remain explicit')
        need(prior['original_first_u_gate_reached'] is False and prior['new_full_material_searches']==0 and
             len(prior['new_diagnostic_local_plane_probes'])==4,'fixed original four-target diagnostic scope differs')
        actual=load(inputs['actual_V9_certificate'],True);root=actual['roots'][0];frame=actual['frame']
        need(len(actual['roots'])==1 and root['base_V6_leaf_locator']==[76,47] and root['tree']['nodes'][0]['id']==0,
             'fixed original V9 root/node differs')
        source_lock=load(inputs['frozen_V9_source_lock']);frozen={r['path']:r for r in source_lock['r5_files']}
        need(same(inputs['original_primitive_projection'],frozen['R5E_V6_PRIMITIVE_SOURCE.json.gz']) and
             same(inputs['additional_original_projection'],frozen['R7E_V9_ORIGINAL_LINE_PLANE_PROJECTION.json']),
             'frozen complete original source projections differ')
        original=load(inputs['original_primitive_projection'],True);additional=load(inputs['additional_original_projection'])
        faces={}
        for record in original['records']+additional['records']:
            for candidate in record['candidate_faces']:
                key=(record['input']['case_id'],record['input']['material_id'],candidate['face_index'])
                need(key not in faces,'unique complete original face mapping required');faces[key]=candidate
        models={m['model_index']:m for s in actual['planar_models']['sources'] for m in s['models']}
        failures=root['tree']['nodes'][0]['actual_channel_observation']['all_registered_channels_unresolved']
        failure_map={(f['material_side'],f['axis'],f['end']):f for f in failures}
        need(len(failure_map)==12 and len(models)==8,'complete unchanged actual root/model census required')
        report['synthetic_controls']=analytic_controls(counters)
        total_pieces=0;total_lines=0;total_fixed_circle_parameters=0
        for probe in prior['new_diagnostic_local_plane_probes']:
            mi=probe['model_index'];model=models[mi];fi=probe['original_face_index']
            need(fi in (37,39,41,42) and probe['material_side']==0 and probe['actual_node_id']==0 and model['original_face_index']==fi,
                 'fixed four original actual face targets required')
            f=failure_map[(0,probe['spatial_axis'],probe['spatial_end'])];attempt=f['planar_exterior_attempt']
            need(attempt['model_index']==mi and attempt['stationary_candidate_box_exact']==probe['stationary_candidate_box_exact'] and
                 probe['full_original_D_exact']==model['full_D_exact']==frame['original_remaining_displacement_box_exact'],
                 'full original D and actual saved spatial target must be unchanged')
            candidate=faces[('case-028',3,fi)];face=candidate['complete_original_face'];surface=face['local_surface']
            need(canonical(face)==candidate['complete_original_face_canonical_sha256']==model['source_face_canonical_sha256'] and
                 face['index']==fi and surface['type']=='GeomAbs_SurfaceType.GeomAbs_Plane','complete original face identity/type differs')
            O,X,Y=[vec(surface[k]) for k in ('origin_exact','X_exact','Y_exact')]
            need(all(model[label]==encpoint(v) for label,v in [('plane_origin_exact',O),('basis_X_exact',X),('basis_Y_exact',Y)]),
                 'original exact affine plane source differs')
            known=box(model['known_UV_box_exact']);B=box(probe['stationary_candidate_box_exact'])
            constraints=rectangle_constraints(known)
            for k in range(3):constraints.extend([((X[k],Y[k]),B[k][1]-O[k]),((-X[k],-Y[k]),O[k]-B[k][0])])
            need(probe['all_closed_halfplanes']==[{'normal_exact':encpoint(n),'upper_exact':str(b)} for n,b in constraints],
                 'complete original preimage constraints differ')
            vertices=unique_adjacent([(known[0][0],known[1][0]),(known[0][1],known[1][0]),(known[0][1],known[1][1]),(known[0][0],known[1][1])])
            for n,b in constraints[4:]:vertices=clip_polygon(vertices,n,b,counters)
            need(vertices and [encpoint(p) for p in vertices]==probe['final_clipped_vertices_exact'] and encbox(hull(vertices))==probe['hull_exact'],
                 'complete original exact preimage polygon differs')
            point=tuple(sum((p[k] for p in vertices),F(0))/len(vertices) for k in range(2))
            for n,b in constraints:
                charge(counters,'target_binding_inequalities');need(dot(n,point)<=b,'fixed vertex-average point left closed convex target')
            row={'original_face_index':fi,'model_index':mi,'material_side':0,'spatial_axis':probe['spatial_axis'],'spatial_end':probe['spatial_end'],
                 'original_face_canonical_sha256':model['source_face_canonical_sha256'],'full_original_D_exact':model['full_D_exact'],
                 'complete_closed_target_vertices_exact':[encpoint(p) for p in vertices],'fixed_query_point_exact':encpoint(point),
                 'fixed_query_rule':'arithmetic average of the complete saved convex polygon vertices',
                 'saved_source_piece_cover_tests':[],'original_Line_target_tests':[],'fixed_original_Circle_parameter_tests':[]}
            pieces=model['uv_boundary_pieces'];need(len(pieces)==(225 if fi in (37,39) else 8),'complete fixed source-piece census differs')
            total_pieces+=len(pieces)
            for i,piece in enumerate(pieces):
                result=saved_cover_intersection(vertices,piece,counters)
                result.update(source_piece_index=i,kind=piece['kind'],source_edge_index=piece['source_edge_index'])
                row['saved_source_piece_cover_tests'].append(result)
            wire=face['wires'][0]
            for oi,occurrence in enumerate(wire['edge_occurrences']):
                curve=occurrence['pcurve']
                if curve['type'].split('.')[-1]!='GeomAbs_Line':continue
                domain=(q(curve['first_parameter']),q(curve['last_parameter']));origin=vec(curve['origin_exact']);direction=vec(curve['direction_exact'])
                intersection=line_target_interval(origin,direction,domain,constraints,counters);total_lines+=1
                witness_t=(intersection[0]+intersection[1])/2 if intersection else None
                row['original_Line_target_tests'].append({'occurrence_index':oi,'source_edge_index':occurrence['edge_index'],
                    'complete_original_parameter_interval_exact':encpoint(domain),'intersects_closed_target':intersection is not None,
                    'exact_intersection_parameter_interval':encpoint(intersection) if intersection is not None else None,
                    'exact_source_curve_witness_parameter':str(witness_t) if witness_t is not None else None,
                    'exact_source_curve_witness_point':encpoint(tuple(origin[k]+witness_t*direction[k] for k in range(2))) if witness_t is not None else None})
            selected=[]
            for path in probe['new_local_UV_channel_probes']:
                blocker=path['first_remaining_blocker']
                if blocker and blocker['kind']=='circle_patch' and blocker['piece_index'] not in selected:selected.append(blocker['piece_index'])
            need(len(selected)<=(1 if fi in (37,39) else 0),'fixed actually observed Circle-blocker census differs')
            for pi in selected:
                piece=pieces[pi];occurrence=wire['edge_occurrences'][piece['occurrence_index']];curve=occurrence['pcurve']
                need(piece['source_edge_index']==occurrence['edge_index'] and piece['kind']=='circle_patch','fixed Circle-blocker source differs')
                a,b=map(F,piece['parameter_interval_exact'])
                tests=[circle_parameter_witness(curve,t,constraints,counters) for t in (a,(a+b)/2,b)];total_fixed_circle_parameters+=3
                row['fixed_original_Circle_parameter_tests'].append({'actual_first_blocker_piece_index':pi,'source_edge_index':piece['source_edge_index'],
                    'parameter_patch_index':piece['parameter_patch_index'],'complete_original_patch_interval_exact':[str(a),str(b)],
                    'fixed_parameter_rule':'first endpoint, exact midpoint, last endpoint of the saved first-blocker patch','tests':tests})
            row['wire_winding_diagnosis']=classify_source_wire(face,model,point,counters)
            cover_hits=[p['source_piece_index'] for p in row['saved_source_piece_cover_tests'] if p['intersects_closed_target']]
            line_contacts=sum(p['intersects_closed_target'] for p in row['original_Line_target_tests'])
            circle_contacts=sum(t['certified_actual_source_curve_point_in_closed_target'] for p in row['fixed_original_Circle_parameter_tests'] for t in p['tests'])
            row.update(saved_boundary_cover_contact_piece_indices=cover_hits,all_saved_boundary_covers_separated_from_closed_target=not cover_hits,
                       actual_source_Line_contact_count=line_contacts,certified_actual_source_Circle_point_contact_count=circle_contacts,
                       actual_source_boundary_contact_proved=bool(line_contacts or circle_contacts),
                       boundary_cover_only_uncertainty=bool(cover_hits and not (line_contacts or circle_contacts)),
                       simple_wire_filling_semantics_assumed=False,native_face_contact_or_membership_proved=False)
            report['targets'].append(row)
        need(total_pieces==466 and total_lines==38 and total_fixed_circle_parameters==6,'registered finite original source/parameter census differs')
        report.update(completed=True,source_input_identities=before,original_V9_owned_failure_retained=controller['failure'],
                      complete_saved_source_piece_tests=total_pieces,complete_original_Line_tests=total_lines,
                      fixed_original_Circle_parameter_tests=total_fixed_circle_parameters,
                      independent_Taylor_parameter_count=trig_point.cache_info().currsize,
                      fixed_original_angular_subdivision=64,Taylor_terms_per_function=32,
                      all_inputs_unchanged=all(same(ident(v['path']),before[k]) for k,v in inputs.items()))
        need(report['independent_Taylor_parameter_count']<=512,'registered finite Taylor parameter cache exceeded')
        need(report['all_inputs_unchanged'],'registered original input changed during diagnostic')
    except Exception as exc:
        report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0)
        report.update(counters=dict(counters),elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                      finished_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=60,address_space_bytes=536870912)
        output=args.output/'R7E_SAVED_V9_WIRE_MEANING_DIAGNOSIS_V2.json'
        output.write_text(json.dumps(report,indent=2)+'\n')
        need(output.stat().st_size<=8388608,'registered 8-MiB diagnostic output cap exceeded')
    print(json.dumps({'completed':report['completed'],'report':ident(output),'seconds':report['elapsed_seconds'],
                      'RSS':report['peak_RSS_bytes'],'failure':report.get('failure')}))
    return 0 if report['completed'] else 2


if __name__=='__main__':raise SystemExit(main())
