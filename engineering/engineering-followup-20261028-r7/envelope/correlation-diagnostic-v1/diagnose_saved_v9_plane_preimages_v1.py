"""Finite exact plane-preimage probe on actual saved V9 failed prefixes.

This is a new bounded diagnostic, not a qualification or whole-material run.
No producer/helper import, native call, changed old source, or gate relaxation.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
import gc
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import resource
import signal
import sys
import time
import traceback


def need(ok, message):
    if not ok:
        raise ValueError(message)


def ident(path):
    p = Path(path).resolve(); h = hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):
            h.update(block)
    return {'path':str(p), 'bytes':p.stat().st_size, 'sha256':h.hexdigest()}


def same(a,b): return all(a[k] == b[k] for k in ('bytes','sha256'))
def canonical(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def q(x): return F(x['exact']) if isinstance(x,dict) else F(x)
def box(x): return tuple(tuple(map(F,p)) for p in x)
def encbox(x): return [[str(v) for v in p] for p in x]
def encpoint(x): return [str(v) for v in x]
def dot(a,b): return sum((x*y for x,y in zip(a,b)),F(0))


def load(row, compressed=False):
    need(same(ident(row['path']),row), 'bound original input changed')
    if compressed:
        with gzip.open(row['path'],'rb') as stream: raw=stream.read(67108865)
    else:
        need(row['bytes'] <= 67108864,'input size exceeds registered cap')
        raw=Path(row['path']).read_bytes()
    need(len(raw) <= 67108864,'decoded source exceeds registered cap')
    return json.loads(raw)


def charge(counters,name,amount=1):
    counters[name] += amount
    need(sum(counters[k] for k in ('clip_endpoint_inequalities','vertex_feasibility_inequalities','UV_support_inequalities')) <= 100000,
         'registered combined diagnostic exact inequality limit')
    need(counters['UV_piece_tests'] <= 10800,'registered finite UV-piece diagnostic limit')


def unique_adjacent(vertices):
    result=[]
    for p in vertices:
        if not result or result[-1] != p: result.append(p)
    if len(result)>1 and result[0] == result[-1]: result.pop()
    return result


def clip_polygon(vertices, normal, bound, counters):
    """Closed exact halfplane clipping; a point or segment remains nonempty."""
    if not vertices:return []
    output=[]
    for previous,current in zip(vertices[-1:]+vertices[:-1],vertices):
        p=dot(normal,previous); c=dot(normal,current)
        charge(counters,'clip_endpoint_inequalities',2)
        pin,cin=p<=bound,c<=bound
        if pin != cin:
            need(c != p,'crossing exact edge needs nonzero interpolation denominator')
            t=(bound-p)/(c-p)
            need(0<=t<=1,'closed exact intersection lies on source edge')
            intersection=tuple(previous[k]+t*(current[k]-previous[k]) for k in range(2))
            need(dot(normal,intersection)==bound,'exact clipping intersection equation differs')
            output.append(intersection)
        if cin:output.append(current)
    result=unique_adjacent(output)
    need(len(result)<=10,'bounded ten-halfplane polygon vertex census exceeded')
    return result


def hull(vertices):
    return tuple((min(p[k] for p in vertices),max(p[k] for p in vertices)) for k in range(2)) if vertices else None


def bounded_preimage(known, spatial_constraints, counters):
    need(all(a<=b for a,b in known),'closed ordered initial UV box required')
    domain_constraints=[((F(1),F(0)),known[0][1]),((-F(1),F(0)),-known[0][0]),
                        ((F(0),F(1)),known[1][1]),((F(0),-F(1)),-known[1][0])]
    constraints=domain_constraints+spatial_constraints
    need(len(constraints)<=10,'registered finite halfplane count exceeded')
    vertices=unique_adjacent([(known[0][0],known[1][0]),(known[0][1],known[1][0]),
                              (known[0][1],known[1][1]),(known[0][0],known[1][1])])
    trace=[]
    for i,(normal,bound) in enumerate(spatial_constraints):
        vertices=clip_polygon(vertices,normal,bound,counters)
        trace.append({'constraint_index':i+4,'closed_vertices_exact':[encpoint(p) for p in vertices]})
    candidates=[]; nonsingular=0
    for (a,b),(c,d) in itertools.combinations(constraints,2):
        determinant=a[0]*c[1]-a[1]*c[0]
        if determinant==0:continue
        nonsingular+=1
        p=((b*c[1]-a[1]*d)/determinant,(a[0]*d-b*c[0])/determinant)
        feasible=True
        for normal,bound in constraints:
            charge(counters,'vertex_feasibility_inequalities')
            if dot(normal,p)>bound:feasible=False;break
        if feasible and p not in candidates:candidates.append(p)
    need(bool(vertices)==bool(candidates),'closed clipping and independently enumerated feasible vertices disagree on emptiness')
    clipped_hull=hull(vertices); enum_hull=hull(candidates)
    need(clipped_hull==enum_hull,'independent complete vertex enumeration and clipping hull differ')
    for p in vertices:
        for n,b in constraints:
            charge(counters,'vertex_feasibility_inequalities')
            need(dot(n,p)<=b,'clipped vertex violates a complete original affine constraint')
    return {'empty':not vertices,'hull_exact':encbox(clipped_hull) if clipped_hull else None,
            'all_closed_halfplanes':[{'normal_exact':encpoint(n),'upper_exact':str(b)} for n,b in constraints],
            'clipping_trace':trace,'final_clipped_vertices_exact':[encpoint(p) for p in vertices],
            'independently_enumerated_vertices_exact':[encpoint(p) for p in candidates],
            'nonsingular_pair_count':nonsingular,'complete_pair_count':len(constraints)*(len(constraints)-1)//2,
            'two_exact_hulls_equal':True,'nonempty_zero_width_hull_retained':bool(clipped_hull and any(a==b for a,b in clipped_hull))}


def interval_projection(normal,ranges):
    lo=hi=F(0)
    for n,(a,b) in zip(normal,ranges):
        values=(n*a,n*b);lo+=min(values);hi+=max(values)
    return lo,hi


def UV_piece_separator(piece,channel,counters):
    charge(counters,'UV_piece_tests')
    ranges=box(piece['box_exact'])
    for axis in (0,1):
        charge(counters,'UV_support_inequalities')
        if channel[axis][1] < ranges[axis][0]:return str(2*axis)
        charge(counters,'UV_support_inequalities')
        if channel[axis][0] > ranges[axis][1]:return str(2*axis+1)
    need(len(piece['additional_slabs'])<=1,'at most one original UV slab supported')
    for slab in piece['additional_slabs']:
        mapped=interval_projection(tuple(map(F,slab['normal_exact'])),channel);bounds=tuple(map(F,slab['bounds_exact']))
        charge(counters,'UV_support_inequalities')
        if mapped[1]<bounds[0]:return '4'
        charge(counters,'UV_support_inequalities')
        if mapped[0]>bounds[1]:return '5'
    return None


def probe_UV_paths(target,known,pieces,counters):
    need(len(pieces)<=225,'original per-face complete UV-piece limit exceeded')
    outcomes=[]
    for axis in (0,1):
        for end in (0,1):
            channel=list(target)
            channel[axis]=(min(target[axis][0],known[axis][0]-1),target[axis][1]) if end==0 else (target[axis][0],max(target[axis][1],known[axis][1]+1))
            codes=[];blocker=None
            for i,piece in enumerate(pieces):
                code=UV_piece_separator(piece,channel,counters)
                if code is None:
                    blocker={'piece_index':i,'kind':piece['kind'],'source_edge_index':piece.get('source_edge_index')};break
                codes.append(code)
            outcomes.append({'axis':axis,'end':end,'closed_UV_channel_exact':encbox(channel),
                'complete_original_UV_cover_separated':blocker is None,'completed_prefix_piece_count':len(codes),
                'complete_piece_separation_codes':''.join(codes) if blocker is None else None,'first_remaining_blocker':blocker})
    return outcomes


def analytic_controls(counters):
    known=((-F(1),F(1)),(-F(1),F(1)))
    examples=[('full-rectangle',[],known),
              ('closed-segment',[((F(1),F(0)),F(0)),((-F(1),F(0)),F(0))],((F(0),F(0)),known[1])),
              ('closed-single-point',[((F(1),F(0)),F(0)),((-F(1),F(0)),F(0)),((F(0),F(1)),F(0)),((F(0),-F(1)),F(0))],((F(0),F(0)),(F(0),F(0)))),
              ('strictly-empty',[((-F(1),F(0)),-F(2))],None),
              ('positive-tiny-strip',[((-F(1),F(0)),F(0)),((F(1),F(0)),F(1,2**80))],((F(0),F(1,2**80)),known[1]))]
    rows=[]
    for name,constraints,expected in examples:
        actual=bounded_preimage(known,constraints,counters)
        need(actual['hull_exact']==(encbox(expected) if expected else None),'analytic closed-preimage control failed: '+name)
        rows.append({'name':name,'execution_kind':'synthetic_analytic_diagnostic','passed':True,'result':actual})
    return rows


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();need(sys.flags.isolated==1 and sys.flags.no_site==1 and sys.flags.optimize==0,'isolated unoptimized entry required')
    contract=json.loads(args.contract.read_text());need(same(ident(__file__),contract['source']),'registered diagnostic source differs')
    need(contract['wall_seconds']==60 and contract['address_space_bytes']==536870912,'registered diagnostic resource bounds differ')
    need(not args.output.exists(),'new diagnostic output directory required');args.output.mkdir(parents=True)
    started=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('60-second original-plane diagnostic cap')));signal.alarm(60)
    counters=Counter({k:0 for k in ('clip_endpoint_inequalities','vertex_feasibility_inequalities','UV_support_inequalities','UV_piece_tests')})
    report={'schema':'razr-r7e-v9-saved-prefix-correlation-diagnostic-v1','started_utc':datetime.now(timezone.utc).isoformat(),
            'completed':False,'source':ident(__file__),'contract':ident(args.contract),'new_scientific_qualification':False,
            'original_V9_owned_verification_passed':False,'original_first_u_gate_reached':False,
            'whole_material_new_channel_exclusion_claimed':False,'native_operations':0,'producer_or_helper_imported':False,
            'all_blockers_closed':False,'full_continuous_G2':False,'new_diagnostic_local_plane_probes':[]}
    try:
        inputs=contract['inputs'];before={k:ident(v['path']) for k,v in inputs.items()};need(all(same(before[k],v) for k,v in inputs.items()),'original diagnostic input binding differs')
        producer=load(inputs['actual_V9_producer_report']);checker=load(inputs['actual_V9_checker_report']);controller=load(inputs['actual_V9_checker_controller']);pipeline=load(inputs['actual_V9_pipeline'])
        need(producer['execution_completed'] and checker['execution_completed'] and controller['worker_exit_code']==0 and controller['completed'] is False,
             'actual V9 worker-completed/owned-failed distinction differs')
        need(controller['failure']=={'type':'RuntimeError','message':"still-running owned child RSS unavailable: KeyError: 'VmRSS'"} and
             pipeline['completed'] is False and len(pipeline['stages'])==2,'original V9 ownership failure must remain explicit')
        need(checker['total_saved_planar_u_separations_verified']==0,'original V9 saved u=0 record differs')
        frame=producer['frames'][0];need((frame['case_id'],frame['frame'])==('case-028',1),'exact original selected frame required')
        need(same(frame['certificate'],inputs['actual_V9_certificate']),'actual V9 certificate identity differs')
        need(same(frame['base_V6_certificate'],inputs['original_V6_certificate']),'original V6 boundary certificate differs')
        base=load(inputs['original_V6_certificate'],True);boundary=base['boundary_refinement'];del base;gc.collect()
        actual=load(inputs['actual_V9_certificate'],True)
        need(actual['frame']=={k:v for k,v in frame.items() if k!='certificate'} and len(actual['roots'])==1,'complete original V9 frame/root binding differs')
        root=actual['roots'][0];need(root['base_V6_leaf_locator']==[76,47],'original selected V6 root/node changed')
        need(canonical(boundary)==frame['base_V6_boundary_canonical_sha256'],'complete inherited spatial source differs')
        records={m['model_index']:(side,m) for side,s in enumerate(actual['planar_models']['sources']) for m in s['models']}
        need(len(records)==8 and all(m['applied'] for _,m in records.values()),'actual eight accepted source models required')
        source_lock=load(inputs['frozen_V9_source_lock']);frozen={r['path']:r for r in source_lock['r5_files']}
        need(same(inputs['original_primitive_projection'],frozen['R5E_V6_PRIMITIVE_SOURCE.json.gz']) and
             same(inputs['additional_original_projection'],frozen['R7E_V9_ORIGINAL_LINE_PLANE_PROJECTION.json']),
             'original model projections differ from frozen V9 source lock')
        original=load(inputs['original_primitive_projection'],True);extra=load(inputs['additional_original_projection'])
        faces={}
        for item in original['records']+extra['records']:
            key=(item['input']['case_id'],item['input']['material_id'])
            for candidate in item['candidate_faces']:
                face_key=key+(candidate['face_index'],)
                need(face_key not in faces,'unique original face source mapping required')
                faces[face_key]=candidate
        for side,model in records.values():
            key=tuple(boundary['sources'][side]['material_key'])+(model['original_face_index'],);candidate=faces[key]
            face=candidate['complete_original_face'];surface=face['local_surface']
            need(canonical(face)==candidate['complete_original_face_canonical_sha256']==model['source_face_canonical_sha256'],
                 'actual plane model does not bind complete original source face')
            need(surface['type']=='GeomAbs_SurfaceType.GeomAbs_Plane' and
                 all(model[label]==[str(q(v)) for v in surface[source]] for label,source in
                     [('plane_origin_exact','origin_exact'),('basis_X_exact','X_exact'),('basis_Y_exact','Y_exact')]),
                 'actual original plane O/X/Y source differs')
        nodes=root['tree']['nodes'];need(len(nodes)==163 and sum(n['kind']=='split' for n in nodes)==81 and sum(n['kind']=='excluded' for n in nodes)==82,'actual saved node census differs')
        census=Counter();uv_census=Counter();saved=[]
        for node in nodes:
            if 'actual_channel_observation' not in node:continue
            failures=node['actual_channel_observation']['all_registered_channels_unresolved'];need(len(failures)==12,'complete saved original twelve-channel prefix required')
            concise=[]
            for f in failures:
                side,index=f['material_side'],f['unresolved_piece_index'];piece=boundary['sources'][side]['pieces'][index]
                label=(side,f['axis'],f['end'],piece['kind'],piece['index'],piece['replacement']);census[label]+=1
                row={'material_side':side,'axis':f['axis'],'end':f['end'],'original_piece_index':index,
                     'source_kind':piece['kind'],'source_index':piece['index'],'source_replacement':piece['replacement']}
                if 'planar_exterior_attempt' in f:
                    attempt=f['planar_exterior_attempt'];model=records[attempt['model_index']][1]
                    need(attempt['excluded'] is False and len(attempt['all_closed_UV_channels_unresolved'])==4,'complete saved failed UV prefix required')
                    row['model_index']=attempt['model_index'];row['UV_first_blockers']=[]
                    for item in attempt['all_closed_UV_channels_unresolved']:
                        p=model['uv_boundary_pieces'][item['unresolved_UV_piece_index']]
                        row['UV_first_blockers'].append({'axis':item['axis'],'end':item['end'],'piece_index':item['unresolved_UV_piece_index'],
                                                        'kind':p['kind'],'source_edge_index':p.get('source_edge_index')})
                        uv_census[(side,model['original_face_index'],item['axis'],item['end'],item['unresolved_UV_piece_index'],p['kind'],p.get('source_edge_index'))]+=1
                concise.append(row)
            saved.append({'node_id':node['id'],'kind':node['kind'],'failed_channels':concise})
        need(len(saved)==81 and sum(census.values())==972,'complete saved failed-prefix census differs')
        report['saved_failed_prefix_nodes']=saved
        report['spatial_blocker_frequency']=[{'key':list(k),'count':v} for k,v in sorted(census.items())]
        report['UV_blocker_frequency']=[{'key':list(k),'count':v} for k,v in sorted(uv_census.items())]
        report['actual_saved_failed_prefix_node_count']=81;report['excluded_leaf_failed_prefixes_not_saved']=82
        report['synthetic_closed_degenerate_controls']=analytic_controls(counters)
        node=nodes[0];need(node['id']==0 and node['kind']=='split','registered first actual root split required')
        cell=box(root['root_box_exact']);probes=[]
        for f in node['actual_channel_observation']['all_registered_channels_unresolved']:
            if 'planar_exterior_attempt' not in f:continue
            side=f['material_side'];attempt=f['planar_exterior_attempt'];model_side,model=records[attempt['model_index']]
            need(model_side==side and model['piece_index']==f['unresolved_piece_index'],'actual UV model/source carrier differs')
            whole=box(boundary['sources'][side]['known_whole_exact']);channel=list(cell);axis,end=f['axis'],f['end']
            channel[axis]=(min(whole[axis][0]-1,cell[axis][0]-1),cell[axis][1]) if end==0 else (cell[axis][0],max(whole[axis][1]+1,cell[axis][1]+1))
            D=box(model['full_D_exact']);stationary=box(model['stationary_face_box_exact'])
            need(encbox(D)==(frame['original_remaining_displacement_box_exact'] if side==0 else [['0','0']]*3),'whole original model D changed')
            B=tuple((max(channel[k][0]-D[k][1],stationary[k][0]),min(channel[k][1]-D[k][0],stationary[k][1])) for k in range(3))
            need(all(a<=b for a,b in B) and encbox(B)==attempt['stationary_candidate_box_exact'],'actual closed stationary candidate differs')
            O,X,Y=[tuple(map(F,model[k])) for k in ('plane_origin_exact','basis_X_exact','basis_Y_exact')]
            inverse=[tuple(map(F,r)) for r in model['left_inverse_exact']]
            need([[dot(r,c) for c in (X,Y)] for r in inverse]==[[F(1),F(0)],[F(0),F(1)]],'actual exact plane left inverse differs')
            relative=tuple((a-O[k],b-O[k]) for k,(a,b) in enumerate(B))
            old_target=tuple(interval_projection(r,relative) for r in inverse)
            need(encbox(old_target)==attempt['closed_UV_target_box_exact'],'actual old inverse-box projection differs')
            known=box(model['known_UV_box_exact']);constraints=[]
            for k in range(3):
                constraints.extend([((X[k],Y[k]),B[k][1]-O[k]),((-X[k],-Y[k]),O[k]-B[k][0])])
            result=bounded_preimage(known,constraints,counters)
            result.update(actual_node_id=0,material_side=side,spatial_axis=axis,spatial_end=end,
                          original_face_index=model['original_face_index'],model_index=model['model_index'],
                          full_original_D_exact=encbox(D),stationary_candidate_box_exact=encbox(B),
                          original_inverse_box_target_exact=encbox(old_target),known_UV_rectangle_exact=encbox(known))
            if not result['empty']:
                target=box(result['hull_exact'])
                need(all(old_target[k][0]<=target[k][0]<=target[k][1]<=old_target[k][1] for k in range(2)),
                     'exact affine-preimage hull must be contained in original inverse-box overestimate')
                result['strictly_tighter_component_count']=sum(target[k][j]!=old_target[k][j] for k in range(2) for j in range(2))
                result['new_local_UV_channel_probes']=probe_UV_paths(target,known,model['uv_boundary_pieces'],counters)
            else:
                result['new_local_UV_channel_probes']=[]
            probes.append(result)
        need(len(probes)<=12,'registered finite selected-root probe limit exceeded')
        report['new_diagnostic_local_plane_probes']=probes
        report.update(completed=True, actual_V9_verifier_owned_failure=controller['failure'],
                      actual_V9_scientific_worker_reports_completed=True,
                      source_input_identities=before,actual_full_original_D=frame['original_remaining_displacement_box_exact'],
                      fixed_selected_root_node=0, new_full_material_searches=0,
                      all_inputs_unchanged=all(same(ident(v['path']),before[k]) for k,v in inputs.items()))
        need(report['all_inputs_unchanged'],'original input changed during bounded diagnostic')
    except Exception as exc:
        report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0)
        report.update(counters=dict(counters),elapsed_seconds=time.monotonic()-started,
                      peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                      finished_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=60,address_space_bytes=536870912)
        p=args.output/'R7E_V9_SAVED_PREFIX_PLANE_PREIMAGE_DIAGNOSIS_V1.json'
        p.write_text(json.dumps(report,indent=2)+'\n');need(p.stat().st_size<=8388608,'registered finite diagnostic output cap exceeded')
    print(json.dumps({'completed':report['completed'],'report':ident(p),'seconds':report['elapsed_seconds'],
                      'RSS':report['peak_RSS_bytes'],'failure':report.get('failure')}))
    return 0 if report['completed'] else 2


if __name__=='__main__':raise SystemExit(main())
