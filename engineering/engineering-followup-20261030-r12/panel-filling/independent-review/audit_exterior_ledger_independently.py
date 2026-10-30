"""Independent raw-parameter projection and complete exterior-ledger audit."""
from pathlib import Path
from fractions import Fraction as F
import ast,math,json,gzip,hashlib,datetime,time,copy
ROOT=Path(__file__).resolve().parent
PANEL=ROOT.parent/'panel_fill_work'
NATIVE=PANEL/'native-boundaries-attempt4/report.json'
REFINE=PANEL/'exterior-refinement-attempt1'
SOURCE=ROOT/'certify_key_bent_channels.py'
SQRT=ROOT.parent/'geometry_work/complete_surface_support_v3.py'
NORMALS=[(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,-1,0)]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def readz(p):
    with gzip.open(p,'rt') as f:return json.load(f)
env={'F':F,'math':math}
nodes=[n for n in ast.parse(SQRT.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='sqrt_upper']
nodes += [n for n in ast.parse(SOURCE.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ('dot','affine_range','curve_scalar','face_scalar')]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'independent_full_boundary_projection','exec'),env)
started=time.monotonic()
native=json.loads(NATIVE.read_text());stored=readz(REFINE/'complete_face_projections.json.gz')
assert native['completed'] and stored['normals']==[list(v) for v in NORMALS]
projections={}
for name,body in native['bodies'].items():
    values=[]
    for i,face in enumerate(body['faces']):
        assert face['face_index']==i
        values.append([env['face_scalar'](face,n) for n in NORMALS])
    assert values==[[tuple(map(F,p)) for p in face] for face in stored['bodies'][name]]
    projections[name]=values

def box(b):return [tuple(map(F,p)) for p in b]
def volume(b):
    assert all(a<c for a,c in b)
    return math.prod(c-a for a,c in b)
def projected(b,n):
    return (sum(min(F(e)*a,F(e)*c) for e,(a,c) in zip(n,b)),
            sum(max(F(e)*a,F(e)*c) for e,(a,c) in zip(n,b)))
def channel(proof,body):
    b=box(proof['open_channel_bounds_exact']);volume(b)
    witnesses=proof['all_face_separation_witnesses']
    assert len(witnesses)==len(projections[body]),'omitted boundary face'
    assert sorted(w['face'] for w in witnesses)==list(range(len(projections[body]))),'duplicate/missing face identity'
    for w in witnesses:
        k=w['normal'];assert k in range(5)
        lo,hi=projected(b,NORMALS[k]);a,c=projections[body][w['face']][k]
        if w['relation']=='boundary_at_or_below_open_channel':assert c<=lo,'unsupported lower separation'
        elif w['relation']=='boundary_at_or_above_open_channel':assert a>=hi,'unsupported upper separation'
        else:raise AssertionError('unknown separation relation')
    return b
def ledger_audit(data,coarse):
    key=data['key'];g=[list(map(F,p)) for p in coarse['grid_exact']]
    expected={}
    for i,piece in enumerate(coarse['x_pieces']):
        a,c=piece['x_grid_interval']
        for j,(row,runs) in enumerate(piece['occupied_y_rows']):
            for k,(u,v) in enumerate(runs):expected[(i,j,k)]=[(g[0][a],g[0][c]),(g[1][row],g[1][row+1]),(g[2][u],g[2][v])]
    rows=data['original_positive_boxes'];assert len(rows)==len(expected),'omitted positive contribution'
    assert len({tuple(r['locator']) for r in rows})==len(rows),'duplicate positive contribution'
    total=F(0);remaining=F(0);excluded=0
    for r in rows:
        b=box(r['box_exact']);assert b==expected[tuple(r['locator'])]
        v=volume(b);assert v==F(r['positive_full_box_volume_exact']);total+=v
        if r['kind']=='retained_positive_full_box':
            assert F(r['upper_exact'])==v,'understated unresolved positive volume'
        else:
            assert F(r['upper_exact'])==0
            target='A_BACK_PANEL' if r['kind']=='panel_positive_Y_channel' else key
            assert r['kind'] in ('panel_positive_Y_channel','KEY_bent_negative_Y_then_outside_X')
            tubes=[channel(p,target) for p in r['channels']]
            first=tubes[0]
            assert all(a<=u<v<=c for (a,c),(u,v) in zip(first,b)),'query not contained in first open channel'
            for a,c in zip(tubes,tubes[1:]):
                assert all(min(ah,bh)>max(al,bl) for (al,ah),(bl,bh) in zip(a,c)),'disconnected path'
            axis=r['outside_global_support_axis'];last=tubes[-1]
            low=min(p[axis][0] for p in projections[target]);high=max(p[axis][1] for p in projections[target])
            assert last[axis][0]<low or last[axis][1]>high,'missing strict exterior endpoint'
            assert F(r['outside_global_support_end']) in (low,high)
            if target=='A_BACK_PANEL':assert len(tubes)==1 and axis==1
            else:assert len(tubes)==2 and axis==0
            excluded+=1
        remaining+=F(r['upper_exact'])
    assert total==F(coarse['exact_intersection_upper_volume'])==F(data['original_full_bound_exact'])
    assert remaining==F(data['remaining_full_bound_exact'])
    assert (remaining<=F(1e-7))==data['gate_pass_under_complete_represented_boundary_compact_filling_model']
    return {'complete_positive_boxes':len(rows),'excluded_full_boxes':excluded,'exact_original_sum':str(total),
            'exact_remaining_sum':str(remaining),'remaining_approx_mm3':float(remaining)}

