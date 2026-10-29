"""Read saved original profiles and the exact current factory q call chain.

This does not import any project/native module or run CAD, force, or contact
solvers.  It preserves the complete original compressed and decompressed
report, the four exact profile JSON byte spans, and bound source bytes.
"""
from pathlib import Path
import ast
import datetime
import gzip
import hashlib
import json
import math
import resource
import signal
import stat
import time
import traceback

BASE = Path(__file__).resolve().parent.parent
S4 = BASE / 'r7-native/genuine-s4-worktree-v3'
DRIVERS = BASE / 'r7-recovery/k3/source/k3full'
OUT = BASE / 'r7-audit/blocker-ledger/positive-q-source-readback'
WALL = 30
AS = 128 * 2**20
INPUT_CAP = 16 * 2**20
OUTPUT_CAP = 2 * 2**20
START = time.monotonic()
S4_NAMES = (
    'product_assembly.py', 'product_nominal_motion.py',
    'product_split_assembly.py', 'product_routing_ep5.py',
    'cam_contact_profile.py', 'verify_cam_coupling.py',
    'verify_pawl_actuator.py', 'verify_serviceable_pawl.py',
    'verify_endpoint_joint_pawl.py', 'verify_frame_nut_anchor.py',
    'verify_panel_shear_key.py', 'verify_cover_backing.py',
)
DRIVER_NAMES = ('full_factory_stops.py', 'frozen_key_factory_adapter.py',
                'full_stop_states.py', 'panel_key_travel_stops_v1.py')
PROFILE_REL = 'engineering/thin-mechanism-20261015/native-verification.json.gz'
REFS = {name: S4 / 'integration' / name for name in S4_NAMES}
REFS.update({name: DRIVERS / name for name in DRIVER_NAMES})
REFS.update({
    'original_profile_report': S4 / PROFILE_REL,
    'S4_source_contract': BASE / 'r7-native/R7_SETUP_INSTALL_ONLY_CONTRACT_V3.json',
    'near_actual_factory_report': BASE / 'r7-native/full-near-attempt1/factory/worker/report.json',
    'far_actual_factory_report': BASE / 'r7-native/full-far-attempt1/factory/worker/report.json',
})


class ReadBudgetExceeded(BaseException):
    pass


