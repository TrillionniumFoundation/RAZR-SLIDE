"""Preserve complete concrete control variants and replay their rejection."""
from pathlib import Path
from fractions import Fraction as F
import copy,gzip,hashlib,json
import audit_r13_trim_independently as a

HERE=Path(__file__).resolve().parent;OUT=HERE/'trim-negative-controls';OUT.mkdir(exist_ok=False)
native=json.loads((a.SRC/'native-attempt1/report.json').read_text())
certs=json.loads((a.SRC/'producer-attempt1/complete_trim_corridors.json').read_text())
raws={r['face_index']:r for r in native['faces']};cs={r['face_index']:r for r in certs['faces']}
models={i:a.reconstruct(raws[i],cs[i]) for i in raws}
prior=a.rz(a.OLD/'L_KEY-exterior-ledger.json.gz')
ledger=a.rz(a.SRC/'producer-attempt1/L_KEY-completed-trim-ledger.json.gz')
projections=a.rz(a.SRC/'inputs/R12_complete_projections.json.gz')['bodies']['A_BACK_PANEL']
def enc(v):
    if isinstance(v,F):return str(v)
    if isinstance(v,dict):return {k:enc(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [enc(x) for x in v]
    return v
variants=[]
def keep(label,stage,data,call):
    verdict=a.rejected(label,call);p=OUT/(label+'.json.gz')
    with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write((json.dumps(enc(data),separators=(',',':'))+'\n').encode())
    variants.append({'control':label,'checker_entry_point':stage,'complete_variant_file':str(p.relative_to(HERE)),
                     'bytes':p.stat().st_size,'sha256':a.sha(p),'replay':verdict})
bad=copy.deepcopy(cs[104]);bad['wires'][0]['edges'].pop();keep('omit_complete_edge','reconstruct(raw_face_104,variant)',bad,lambda:a.reconstruct(raws[104],bad))
bad=copy.deepcopy(cs[104]);bad['wires'][0]['joins'].pop();keep('omit_vertex_join','reconstruct(raw_face_104,variant)',bad,lambda:a.reconstruct(raws[104],bad))
bad=copy.deepcopy(cs[104]);b=a.rb(bad['wires'][0]['joins'][0]['complete_join_rectangle_exact']);bad['wires'][0]['joins'][0]['complete_join_rectangle_exact']=a.fmt(tuple(((x+y)/2,(x+y)/2) for x,y in b));keep('shrink_join_below_full_vertex_tolerance_sphere_projection','reconstruct(raw_face_104,variant)',bad,lambda:a.reconstruct(raws[104],bad))
row=next(x for x in ledger['original_positive_boxes'] if x['kind']=='new_panel_completed_trim_exterior');face=next(x['face_index'] for x in row['all_298_complete_face_witnesses'] if x['method']!='original_complete_support')
bad=copy.deepcopy(models[face]);bad['wires'][1]['polygon'].reverse();tube=a.rb(row['open_tube_exact']);keep('reverse_only_inner_oriented_reference_loop','check_trim_query(variant.tube,variant.model)',{'face_index':face,'tube':tube,'model':bad},lambda:a.check_trim_query(tube,bad))
bad=copy.deepcopy(ledger);next(x for x in bad['original_positive_boxes'] if x['kind']=='new_panel_completed_trim_exterior')['all_298_complete_face_witnesses'].pop();keep('omit_one_complete_panel_face','check_ledger(prior_L,variant,models,projections)',bad,lambda:a.check_ledger(prior,bad,models,projections))
bad=copy.deepcopy(ledger);bad['original_positive_boxes'].pop();keep('omit_original_positive_cell','check_ledger(prior_L,variant,models,projections)',bad,lambda:a.check_ledger(prior,bad,models,projections))
bad=copy.deepcopy(ledger);q=next(x for x in bad['original_positive_boxes'] if F(x['upper_under_B0_and_T_exact'])>F(1,2**80));q['upper_under_B0_and_T_exact']=str(F(q['upper_under_B0_and_T_exact'])-F(1,2**80));assert F(q['upper_under_B0_and_T_exact'])>0;keep('understate_still_positive_residual_by_2^-80','check_ledger(prior_L,variant,models,projections)',bad,lambda:a.check_ledger(prior,bad,models,projections))
bad=copy.deepcopy(ledger);bad['actual_native_T_membership_proved']=True;keep('promote_conditional_model_to_native_identity','check_ledger(prior_L,variant,models,projections)',bad,lambda:a.check_ledger(prior,bad,models,projections))
r={'schema':'razr-r13-complete-trim-negative-control-variants-and-replay-v1','source_sha256':a.sha(__file__),
   'checker_sha256':a.sha(HERE/'audit_r13_trim_independently.py'),'original_independent_review_sha256':a.sha(HERE/'R13_TRIM_INDEPENDENT_REVIEW.json'),
   'seed_native_report_sha256':a.sha(a.SRC/'native-attempt1/report.json'),'seed_corridors_sha256':a.sha(a.SRC/'producer-attempt1/complete_trim_corridors.json'),
   'seed_L_ledger_sha256':a.sha(a.SRC/'producer-attempt1/L_KEY-completed-trim-ledger.json.gz'),
   'complete_variants':variants,'all_replayed_rejections':all(v['replay']['rejected'] for v in variants)}
(OUT/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'variants':len(variants),'all_replayed_rejections':r['all_replayed_rejections'],'sha256':a.sha(OUT/'report.json')}))
