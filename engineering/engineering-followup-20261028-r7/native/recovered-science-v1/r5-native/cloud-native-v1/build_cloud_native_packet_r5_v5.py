"""Build a reviewed cloud submission without executing CAD or publishing Git.

The original hosted harness and complete K3 driver creation step stay exact.
Original scientific inputs and workers are copied by identity into a compact
archive. Only runtime admission and concrete path registration are new.
"""
from pathlib import Path
import argparse
import ast
import copy
import datetime as dt
import gzip
import hashlib
import io
import json
import re
import shutil
import tarfile
import tomllib
import yaml


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
S4 = ROOT / 'recovered-inputs/RAZR-F1a-R2-near-fresh-native-complete-raw-evidence-20261027/functional-source'


def identity(path):
    data = Path(path).read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.exists(), 'New immutable build target required: ' + str(path))
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'publication-v1')
    parser.add_argument('--repository-directory', default='engineering/full-sprint-20261028-r5/cloud-native-v1')
    parser.add_argument('--trigger-branch', default='diagnostic/r5-native-fresh-20261028-v1')
    parser.add_argument('--argument-controls', type=Path, default=HERE / 'argument-controls-v2')
    args = parser.parse_args()
    out = args.output.resolve()
    require(not out.exists(), 'Fresh publication directory required')
    require(shutil.disk_usage(HERE).free >= 32 * 2**20, 'Bounded local packet construction reserve unavailable')
    out.mkdir()
    frozen = ROOT / 'r5-native/trim-core-witness/R5_NATIVE_TRIM_CORE_PRODUCER_CONTRACT.json'
    contract = json.loads(frozen.read_text())
    old_runtime = str(ROOT / 'r4-runtime') + '/'
    replaced = []
    science = copy.deepcopy(contract)
    for key in ('bound_records', 'bound_sources'):
        removed = [r for r in science[key] if r['path'].startswith(old_runtime)]
        replaced.extend({'old_role': key, **r} for r in removed)
        science[key] = [r for r in science[key] if not r['path'].startswith(old_runtime)]
    ascii_producer = ROOT / 'r5-native/trim-core-witness/native_trim_core_witness_r5_ascii_v2.py'
    ascii_reader = ROOT / 'r5-native/trim-core-witness/read_native_trim_core_witness_r5_ascii_v2.py'
    serialization = HERE / 'serialization-v1/R5_NATIVE_ASCII_BREP_REVISION_PREPARATION.json'
    format_controls_path = HERE / 'serialization-v1/dispatch-controls/R5_ASCII_BREP_DISPATCH_CONTROLS_ACTUAL.json'
    format_controls = json.loads(format_controls_path.read_text())
    require(format_controls['completed'] and len(format_controls['controls']) == 28 and not format_controls['blocked_native_import_attempts'] and not format_controls['native_numeric_modules_loaded'],
            'Actual complete stdlib ASCII format controls required')
    require({r['source']: r['source_identity'] for r in format_controls['source_comparisons']} == {ascii_producer.name: identity(ascii_producer), ascii_reader.name: identity(ascii_reader)},
            'Format controls do not cover these exact newly named native workers')
    science['worker_identity'] = identity(ascii_producer)
    science['independent_reader_source_identity'] = identity(ascii_reader)
    science['native_brep_serialization'] = 'OCCT_ASCII_BREP_V3'
    science['bound_sources'] += [{'path': str(p), 'identity': identity(p)} for p in (ascii_producer, ascii_reader)]
    science['bound_records'] += [{'path': str(p), 'identity': identity(p)} for p in (serialization, format_controls_path)]
    science['serialization_revision_changes_native_IO_only'] = True
    science['all_original_geometry_operator_call_ASTs_unchanged'] = all(x['all_geometry_operator_call_ASTs_equal'] for x in format_controls['source_comparisons'])
    science['capacity']['ASCII_output_capacity_basis'] = {
        'all_six_original_ASCII_input_bytes': 1225201,
        'same_original_20MiB_per_worker_output_cap': 20971520,
        'same_original_64MiB_campaign_cap': 67108864,
        'basis': 'Six actual complete ASCII input bodies total1,225,201 bytes; four additional full mapped panels and finite face/patch/common exports remain bounded by the original20 MiB per-worker cap. No native output-size success is assumed before actual execution.',
        'output_format_changes_to_match_the_originals': 'OCCT_ASCII_BREP_V3',
        'any_unknown_format_or_native_null_read_is_unresolved_failure': True}
    members = {str(Path(row['path']).relative_to(ROOT)): row['identity'] for key in ('bound_records', 'bound_sources') for row in science[key]}
    for path in (frozen, ROOT / 'r4-native/recovered/native/source/supervise_native_r3.py'):
        members[str(path.relative_to(ROOT))] = identity(path)
    control_root = args.argument_controls.resolve()
    control_path = control_root / 'R5_CLOUD_ARGUMENT_CONTROLS_ACTUAL.json'
    controls = json.loads(control_path.read_text())
    require(controls['completed'] and controls['sources_unchanged'] and len(controls['controls']) == 17,
            'Actual complete stdlib argument denial controls required')
    require(controls['entry'] == identity(HERE / 'run_fresh_runtime_script_r5.py') and controls['qualifier'] == identity(HERE / 'qualify_fresh_runtime_r5.py'),
            'Argument controls do not cover the exact entry and qualifier being published')
    for path in [Path(__file__), HERE / 'check_cloud_argument_binding_r5.py', *sorted(control_root.rglob('*'))]:
        if path.is_file():
            members[str(path.relative_to(ROOT))] = identity(path)
    for path in [HERE / 'prepare_ascii_native_revision_r5.py', HERE / 'prepare_ascii_native_revision_r5_v2.py', HERE / 'check_ascii_brep_dispatch_r5.py', *sorted((HERE / 'serialization-v1').rglob('*'))]:
        if path.is_file():
            members[str(path.relative_to(ROOT))] = identity(path)
    bootstrap_report = HERE / 'bootstrap-v5/R5_BOOTSTRAP_V5_CONTROLS_ACTUAL.json'
    bootstrap = json.loads(bootstrap_report.read_text())
    require(bootstrap['completed'] and bootstrap['new_registrar_identity'] == identity(HERE / 'register_cloud_native_r5_bootstrap_v5.py'), 'Exact actual v5 bootstrap controls required')
    for path in [HERE / 'prepare_bootstrap_revision_r5_v5.py', HERE / 'register_cloud_native_r5_bootstrap_v5.py', HERE / 'build_cloud_native_packet_r5_v4_frozen.py', HERE / 'check_bootstrap_compatibility_r5_v5.py', *sorted((HERE / 'bootstrap-v5').rglob('*'))]:
        if path.is_file():
            members[str(path.relative_to(ROOT))] = identity(path)
    forbidden = {
        'library_transfer_identifier': re.compile(rb'(?:libfile_|file-inline-libfile_)[A-Za-z0-9_-]{12,}|(?:library-file:|oai-library:)[A-Za-z0-9/_-]{8,}'),
        'credential_token': re.compile(rb'(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_]{12,}'),
        'signed_transfer_URL': re.compile(rb'https?://[^\s\"\']+[?&](?:sig|token|X-Amz-Signature|X-Goog-Signature)='),
    }
    for relative, expected in members.items():
        path = ROOT / relative
        require(identity(path) == expected and path.is_file() and not path.is_symlink(), 'Original source/input changed before packaging')
        data = path.read_bytes()
        if relative.endswith('.gz'):
            data = gzip.decompress(data)
        if not relative.endswith('.brep'):
            require(not any(pattern.search(data) for pattern in forbidden.values()), 'Excluded credential, signed transfer URL or Library identifier in packet member: ' + relative)
        if relative.endswith('.py'):
            ast.parse(data.decode())
    raw_bytes = sum(r['bytes'] for r in members.values())
    require(raw_bytes <= 8 * 2**20, 'Original 8 MiB scientific source/control reserve exceeded before execution')
    packet = out / 'scientific-inputs.tar.gz'
    with packet.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as gz, tarfile.open(fileobj=gz, mode='w') as archive:
        for relative in sorted(members):
            data = (ROOT / relative).read_bytes()
            info = tarfile.TarInfo(relative)
            info.size = len(data)
            info.mode = 0o444
            info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
    write(out / 'SCIENTIFIC_INPUT_MANIFEST.json', {
        'schema': 'razr-r5-cloud-exact-scientific-input-manifest-v1', 'members': members,
        'member_count': len(members), 'uncompressed_bytes': raw_bytes, 'archive_identity': identity(packet),
        'original_scientific_bytes_preserved': True,
        'historical_random_workspace_paths_preserved_as_original_evidence': True,
        'actual_current_input_access_uses_new_contract_root': True,
        'historical_absolute_paths_not_used_as_cloud_input_locators': True,
        'explicit_credential_signed_URL_and_Library_identifier_scan_passed': True})
    original_execution = json.loads((ROOT / 'r5-native/trim-core-witness/R5_NATIVE_TRIM_CORE_PRODUCER_EXECUTION_CONTRACT.json').read_text())
    lock = tomllib.loads((S4 / 'uv.lock').read_text())
    largest_wheel = max(w['size'] for p in lock['package'] for w in p.get('wheels', []))
    runtime_basis = {
        'algorithm': 'New uv 0.10.10 sync --locked --no-cache in genuine S4 Python 3.12.14 venv; then verify every selected original locked wheel SHA/size, wheel RECORD, actual installed payload, all 43 installed RECORDs, actual import/namespace probes and full venv before/after inventory under unchanged native supervisor.',
        'old_R4_pass_not_admission': True, 'wheel_verification_streamed_downloads_sequential': True,
        'largest_wheel_in_entire_actual_S4_lock_bytes': largest_wheel,
        'transient_single_wheel_hard_cap_bytes': 268435456,
        'prior_actual_43_payload_reference_bytes_not_new_runtime_identity': 1226421880,
        'hosted_setup_minimum_available_bytes': 4 * 2**30,
        'estimated_qualification_seconds': [90, 240], 'estimated_peak_RSS_bytes': [450000000, 838860800],
        'basis': 'Original hosted install +43 version check+native box preflight took 9 s near /11 s far. Additional sequential locked-wheel reread and whole installed-file verification has an estimated 90–240 s budget; network/kernel success is not guaranteed. The original1200 s/1536 MiB/shared/disk limits remain hard gates.',
        'maximum_qualification_report_bytes': 6291456, 'maximum_qualification_output_bytes': 8388608,
        'maximum_core_runtime_receipts_total_bytes': 16777216,
        'study_native_worker_not_started_before_this_new_qualification_completes': True,
        'native_import_probes_are_part_of_the_separately_supervised_runtime_qualification': True}
    write(out / 'R5_CLOUD_NATIVE_SCIENCE_TEMPLATE.json', {
        'schema': 'razr-r5-cloud-native-science-template-v1', 'original_local_contract_identity': identity(frozen),
        'original_workspace_root': str(ROOT), 'science_contract': science,
        'science_worker_paths': {'producer': str(ascii_producer.relative_to(ROOT)), 'reader': str(ascii_reader.relative_to(ROOT))},
        'native_IO_revision_receipt': {'relative': str(serialization.relative_to(ROOT)), **identity(serialization)},
        'historical_admission_bindings_replaced': replaced,
        'original_resource_limits': original_execution['resource_limits'],
        'locked_project_inputs': {name: identity(S4 / name) for name in ('pyproject.toml', 'uv.lock')},
        'fresh_runtime_capacity_basis': runtime_basis,
        'scientific_algorithm_or_original_geometry_or_acceptance_thresholds_changed': False})
    for name in ('qualify_fresh_runtime_r5.py', 'run_fresh_runtime_script_r5.py', 'register_cloud_native_r5.py'):
        source = HERE / ('register_cloud_native_r5_bootstrap_v5.py' if name == 'register_cloud_native_r5.py' else name)
        ast.parse(source.read_text())
        shutil.copyfile(source, out / name)
    historical = HERE / 'historical/s4-panel-key-stop-k3full-hosted.yml'
    w = yaml.safe_load(historical.read_text())
    steps = w['jobs']['full']['steps']
    original_setup = steps[2]['run']
    # Keep the exact driver-generation/identity/harness step; source identities
    # are independently checked by that original step on the real hosted S4.
    initialize = copy.deepcopy(steps[0])
    initialize['run'] = initialize['run'].replace('razr-s4-panel-key-stop-k3full-20261026', 'razr-r5-new-native-20261028-v1')
    asset_checkout = {'name': 'Checkout reviewed current cloud sources separately from immutable S4',
                      'uses': steps[1]['uses'], 'with': {'ref': '${{ github.sha }}', 'persist-credentials': False,
                      'path': '.r5-cloud-assets', 'sparse-checkout-cone-mode': False,
                      'sparse-checkout': '/' + args.repository_directory + '/\n/.github/workflows/r5-native-fresh-hosted-v1.yml'}}
    asset_move = {'name': 'Move genuine diagnostic checkout outside S4 and bind current asset identities', 'shell': 'bash',
                  'run': 'set -euo pipefail\nmv "$GITHUB_WORKSPACE/.r5-cloud-assets" "$HOST_ROOT/campaign-source"\n'
                         + 'test -z "$(git status --porcelain --untracked-files=all)"\n'
                         + 'R5_ASSETS="$HOST_ROOT/campaign-source/' + args.repository_directory + '"\n'
                         + 'echo "R5_ASSETS=$R5_ASSETS" >> "$GITHUB_ENV"\n'
                         + 'python3 -B "$R5_ASSETS/register_cloud_native_r5.py" verify-submission --assets "$R5_ASSETS"\n'}
    install = copy.deepcopy(steps[5])
    cut = install['run'].index('/usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/CAD-runtime-preflight"')
    install['run'] = install['run'][:cut]
    install['name'] = 'Fresh S4 uv locked install and all43 version checks before new artifact/namespace qualification'
    qualify = {'name': 'Qualify this actual new runtime under unchanged native gates before study CAD', 'shell': 'bash',
               'run': 'set -euo pipefail\npython3 -B "$R5_ASSETS/register_cloud_native_r5.py" register qualify --assets "$R5_ASSETS"\n'
                      'python3 -B "$R5_ASSETS/register_cloud_native_r5.py" execute "$CASE_DIR/qualify-command.json"\n'}
    prefix = [initialize, copy.deepcopy(steps[1]), copy.deepcopy(steps[2]), copy.deepcopy(steps[3]),
              asset_checkout, asset_move, copy.deepcopy(steps[4]), install, qualify]
    preserve = copy.deepcopy(steps[10])
    seal = {'name': 'Seal complete raw evidence and original finite scientific budget without reclassifying results',
            'if': 'always()', 'shell': 'bash',
            'run': 'set -euo pipefail\nif test -n "${R5_ASSETS:-}" && test -f "$R5_ASSETS/register_cloud_native_r5.py"; then\n'
                   ' python3 -B "$R5_ASSETS/register_cloud_native_r5.py" seal --assets "$R5_ASSETS"\nfi\n'}
    raw_upload = {'name': 'Preserve actual original inputs, native operands/results, raw controllers and new runtime evidence',
                  'if': 'always()', 'uses': steps[12]['uses'], 'with': {
                      'name': 'R5-fresh-native-${{ env.CASE_KEY }}-${{ github.run_id }}-${{ github.run_attempt }}-complete-raw',
                      'path': '${{ env.CASE_DIR }}\n${{ env.HOST_ROOT }}/native-science\n${{ env.HOST_ROOT }}/campaign-source/' + args.repository_directory,
                      'if-no-files-found': 'error', 'include-hidden-files': False, 'retention-days': 14}}
    core_steps = copy.deepcopy(prefix)
    for phase, name in (('core-producer', 'Execute unchanged80 original cores +8 controls and gated current K3 mappings'),
                        ('core-reader', 'Independently reread every exact BREP and repeat all eligible native operations')):
        core_steps.append({'name': name, 'shell': 'bash', 'run':
            'set -euo pipefail\npython3 -B "$R5_ASSETS/register_cloud_native_r5.py" register ' + phase + ' --assets "$R5_ASSETS"\n'
            'python3 -B "$R5_ASSETS/register_cloud_native_r5.py" execute "$CASE_DIR/' + phase + '-command.json"\n'})
    core_steps += [copy.deepcopy(preserve), copy.deepcopy(seal), copy.deepcopy(raw_upload)]
    full_steps = copy.deepcopy(prefix)
    for i in (6, 7):
        step = copy.deepcopy(steps[i])
        step['with']['path'] = step['with']['path'].replace('razr-s4-panel-key-stop-k3full-20261026', 'razr-r5-new-native-20261028-v1')
        full_steps.append(step)
    full_steps.append(copy.deepcopy(steps[8]))
    full_steps.append({'name': 'Fresh complete S4 K3 factory followed by original independent all-pair reader', 'shell': 'bash', 'run':
        'set -euo pipefail\nfactory_exit=0\n'
        'python3 -B "$R5_ASSETS/register_cloud_native_r5.py" register full-factory --assets "$R5_ASSETS"\n'
        'python3 -B "$R5_ASSETS/register_cloud_native_r5.py" execute "$CASE_DIR/full-factory-command.json" || factory_exit=$?\n'
        'echo "$factory_exit" > "$CASE_DIR/factory-supervisor.exit-code.txt"\n'
        'reader_exit=not_executed\n'
        'if python3 -B "$R5_ASSETS/register_cloud_native_r5.py" register full-reader --assets "$R5_ASSETS"; then\n'
        ' reader_exit=0\n'
        ' python3 -B "$R5_ASSETS/register_cloud_native_r5.py" execute "$CASE_DIR/full-reader-command.json" || reader_exit=$?\n'
        'fi\necho "$reader_exit" > "$CASE_DIR/readback-supervisor.exit-code.txt"\n'
        'python3 -B "$HOST_ROOT/k3full/verify_k3full_complete.py" --case "$CASE_DIR" --pose "$POSE"\n'
        'test "$factory_exit" = 0 && test "$reader_exit" = 0\n'})
    full_steps += [copy.deepcopy(preserve), copy.deepcopy(steps[11]), copy.deepcopy(seal)]
    engineering_upload = copy.deepcopy(steps[12])
    engineering_upload['with']['name'] = 'R5-fresh-K3FULL-${{ matrix.pose }}-${{ github.run_id }}-${{ github.run_attempt }}-engineering'
    engineering_upload['with']['path'] = engineering_upload['with']['path'].replace('razr-s4-panel-key-stop-k3full-20261026', 'razr-r5-new-native-20261028-v1')
    full_steps += [engineering_upload, copy.deepcopy(raw_upload)]
    guard = "github.repository == 'TrillionniumFoundation/RAZR-SLIDE' && github.ref == 'refs/heads/" + args.trigger_branch + "'"
    workflow = {'name': 'R5 new-qualified runtime finite80-core witness then fresh S4 near/far full factories',
                'on': {'push': {'branches': [args.trigger_branch], 'paths': [args.repository_directory + '/RUN_REQUEST.json']}, 'workflow_dispatch': None},
                'permissions': {'contents': 'read', 'actions': 'read'},
                'concurrency': {'group': 'r5-new-native-${{ github.ref }}', 'cancel-in-progress': False},
                'env': copy.deepcopy(w['env']), 'jobs': {
                    'core': {'name': 'R5 finite native80 cores with same-job new runtime qualification', 'if': '${{ ' + guard + ' }}', 'runs-on': 'ubuntu-22.04',
                             'timeout-minutes': 60, 'env': {'CASE_KIND': 'core', 'CASE_KEY': 'native80'}, 'steps': core_steps},
                    'full': {'name': 'R5 genuine new S4 K3 complete factory +all pairs: ${{ matrix.pose }}',
                             'needs': 'core', 'if': '${{ !cancelled() && ' + guard + ' }}', 'runs-on': 'ubuntu-22.04', 'timeout-minutes': 60,
                             'strategy': {'fail-fast': False, 'max-parallel': 1, 'matrix': {'pose': ['near', 'far']}},
                             'env': {'CASE_KIND': 'factory', 'CASE_KEY': '${{ matrix.pose }}', 'POSE': '${{ matrix.pose }}'},
                             'steps': full_steps}}}
    name = 'r5-native-fresh-hosted-v1.yml'
    (out / name).write_text(yaml.safe_dump(workflow, sort_keys=False, allow_unicode=True, width=110))
    reload = yaml.safe_load((out / name).read_text())
    require(reload['jobs']['core']['steps'][2]['run'] == original_setup and reload['jobs']['full']['steps'][2]['run'] == original_setup, 'Original native source/harness generation changed')
    for job in reload['jobs'].values():
        require(job['steps'][3]['run'] == steps[3]['run'], 'Original INT/TERM lifecycle probes changed')
        for step in job['steps']:
            if 'run' in step:
                require('CAD-runtime-preflight' not in step.get('name', ''), 'Old unqualified CAD preflight retained')
    historical_capacity = json.loads((ROOT / 'r5-native/trim-core-witness/R5_HISTORICAL_K3_NATIVE_CAPACITY_REFERENCE.json').read_text())
    historical_output = json.loads((ROOT / 'r5-native/trim-core-witness/R5_HISTORICAL_K3_STAGE_OUTPUT_CAPACITY.json').read_text())
    write(out / 'R5_CLOUD_NATIVE_EXECUTION_PLAN_V1.json', {
        'schema': 'razr-r5-new-qualified-cloud-native-plan-v1', 'registered_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'new_execution_claimed': False, 'repository_directory': args.repository_directory,
        'trigger_branch': args.trigger_branch, 'workflow_identity': identity(out / name),
        'original_historical_workflow_identity': identity(historical), 'original_historical_workflow_commit': '566197a97ee137ce4a58097656eb4fd6bc084b05',
        'original_historical_run_id': 40285103942, 'functional_source_commit': 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560',
        'functional_source_tree': 'cdd9e2c41216201b6cd04dd610d45fde80499045',
        'genuine_new_uv_venv_not_fake_local_projection': True, 'runtime_qualification': runtime_basis,
        'original_six_native_gates_unchanged': original_execution['resource_limits'],
        'original_INT_TERM_and_actual_service_cgroup_harness_bytes_unchanged': True,
        'original_geometry_algorithms_thresholds_and_complete_pair_drivers_unchanged': True,
        'bootstrap_portable_hash_actual_stdlib_controls': bootstrap,
        'bootstrap_control_report_member': str(bootstrap_report.relative_to(ROOT)),
        'bootstrap_control_report_identity': identity(bootstrap_report),
        'v4_actual_bootstrap_failure_retained': True,
        'always_environment_success_assertions_preserved_exactly': True,
        'strict_entry_qualifier_argument_binding_actual_stdlib_controls': controls,
        'strict_argument_controls_report_member': str(control_path.relative_to(ROOT)),
        'strict_argument_controls_report_identity': identity(control_path),
        'native_IO_format_revision': json.loads(serialization.read_text()),
        'native_IO_format_actual_stdlib_controls': format_controls,
        'native_Boolean_geometry_patch_and_acceptance_algorithm_unchanged_by_IO_revision': True,
        'first_scope': contract['capacity'], 'scientific_input_packet': identity(packet),
        'scientific_input_member_count': len(members), 'scientific_input_uncompressed_bytes': raw_bytes,
        'original_core_scientific_campaign_budget_bytes_unchanged': 67108864,
        'genuine_S4_checkout_new_venv_and_sequential_transient_wheel_setup_fixture_separately_budgeted': True,
        'full_factory_historical_actual_self_peak_and_times': historical_capacity,
        'full_factory_historical_actual_output_census': historical_output,
        'near_far_fresh_native_workers': 4, 'expected_bodies_each': 154, 'expected_all_pairs_each': 11781,
        'estimated_four_full_factory_worker_seconds': 1083.602044427,
        'new_full_factory_stage_output_reserve_bytes': 134217728,
        'original_full_factory_prerequisite_copy_and_export_additional_reserve_bytes_unchanged': 1610612736,
        'entire_original_raw_current_run_and_independent_reader_artifacts_retained': True,
        'core_failure_does_not_suppress_independently_qualified_near_far_reproduction': True,
        'new_runtime_failure_or_resource_refusal_does_not_admit_that_jobs_native_worker': True,
        'continuous_native_membership_or_full_G2_claimed': False, 'physical_qualification': False,
        'all_original_failures_and_unresolved_boundary_states_remain_visible': True})
    for name in ('ORIGINAL_WORKFLOW_READBACK.json', 'ORIGINAL_NEAR_FAR_JOB_TIMINGS.json'):
        shutil.copyfile(HERE / 'historical' / name, out / name)
    shutil.copyfile(historical, out / 'ORIGINAL_s4-panel-key-stop-k3full-hosted.yml')
    # The workflow and large evidence plan are included in the source manifest;
    # the manifest cannot include its own bytes. No mutable tag is used as input.
    write(out / 'CLOUD_ASSET_MANIFEST.json', {'schema': 'razr-r5-reviewed-cloud-assets-v1',
          'files': {str(p.relative_to(out)): identity(p) for p in sorted(out.rglob('*')) if p.is_file()},
          'builder': {'relative_source': str(Path(__file__).relative_to(ROOT)), **identity(__file__)},
          'no_native_or_numeric_worker_started_by_build': True})
    write(out / 'SOURCE_LOCK.json', {
        'schema': 'razr-r5-native-cloud-source-lock-v1', 'repository': 'TrillionniumFoundation/RAZR-SLIDE',
        'branch': args.trigger_branch, 'repository_directory': args.repository_directory,
        'workflow_path': '.github/workflows/r5-native-fresh-hosted-v1.yml',
        'workflow_identity': identity(out / 'r5-native-fresh-hosted-v1.yml'),
        'asset_files': {str(p.relative_to(out)): identity(p) for p in sorted(out.rglob('*')) if p.is_file()},
        'independent_RUN_REQUEST_required_to_trigger': True,
        'RUN_REQUEST_required_schema': 'razr-r5-native-cloud-run-request-v1',
        'RUN_REQUEST_required_scope': 'native80-then-fresh-S4-near-far',
        'RUN_REQUEST_required_source_lock_sha256': 'SHA256 of this exact SOURCE_LOCK.json file',
        'historical_failures_not_reclassified': True,
        'original_six_native_limits_unchanged': original_execution['resource_limits']})
    size = sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    require(size <= 8 * 2**20, 'Published source and input bundle exceeds original8 MiB reserve')
    print(json.dumps({'publication_directory': str(out), 'files': sum(p.is_file() for p in out.rglob('*')),
                      'source_and_input_publication_bytes': size, 'scientific_archive_bytes': packet.stat().st_size,
                      'original_input_uncompressed_bytes': raw_bytes, 'native_execution': False}), flush=True)


if __name__ == '__main__':
    main()
