"""Independent rational reconstruction of the conditional R13 trim proof.

Imports no producer, completion-model, projection, native, or square-root
helper. Winding uses a vertical ray with rational intersection coordinates.
The original 169-box R12 ledger and every face/edge/join remain mandatory.
"""
from fractions import Fraction as F
from pathlib import Path
import copy
import gzip
import hashlib
import itertools
import json
import math
import time

HERE=Path(__file__).resolve().parent
SRC=HERE.parent/'r13_envelope_work'
OLD=HERE.parent/'panel_fill_work/exterior-refinement-attempt1'
NORMALS=((1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,-1,0))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rz(p):
    with gzip.open(p,'rt') as f:return json.load(f)
def fv(v):return tuple(F(x) for x in v)
def dot(x,y):return sum((a*b for a,b in zip(x,y)),F(0))
def dist2(x,y):return sum(((a-b)**2 for a,b in zip(x,y)),F(0))
def rb(v):return tuple(fv(p) for p in v)
def fmt(b):return [[str(x) for x in p] for p in b]
def hull(points):return tuple((min(p[i] for p in points),max(p[i] for p in points)) for i in range(2))
def boxhull(bs):return tuple((min(b[i][0] for b in bs),max(b[i][1] for b in bs)) for i in range(2))
def expand(b,t):return tuple((lo-t,hi+t) for lo,hi in b)
def encloses(b,c):return all(lo<=a<=z<=hi for (lo,hi),(a,z) in zip(b,c))
def corners(b):return itertools.product(*(p for p in b))
def separated(b,q):return any(hi<a or z<lo for (lo,hi),(a,z) in zip(b,q))

def complete_line(edge,which):
    r=edge[which];assert r['type']=='LINE'
    o=fv(r['origin_exact']);d=fv(r['direction_exact']);ts=fv(r['complete_parameter_interval'])
    assert fv(r['origin'])==o and fv(r['direction'])==d and ts[0]<=ts[1]
    assert edge['orientation'].endswith(('TopAbs_FORWARD','TopAbs_REVERSED'))
    if edge['orientation'].endswith('TopAbs_REVERSED'):ts=ts[::-1]
    return [tuple(x+t*y for x,y in zip(o,d)) for t in ts]

