"""Independent raw pcurve interval and exact ordered-wire gap arithmetic."""
from pathlib import Path
from fractions import Fraction as F
import ast,math,json,hashlib,datetime,collections
ROOT=Path(__file__).resolve().parent
NATIVE=ROOT.parent/'panel_fill_work/native-boundaries-attempt4/report.json'
TRIM=ROOT.parent/'panel_fill_work/trim-frontier-attempt1/report.json'
FORMULA=ROOT/'certify_key_bent_channels.py'
SQRT=ROOT.parent/'geometry_work/complete_surface_support_v3.py'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
env={'F':F,'math':math}
nodes=[n for n in ast.parse(SQRT.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='sqrt_upper']
nodes += [n for n in ast.parse(FORMULA.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ('dot','affine_range','curve_scalar')]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'independent_curve_bounds','exec'),env)
def range2d(curve):
    if curve['type']!='GeomAbs_BSplineCurve':
        return [env['curve_scalar'](curve,n) for n in [(1,0),(0,1)]]
    assert curve['degree']==1 and all(F(w)==1 for w in curve['weights'])
    knots=list(map(F,curve['knots']));poles=[list(map(F,p)) for p in curve['poles']]
    assert len(knots)==len(poles) and all(a<b for a,b in zip(knots,knots[1:]))
    assert curve['multiplicities']==[2]+[1]*(len(knots)-2)+[2]
    a,b=map(F,curve['complete_trim_parameter_interval']);assert a<=b
    result=[]
    for dim in range(2):
        values=[]
        for left,right in zip([a]+[k for k in knots if a<k<b],[k for k in knots if a<k<b]+[b]):
            mid=(left+right)/2
            if mid<knots[0]:i=0
            elif mid>knots[-1]:i=len(knots)-2
            else:i=next(i for i in range(len(knots)-1) if knots[i]<=mid<=knots[i+1])
            slope=(poles[i+1][dim]-poles[i][dim])/(knots[i+1]-knots[i])
            values += [poles[i][dim]+slope*(t-knots[i]) for t in (left,right)]
        result.append((min(values),max(values)))
    return result

native=json.loads(NATIVE.read_text());assert native['completed']
census={};pcurve_total=0
for name,body in native['bodies'].items():
    count=collections.Counter()
    for face in body['faces']:
        intervals=[tuple(map(F,p)) for p in face['reported_native_UV']]
        for edge in face['edges']:
            c=edge['pcurve'];r=range2d(c)
            assert r==[tuple(map(F,p)) for p in c['exact_range']]
            intervals=[(min(a,x),max(b,y)) for (a,b),(x,y) in zip(intervals,r)]
            count[c['type']]+=1;pcurve_total+=1
        assert intervals==[tuple(map(F,p)) for p in face['complete_pcurve_UV']]
    assert dict(count)==body['complete_pcurve_occurrence_types']
    census[name]=dict(count)
trim=json.loads(TRIM.read_text());assert trim['completed']
wire_rows=[];edge_count=0;nonzero=0;maximum=F(0)
for face in trim['faces']:
    assert face['wire_count']==len(face['wires'])==2
    assert sum(w['native_is_outer_wire'] for w in face['wires'])==1
    for wire in face['wires']:
        edges=wire['edges'];assert len(edges)==4 and wire['native_closed_flag']
        endpoints=[]
        for e in edges:
            assert e['type']=='LINE';origin=list(map(F,e['origin_exact']));direction=list(map(F,e['direction_exact']));a,b=map(F,e['complete_trim_interval'])
            first=[o+d*a for o,d in zip(origin,direction)];last=[o+d*b for o,d in zip(origin,direction)]
            if e['orientation'].endswith('TopAbs_REVERSED'):first,last=last,first
            else:assert e['orientation'].endswith('TopAbs_FORWARD')
            assert first==list(map(F,e['oriented_start_UV'])) and last==list(map(F,e['oriented_end_UV']))
            endpoints.append((first,last));edge_count+=1
        gaps=[]
        for i,(first,last) in enumerate(endpoints):
            delta=[a-b for a,b in zip(endpoints[(i+1)%len(endpoints)][0],last)]
            recorded=wire['exact_endpoint_gaps'][i]
            assert delta==list(map(F,recorded['delta_UV_exact']))
            zero=all(x==0 for x in delta);assert zero==recorded['exactly_zero']
            nonzero+=not zero;maximum=max(maximum,*map(abs,delta));gaps.append(list(map(str,delta)))
        closed=all(all(F(v)==0 for v in gap) for gap in gaps)
        assert closed==wire['exactly_closed'] and not closed
        wire_rows.append({'face':face['face_index'],'wire':wire['wire_index'],'native_closed_flag':True,
                          'exact_closure':False,'independently_recomputed_UV_join_gaps':gaps})
assert edge_count==trim['complete_ordered_edge_occurrences']==48
assert len(wire_rows)==12 and nonzero==44 and not trim['exact_trim_hole_refinement_admitted']
result={'schema':'razr-r12-complete-pcurve-and-ordered-trim-independent-arithmetic-review-v1',
    'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'completed':True,
    'source_sha256':sha(__file__),'native_boundary_report_sha256':sha(NATIVE),'trim_report_sha256':sha(TRIM),
    'projection_formula_source_sha256':sha(FORMULA),'sqrt_source_sha256':sha(SQRT),
    'all_pcurve_intervals_and_complete_UV_enclosures_recomputed':True,'pcurve_occurrences':pcurve_total,
    'pcurve_census_by_body':census,'wire_census':wire_rows,'ordered_edges_checked':edge_count,
    'nonzero_exact_joins':nonzero,'maximum_exact_UV_join_gap':str(maximum),'maximum_gap_approx':float(maximum),
    'scope':{'native_closed_flags_do_not_prove_exact_serialized_loop_closure':True,
             'nonzero_serialized_gaps_do_not_prove_physical_material_holes':True,
             'no_snapping_or_unregistered_native_trim_filling_premise_used':True,
             'prior_positive_residual_not_removed':True,'exact_trim_hole_refinement_admitted':False,
             'native_material_identity_and_uniform_compiled_error_bridge_fully_proved':False}}
(ROOT/'PCURVE_AND_TRIM_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'completed':True,'pcurve_occurrences':pcurve_total,'wires':len(wire_rows),'nonzero_joins':nonzero,'max_gap_approx':float(maximum)}))
