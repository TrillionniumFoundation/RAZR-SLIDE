"""Source-bound negative controls for the certified KEY exterior channels."""
from pathlib import Path
from fractions import Fraction as F
import ast,math,json,hashlib,datetime
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'certify_key_bent_channels.py'
SQRT=ROOT.parent/'geometry_work/complete_surface_support_v3.py'
INPUT=ROOT.parent/'panel_fill_work/native-boundaries-attempt4/report.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
env={'F':F,'math':math}
nodes=[n for n in ast.parse(SQRT.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='sqrt_upper']
nodes += [n for n in ast.parse(SOURCE.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ('dot','affine_range','curve_scalar','face_scalar')]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'frozen_channel_formulas','exec'),env)
native=json.loads(INPUT.read_text());rows=[]
for side,sign in [('L',-1),('R',1)]:
    for label,xr,yr in [('cross_actual_arm',(11.3,11.7),(52.,64.)),
                       ('cross_actual_tab_exit',(11.4,32.),(51.5,53.)),
                       ('cross_diagonal_yoke',(11.4,11.7),(52.,72.))]:
        tube=[tuple(map(F,xr)),tuple(map(F,yr)),(F(1.2),F(1.6))]
        if sign<0:tube[0]=(-tube[0][1],-tube[0][0])
        ell=[sign,1,0]
        tlo=sum(min(F(e)*a,F(e)*b) for e,(a,b) in zip(ell,tube));thi=sum(max(F(e)*a,F(e)*b) for e,(a,b) in zip(ell,tube))
        rejected=[]
        for face in native['bodies'][side+'_KEY']['faces']:
            box=[tuple(map(F,p)) for p in face['complete_swept_support']]
            gap=max(max(a-d,c-b) for (a,b),(c,d) in zip(box,tube))
            corr=env['face_scalar'](face,ell)
            if gap<0 and corr[0]<thi and corr[1]>tlo:
                rejected.append({'face_index':face['face_index'],'kind':face['kind'],'correlated_interval':list(map(str,corr))})
        assert rejected,(side,label,'negative channel incorrectly accepted')
        rows.append({'side':side,'control':label,'open_box_exact':[[str(a),str(b)] for a,b in tube],
                     'boundary_exclusion_rejected':True,'unresolved_boundary_faces':rejected,
                     'unresolved_bound_does_not_itself_prove_collision':True})
result={'schema':'razr-r12-KEY-channel-negative-controls-v1','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_sha256':sha(__file__),'channel_formula_sha256':sha(SOURCE),'sqrt_source_sha256':sha(SQRT),
    'boundary_source_sha256':sha(INPUT),'all_six_controls_rejected':True,'controls':rows,
    'native_material_identity_or_uniform_compiled_error_proved':False}
(ROOT/'KEY_CHANNEL_NEGATIVE_CONTROLS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps([(r['side'],r['control'],len(r['unresolved_boundary_faces'])) for r in rows]))
