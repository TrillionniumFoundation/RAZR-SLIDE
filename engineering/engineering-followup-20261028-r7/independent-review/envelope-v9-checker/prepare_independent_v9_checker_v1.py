"""Root-authored V9 checker extension from the exact recovered V7 checker."""
import ast, hashlib, json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
old = root/'razr-current/engineering/engineering-followup-20261028-r5/compute/verify_planar_exterior_r5e_v7.py'
out = root/'r7-envelope/source-v9/verify_planar_exterior_r7e_v9.py'
assert not out.exists(), 'new checker path required'
source = old.read_text()
original = source
def replace_once(a,b):
    global source
    assert source.count(a) == 1, (a,source.count(a))
    source = source.replace(a,b)

replace_once('Independent exact V7 planar exterior-certificate verifier.', 'Independent exact V9 original Line-domain planar exterior-certificate verifier.')
replace_once('def verify_models(serialized, prior_boundary, frame, projection, limits):',
             'def verify_legacy_models(serialized, prior_boundary, frame, projection, limits):')
replace_once('def model_controls(serialized, boundary, frame, projection, limits):',
             'def model_controls(serialized, boundary, frame, projection, limits, extra_projection):')
assert source.count('verify_models(changed,boundary,frame,projection,limits)') == 2
source = source.replace('verify_models(changed,boundary,frame,projection,limits)',
                        'verify_models(changed,boundary,frame,projection,limits,extra_projection)')
replace_once("'real_retained_leaf_selection','static_source_capacity')", "'real_retained_leaf_selection','static_source_capacity','extra_line_plane_source')")
replace_once("'maximum_total_UV_pieces':4064,'maximum_planar_models':48,'maximum_actual_V6_retained_roots':4943}",
             "'maximum_total_UV_pieces':4100,'maximum_planar_models':50,'maximum_actual_V6_retained_roots':4943}")
replace_once('def validate_static_capacity(contract, records):','def validate_legacy_static_capacity(contract, records):')
replace_once("report['all_frame_capacity_observations_completed'] is True and report['actual_total_UV_boundary_pieces'] <= 4064 and",
             "report['all_frame_capacity_observations_completed'] is True and report['actual_total_UV_boundary_pieces'] <= 4100 and")
replace_once("'schema':'razr-r5e-independent-planar-exterior-verification-v7'","'schema':'razr-r7e-independent-planar-exterior-verification-v9'")
replace_once("'UV_channel_negative_controls':[],'real_case_control_applicability':{},'mandatory_analytic_controls':None}",
             "'UV_channel_negative_controls':[],'supplemental_original_source_negative_controls':[],\n              'missing_V8_archived_bytes_not_reconstructed':True,'real_case_control_applicability':{},'mandatory_analytic_controls':None}")
replace_once("producer['schema'] == 'razr-r5e-planar-exterior-refinement-v7'", "producer['schema'] == 'razr-r7e-planar-exterior-refinement-v9'")
replace_once("certificate['schema'] == 'razr-r5e-planar-exterior-tree-v7'", "certificate['schema'] == 'razr-r7e-planar-exterior-tree-v9'")
replace_once("report['independent_static_source_capacity'] = validate_static_capacity(contract,records)",
             "raw_projection = gzip_json(bound(contract['primitive_source_bundle']))\n        extra_projection = load_extra_projection(contract,raw_projection,records,baseline)\n        report['independent_static_source_capacity'] = validate_static_capacity(contract,records,extra_projection)")
replace_once("verify_models(certificate['planar_models'],certificate6['boundary_refinement'],old6,projection,limits)",
             "verify_models(certificate['planar_models'],certificate6['boundary_refinement'],old6,projection,limits,extra_projection)")
replace_once("model_controls(certificate['planar_models'],certificate6['boundary_refinement'],old6,projection,limits)",
             "model_controls(certificate['planar_models'],certificate6['boundary_refinement'],old6,projection,limits,extra_projection)\n            need(all(row[name] == audit_models.get(name,0) for name in ('additional_original_plane_count','additional_applied_plane_count','additional_rejected_plane_count')),\n                 'actual additional original model census differs')\n            if audit_models.get('additional_applied_plane_count',0) and not report['supplemental_original_source_negative_controls']:\n                report['supplemental_original_source_negative_controls'] = supplemental_controls(certificate['planar_models'],certificate6['boundary_refinement'],old6,projection,limits,extra_projection)")
replace_once("for name in ('applied','rejected','UV_pieces'): totals['model_'+name] += audit_models.get(name,0)",
             "for name in ('applied','rejected','UV_pieces','additional_original_plane_count','additional_applied_plane_count','additional_rejected_plane_count','additional_UV_piece_count'): totals['model_'+name] += audit_models.get(name,0)")
replace_once("producer['actual_total_UV_boundary_pieces'] == totals['model_UV_pieces'] <= 4064", "producer['actual_total_UV_boundary_pieces'] == totals['model_UV_pieces'] <= 4100")
replace_once("totals['model_applied']+totals['model_rejected'] <= (6 if contract['expected_phase'] == 'single_planar_exterior_leaf' else 48)",
             "totals['model_applied']+totals['model_rejected'] <= (8 if contract['expected_phase'] == 'single_planar_exterior_leaf' else 50)")
replace_once("        source_controls = report['planar_source_negative_controls']", "        supplemental = report['supplemental_original_source_negative_controls']\n        report['real_case_control_applicability']['supplemental_original_source_mutations'] = applicability(\n            supplemental,totals['model_additional_applied_plane_count'],12,'No actual applied original supplemental plane.')\n        source_controls = report['planar_source_negative_controls']")
extra = (Path(__file__).parent/'independent_v9_extensions.py.txt').read_text()
replace_once('\ndef main():','\n'+extra+'\n\ndef main():')
ast.parse(source)
out.write_text(source)
def functions(s):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
a,b = functions(original),functions(source)
same = [n for n in a if n in b and a[n] == b[n]]
proofs = ['check_exclusion','verify_uv_exclusion','verify_uv_unresolved','check_unresolved','verify_tree','source_occurrence','source_wire','source_face','analytic_controls']
assert all(n in same for n in proofs)
assert b['verify_legacy_models'] == a['verify_models'].replace("name='verify_models'","name='verify_legacy_models'",1)
assert b['validate_legacy_static_capacity'] == a['validate_static_capacity'].replace("name='validate_static_capacity'","name='validate_legacy_static_capacity'",1)
record = {'schema':'razr-r7e-independent-v9-checker-source-preparation-v1',
          'original_checker':{'bytes':old.stat().st_size,'sha256':hashlib.sha256(old.read_bytes()).hexdigest()},
          'new_checker':{'path':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()},
          'AST_unchanged_original_functions':same,'AST_unchanged_original_proof_functions':proofs,
          'old_model_checker_only_renamed':True,'old_static_capacity_checker_only_renamed':True,
          'new_source_math':'Exact Line endpoint enumeration and four-corner affine image; original strict full-D forward equality',
          'producer_or_helper_imported':False,'new_actual_run_executed':False,
          'actual_supplemental_control_count_required_when_eligible':12,'review_pending':True}
p=Path(__file__).parent/'R7E_V9_INDEPENDENT_CHECKER_SOURCE_PREPARATION_V1.json';p.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