def reconstruct(raw,cert):
    assert raw['face_index']==cert['face_index'] and raw['plane_recipe']==cert['plane_recipe']
    assert raw['native_face_orientation']==cert['native_face_orientation']
    assert len(raw['wires'])==len(cert['wires'])==raw['wire_count']==2
    assert sorted(e['face_occurrence_index'] for w in raw['wires'] for e in w['edges'])==list(range(8))
    assert sum(w['native_is_outer_wire'] for w in raw['wires'])==1
    p=raw['plane_recipe'];origin,x,y=map(fv,(p['origin'],p['x_direction'],p['y_direction']))
    assert dot(x,x)==dot(y,y)==1 and dot(x,y)==0 and x[1]==y[1]==0
    assert all(v in (-1,0,1) for v in (*x,*y))
    project=lambda v:(dot(tuple(a-b for a,b in zip(v,origin)),x),dot(tuple(a-b for a,b in zip(v,origin)),y))
    lift=lambda uv:tuple(origin[i]+uv[0]*x[i]+uv[1]*y[i] for i in range(3))
    tol=F(raw['face_tolerance_exact']);assert tol>=0 and tol==F(cert['face_tolerance_exact'])
    rebuilt={'origin':origin,'axes':(x,y),'face_tolerance':tol,'wires':[]};slacks=[]
    for w,cw in zip(raw['wires'],cert['wires']):
        assert len(w['edges'])==len(w['joins'])==len(cw['edges'])==len(cw['joins'])==4
        assert w['wire_index']==cw['wire_index'] and w['native_is_outer_wire']==cw['native_is_outer_wire']
        assert w['orientation']==cw['native_wire_orientation']
        P=[];C=[];VB=[]
        for i,(e,ce) in enumerate(zip(w['edges'],cw['edges'])):
            assert ce['edge_index']==i and ce['orientation']==e['orientation'] and ce['face_occurrence_index']==e['face_occurrence_index']
            assert e['same_parameter_flag'] and e['same_range_flag'] and not e['degenerated_flag']
            assert e['pcurve']['complete_parameter_interval']==e['curve3d']['complete_parameter_interval']
            pc=complete_line(e,'pcurve');c3=complete_line(e,'curve3d');uv3=[project(v) for v in c3]
            assert [list(map(str,p)) for p in pc]==ce['exact_pcurve_endpoints']
            assert [list(map(str,p)) for p in uv3]==ce['projected_complete_3d_line_endpoints']
            et=F(e['edge_tolerance_exact']);assert et>=tol
            ds=[dist2(lift(u),v) for u,v in zip(pc,c3)];assert max(ds)<=et*et
            assert F(ce['consistency']['complete_affine_same_parameter_distance_squared_max_exact'])==max(ds)
            assert F(ce['consistency']['recorded_edge_tolerance_squared_exact'])==et*et
            assert len(e['oriented_vertices'])==2;vboxes=[]
            for j,v in enumerate(e['oriented_vertices']):
                point=fv(v['point']);vt=F(v['tolerance_exact']);assert vt>=et
                dpc=dist2(lift(pc[j]),point);d3=dist2(c3[j],point);assert max(dpc,d3)<=vt*vt
                uv=project(point);vb=tuple((a-vt,a+vt) for a in uv);vboxes.append(vb);slacks.append(vt*vt-max(dpc,d3))
                stored=ce['consistency']['oriented_vertex_checks'][j]
                assert stored['vertex_point']==v['point'] and F(stored['vertex_tolerance_exact'])==vt
                assert F(stored['pcurve_lift_distance_squared_exact'])==dpc and F(stored['curve3d_distance_squared_exact'])==d3
                assert rb(stored['vertex_tolerance_projection_box_exact'])==vb
            P.append(pc);C.append(uv3);VB.append(vboxes)
        joins=[]
        for i,(j,cj) in enumerate(zip(w['joins'],cw['joins'])):
            nxt=(i+1)%4
            assert j['after_edge']==cj['after_edge']==i and j['to_edge']==cj['to_edge']==nxt and j['same_native_vertex_identity']
            assert w['edges'][i]['oriented_vertices'][1]==w['edges'][nxt]['oriented_vertices'][0]
            target=boxhull([hull([P[i][1],P[nxt][0],C[i][1],C[nxt][0]]),VB[i][1],VB[nxt][0]])
            assert rb(cj['complete_join_rectangle_exact'])==target,'join rectangle must enclose the full recorded vertex sphere projection'
            assert fv(cj['original_exact_pcurve_gap'])==tuple(a-b for a,b in zip(P[nxt][0],P[i][1]))
            joins.append(target)
        tubes=[]
        for i,(e,ce) in enumerate(zip(w['edges'],cw['edges'])):
            et=F(e['edge_tolerance_exact']);pad=max(et,tol)
            target=boxhull([expand(hull(P[i]+C[i]),pad),joins[(i-1)%4],joins[i]])
            assert F(ce['full_trace_expansion_exact'])==pad and rb(ce['whole_edge_corridor_exact'])==target
            assert encloses(target,joins[(i-1)%4]) and encloses(target,joins[i]);tubes.append(target)
        polygon=[point for segment in P for point in segment]
        assert [list(map(str,p)) for p in polygon]==cw['reference_loop_exact']
        area=sum((u[0]*v[1]-v[0]*u[1] for u,v in zip(polygon,polygon[1:]+polygon[:1])),F(0))
        assert area==F(cw['reference_signed_twice_area_exact']) and area!=0
        rebuilt['wires'].append({'polygon':polygon,'corridors':tubes,'joins':joins,'wire_index':w['wire_index'],'outer':w['native_is_outer_wire'],'twice_area':area})
    assert min(slacks)==F(cert['minimum_vertex_tolerance_squared_slack_exact'])
    assert cert['native_semantics_assumed_proved'] is False
    return rebuilt

