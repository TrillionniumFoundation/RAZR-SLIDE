"""Exact correlated-boundary checks for the current KEY's exterior channel."""
from pathlib import Path
from fractions import Fraction as F
import math,json,hashlib,datetime,ast
ROOT=Path(__file__).resolve().parent
INPUT=ROOT.parent/'panel_fill_work/native-boundaries-attempt4/report.json'
HELPER=ROOT.parent/'geometry_work/complete_surface_support_v3.py'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
node=next(n for n in ast.parse(HELPER.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='sqrt_upper')
scope={'F':F,'math':math};exec(compile(ast.Module(body=[node],type_ignores=[]),'exact_sqrt_from_frozen_source','exec'),scope)
sqrt_upper=scope['sqrt_upper']

def dot(a,b):return sum((F(x)*F(y) for x,y in zip(a,b)),F(0))
def affine_range(c,a,b):
    x,y=sorted((c*a,c*b));return x,y

def curve_scalar(c,ell):
    if c['type']=='GeomAbs_Line':
        t0,t1=map(F,c['complete_trim_parameter_interval']);d=dot(ell,c['direction']);origin=dot(ell,c['origin'])
        a,b=affine_range(d,t0,t1);return origin+a,origin+b
    if c['type'] in ('GeomAbs_Circle','GeomAbs_Ellipse'):
        center=dot(ell,c['center']);a=F(c['major'])*dot(ell,c['x_direction']);b=F(c['minor'])*dot(ell,c['y_direction'])
        rad=sqrt_upper(a*a+b*b);return center-rad,center+rad
    raise ValueError('unsupported actual KEY complete curve '+c['type'])

def face_scalar(face,ell):
    recipe=face['recipe'];u,v=[tuple(map(F,p)) for p in face['complete_pcurve_UV']]
    origin=dot(ell,recipe['origin'])
    if face['kind']=='PLANE':
        a,b=affine_range(dot(ell,recipe['x_direction']),*u)
        c,d=affine_range(dot(ell,recipe['y_direction']),*v)
        bounds=[(origin+a+c,origin+b+d)]
    else:
        a,b=affine_range(dot(ell,recipe['axis']),*v)
        radius=F(recipe['radius'])*sqrt_upper(dot(ell,recipe['x_direction'])**2+dot(ell,recipe['y_direction'])**2)
        bounds=[(origin+a-radius,origin+b+radius)]
    bounds += [curve_scalar(e['curve3d'],ell) for e in face['edges']]
    bounds += [(dot(ell,p),dot(ell,p)) for p in face['vertices']]
    q=dot(ell,list(map(F,face['motion_exact'])))
    return min(a for a,b in bounds)+min(F(0),q),max(b for a,b in bounds)+max(F(0),q)

native=json.loads(INPUT.read_text());assert native['completed']
result={'schema':'razr-r12-current-KEY-exact-bent-exterior-channel-v1',
    'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(__file__),
    'raw_boundary_source_sha256':sha(INPUT),'exact_sqrt_source_sha256':sha(HELPER),'sides':{},
    'native_Common_calls':0,'all_actual_native_filling_or_compiled_error_premises_closed':False}
for side,sign in [('L',-1),('R',1)]:
    body=native['bodies'][side+'_KEY'];faces=body['faces'];ell=[sign,1,0]
    tubes={'first_Y_exit':[(F(11.4),F(11.7)),(F(52),F(64)),(F(1.2),F(1.6))],
           'second_X_exit':[(F(11.4),F(32)),(F(52),F(53)),(F(1.2),F(1.6))]}
    if side=='L':
        for tube in tubes.values():tube[0]=(-tube[0][1],-tube[0][0])
    records={}
    for name,tube in tubes.items():
        lo=sum(min(F(e)*a,F(e)*b) for e,(a,b) in zip(ell,tube));hi=sum(max(F(e)*a,F(e)*b) for e,(a,b) in zip(ell,tube))
        rows=[]
        for face in faces:
            box=[tuple(map(F,p)) for p in face['complete_swept_support']]
            gaps=[max(a-d,c-b) for (a,b),(c,d) in zip(box,tube)]
            corr=face_scalar(face,ell)
            if max(gaps)>=0:
                method='axis_support_outside_open_tube';passed=True
            elif corr[0]>=hi or corr[1]<=lo:
                method='complete_correlated_linear_support_outside_open_tube';passed=True
            else:method='unresolved_boundary_box';passed=False
            rows.append({'face_index':face['face_index'],'surface':face['kind'],'passed':passed,'method':method,
                'axis_gaps_mm':list(map(str,gaps)),'complete_correlated_scalar_range':list(map(str,corr)),
                'source_full_trim_occurrences':len(face['edges'])})
        records[name]={'open_box_exact':[[str(a),str(b)] for a,b in tube],
            'linear_function_coefficients':ell,'tube_linear_range':[str(lo),str(hi)],
            'all_complete_boundary_faces_excluded':all(r['passed'] for r in rows),'faces':rows,
            'unresolved_faces':[r['face_index'] for r in rows if not r['passed']]}
    global_x=[min(F(f['complete_swept_support'][0][0]) for f in faces),max(F(f['complete_swept_support'][0][1]) for f in faces)]
    exterior=F(sign*31)
    assert exterior>global_x[1] if sign>0 else exterior<global_x[0]
    result['sides'][side]={'global_complete_boundary_X_interval':list(map(str,global_x)),
        'second_tube_contains_point_outside_global_X_support':True,'outside_X_coordinate':str(exterior),
        'two_open_tubes_intersect_in_positive_volume':True,'tubes':records,
        'conditional_source_material_channel_empty':all(r['all_complete_boundary_faces_excluded'] for r in records.values())}
result['conditional_channel_proof']='The two open boxes form a connected open set with a point outside the compact material global X support. If that connected set is disjoint from the complete boundary of each admitted-q material, it is wholly in the exterior component; no Common zero or mesh samples are used. Open-box boundary strips must be separately retained in any volume bound.'
(ROOT/'KEY_BENT_CHANNEL_CORRELATED_SUPPORT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({s:{n:r['unresolved_faces'] for n,r in v['tubes'].items()} for s,v in result['sides'].items()}))