records=[];originals={}
for key in ('L_KEY','R_KEY'):
    lp=REFINE/(key+'-exterior-ledger.json.gz');cp=PANEL/'fibre-intersection-attempt1'/(key+'-XYZ_intersection.json.gz')
    d,c=readz(lp),readz(cp);originals[key]=(d,c)
    row=ledger_audit(d,c);row.update(key=key,ledger_sha256=sha(lp),coarse_sha256=sha(cp));records.append(row)

controls=[]
def rejected(label,alter):
    d,c=copy.deepcopy(originals['R_KEY'])
    alter(d)
    try:ledger_audit(d,c)
    except (AssertionError,KeyError,ValueError) as e:
        controls.append({'control':label,'rejected':True,'reason':str(e)});return
    raise AssertionError('negative control passed: '+label)
rejected('omit_one_positive_box',lambda d:d['original_positive_boxes'].pop())
def drop_face(d):
    r=next(r for r in d['original_positive_boxes'] if r['kind']!='retained_positive_full_box')
    r['channels'][0]['all_face_separation_witnesses'].pop()
rejected('omit_one_complete_boundary_face',drop_face)
def duplicate_face(d):
    r=next(r for r in d['original_positive_boxes'] if r['kind']!='retained_positive_full_box')
    w=r['channels'][0]['all_face_separation_witnesses'];w[0]['face']=w[1]['face']
rejected('replace_one_face_by_duplicate',duplicate_face)
def understate(d):
    r=next(r for r in d['original_positive_boxes'] if r['kind']=='retained_positive_full_box')
    r['upper_exact']=str(F(r['upper_exact'])-F(1,2**80))
rejected('understate_unresolved_box_by_2^-80',understate)
def disconnect(d):
    r=next(r for r in d['original_positive_boxes'] if r['kind']=='KEY_bent_negative_Y_then_outside_X')
    r['channels'][1]['open_channel_bounds_exact'][1]=['100','101']
rejected('disconnect_bent_path',disconnect)

result={'schema':'razr-r12-independent-exterior-refinement-audit-v1',
    'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'completed':True,
    'source_sha256':sha(__file__),'projection_formula_source_sha256':sha(SOURCE),'sqrt_source_sha256':sha(SQRT),
    'native_boundary_source_sha256':sha(NATIVE),'stored_projection_sha256':sha(REFINE/'complete_face_projections.json.gz'),
    'all_482_faces_times_5_covectors_recomputed_from_raw_parameters':True,
    'producer_projection_module_imported':False,'producer_refinement_module_imported':False,
    'all_positive_RLE_boxes_accounted':True,'pairs':records,'negative_controls':controls,
    'seconds':time.monotonic()-started,
    'scope':{'source_representation_boundary_exclusion_and_connected_exterior_paths_verified':True,
             'original_1e_minus7_remaining_bound_passes':False,'actual_collision_proved':False,
             'all_actual_native_material_filling_identity_or_uniform_compiled_error_premises_closed':False,
             'whole_15D_G2':False,'G3':False,'G4':False,'G5':False,'manufacturing_go':False}}
(ROOT/'EXTERIOR_LEDGER_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'completed':True,'pairs':records,'negative_controls':len(controls),'seconds':result['seconds']}))