def vertical_ray_winding(poly,point):
    # A ray towards +V: leftward crossings count positively.
    u,v=point;w=0
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if a[0]==b[0]:continue
        if min(a[0],b[0])<=u<max(a[0],b[0]):
            crossing=a[1]+(u-a[0])*(b[1]-a[1])/(b[0]-a[0])
            if crossing>v:w+=1 if b[0]<a[0] else -1
    return w

def check_trim_query(tube,model,witness=None):
    uvpoints=[tuple(dot(tuple(p[i]-model['origin'][i] for i in range(3)),n) for n in model['axes']) for p in corners(tube)]
    query=hull(uvpoints);expanded=expand(query,model['face_tolerance']);center=tuple((a+b)/2 for a,b in expanded)
    values=[]
    if witness is not None:
        assert rb(witness['query_UV_exact'])==query and rb(witness['face_tolerance_expanded_query_UV_exact'])==expanded
        assert fv(witness['algebraic_reference_point_exact'])==center
        assert witness['complete_connected_query_certified'] and witness['all_admissible_corridor_completions_certified']
        assert witness['native_filled_domain_membership_proved'] is False
        assert len(witness['wires'])==2
    for i,wire in enumerate(model['wires']):
        assert all(separated(b,expanded) for b in wire['corridors']+wire['joins']),'query meets admissible complete path corridor'
        w=vertical_ray_winding(wire['polygon'],center);assert abs(w)==1;values.append(w)
        # Same result at all query corners checks arithmetic consistency. The
        # whole-query implication is connectedness and boundary exclusion.
        assert all(vertical_ray_winding(wire['polygon'],p)==w for p in corners(expanded))
        if witness is not None:
            cw=witness['wires'][i];assert cw['wire_index']==wire['wire_index'] and cw['reference_winding']==w
            assert cw['native_is_outer_wire']==wire['outer'] and len(cw['all_complete_edge_corridors_strictly_outside_query'])==4
            for j,r in enumerate(cw['all_complete_edge_corridors_strictly_outside_query']):
                assert r['edge_index']==j
                k=r['axis'];lo,hi=wire['corridors'][j][k];a,b=expanded[k]
                assert max(lo-b,a-hi)==F(r['strict_gap_exact'])>0
    assert sum(values)==0,'oriented inner and outer windings must cancel'
    if witness is not None:assert witness['total_winding']==0
    return values

def check_ledger(prior,ledger,models,projections):
    assert ledger['all_original_positive_boxes_accounted']
    for k in ('actual_native_T_membership_proved','actual_native_B0_membership_proved','uniform_compiled_error_proved','continuous_G2'):
        assert ledger[k] is False,'native qualification cannot be promoted by this conditional proof'
    old=prior['original_positive_boxes'];new=ledger['original_positive_boxes'];assert len(old)==len(new),'missing original positive box'
    sums=[F(0),F(0),F(0)];counts={};query_count=0
    ymax=max(F(p[1][1]) for p in projections)
    for before,now in zip(old,new):
        assert before['locator']==now['locator'] and before['box_exact']==now['box_exact']
        B=rb(before['box_exact']);vol=math.prod(b-a for a,b in B);assert vol>0
        assert vol==F(before['positive_full_box_volume_exact'])==F(now['original_positive_full_box_volume_exact'])
        upper0=F(before['upper_exact']);assert upper0==F(now['R12_upper_exact']) and upper0 in (0,vol)
        kind=now['kind'];counts[kind]=counts.get(kind,0)+1
        if kind=='inherited_KEY_exterior':
            assert upper0==0 and now['original_certificate']==before;upper=F(0)
        elif kind=='retained_positive_full_box':upper=vol;assert upper0==vol
        else:
            assert kind=='new_panel_completed_trim_exterior' and upper0==vol
            tube=rb(now['open_tube_exact']);assert tube==(B[0],(B[1][0],ymax+1),B[2])
            assert F(now['outside_global_Y_support_exact'])==ymax
            assert all(a<=c<d<=b for (a,b),(c,d) in zip(tube,B))
            outside=(ymax+ymax+1)/2;assert tube[1][0]<outside<tube[1][1] and outside>ymax
            ws=now['all_298_complete_face_witnesses'];assert len(ws)==298 and sorted(x['face_index'] for x in ws)==list(range(298)),'incomplete panel face census'
            trim_faces=[]
            for w in ws:
                fi=w['face_index']
                if w['method']=='original_complete_support':
                    n=NORMALS[w['normal']];lo=sum(min(a*c,b*c) for (a,b),c in zip(tube,n));hi=sum(max(a*c,b*c) for (a,b),c in zip(tube,n));a,b=map(F,projections[fi][w['normal']])
                    assert (w['relation']=='at_or_below_open_tube' and b<=lo) or (w['relation']=='at_or_above_open_tube' and a>=hi)
                else:
                    assert fi in models and w['method']=='all_completion_corridors_disjoint_and_opposite_complete_wire_windings'
                    check_trim_query(tube,models[fi],w);query_count+=1;trim_faces.append(fi)
            assert now['new_trim_faces']==trim_faces;upper=F(0)
        assert F(now['upper_under_B0_and_T_exact'])==upper,'understated or unsupported contribution'
        sums=[a+b for a,b in zip(sums,(vol,upper0,upper))]
    assert counts==ledger['counts']
    assert sums[0]==F(prior['original_full_bound_exact'])==F(ledger['original_coarse_sum_exact'])
    assert sums[1]==F(prior['remaining_full_bound_exact'])==F(ledger['unchanged_R12_B0_only_sum_exact'])
    assert sums[2]==F(ledger['new_B0_and_T_sum_exact'])
    assert ledger['new_B0_and_T_threshold_passes']==(sums[2]<=F(1e-7))
    return {'positive_boxes':len(old),'counts':counts,'trim_query_face_certificates':query_count,
            'unchanged_R12_B0_only_exact':str(sums[1]),'conditional_B0_and_T_exact':str(sums[2]),
            'unchanged_R12_B0_only_mm3':float(sums[1]),'conditional_B0_and_T_mm3':float(sums[2])}

