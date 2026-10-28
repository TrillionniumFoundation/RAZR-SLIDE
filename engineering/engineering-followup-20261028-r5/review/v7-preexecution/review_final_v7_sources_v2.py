"""Bounded read-only final static review; no V7 implementation is imported."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import stat
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PLAN = HERE/'R5_V7_FINAL_STATIC_REVIEW_BUDGET.json'
OUTPUT = HERE/'R5_V7_FINAL_INDEPENDENT_STATIC_REVIEW_V2.json'
LOCK = 'da61d0c1af1b6ac7ca2013990bf6cda43d1e8309a859b7bbfd7ec51abbf9971f'
CHECKER = '147fbe2ac883428a4669a8659d51e22dd8c4b6f9c76a58064fdea305fd10ba7e'
BASIS = '557c4dfb08e532eb1e440c1c3f7d74155a6a2fbee5e1c6c6a32a42d657eb69e0'
OLD_LOCK = '5cf2c18e7971912949e7e7167451cf547e291be421f205d78ef668fd7ab5b499'
started = time.monotonic()
plan = json.loads(PLAN.read_text())
streamed = assertions = 0
watched = {}


def need(ok, message):
    global assertions
    assertions += 1
    if not ok: raise ValueError(message)


def guard():
    need(time.monotonic()-started <= plan['wall_seconds'], 'registered static wall budget exceeded')
    need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <= plan['RSS_limit_bytes'], 'registered static RSS budget exceeded')
    need(streamed <= plan['maximum_streamed_identity_bytes'], 'registered total streaming identity budget exceeded')


def identity(path):
    global streamed
    path = Path(path).resolve(); digest = hashlib.sha256()
    with path.open('rb') as source:
        while True:
            block = source.read(1024*1024)
            if not block: break
            streamed += len(block); digest.update(block); guard()
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':digest.hexdigest()}


def equal(left, right): return all(left[key] == right[key] for key in ('bytes','sha256'))


def watch(path, expected=None):
    actual = identity(path)
    if expected is not None: need(equal(actual,expected), 'actual bytes differ: '+str(path))
    if actual['path'] in watched: need(watched[actual['path']] == actual, 'identity changed within static review')
    watched[actual['path']] = actual
    return actual


def read(path):
    path = Path(path); need(path.stat().st_size <= plan['maximum_single_metadata_bytes'], 'static metadata read exceeds registered bound')
    return path.read_text()


def data(path): return json.loads(read(path))


def assigned(tree, name):
    return next(node.value for node in ast.walk(tree) if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id == name for t in node.targets))


def function(tree, name): return next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name == name)


def field_keys(tree, variable):
    return {node.slice.value for node in ast.walk(tree) if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name) and
            node.value.id == variable and isinstance(node.slice,ast.Constant) and isinstance(node.slice.value,str)}


def dictionary_literals(tree, name):
    dictionary = assigned(tree,name); need(isinstance(dictionary,ast.Dict), 'registered dictionary assignment missing: '+name)
    return {key.value:value.value for key,value in zip(dictionary.keys,dictionary.values) if isinstance(key,ast.Constant) and isinstance(value,ast.Constant)}


report = {'schema':'r5-v7-final-independent-static-review-v2','started_utc':datetime.now(timezone.utc).isoformat(),
          'execution_completed':False,'source_static_review_passed':False,'V7_mathematical_experiments_executed':0,
          'V7_control_suites_executed':0,'new_native_CAD_operations':0,'new_producer_helper_or_checker_imported':False,
          'GitHub_mutations_performed':0,'external_run_status_queried':False,'prepared_workflow_is_not_run_evidence':True,
          'conditional_planar_exterior_model_only':True,'native_planar_region_semantics_verified':False,
          'native_primitive_semantics_verified':False,'native_trim_class_membership_verified':False,
          'original_raw_gate_reclassified':False,'full_continuous_G2':False,'all_blockers_closed':False,
          'static_review_does_not_admit_a_worker_to_runtime_resources':True}

try:
    need(not OUTPUT.exists(), 'append-only review output already exists')
    report['prior_actual_static_review_failure'] = watch(HERE/'R5_V7_FINAL_INDEPENDENT_STATIC_REVIEW_V1.json')
    report['only_review_implementation_correction'] = 'Read ast.Dict.values as an AST list, not as a mapping method; frozen V7 source, lock, inputs, original gates and workflow unchanged.'
    need(plan['wall_seconds'] == 90 and plan['RSS_limit_bytes'] == 268435456 and plan['maximum_streamed_identity_bytes'] == 536870912 and
         plan['source_imports_permitted'] is False and plan['V7_model_construction_permitted'] is False and
         plan['V7_channel_or_control_execution_permitted'] is False and plan['GitHub_mutations_permitted'] is False,
         'registered static-only budget/scope differs')
    report['budget_identity'] = watch(PLAN); report['review_script_identity'] = watch(__file__)
    for row in plan['inputs']: watch(ROOT/row['path'],row)
    src = ROOT/'r5-envelope'; snap = ROOT/'r5-local-v7/input-snapshot-v1'
    lock_path = src/'R5E_PORTABLE_SOURCE_LOCK_V7.json'; lock_id = watch(lock_path); lock = data(lock_path)
    need(lock_id['sha256'] == LOCK == plan['fixed_source_lock_sha256'], 'exact final V7 lock differs')
    ready = data(src/'R5E_V7_READINESS.json'); local = data(ROOT/'r5-local-v7/R5_V7_LOCAL_EXECUTION_READINESS.json')
    need(lock['schema'] == 'razr-r5e-portable-source-lock-v7-planar-exterior-conditioned' and len(lock['r5_files']) == 37 and
         len(lock['r4_source_files']) == 3 and len({r['path'] for r in lock['r5_files']}) == 37, 'complete final source lock differs')
    need(lock['source_commit'] == 'c5f6606924937d716b007cd3ffa8e54df8ecfa5d' and lock['actual_V6_execution_kind'] == 'local_owned_pipeline' and
         lock['actual_V6_source_lock']['sha256'] == OLD_LOCK and lock['V5_producer_rerun'] is False and lock['V6_producer_rerun'] is False,
         'original provenance/scope chain differs')
    for name in ('conditional_planar_exterior_model_only','conditional_primitive_support_model_only','conditional_trim_model_only'):
        need(lock[name] is True, 'conditional model scope changed')
    for name in ('native_planar_region_semantics_verified','native_primitive_semantics_verified','native_trim_class_membership_verified',
                 'original_raw_gate_reclassified','full_continuous_G2'):
        need(lock[name] is False and ready[name] is False and local[name] is False, 'static source readiness cannot promote native/original scope')
    need(equal(ready['source_lock'],lock_id) and equal(local['source_lock'],lock_id) and local['source_lock_sha256_literal'] == LOCK and
         ready['formal_V7_worker_executions'] == ready['V7_mathematical_controls_executed'] == local['formal_worker_executions_so_far'] ==
         local['V7_mathematical_controls_executed_here'] == 0 and ready['new_geometric_pass_claimed'] is False and
         ready['final_independent_static_readback_still_required'] is True and local['formal_execution_waits_for_final_independent_static_review'] is True,
         'prepared source or input snapshot falsely claims executed V7 qualification')
    public = data(src/'R5E_PUBLIC_INPUT_BRIDGE.json'); v5 = data(src/'R5E_V6_BASE_V5_INPUT_BRIDGE.json'); v6 = data(src/'R5E_V7_BASE_V6_INPUT_BRIDGE.json')
    need(len(public['files']) == 19 and all(r['decoded_json_equal'] is True and not r['changed_strings'] for r in public['files']) and
         len(v5['files']) == 25 and v5['actual_run_id'] == 40645988108 and v5['original_reports_or_certificates_edited'] is False and
         v5['path_mapping_only'] is True and len(v6['files']) == 53 and v6['actual_execution_kind'] == 'local_owned_pipeline' and
         v6['actual_pipeline_source_lock_sha256'] == OLD_LOCK and v6['original_reports_or_certificates_edited'] is False and v6['path_mapping_only'] is True,
         'complete original byte-preserving public/V5/V6 input bridges differ')
    expected = {'source/'+row['path']:row for row in lock['r5_files']}
    expected['source/'+lock_path.name] = lock_id
    expected.update({'r4/'+row['path']:row for row in lock['r4_source_files']})
    expected.update({'r4/'+row['path']:row['public_identity'] for row in public['files']})
    expected.update({'base-v5/'+row['path']:row for row in v5['files']})
    expected.update({'base-v6/'+row['path']:row for row in v6['files']})
    need(len(expected) == len(local['source_snapshots']) == plan['complete_snapshot_expected_files'] == 138 and
         local['snapshot_counts'] == plan['expected_snapshot_counts'], 'complete snapshot census differs')
    snapshot_rows = []; seen = set(); total = 0
    for row in local['source_snapshots']:
        path = Path(row['snapshot']['path']).resolve(); need(path.is_relative_to(snap), 'snapshot file escapes complete root')
        name = path.relative_to(snap).as_posix(); need(name in expected and name not in seen, 'unexpected or duplicate snapshot member'); seen.add(name)
        original = watch(row['source']['path'],row['source']); copied = watch(path,row['snapshot'])
        need(equal(original,copied) and equal(copied,expected[name]) and row['original_bytes_changed'] is False and
             row['mode'] == '0444' and stat.S_IMODE(path.stat().st_mode) == 0o444 and not path.is_symlink(),
             'original/snapshot complete bytes, containment or read-only mode differ')
        total += copied['bytes']; snapshot_rows.append({'relative_path':name,'source':original,'snapshot':copied,'mode':'0444'})
    need(seen == set(expected) == {p.relative_to(snap).as_posix() for p in snap.rglob('*') if p.is_file()} and
         total == local['snapshot_bytes'] == plan['complete_snapshot_expected_bytes'] == 43211475, 'unlisted, omitted or altered source snapshot bytes')
    report['complete_snapshot_inputs'] = snapshot_rows
    report.update(source_lock=lock_id,complete_snapshot_files=138,complete_snapshot_bytes=total,snapshot_counts=local['snapshot_counts'])
    prior_locks = []
    for old in ready['prior_frozen_sources_actually_rehashed']:
        old_path = src/old['lock']['path']; old_id = watch(old_path,old['lock']); old_value = data(old_path)
        for row in old_value['r5_files']: watch(src/row['path'],row)
        for row in old_value['r4_source_files']:
            need(equal(expected['r4/'+row['path']],row), 'original R4 supervisor source changed across frozen lock generations')
        need(old['r5_members_unchanged'] == len(old_value['r5_files']) and old['r4_members_unchanged'] == len(old_value['r4_source_files']),
             'original lock membership rehash census differs')
        prior_locks.append({'lock':old_id,'r5_members_rehashed':len(old_value['r5_files']),'r4_members_unchanged':len(old_value['r4_source_files'])})
    report['independently_rehashed_prior_source_locks'] = prior_locks
    trees = {}; source_text = {}; python_rows = []
    for row in lock['r5_files']:
        if not row['path'].endswith('.py'): continue
        content = read(src/row['path']); parsed = ast.parse(content,filename=row['path']); trees[row['path']] = parsed; source_text[row['path']] = content
        imports = [ast.unparse(node) for node in parsed.body if isinstance(node,(ast.Import,ast.ImportFrom))]
        python_rows.append({'file':row['path'],'AST_parsed':True,'functions':len([n for n in parsed.body if isinstance(n,ast.FunctionDef)]),'direct_imports':imports})
    need(len(python_rows) == len(ready['python_sources_AST_parsed']) == 18 and
         {row['file'] for row in python_rows} == set(ready['python_sources_AST_parsed']), 'all frozen Python sources need syntax inspection')
    driver = trees['run_portable_planar_r5e_v7.py']; producer = trees['planar_exterior_refinement_r5e_v7.py']
    helper = trees['planar_exterior_model_r5e_v7.py']; checker = trees['verify_planar_exterior_r5e_v7.py']
    members = {r['path']:r for r in lock['r5_files']}
    need(members['verify_planar_exterior_r5e_v7.py']['sha256'] == CHECKER == plan['fixed_checker_sha256'] and
         members['R5E_PLANAR_EXTERIOR_V7_BASIS.md']['sha256'] == BASIS, 'final checker or affine-basis correction absent from lock')
    phases = ast.literal_eval(assigned(driver,'sequence'))
    need(phases == [('single-planar-exterior-leaf','single_planar_exterior_leaf'),('verify-single','verify_single'),
                    ('preflight-planar-exterior','preflight_planar_exterior'),('all-planar-exterior-frames','all_planar_exterior_frames'),('verify-all','verify_all')] and
         [row[0] for row in phases] == ready['sequential_stages'] == local['stage_order'], 'exact five sequential stages differ')
    gates = {'wall_seconds':600,'RSS_limit_bytes':805306368,'shared_ceiling_bytes':7301444403,'disk_floor_bytes':104857600,
             'maximum_output_bytes':41943040,'metadata_margin_bytes':4194304}
    shared = dictionary_literals(driver,'shared_base')
    need(all(shared[key] == value for key,value in gates.items()) and shared['expected_output_bytes'] == 41943040 and
         shared['zero_RSS_missing_observations_allowed'] is False and ready['original_owned_limits_per_stage'] == gates == local['original_limits_per_stage'],
         'original worker/owned resource gates changed')
    driver_contract = assigned(driver,'contract'); capacity_node = next(value for key,value in zip(driver_contract.keys,driver_contract.values) if isinstance(key,ast.Constant) and key.value == 'capacity')
    driver_capacity = {key.value:value.value for key,value in zip(capacity_node.keys,capacity_node.values) if isinstance(value,ast.Constant)}
    wanted_capacity = {'wall_seconds':600,'RSS_limit_bytes':805306368,'maximum_splits':4096,'maximum_depth':24,
        'maximum_boundary_box_tests':12000000,'maximum_support_inequality_tests':12000000,'maximum_boundary_pieces_per_material':4096,
        'cylinder_angular_patch_count':64,'circle_angular_patch_count':64,'Taylor_term_count':24,'centre_grid_denominator':65536,
        'maximum_UV_pieces_per_face':225,'maximum_total_UV_pieces':4064,'maximum_planar_models':48,'maximum_actual_V6_retained_roots':4943,
        'all_UV_tests_charged_to_original_combined_budgets':True}
    need(driver_capacity == wanted_capacity, 'exact original/new finite capacity literals differ')
    tiny_node = next(value for key,value in zip(capacity_node.keys,capacity_node.values) if isinstance(key,ast.Constant) and key.value == 'tiny_retained_volume_exact')
    need(ast.unparse(tiny_node) == 'str(Fraction(1e-07) / 100000)', 'original exact float64-derived tiny threshold changed')
    shared_producer = ast.literal_eval(assigned(producer,'SHARED_INPUT_FIELDS')); shared_checker = ast.literal_eval(assigned(checker,'SHARED_INPUT_FIELDS'))
    need(list(shared_checker) == shared_producer and len(shared_producer) == len(set(shared_producer)) == 26,
         'complete shared producer/checker source/input identity binding differs')
    declared_contract_fields = {key.value for node in ast.walk(driver) if isinstance(node,ast.Dict) for key in node.keys if isinstance(key,ast.Constant) and isinstance(key.value,str)}
    declared_contract_fields.update(node.slice.value for node in ast.walk(driver) if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name) and
        node.value.id == 'contract' and isinstance(node.ctx,ast.Store) and isinstance(node.slice,ast.Constant))
    need(set(shared_producer) <= declared_contract_fields and field_keys(producer,'contract') <= declared_contract_fields and
         field_keys(checker,'contract') <= declared_contract_fields, 'producer/checker contract consumes an undeclared driver field')
    reader_fields = [node.args[0].slice.value for node in ast.walk(checker) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and
                     node.func.id == 'prior_module' and isinstance(node.args[0],ast.Subscript)]
    need(set(reader_fields) == {'base_V6_verifier_source','base_V5_verifier_source','base_verifier_source'} and len(reader_fields) == 3,
         'new independent checker must import only the three frozen prior independent readers')
    need(ast.literal_eval(assigned(checker,'V6_LOCK')) == OLD_LOCK and
         ast.literal_eval(assigned(checker,'V6_CHECKER')) == members['verify_primitive_support_r5e_v6.py']['sha256'], 'frozen independent import literal changed')
    strict_checks = []
    for parsed,name,targets in [(helper,'closed_piece_separator',{'channel[axis][1]','channel[axis][0]','mapped[1]','mapped[0]'}),
                                (checker,'strict_separator',{'target[axis][1]','target[axis][0]','projected[1]','projected[0]'})]:
        comparisons = [node for node in ast.walk(function(parsed,name)) if isinstance(node,ast.Compare) and ast.unparse(node.left) in targets]
        need(len(comparisons) == 4 and all(len(node.ops) == 1 and isinstance(node.ops[0],(ast.Lt,ast.Gt)) for node in comparisons),
             'every closed UV coordinate/slab separation must remain strict')
        strict_checks.append({'function':name,'strict_comparisons':[ast.unparse(node) for node in comparisons]})
    for parsed,name,terms in [(helper,'affine_project',['spatial_box[k][0] - origin[k]','spatial_box[k][1] - origin[k]']),
                              (checker,'plane_project',['lo - origin[k]','hi - origin[k]']),
                              (helper,'planar_channel_exclusion',["spatial_channel[k][0] - model['D'][k][1]","spatial_channel[k][1] - model['D'][k][0]"]),
                              (checker,'projected_candidate',["spatial_channel[k][0] - model['D'][k][1]","spatial_channel[k][1] - model['D'][k][0]"])]:
        normalized = ast.unparse(function(parsed,name)); need(all(term in normalized for term in terms), 'full origin/D projection term absent: '+name)
    driver_text = source_text['run_portable_planar_r5e_v7.py']
    need("row['actual_planar_exterior_separator_count_in_excluded_leaves']>0" in driver_text and
         "Fraction(row['newly_excluded_open_leaf_sum_exact'])>0" in driver_text and
         "first['planar_exterior_model_conditional_clearance_passes']==1" in driver_text and
         "finished['verify_single']['report']['execution_completed']" in driver_text and
         "capacity['total_actual_V6_retained_roots']==4943" in driver_text and "capacity['complete_phase_maximum_tree_nodes']==13135" in driver_text,
         'actual selected first witness/independent/source-capacity prerequisites were weakened')
    design_path = ROOT/'r5-integration/v7-independent-checker/R5_V7_INDEPENDENT_CHECKER_SOURCE_CONTRACT_V2.json'; design = data(design_path)
    need(equal(design['source'],members['verify_planar_exterior_r5e_v7.py']) and equal(design['basis'],members['R5E_PLANAR_EXTERIOR_V7_BASIS.md']) and
         design['V7_mathematical_workers_executed_by_this_agent'] == design['V7_control_suites_executed_by_this_agent'] == 0 and
         len(design['registered_analytic_positives']) == 5 and design['registered_analytic_negative_count'] == 21 and
         design['self_authored_design_record_not_cross_author_audit'] is True, 'checker design contract cannot claim executed independent validation')
    static_capacity = data(src/'R5E_V7_STATIC_SOURCE_CAPACITY.json'); selection = data(src/'R5E_V7_REAL_RETAINED_LEAF.json')
    need(static_capacity['new_mathematical_qualification'] is False and static_capacity['new_primitive_or_planar_enclosures_computed'] is False and
         static_capacity['maximum_total_UV_pieces'] == 4064 and static_capacity['maximum_UV_pieces_per_face'] == 225 and
         static_capacity['maximum_new_forest_nodes'] == 13135 and static_capacity['maximum_new_forest_leaves'] == 9039 and
         [selection[key] for key in ('case_id','frame','V6_root_index','V6_node_index','actual_leaf_depth')] == ['case-028',1,76,47,24] and
         selection['base_V5_leaf_locator'] == [28,17] and selection['no_new_geometry_execution'] is True,
         'fixed capacity or original real first witness differs')
    old_producer = data(snap/'base-v6/all-primitive-support-frames/report.json'); old_checker = data(snap/'base-v6/verify-all/report.json')
    need(old_producer['execution_completed'] is True and old_checker['execution_completed'] is True and
         old_producer['primitive_support_model_conditional_clearance_passes'] == old_checker['primitive_support_model_conditional_clearance_passes'] == 8 and
         len(old_producer['frames']) == 16 and old_producer['counters']['splits'] == 4096, 'original actual V6 result or budget exhaustion changed')
    report['AST_source_observations'] = python_rows
    report['strict_closed_UV_comparisons'] = strict_checks
    report['registered_stage_sequence'] = phases
    report['same_original_worker_limits'] = gates
    report['same_combined_spatial_UV_capacity'] = wanted_capacity
    report['fixed_original_selected_leaf'] = {key:selection[key] for key in ('case_id','frame','V6_root_index','V6_node_index','actual_leaf_depth','base_V5_leaf_locator','positive_directed_volume_mm3')}
    report['actual_original_V6_conditional_result_preserved'] = {'frames':16,'passes':8,'actual_splits':4096,'mathematics_reexecuted_by_static_review':False}
    command = local['exact_driver_command']; output = ROOT/'r5-local-v7/attempt-1'
    expected_command = [command[0],'-I','-S','-B',str(snap/'source/run_portable_planar_r5e_v7.py'),
                        '--r4-root',str(snap/'r4'),'--base-v5-root',str(snap/'base-v5'),'--base-v6-root',str(snap/'base-v6'),'--output',str(output)]
    need(command == expected_command and Path(command[0]).resolve() == Path(local['python']['executable']['path']).resolve() and
         local['python']['flags'] == {'isolated':1,'no_site':1,'optimize':0} and local['new_output_directory'] == str(output) and not output.exists(),
         'prepared isolated original local entry or fresh unexecuted output differs')
    interpreter = watch(command[0],local['python']['executable']); watch(local['preparation_source']['path'],local['preparation_source'])
    resources = local['resource_snapshot']
    need(resources['shared_plus_worker_limit_bytes'] == resources['shared_unreclaimable_bytes']+805306368 and
         resources['startup_disk_required_bytes'] == 104857600+41943040+4194304 and
         resources['instant_snapshot_admits_original_limits'] == (resources['disk_available_bytes'] >= 150994944 and resources['shared_plus_worker_limit_bytes'] <= 7301444403) and
         local['resource_snapshot_is_not_actual_supervisor_admission'] is True and local['actual_owned_supervisor_must_admit_each_stage'] is True,
         'local original capacity snapshot was promoted or arithmetic changed')
    report['local_preparation_preserved'] = {'driver_command':command,'interpreter':interpreter,'recorded_resource_snapshot':resources,
        'actual_V7_local_execution':False,'local_launcher_created_or_run_by_this_review':False,'capacity_snapshot_is_not_admission':True,
        'formal_execution_target':'separate Actions runner under the same original owned gates'}
    template = read(ROOT/'r5-integration/r5-planar-v7-workflow.template.yml')
    workflow = read(ROOT/'r5-integration/r5-planar-v7-workflow.yml')
    previous_workflow = read(ROOT/'r5-integration/r5-primitive-v6-workflow.yml')
    need(template.count('__FINAL_V7_LOCK_SHA__') == 1 and template.replace('__FINAL_V7_LOCK_SHA__',LOCK) == workflow,
         'concrete CI workflow is not solely the registered final-lock substitution')
    expected_workflow = previous_workflow.replace('primitive-support-conditioned','planar-exterior-conditioned').replace('R5E_PORTABLE_SOURCE_LOCK_V6.json','R5E_PORTABLE_SOURCE_LOCK_V7.json')
    expected_workflow = expected_workflow.replace(OLD_LOCK,LOCK).replace('run_portable_primitive_r5e_v6.py','run_portable_planar_r5e_v7.py')
    expected_workflow = expected_workflow.replace('razr-r5-primitive-model-v6','razr-r5-planar-exterior-v7').replace('R5-primitive-model-v6','R5-planar-exterior-v7')
    old_sparse = '            engineering/engineering-followup-20261028-r5/envelope/actions/run-40645988108\n'
    expected_workflow = expected_workflow.replace(old_sparse,old_sparse+'            engineering/engineering-followup-20261028-r5/envelope/local/attempt-v6-1\n')
    old_arg = '            --base-v5-root "$GITHUB_WORKSPACE/engineering/engineering-followup-20261028-r5/envelope/actions/run-40645988108" \\\n'
    expected_workflow = expected_workflow.replace(old_arg,old_arg+'            --base-v6-root "$GITHUB_WORKSPACE/engineering/engineering-followup-20261028-r5/envelope/local/attempt-v6-1" \\\n')
    need(workflow == expected_workflow, 'CI entry changed more than reviewed version identities and complete original V6 input path')
    required_workflow = ["branches: ['evidence/full-sprint-20261028-r5']","github.repository == 'TrillionniumFoundation/RAZR-SLIDE'",
        "github.ref == 'refs/heads/evidence/full-sprint-20261028-r5'",'compute/RUN_REQUEST.json','contents: read','cancel-in-progress: false',
        'runs-on: ubuntu-24.04','timeout-minutes: 55','actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1','ref: ${{ github.sha }}',
        'persist-credentials: false','test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD"','python3 -I -S -B','if: always()',
        'actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9','if-no-files-found: error','retention-days: 14']
    need(all(value in workflow for value in required_workflow), 'prepared CI entry lacks an original head/branch/source/runtime/artifact gate')
    need(ready['maximum_combined_worker_wall_seconds_before_overhead'] == local['whole_pipeline_worker_wall_bound_seconds'] == 5*600 == 3000,
         'actual five-stage finite time policy changed')
    report['prepared_Actions_entry_review'] = {'template':watched[str((ROOT/'r5-integration/r5-planar-v7-workflow.template.yml').resolve())],
        'concrete':watched[str((ROOT/'r5-integration/r5-planar-v7-workflow.yml').resolve())],
        'old_reviewed_V6_workflow':watched[str((ROOT/'r5-integration/r5-primitive-v6-workflow.yml').resolve())],
        'only_lock_substitution_between_template_and_concrete':True,'all_original_pins_branch_head_resource_and_artifact_policies_preserved':True,
        'original_V6_raw_file_count':53,'same_owned_limits_on_separate_runner':True,'job_timeout_minutes':55,
        'combined_worker_wall_limit_seconds':3000,'remaining_job_time_before_checkout_and_other_overhead_seconds':300,
        'completion_within_job_timeout_guaranteed':False,'new_workflow_executed_by_this_review':False,
        'external_publication_or_run_is_not_claimed_by_this_static_record':True}
    for row in list(watched.values()): need(identity(row['path']) == row, 'input/source changed during final static readback')
    need(not output.exists(), 'local V7 output appeared during an explicitly static-only review')
    report['all_watched_source_and_input_bytes_unchanged'] = True
    report['watched_identity_count'] = len(watched)
    report['source_static_review_passed'] = True
    report['execution_completed'] = True
    guard()
except BaseException as exc:
    report['failure'] = {'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
finally:
    report['finished_utc'] = datetime.now(timezone.utc).isoformat(); report['elapsed_seconds'] = time.monotonic()-started
    report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    report['identity_streamed_bytes'] = streamed; report['assertion_count'] = assertions
    payload = json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if len(payload.encode()) > plan['maximum_report_bytes']: raise RuntimeError('registered static report size budget exceeded')
    if OUTPUT.exists(): raise RuntimeError('never overwrite an old actual static review record')
    OUTPUT.write_text(payload)
    print(json.dumps({key:report.get(key) for key in ('execution_completed','source_static_review_passed','elapsed_seconds','peak_RSS_bytes',
                                                    'identity_streamed_bytes','assertion_count','failure')}),flush=True)
raise SystemExit(0 if report['execution_completed'] else 2)