def need(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    need(stat.S_ISREG(path.lstat().st_mode), 'Expected a regular original source')
    value = path.read_bytes()
    need(len(value) == path.stat().st_size, 'Original length changed during read')
    return {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}


def emit(path, raw):
    need(not path.exists(), 'New immutable output required: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def literal_assignment(source, name):
    tree = ast.parse(source)
    values = [node.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)]
    need(len(values) == 1, 'Unique original assignment required: ' + name)
    return values[0]


def function_source(source, name):
    matches = [node for node in ast.walk(ast.parse(source))
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    need(len(matches) == 1, 'Unique original function required: ' + name)
    node = matches[0]
    return {'line_start': node.lineno, 'line_end': node.end_lineno,
            'exact_source_segment': ast.get_source_segment(source, node)}


def selected_json_spans(raw, targets):
    """Locate exact JSON value byte substrings without reserialization."""
    text = raw.decode('utf-8')
    decoder = json.JSONDecoder()
    spans = {}

    def ws(i):
        while i < len(text) and text[i] in ' \n\r\t':
            i += 1
        return i

    def walk(i, path):
        i = ws(i)
        begin = i
        if text[i] == '{':
            i = ws(i + 1)
            keys = set()
            while text[i] != '}':
                key, i = decoder.raw_decode(text, i)
                need(isinstance(key, str) and key not in keys, 'Duplicate/invalid original JSON key')
                keys.add(key)
                i = ws(i)
                need(text[i] == ':', 'Original JSON object colon missing')
                i = ws(walk(i + 1, path + (key,)))
                if text[i] == ',':
                    i = ws(i + 1)
                else:
                    need(text[i] == '}', 'Original JSON object delimiter missing')
            end = i + 1
        elif text[i] == '[':
            i = ws(i + 1)
            index = 0
            while text[i] != ']':
                i = ws(walk(i, path + (index,)))
                index += 1
                if text[i] == ',':
                    i = ws(i + 1)
                else:
                    need(text[i] == ']', 'Original JSON array delimiter missing')
            end = i + 1
        else:
            _, end = decoder.raw_decode(text, i)
        if path in targets:
            spans[path] = text[begin:end].encode('utf-8')
        return end

    end = ws(walk(0, ()))
    need(end == len(text) and set(spans) == targets, 'Original full JSON/profile span census differs')
    return spans


def run():
    identities = {key: {'workspace_relative_path': str(path.relative_to(BASE)), **identity(path)}
                  for key, path in REFS.items()}
    total = sum(value['bytes'] for value in identities.values())
    need(total <= INPUT_CAP, 'Registered original read input cap exceeded')
    source_contract = json.loads(REFS['S4_source_contract'].read_bytes())
    for name in S4_NAMES + ('original_profile_report',):
        path = REFS[name]
        expected = source_contract['expected_sources'][str(path.relative_to(S4))]
        need(identity(path) == expected, 'Exact actual S4 closure differs: ' + name)
    sources = {name: REFS[name].read_text() for name in S4_NAMES + DRIVER_NAMES}
    cam_source = sources['verify_cam_coupling.py']
    K_node = literal_assignment(cam_source, 'K')
    need(isinstance(K_node, ast.BinOp) and isinstance(K_node.op, ast.Div), 'Original K quotient differs')
    K = ast.literal_eval(K_node.left) / ast.literal_eval(K_node.right)
    need(ast.literal_eval(K_node.left) == 12 and ast.literal_eval(K_node.right) == 79.75, 'Original K numbers differ')
    R = ast.literal_eval(literal_assignment(cam_source, 'R'))
    G = ast.literal_eval(literal_assignment(cam_source, 'G'))
    TOL = ast.literal_eval(literal_assignment(sources['product_assembly.py'], 'TOL'))
    need((R, G, TOL) == (.4, .425, 1e-7), 'Source clearance/tolerance constants differ')
    states = ast.literal_eval(literal_assignment(sources['full_stop_states.py'], 'STATES'))
    original_gzip = REFS['original_profile_report'].read_bytes()
    with gzip.GzipFile(fileobj=__import__('io').BytesIO(original_gzip)) as stream:
        original_json = stream.read(OUTPUT_CAP + 1)
    need(len(original_json) <= OUTPUT_CAP, 'Original decompression exceeds registered bound')
    old_report = json.loads(original_json)
    targets = {('sides', side, 'contacts', index, 'profile') for side in 'LR' for index in (0, 1)}
    profile_spans = selected_json_spans(original_json, targets)
    profiles = {side: [row['profile'] for row in old_report['sides'][side]['contacts']] for side in 'LR'}
    need(all(len(profiles[side]) == 2 for side in 'LR'), 'Exactly four original profiles required')
    for side in 'LR':
        for index, profile in enumerate(profiles[side]):
            need(json.loads(profile_spans[('sides', side, 'contacts', index, 'profile')]) == profile, 'Original profile span differs')
            a, b, c = profile['breakpoints_q_mm']
            need(0 < a < b < c < profile['q_max'] == 12.0, 'Original four-branch ordering differs')
            need(profile['pin_q'] == 0.0 and profile['selected_branch_requires_lower_restoring_force']
                 and not profile['dynamic_force_friction_and_material_qualification'], 'Original contact law scope differs')
    checks = {
        'full_factory_stops.py': ["baseline,meta=adapter.full_scene(keys,nominal,cam,p,**spec)",
                                  "q={side:cam.K*spec['slide']+offset for side,offset in zip('LR',spec['key_offsets'])}"],
        'frozen_key_factory_adapter.py': ["parts,metadata=nominal.full_scene(slide,descent,left_tab,right_tab,**kwargs)",
                                         "q=cam.K*actual['slide_mm']+dq", "translate((0,q,0))"],
        'product_nominal_motion.py': ["baseline,meta=split.split_scene(slide,descent,left_tab,right_tab,**kwargs)"],
        'product_split_assembly.py': ["p.product_scene(slide_mm, descent_mm, left_tab_mm, right_tab_mm, **kwargs)"],
        'product_assembly.py': ["q=cam.K*slide_mm+dq", "profile.evaluate(q)",
                                "state=e.scene(parts,parent,prior,old,profiles,slots,slide_mm,descent_mm,tabs,flanks=flanks)",
                                "if allocations[side] is not None or dq or dx:",
                                "delta=profile.evaluate(q)[0]-profile.evaluate(0)[0]"],
        'verify_endpoint_joint_pawl.py': ["p=v.scene(new,parent,prior,old,profiles,slide,descent,tabs)"],
        'verify_serviceable_pawl.py': ["parts=w.scene(parent,prior,old,profiles,s,d,tabs)",
                                       "prior,old,profiles=w.prior_native(h, verified_mounted_members=verified_mounted_members)"],
        'verify_pawl_actuator.py': ["parts=v.scene(prior,old,profiles,s,d)",
                                   "f=ROOT/'engineering/thin-mechanism-20261015/native-verification.json.gz'"],
        'verify_cam_coupling.py': ["pr=prototype(p,s,d);q=K*s", "profile.evaluate(q)[0]-profile.evaluate(0)[0]",
                                  "cq.Solid.makeCylinder(.43,high-low"],
        'cam_contact_profile.py': ["a,b,c=self.breakpoints;x=self.pin_q-q",
                                   "if q>=c:return self.lower_stop_height,0.,'lower_stop'",
                                   "if q>=b:return self.intercept+self.ramp_slope*x,-self.ramp_slope,'ramp'",
                                   "if q<=a:return self.floor_height+self.pin_radius,0.,'plateau'"],
    }
    for name, fragments in checks.items():
        need(all(fragment in sources[name] for fragment in fragments), 'Original source call-chain fragment differs: ' + name)
    pose_records = {}
    for pose in ('near', 'far'):
        report = json.loads(REFS[pose + '_actual_factory_report'].read_bytes())
        need(report['execution_completed'] and report['finite_pose_clear'], 'Completed original finite pose required')
        metadata = report['native_scene_metadata']['scene']
        spec = report['pose_input']
        expected_spec = {key: value for key, value in states[pose].items()
                         if key not in ('expected_bodies', 'actual_binary64_q_from_declared_factory_inputs')}
        need(spec == expected_spec, 'Actual pose inputs differ from original registered state')
        need(metadata['source_inputs'][PROFILE_REL] == identities['original_profile_report']['sha256'], 'Actual profile source identity differs')
        for name in S4_NAMES + ('original_profile_report',):
            need(report['identity_before']['available_source_sha256'][str(REFS[name])] == identities[name]['sha256'],
                 'Actual factory S4 source binding differs: ' + name)
        for name in DRIVER_NAMES:
            need(report['external_source_sha256'][str(REFS[name])] == identities[name]['sha256'],
                 'Actual factory external driver binding differs: ' + name)
        need(metadata['slide_mm'] == spec['slide'] and metadata['KEY_offsets_mm'] == spec['key_offsets'], 'Actual slide/dq mapping differs')
        need(spec['key_offsets'] == [0.0, 0.0] and spec['crosshead_offsets'] == [0.0, 0.0]
             and spec['telescope_offsets'] is None, 'This original pose no longer follows the nominal branch')
        q_by_side = {side: K * spec['slide'] + dq for side, dq in zip('LR', spec['key_offsets'])}
        need(q_by_side == report['actual_q_by_side_mm'], 'Original q operation/result differs')
        selected = {}
        for side in 'LR':
            q = q_by_side[side]
            mapped = report['native_scene_metadata']['named_KEY_candidate']['current_factory_KEY_material_comparisons'][side + '_KEY']
            need(mapped['actual_q_mm'] == q and mapped['actual_q_binary64_hex'] == q.hex(), 'Actual KEY translation q mapping differs')
            selected[side] = []
            for index, profile in enumerate(profiles[side]):
                a, b, c = profile['breakpoints_q_mm']
                need(c <= q <= profile['q_max'], 'Saved actual q does not select the original lower_stop branch')
                h0 = profile['floor_height'] + profile['pin_radius']
                delta = profile['lower_stop_height'] - h0
                selected[side].append({'contact_index': index, 'q_mm': q, 'q_binary64_hex': q.hex(),
                    'internal_x_equal_pin_q_minus_q_mm': profile['pin_q'] - q,
                    'stored_original_lower_stop_breakpoint_q_mm': c,
                    'selected_source_branch': 'lower_stop',
                    'branch_selection_is_program_semantics_not_actual_contact_or_reachability': True,
                    'source_height_mm': profile['lower_stop_height'], 'source_reference_height_at_q0_mm': h0,
                    'derived_binary64_delta_height_mm': delta,
                    'derived_binary64_STOP_X_translation_mm': (-1 if side == 'L' else 1) * delta,
                    'actual_force_preload_or_contact_proved_by_this_read': False})
        pose_records[pose] = {'original_pose_input': spec, 'actual_scene_q_inputs': {
            'slide_mm': metadata['slide_mm'], 'KEY_offsets_mm': metadata['KEY_offsets_mm'],
            'crosshead_offsets_mm': metadata['crosshead_offsets_mm']},
            'actual_factory_q_by_side_mm': report['actual_q_by_side_mm'],
            'actual_profile_gzip_sha256': metadata['source_inputs'][PROFILE_REL],
            'nominal_source_call_path_used_by_these_zero_offset_inputs': True,
            'current_named_KEY_rigid_translation_uses_same_q': True,
            'program_branch_selections': selected}
    profile_rows = []
    for side in 'LR':
        for index, profile in enumerate(profiles[side]):
            a, b, c = profile['breakpoints_q_mm']
            profile_rows.append({'side': side, 'contact_index': index, 'complete_original_profile_values': profile,
                'exact_original_JSON_span_path': f'originals/profiles/{side}_contact{index}.profile.original.json',
                'positive_q_intervals': [
                    {'branch': 'plateau', 'lo': 0.0, 'hi': a, 'lo_inclusive': False, 'hi_inclusive': True,
                     'height_expression': 'floor_height + pin_radius'},
                    {'branch': 'rounded_corner', 'lo': a, 'hi': b, 'lo_inclusive': False, 'hi_inclusive': False,
                     'height_expression': 'floor_height + sqrt(pin_radius**2 - (pin_q-q-floor_corner_q)**2)'},
                    {'branch': 'ramp', 'lo': b, 'hi': c, 'lo_inclusive': True, 'hi_inclusive': False,
                     'height_expression': 'intercept + ramp_slope*(pin_q-q)'},
                    {'branch': 'lower_stop', 'lo': c, 'hi': profile['q_max'], 'lo_inclusive': True, 'hi_inclusive': True,
                     'height_expression': 'lower_stop_height'},
                ], 'q_zero_reference_selects_plateau': True,
                'outside_q0_to_qmax_source_rejects_without_clamping': True})
    excerpt_names = {
        'full_factory_stops.py': ('main',), 'frozen_key_factory_adapter.py': ('full_scene',),
        'product_nominal_motion.py': ('full_scene',), 'product_split_assembly.py': ('split_scene',),
        'product_routing_ep5.py': ('apply_scene_relief',),
        'product_assembly.py': ('native_inputs', 'native_scene', 'product_scene', 'b_transform'),
        'verify_serviceable_pawl.py': ('parent_native', 'scene'),
        'verify_pawl_actuator.py': ('prior_native', 'scene'),
        'verify_endpoint_joint_pawl.py': ('scene',),
        'verify_cam_coupling.py': ('scene',),
        'cam_contact_profile.py': ('intercept', 'breakpoints', 'evaluate', 'receipt'),
    }
    excerpts = {name: {func: function_source(sources[name], func) for func in funcs}
                for name, funcs in excerpt_names.items()}
    planned_outputs = {
        'originals/native-verification.original.json.gz': original_gzip,
        'originals/native-verification.original.json': original_json,
    }
    planned_outputs.update({'originals/source/' + name: REFS[name].read_bytes() for name in S4_NAMES + DRIVER_NAMES})
    planned_outputs.update({f'originals/profiles/{side}_contact{index}.profile.original.json': profile_spans[('sides', side, 'contacts', index, 'profile')]
                            for side in 'LR' for index in (0, 1)})
    result = {
        'schema': 'razr-r7-original-positive-q-profile-and-current-factory-source-mapping-v1',
        'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Exact original byte readback and source/program-semantics mapping only.',
        'new_CAD_project_import_force_contact_or_motion_execution': False,
        'registered_limits': {'wall_seconds': WALL, 'address_space_bytes': AS,
                              'original_input_bytes': INPUT_CAP, 'new_output_bytes': OUTPUT_CAP},
        'functional_source_commit': 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560',
        'source': {'workspace_relative_path': str(Path(__file__).resolve().relative_to(BASE)), **identity(Path(__file__))},
        'inputs': identities, 'original_input_bytes': total,
        'complete_original_gzip_and_decoded_JSON_and_four_exact_profile_spans_preserved': True,
        'four_profiles': profile_rows,
        'left_and_right_original_profiles_are_value_equal': profiles['L'] == profiles['R'],
        'contact0_contact1_lower_stop_breakpoints_kept_distinct': profiles['L'][0]['breakpoints_q_mm'][2] != profiles['L'][1]['breakpoints_q_mm'][2],
        'q_coordinate_definition': {
            'factory_input': 'q_side = cam.K * slide_mm + KEY_offset_side_mm',
            'K_original_source_expression': '12/79.75', 'K_actual_binary64': K, 'K_actual_binary64_hex': K.hex(),
            'profile_evaluate_argument': 'The same q_side is passed to ContactProfile.evaluate; it is not x.',
            'profile_internal_coordinate': 'x = pin_q - q_side; all four original pin_q values are 0.',
            'KEY_whole_material_mapping': 'Frozen adapter compares original KEY translated by (0,-q,0) to q0 material and places candidate q0 KEY at (0,q,0).',
            'caller_forwarding_chain': ['full_factory_stops.main', 'frozen_key_factory_adapter.full_scene',
                'product_nominal_motion.full_scene', 'product_split_assembly.split_scene',
                'product_assembly.product_scene', 'product_assembly.native_scene'],
            'profile_construction_chain': ['product_assembly.native_inputs',
                'verify_frame_nut_anchor.e (through verify_panel_shear_key.e and verify_cover_backing.e) = verify_endpoint_joint_pawl',
                'verify_endpoint_joint_pawl.v = verify_serviceable_pawl',
                'verify_serviceable_pawl.parent_native -> verify_pawl_actuator.prior_native',
                'gzip original native-verification -> exact four ContactProfile constructor field values'],
        },
        'STOP_SPRING_source_dependency': {
            'nominal_zero_offset_call_chain': ['product_assembly.native_scene -> verify_endpoint_joint_pawl.scene',
                'verify_endpoint_joint_pawl.scene -> verify_serviceable_pawl.scene',
                'verify_serviceable_pawl.scene -> verify_pawl_actuator.scene',
                'verify_pawl_actuator.scene -> verify_cam_coupling.scene',
                'verify_cam_coupling.scene: q=K*s; delta=profile.evaluate(q)[0]-profile.evaluate(0)[0]'],
            'explicit_offset_or_allocation_branch': 'product_assembly.native_scene overrides each side when allocation is not None or dq or dx; evaluates q=cam.K*slide_mm+dq.',
            'STOP_geometry': 'old[side_STOP_i].translate((sign*delta,0,0)); sign=-1 for L,+1 for R.',
            'SPRING_geometry': 'A radius .43 mm cylinder along +X; xlo=old_xmin+min(0,sign*delta), xhi=old_xmax+max(0,sign*delta), length=xhi-xlo; Y/Z center from old bounding box.',
            'SPRING_object_is_outer_diameter_tolerance_envelope': True,
            'actual_spring_free_length_preload_stiffness_force_direction_or_loss_of_contact_established_here': False,
            'nominal_function_uses_BoundingBox_and_offset_override_uses_bounds': True,
            'all_four_original_profiles_require_lower_restoring_force': True,
            'lower_stop_C0_not_C1_source_qualification_only': True,
            'new_actual_native_contact_or_force_readback_run': False,
        },
        'source_defined_independent_input_domain_not_physical_allowed_domain': {
            'slide_descent': '0<=slide<=79.75;0<=descent<=8.2; descent>0 requires slide==79.75.',
            'manual_tabs': 'Independent L/R each [0,3] mm.',
            'slot_flanks': 'Independent L/R each [-1,1].',
            'KEY_and_crosshead_offsets': 'Independent side pairs (dq,dx) subject to abs(dx)<=(G-R)*hypot(1,K)+TOL and abs(dx-dq)<=(G-R)*sqrt(2)+TOL.',
            'R_mm': R, 'G_mm': G, 'TOL_mm': TOL,
            'profile_restriction': 'For both contacts on each side, every q=K*slide+dq must lie in [0,12]; no clamping.',
            'telescope': 'Independent L/R triples; each .1-TOL<=j<=2.9+TOL; abs(sum(j)-8.5+descent)<=TOL.',
            'nominal_telescope_choice': 'When unspecified, three equal .1+(8.2-descent)/3 values per side; source explicitly says not physically enforced.',
            'OPEN_accessories': 'Hold/support flags Boolean; either true requires slide==79.75 and descent==8.2.',
            'K1_K3_adapter_reduces_independent_controls': False,
            'true_physical_allowed_domain_force_preload_and_reachability_proved': False,
            'binary64_input_acceptance_equals_mathematical_or_physical_domain_proved': False,
        },
        'two_actual_pose_report_mappings': pose_records,
        'exact_source_function_segments': excerpts,
        'new_continuous_G2_strength_manufacturing_or_G3_G5_qualification': False,
        'all_blockers_closed': False,
    }
    for name, original in identities.items():
        need(identity(REFS[name]) == {k: original[k] for k in ('bytes', 'sha256')}, 'Original source/report changed during read')
    result['all_original_inputs_unchanged_before_after'] = True
    result['preserved_original_output_identities'] = {rel: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                                                     for rel, raw in planned_outputs.items()}
    result['seconds'] = time.monotonic() - START
    result['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    raw_report = (json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    planned_outputs['R7_POSITIVE_Q_SOURCE_AND_FACTORY_MAPPING_READBACK_V1.json'] = raw_report
    need(sum(len(raw) for raw in planned_outputs.values()) <= OUTPUT_CAP, 'Complete preserved output cap exceeded')
    for rel, raw in planned_outputs.items():
        emit(OUT / rel, raw)
    for rel, raw in planned_outputs.items():
        need((OUT / rel).read_bytes() == raw, 'New copied original/output differs on readback')
    manifest = {'schema': 'razr-r7-positive-q-source-readback-complete-output-manifest-v1',
                'completed': True, 'all_original_inputs_unchanged_before_after': True,
                'outputs': {rel: identity(OUT / rel) for rel in sorted(planned_outputs)},
                'new_scientific_qualification': False, 'all_blockers_closed': False,
                'seconds': time.monotonic() - START}
    emit(OUT / 'MANIFEST.json', (json.dumps(manifest, indent=2) + '\n').encode())
    print(json.dumps({'report': identity(OUT / 'R7_POSITIVE_Q_SOURCE_AND_FACTORY_MAPPING_READBACK_V1.json'),
                      'manifest': identity(OUT / 'MANIFEST.json'), 'preserved_output_files': len(planned_outputs),
                      'preserved_output_bytes': sum(len(raw) for raw in planned_outputs.values()),
                      'seconds': manifest['seconds'], 'peak_RSS_bytes': result['peak_RSS_bytes']}))


def main():
    resource.setrlimit(resource.RLIMIT_AS, (AS, AS))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(ReadBudgetExceeded('Registered source read budget exceeded')))
    signal.alarm(WALL)
    try:
        run()
        return 0
    except BaseException as exc:
        record = {'schema': 'razr-r7-positive-q-source-read-attempt1-actual-failure-v1',
                  'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc(),
                  'original_inputs_modified': False, 'new_CAD_force_or_solver_execution': False,
                  'source': identity(Path(__file__)), 'seconds': time.monotonic() - START}
        emit(OUT / 'ATTEMPT1_ACTUAL_FAILURE.json', (json.dumps(record, indent=2) + '\n').encode())
        print(json.dumps(record))
        return 2
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    raise SystemExit(main())