def rejected(label,call):
    try:call()
    except (AssertionError,ValueError,IndexError,KeyError) as e:return {'control':label,'rejected':True,'reason':str(e)}
    raise AssertionError('negative control escaped: '+label)

def main():
    started=time.monotonic();native_path=SRC/'native-attempt1/report.json';cert_path=SRC/'producer-attempt1/complete_trim_corridors.json'
    native=json.loads(native_path.read_text());certificate=json.loads(cert_path.read_text())
    assert native['completed'] and native['complete_ordered_edge_count']==48 and native['wire_count']==12
    assert native['input']['sha256']==sha(HERE/'inputs/A_BACK_PANEL.brep')
    assert native['native_filled_domain_equals_completion_model_proved'] is False and native['continuous_G2'] is False
    assert certificate['actual_native_trim_model_membership_proved'] is False
    raws={f['face_index']:f for f in native['faces']};certs={f['face_index']:f for f in certificate['faces']}
    assert sorted(raws)==sorted(certs)==[104,109,110,115,118,121]
    models={i:reconstruct(raws[i],certs[i]) for i in raws}
    projection_path=SRC/'inputs/R12_complete_projections.json.gz';projections=rz(projection_path)['bodies']['A_BACK_PANEL'];assert len(projections)==298
    assert sha(projection_path)==sha(OLD/'complete_face_projections.json.gz')
    report={'schema':'razr-r13-independent-completed-trim-corridor-review-v1','completed':False,'source_sha256':sha(__file__),
            'inputs':{'native_report':{'path':str(native_path),'sha256':sha(native_path)},'complete_corridors':{'path':str(cert_path),'sha256':sha(cert_path)},
                      'complete_R12_projections':{'path':str(projection_path),'sha256':sha(projection_path)}},
            'producer_or_model_helpers_imported':False,'sqrt_helper_imported':False,
            'complete_native_faces_reconstructed':6,'complete_ordered_wires':12,'complete_affine_edges':48,'complete_joins':48,'oriented_vertex_endpoint_checks':96,
            'pairs':[],'negative_controls':[]}
    priors={};ledgers={}
    for key in ('L_KEY','R_KEY'):
        prior=rz(OLD/(key+'-exterior-ledger.json.gz'));p=SRC/'producer-attempt1'/(key+'-completed-trim-ledger.json.gz');ledger=rz(p)
        priors[key]=prior;ledgers[key]=ledger
        report['pairs'].append({'key':key,'ledger_sha256':sha(p),**check_ledger(prior,ledger,models,projections)})
    raw=raws[104];cert=certs[104]
    bad=copy.deepcopy(cert);bad['wires'][0]['edges'].pop();report['negative_controls'].append(rejected('omit_complete_edge',lambda:reconstruct(raw,bad)))
    bad=copy.deepcopy(cert);bad['wires'][0]['joins'].pop();report['negative_controls'].append(rejected('omit_vertex_join',lambda:reconstruct(raw,bad)))
    bad=copy.deepcopy(cert);box=rb(bad['wires'][0]['joins'][0]['complete_join_rectangle_exact']);bad['wires'][0]['joins'][0]['complete_join_rectangle_exact']=fmt(tuple(((a+b)/2,(a+b)/2) for a,b in box));report['negative_controls'].append(rejected('shrink_join_below_full_vertex_tolerance_sphere_projection',lambda:reconstruct(raw,bad)))
    first_new=next(x for x in ledgers['L_KEY']['original_positive_boxes'] if x['kind']=='new_panel_completed_trim_exterior')
    fw=next(x for x in first_new['all_298_complete_face_witnesses'] if x['method']!='original_complete_support');model=copy.deepcopy(models[fw['face_index']]);model['wires'][1]['polygon'].reverse()
    report['negative_controls'].append(rejected('reverse_only_inner_oriented_reference_loop',lambda:check_trim_query(rb(first_new['open_tube_exact']),model)))
    bad=copy.deepcopy(ledgers['L_KEY']);next(x for x in bad['original_positive_boxes'] if x['kind']=='new_panel_completed_trim_exterior')['all_298_complete_face_witnesses'].pop();report['negative_controls'].append(rejected('omit_one_complete_panel_face',lambda:check_ledger(priors['L_KEY'],bad,models,projections)))
    bad=copy.deepcopy(ledgers['L_KEY']);bad['original_positive_boxes'].pop();report['negative_controls'].append(rejected('omit_original_positive_cell',lambda:check_ledger(priors['L_KEY'],bad,models,projections)))
    bad=copy.deepcopy(ledgers['L_KEY']);row=next(x for x in bad['original_positive_boxes'] if F(x['upper_under_B0_and_T_exact'])>F(1,2**80));row['upper_under_B0_and_T_exact']=str(F(row['upper_under_B0_and_T_exact'])-F(1,2**80));assert F(row['upper_under_B0_and_T_exact'])>0
    report['negative_controls'].append(rejected('understate_still_positive_residual_by_2^-80',lambda:check_ledger(priors['L_KEY'],bad,models,projections)))
    bad=copy.deepcopy(ledgers['L_KEY']);bad['actual_native_T_membership_proved']=True;report['negative_controls'].append(rejected('promote_conditional_model_to_native_identity',lambda:check_ledger(priors['L_KEY'],bad,models,projections)))
    report.update(completed=True,seconds=time.monotonic()-started,scope={
        'arithmetic_and_query_wide_conditional_implication_verified':True,
        'arbitrary_continuous_paths_in_convex_corridors_have_reference_winding':True,
        'requires_R12_complete_boundary_premise_B0_and_new_oriented_fill_premise_T':True,
        'old_R12_bound_replaced':False,'native_material_belongs_to_B0_and_T_proved':False,
        'existence_of_full_global_native_material_realizing_B0_and_T_proved':False,
        'native_tolerance_is_compiled_error_bound':False,'uniform_compiled_error_proved':False,
        'actual_collision_proved':False,'full_15D_G2':False,'physical_allowed_domain':False,'G3':False,'G4':False,'G5':False})
    output=HERE/'R13_TRIM_INDEPENDENT_REVIEW.json';assert not output.exists();output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'completed':True,'positive_boxes':sum(x['positive_boxes'] for x in report['pairs']),'negative_controls':len(report['negative_controls']),'seconds':report['seconds'],'sha256':sha(output)}))

if __name__=='__main__':main()
