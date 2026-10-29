"""Read saved edge189 results and complete input identities; no geometry rerun."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import itertools
import json
import resource
import signal
import time
import traceback

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / 'R7I_EDGE189_ACTUAL_READBACK_PLAN_V1.json'
OUT = ROOT / 'R7I_EDGE189_ACTUAL_INDEPENDENT_EVIDENCE_READBACK_V1.json'


def identity(path):
    p = Path(path)
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return {'path': str(p.resolve()), 'bytes': p.stat().st_size, 'sha256': h.hexdigest()}


def same(a, b):
    return a['bytes'] == b['bytes'] and a['sha256'] == b['sha256']


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    started = time.monotonic()
    plan = json.loads(PLAN.read_text())
    result = {'schema': 'razr-r7i-edge189-actual-independent-evidence-readback-v1',
              'recorded_utc': datetime.now(timezone.utc).isoformat(), 'completed': False,
              'source': identity(__file__), 'plan': identity(PLAN),
              'method': 'Full file hashes plus structural/source/counter cross-comparison of saved actual evidence. No verify_claim, support, separator, channel, CAD or ContactProfile function is imported or executed. Stored point containment and support outcomes are read, not recalculated.',
              'new_geometry_support_or_channel_execution': False, 'native_operations': 0}
    resource.setrlimit(resource.RLIMIT_AS, (plan['address_space_bytes'],) * 2)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('30 s readback limit')))
    signal.alarm(plan['wall_seconds'])
    try:
        evidence = {k: identity(v['path']) for k, v in plan['evidence'].items()}
        require(all(same(evidence[k], row) for k, row in plan['evidence'].items()), 'Registered actual evidence bytes differ')
        load = lambda key: json.loads(Path(evidence[key]['path']).read_text())
        contract, actual, claim = load('contract'), load('actual'), load('claim')
        startup, post, tool = load('startup'), load('post'), load('exec_tool')
        stdout = load('stdout')
        require(same(actual['contract'], evidence['contract']) and same(actual['source_support_claim'], evidence['claim']),
                'Actual contract/claim binding differs')
        require(tool['exit_code'] == post['actual_exit_code'] == 0 and actual['completed'] is True,
                'Actual execution did not complete successfully')
        require(evidence['stderr']['bytes'] == 0, 'Actual stderr is not empty')
        require(stdout['completed'] is True and stdout['failure'] is None and
                stdout['producer_counters'] == actual['actual_partial_or_complete_producer_counters'] and
                stdout['source_validation'] == actual['source_validation_vertices_and_comparisons'], 'Original stdout differs')
        bound = dict(contract['inputs'])
        bound.update({'V6_archive/' + k: v for k, v in contract['original_V6_archive_files'].items()})
        bound.update({k: contract[k] for k in ('source','basis','static_capacity','source_function_mapping','checker_interface','independent_line_checker')})
        require(len(bound) == contract['registered_input_and_artifact_count'] == 118, 'Complete original input count differs')
        require(sum(v['bytes'] for v in bound.values()) == contract['registered_input_and_artifact_bytes'] == 159865741,
                'Complete original input byte count differs')
        current = {k: identity(row['path']) for k, row in bound.items()}
        for k, expected in bound.items():
            require(all(same(row, expected) for row in [current[k], actual['partial_or_complete_registered_input_identities'][k],
                    startup['actual_input_identities'][k], post['post_input_identities'][k]]), 'Bound input identity differs: ' + k)
        require(actual['all_registered_inputs_unchanged'] and post['all_registered_inputs_unchanged'] and
                post['changed_registered_inputs'] == [] and post['all_readback_checks_passed'], 'Recorded post-input condition differs')
        result['complete_118_bound_input_current_identities'] = current
        result['original_launch_worker_post_and_current_118_hashes_all_equal'] = True
        result['complete_bound_input_bytes'] = 159865741
        original = json.loads(Path(bound['independent_authority/R7I_EDGE189_ORIGINAL_SOURCE_READBACK_V2.json']['path']).read_text())
        original_edge = original['complete_original_selected_record']['complete_original_edge']
        original_carrier = original['complete_original_carrier']
        require(claim['complete_original_edge'] == original_edge and claim['complete_original_carrier'] == original_carrier and
                claim['full_D_exact'] == original['original_full_remaining_D'], 'Complete original source/domain/carrier binding differs')
        require(claim['complete_original_edge_canonical_sha256'] == canonical(original_edge) ==
                'cd8fe627c479422cdc843f171751e6d956fc99e26e3a41a832c1fe359fc7e128', 'Canonical original edge differs')
        require(claim['normal_exact'] == ['1','2','0'] and claim['normal_dot_direction_exact'] == '0', 'Frozen normal identity differs')
        verified = actual['independent_source_support_readback']
        for key in ('normal_exact','forward_source_box_exact','exact_slab_bounds_exact','tau_expanded_slab_bounds_exact','hypothetical_tube_box_exact'):
            require(claim[key] == verified[key], 'Saved producer/independent payload differs: ' + key)
        six = [verified['forward_source_box_exact'][axis][end] == original_carrier['box_exact'][axis][end]
               for axis in range(3) for end in range(2)]
        require(all(six) and verified['source_box_equals_original_carrier'] is True, 'Strict six-endpoint original-box equality differs')
        exact_rows, tube_rows = verified['exact_vertices'], verified['hypothetical_tube_vertices']
        require(len(exact_rows) == 16 and len(tube_rows) == 128, 'Saved corner records are incomplete')
        expected_exact = [(ti, list(di)) for ti in (0,1) for di in itertools.product((0,1), repeat=3)]
        expected_tube = [(ti, list(di), list(ei)) for ti in (0,1)
                         for di in itertools.product((0,1), repeat=3) for ei in itertools.product((0,1), repeat=3)]
        require([(x['t_endpoint_index'],x['D_corner_selector']) for x in exact_rows] == expected_exact,
                'Saved exact endpoint/corner enumeration differs')
        require([(x['t_endpoint_index'],x['D_corner_selector'],x['error_corner_selector']) for x in tube_rows] == expected_tube,
                'Saved hypothetical endpoint/corner enumeration differs')
        curve = original_edge['native_global_curve']
        for row in exact_rows + tube_rows:
            original_t = curve['first_parameter' if row['t_endpoint_index'] == 0 else 'last_parameter']['exact']
            require(row['t_exact'] == original_t and row['D_corner_exact'] ==
                    [claim['full_D_exact'][axis][row['D_corner_selector'][axis]] for axis in range(3)],
                    'A saved corner drops the original endpoint or D selector')
            require(len(row['point_exact']) == 3 and type(row['inside_original_carrier_box']) is bool,
                    'Saved complete 3D point/classification missing')
        require(all(x['inside_original_carrier_box'] for x in exact_rows), 'Saved nominal corner containment differs')
        outside = [i for i, x in enumerate(tube_rows) if not x['inside_original_carrier_box']]
        require(outside and verified['hypothetical_tube_contained_in_original_carrier'] is False and
                actual['whole_hypothetical_tube_containment_in_original_AABB'] is False, 'Saved tube noncontainment was lost')
        result['saved_source_model_readback'] = {'complete_original_edge_and_carrier_bound': True,
            'full_nonzero_Vz_retained': curve['direction_exact'][2], 'full_D_exact': claim['full_D_exact'],
            'strict_six_original_box_endpoints_equal': six, 'exact_saved_corner_count': 16,
            'hypothetical_saved_corner_count': 128, 'nominal_saved_inside_flags_all_true': True,
            'hypothetical_saved_outside_corner_indices': outside, 'first_saved_outside_corner': tube_rows[outside[0]],
            'exact_slab_bounds_exact': verified['exact_slab_bounds_exact'],
            'tau_expanded_slab_bounds_exact': verified['tau_expanded_slab_bounds_exact'],
            'whole_hypothetical_tube_contained_in_B': False,
            'containment_or_support_recomputed_in_this_readback': False,
            'scope': 'Expanded slab alone contains the explicitly hypothetical tau tube according to the executed independent corner proof. The retained B intersect expanded slab is certified only for the bare serialized Line+D; full native geometry and a whole tolerance-shell enclosure remain unproved.'}
        names = ['shortened_complete_parameter_domain','nonzero_Vz_replaced_with_zero','wrong_fixed_normal',
                 'full_D_omitted_from_scalar_support_only','tau_omitted_from_expanded_slab_only']
        phases = ['source_edge_identity','source_edge_identity','fixed_normal','exact_support_16_vertices','tau_support_128_vertices']
        controls = actual['actual_negative_controls']
        require(len(controls) == 5, 'Five registered controls required')
        for i, row in enumerate(controls):
            require(row['name'] == names[i] and row['executed'] and row['rejected'] and row['expected_rejection_confirmed'] and
                    row['expected_rejection_mechanism'] == phases[i] and row['actual_exception']['type'] == 'ClaimError' and
                    row['actual_exception']['actual_rejection_stage'] == phases[i] and
                    row['actual_exception']['message'].startswith(phases[i] + ':'), 'Actual control phase mismatch')
            require(canonical(row['mutated_claim']) == row['mutated_claim_canonical_sha256'], 'Saved mutated claim hash differs')
        for i in (0,1):
            expected = copy.deepcopy(original_edge)
            for kind in ('local_curve','native_global_curve'):
                if i == 0:
                    expected[kind]['first_parameter'] = {'float':0.0,'hex':'0x0.0p+0','exact':'0'}
                else:
                    expected[kind]['direction_exact'][2] = '0'
            require(controls[i]['mutated_claim']['complete_original_edge'] == expected, 'Source-identity control mutation differs')
        expected = copy.deepcopy(claim); expected['normal_exact'] = ['1','1','0']
        require(controls[2]['mutated_claim'] == expected, 'Wrong-normal control changed another field')
        missing_D = controls[3]['mutated_claim']
        require(all(missing_D[k] == v for k,v in claim.items() if k not in ('exact_slab_bounds_exact','tau_expanded_slab_bounds_exact')),
                'Missing-D support control changed another source field')
        require(missing_D['exact_slab_bounds_exact'] == [claim['line_dot_constant_exact']] * 2 and
                controls[3]['validation_counter_cost'].get('exact_vertices') == 16 and
                controls[3]['validation_counter_cost'].get('hypothetical_tube_vertices',0) == 0,
                'Missing-D control did not reach exactly the 16-corner phase')
        expected = copy.deepcopy(claim); expected['tau_expanded_slab_bounds_exact'] = claim['exact_slab_bounds_exact']
        require(controls[4]['mutated_claim'] == expected and controls[4]['validation_counter_cost'].get('exact_vertices') == 16 and
                controls[4]['validation_counter_cost'].get('hypothetical_tube_vertices') == 128,
                'Missing-tau control did not preserve tau fields/reach 128-corner phase')
        result['five_actual_controls'] = [{k:row[k] for k in ('name','executed','expected_rejection_mechanism','actual_exception','validation_counter_cost')}
                                        for row in controls]
        local = actual['actual_three_fixed_piece_comparisons']
        require(len(local) == 3 and [x['separation_code'] for x in local] == [None,'7','7'] and
                all(x['source_box_gate_satisfied'] for x in local), 'Saved three local comparison results differ')
        full = actual['fixed_whole_channel_result']; cert = full['complete_new_conditional_certificate']
        require(actual['fixed_whole_channel_eligible'] and actual['actual_fixed_whole_channel_attempts'] == 1 and
                full['executed'] and (full['material_side'],full['axis'],full['end']) == (0,1,0), 'Saved fixed-channel scope differs')
        codes = cert['complete_piece_separation_codes']
        require(codes == full['separated_original_piece_prefix_codes'] and len(codes) == 523 and set(codes) <= set('01234567'),
                'Complete 523-piece saved coverage differs')
        nonaxis = [i for i, code in enumerate(codes) if code in '67']
        require(nonaxis == [77,332] and full['original_independent_certificate_readback'] == {'pieces':523,'nonaxis':2} and
                full['first_unresolved_original_piece_index'] is None and full['conditional_source_model_open_interior_excluded'] is True,
                'Saved original independent full-channel result differs')
        require(actual['original_material_piece_counts'] == [523,179] and actual['original_total_piece_count'] == 702 and
                actual['completely_unchanged_piece_count'] == 701 and actual['carrier_with_one_added_slab_count'] == 1 and
                actual['all_702_original_carriers_and_order_preserved_except_one_added_slab'], 'Original complete carrier census differs')
        omit = actual['conditional_complete_channel_omitted_code_control']
        require(omit == {'executed':True,'rejected':True,'actual_exception':{'type':'ValueError','message':'complete per-piece separation code coverage required'}},
                'Original omitted-code control did not fail with the coverage error')
        result['actual_fixed_local_and_channel_scope'] = {'three_local_comparisons': local, 'fixed_channel': contract['fixed_channel'],
            'fixed_channel_attempts':1,'complete_saved_piece_codes':codes,'code_count':523,'nonaxis_piece_indices':nonaxis,
            'original_reader_saved_result':full['original_independent_certificate_readback'],'total_two_material_carriers':702,
            'unchanged_carriers':701,'one_original_AABB_preserved_with_added_slab':True,'omitted_code_control':omit,
            'whole_closed_cell_disjoint_claimed':full['whole_closed_cell_disjoint_claimed'],
            'conditional_open_interior_only':True,'new_channel_or_separator_execution_in_this_readback':False}
        require(not full['whole_closed_cell_disjoint_claimed'] and full['closed_cell_boundary_retained_as_zero_volume_carrier'] and
                not full['actual_material_interference_claimed'] and not full['native_qualification_claimed'], 'Finite channel scope escalated')
        prior = json.loads(Path(bound['actual_cost_probe_report']['path']).read_text())
        require(actual['previous_actual_additional_stage_debit'] == prior['cumulative_conservative_additional_stage_debit'] ==
                {'splits':82,'piece_like_tests':174854,'support_like_tests':366314}, 'Prior ledger reset or changed')
        require(prior['original_V9_owned_failure_retained'] == {'type':'RuntimeError','message':"still-running owned child RSS unavailable: KeyError: 'VmRSS'"}
                and prior['original_first_u_gate_reached'] is False, 'Original V9 failure meaning differs')
        for key, value in {'original_V6_depth_gate_passed':False,'source_child_cumulative_depth':25,'new_splits':0,
                'V9_first_u_qualification':False,'original_V9_owned_failure_reclassified':False,'new_full_frame_execution':False,
                'native_BREP_error_bound_certified':False,'native_trim_membership_verified':False,'full_continuous_G2':False,
                'all_blockers_closed':False,'new_full_frame_execution_authorized_by_this_diagnostic':False}.items():
            require(actual[key] == value, 'Original diagnostic scope flag differs: ' + key)
        counters = actual['actual_partial_or_complete_producer_counters']; validation = actual['actual_source_validation_counters']
        vertices = sum(v for k,v in validation.items() if k.endswith('_vertices'))
        debits = sum(v for k,v in validation.items() if not k.endswith('_vertices'))
        independent_calls = actual['actual_independent_original_separator_calls']
        require(counters == {'channels_tested':1,'boundary_box_tests':526,'support_inequality_tests':951,'successful_nonaxis_separations':4} and
                independent_calls == 531 and actual['actual_independent_claim_calls'] == 6 and vertices == 304 and debits == 22793,
                'Saved actual counts differ')
        cumulative = {'splits':82,'piece_like_tests':174854+526+531+vertices,'support_like_tests':366314+951+531+debits}
        require(cumulative == actual['cumulative_conservative_additional_stage_debit'] and vertices <= 864 and debits <= 50000,
                'Cumulative budget bookkeeping differs')
        require(actual['elapsed_seconds'] <= 60 and actual['peak_RSS_bytes'] <= 536870912 and
                actual['actual_startup_original_formula_resources']['disk_available_bytes'] >=
                actual['actual_startup_original_formula_resources']['required_startup_disk_bytes'] and
                actual['actual_final_original_formula_resources']['disk_available_bytes'] >= 104857600 and
                actual['actual_final_original_formula_resources']['shared_unreclaimable_bytes'] <= 7301444403,
                'Original resource outcome differs')
        require(actual['actual_startup_original_formula_resources']['shared_plus_registered_RSS_bytes'] <= 7301444403,
                'Original startup shared formula differs')
        result['scope_and_cost_readback'] = {'source_depth':25,'original_depth24_gate_passed':False,
            'original_V9_owned_failure_retained':prior['original_V9_owned_failure_retained'], 'V9_first_u_qualified':False,
            'producer_counters':counters,'independent_original_separator_calls':independent_calls,
            'independent_claim_calls':6,'actual_validation_label_counts':validation,'vertices':vertices,
            'conservative_debits_not_literal_comparisons':debits,'cumulative_ledger':cumulative,
            'actual_wall_seconds':actual['elapsed_seconds'],'actual_peak_RSS_bytes':actual['peak_RSS_bytes'],
            'full_frame_or_native_or_physical_qualification':False}
        after = {k: identity(row['path']) for k,row in bound.items()}
        evidence_after = {k: identity(row['path']) for k,row in plan['evidence'].items()}
        require(current == after and evidence == evidence_after, 'Source/evidence bytes changed during independent readback')
        result['bound_actual_evidence'] = evidence
        result['all_118_sources_and_all_actual_evidence_unchanged_during_readback'] = True
        result['all_requested_read_only_checks_passed'] = True
        result['completed'] = True
    except BaseException as exc:
        result['failure'] = {'type':type(exc).__name__, 'message':str(exc), 'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0)
        result['reader_wall_seconds'] = time.monotonic() - started
        result['reader_peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        raw = (json.dumps(result, indent=2, allow_nan=False) + '\n').encode()
        require(len(raw) <= plan['maximum_output_bytes'], 'Readback output capacity exceeded')
        with OUT.open('xb') as f:
            f.write(raw)
        print(json.dumps({'result':identity(OUT),'completed':result['completed'],'failure':result.get('failure'),
                          'wall_seconds':result['reader_wall_seconds'],'peak_RSS_bytes':result['reader_peak_RSS_bytes']}))
    return 0 if result['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
