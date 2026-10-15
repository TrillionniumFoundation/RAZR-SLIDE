from pathlib import Path
import hashlib,json,math,platform
import cadquery as cq
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def whole(s):
 if not s.isValid():raise ValueError('invalid whole payload')
 n=s
 while n.ShapeType()=='Compound':
  ch=list(n)
  if len(ch)!=1:raise ValueError('extra compound payload')
  n=ch[0]
 if n.ShapeType()!='Solid' or len(s.Solids())!=1:raise ValueError('loose or multiple payload')
 v=float(s.Volume())
 if not math.isfinite(v) or v<=0:raise ValueError('nonpositive signed volume')
 return v
inp=ROOT/'recovered_x230/input';out=ROOT/'recovered_x230/output'
manifest=json.loads((inp/'native_input_manifest.json').read_text())
before={name:sha(inp/name) for name in manifest['files']}
assert before==manifest['files']
native=json.loads((out/'native_receipt.json').read_text())
assert native['input_sha256_before']==before==native['input_sha256_after']
assert native['all_actual_native_exit_codes_zero'] and len(native['runs'])==2
d=json.loads((out/'actual/actual_obstacle_and_J_report.json').read_text())
rows=[]
for r in d['finite_sweep_rows']:
 if 'STEP' not in r:continue
 p=out/'actual/cad'/r['STEP']['file'];assert sha(p)==r['STEP']['sha256']
 wp=cq.importers.importStep(str(p));assert len(wp.vals())==1
 v=whole(wp.val());reference=r['full_reimport_payload_guard']['complete_payload_positive_volume_mm3']
 assert abs(v-reference)<1e-6
 rows.append({'file':str(p.relative_to(ROOT)),'sha256':sha(p),'whole_positive_solid_count':1,'volume_mm3':v,'reference_difference_mm3':v-reference})
assert len(rows)==12
summary={'host':platform.node(),'CadQuery':cq.__version__,'native_X230_input_file_count':len(before),'restored_input_sha256_exact':True,'recovered_native_runs':native['runs'],'independent_STEP_full_payload_rows':rows,'STEP_count':len(rows),'centerline_rejected_rows':sum(any(p['inside_or_on_face_count'] for p in r['all_23_obstacles'].values()) for r in d['rows']),'WIDTH_Y_nonpositive_conditional_J_rows':sum(r['local_section_regularity']['WIDTH_Y']['minimum_conditional_section_J']<=0 for r in d['rows']),'valid_single_sweep_with_boolean_exception_count':sum(r['actual_finite_sweep_valid'] and r.get('actual_exception') is not None for r in d['finite_sweep_rows']),'source_bytes_unchanged_after':before=={name:sha(inp/name) for name in before},'candidate_route_accepted':False,'manufacturing_go':False}
assert summary['source_bytes_unchanged_after']
(ROOT/'recovered_artifact_verification.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['independent_STEP_full_payload_rows','recovered_native_runs']}))
