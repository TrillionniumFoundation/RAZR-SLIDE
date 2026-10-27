"""Independent source and small-manifest review; never load numerical arrays."""
from pathlib import Path
import argparse
import datetime
import hashlib
import importlib.util
import json
import re
import tempfile
import textwrap

OLD_REQUEST_SHA = 'b8f4d47bf9173cce528d3db6614756bab15e4b99edd894ee1d2f95253562e4e3'
NEW_REQUEST_SHA = '4048278413596e5c401e78daa2dfa42869c44815a8fd3678368f423aa7bcd4d6'
INITIAL_REVIEW_SHA = 'e47c26d9e912a82373b76096fe9c2631a9c1d5f66b936b68d7cb9fd7f9c66860'
N8 = (166609, 'aa84d34b26847f308296809ff83002d32535a56a92eb09adcc7e42b571e88ee7')
N7 = (167280, 'f911ecc8f08fe78526af1be49ea2292f94ee49e64789f514359196d7875d01b2')
EXPORT_PATH = 'engineering/engineering-integration-20261026/numerics/n9/export_n9_engineering.py'
WORKFLOW_PATH = '.github/workflows/s4-panel-n9-hosted.yml'


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def read_small(path, sha=None):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 1024**2:
        raise ValueError('expected bounded original text file')
    raw = path.read_bytes()
    if sha is not None and identity(raw)['sha256'] != sha:
        raise ValueError('frozen original small file identity differs')
    return raw


def module_at(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args):
    old_raw = read_small(args.old_request, OLD_REQUEST_SHA)
    new_raw = read_small(args.new_request, NEW_REQUEST_SHA)
    initial_raw = read_small(args.initial_review, INITIAL_REVIEW_SHA)
    old_request, new_request = json.loads(old_raw), json.loads(new_raw)
    assert old_request['repository_full_name'] == new_request['repository_full_name']
    assert old_request['base_tree_sha'] == new_request['base_tree_sha']
    old = {entry['path']: entry for entry in old_request['tree_elements']}
    new = {entry['path']: entry for entry in new_request['tree_elements']}
    assert len(old) == len(new) == 13 and set(old) == set(new)
    changed = sorted(path for path in old if old[path] != new[path])
    assert changed == sorted([EXPORT_PATH, WORKFLOW_PATH])
    for path in old:
        assert {k:v for k,v in old[path].items() if k != 'content'} == {k:v for k,v in new[path].items() if k != 'content'}
    old_export, new_export = old[EXPORT_PATH]['content'], new[EXPORT_PATH]['content']
    old_expression = f'if p.stat().st_size != {N7[0]} or sha(p) != "{N7[1]}":'
    new_expression = f'if p.stat().st_size != {N8[0]} or sha(p) != "{N8[1]}":'
    assert old_export.count(old_expression) == new_export.count(new_expression) == 1
    assert old_export.replace(old_expression, new_expression) == new_export
    old_digest = identity(old_export.encode())['sha256']
    new_digest = identity(new_export.encode())['sha256']
    old_workflow, new_workflow = old[WORKFLOW_PATH]['content'], new[WORKFLOW_PATH]['content']
    assert old_workflow.count(old_expression) == old_workflow.count(old_digest) == 1
    assert old_workflow.replace(old_expression, new_expression).replace(old_digest, new_digest) == new_workflow
    pattern = re.escape('        cat > "$HOST_ROOT/export_n9_engineering.py" <<\'N9_SOURCE_4\'\n') + '(.*?)' + re.escape('        N9_SOURCE_4\n')
    match = re.search(pattern, new_workflow, re.S)
    assert match is not None and textwrap.dedent(match.group(1)) == new_export
    assert f"printf '{new_digest}  %s\\n' \"$HOST_ROOT/export_n9_engineering.py\" | sha256sum --check --strict" in new_workflow
    fixed_folder = args.new_request.parent
    for path, entry in new.items():
        assert read_small(fixed_folder/Path(path).name) == entry['content'].encode()
    n8_raw = read_small(args.original_n8_root/'EXPORT_MANIFEST.json', N8[1])
    n7_raw = read_small(args.original_n8_root/'frozen/EXPORT_MANIFEST.json', N7[1])
    assert len(n8_raw) == N8[0] and len(n7_raw) == N7[0]
    fixed_exporter = module_at(fixed_folder/'export_n9_engineering.py', 'independent_fixed_n9_exporter')
    old_exporter = module_at(args.old_request.parent/'export_n9_engineering.py', 'independent_original_n9_exporter')
    damaged = n8_raw[:-1] + (b' ' if n8_raw[-1:] != b' ' else b'\n')
    assert len(damaged) == len(n8_raw) and identity(damaged)['sha256'] != N8[1]
    observed = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='n9-small-independent-', dir=args.output.parent) as temporary:
        base = Path(temporary)
        controls = [('old_rejects_actual_N8', old_exporter, n8_raw, False),
                    ('fixed_accepts_actual_N8', fixed_exporter, n8_raw, True),
                    ('fixed_rejects_actual_N7', fixed_exporter, n7_raw, False),
                    ('fixed_rejects_same_size_damaged_N8', fixed_exporter, damaged, False)]
        for label, module, original, expected in controls:
            case = base/label/'case'
            (case/'frozen').mkdir(parents=True)
            (case/'frozen/EXPORT_MANIFEST.json').write_bytes(original)
            output = base/label/'export'
            result = {'control': label, 'input_identity': identity(original), 'expected_acceptance': expected}
            try:
                module.export(case, output)
                result['accepted'] = True
            except ValueError as error:
                result.update(accepted=False, failure_type=type(error).__name__, failure_message=str(error))
                assert str(error) == 'original N8 scientific manifest differs'
            assert result['accepted'] == expected
            assert (case/'frozen/EXPORT_MANIFEST.json').read_bytes() == original
            result['input_original_unchanged'] = True
            if expected:
                copied = (output/'frozen/EXPORT_MANIFEST.json').read_bytes()
                result['exported_original_manifest_byte_identical'] = copied == original
                assert copied == original
                export_manifest = json.loads((output/'EXPORT_MANIFEST.json').read_text())
                actual = export_manifest['scientific_preservation_actual']
                assert actual['original_source_manifest_identity_verified'] is True
                assert actual['selected_complete_input_identities_verified'] == 0
                assert len(actual['missing_selected_complete_inputs']) == 22
                assert actual['all_22_selected_complete_inputs_identity_verified'] is False
                assert actual['all_ten_final_arrays_present'] is False
                result['manifest_only_control_missing_22_inputs_and_final_arrays_truthfully_preserved'] = True
                result['raw_runtime_exported'] = export_manifest['raw_runtime_records_exported']
                assert result['raw_runtime_exported'] is False
            observed.append(result)
    result = {'schema': 'razr-N9-independent-manifest-correction-review-v1',
        'reviewed_at_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'review_source_sha256': identity(Path(__file__).read_bytes())['sha256'],
        'old_request_identity': identity(old_raw), 'new_request_identity': identity(new_raw),
        'initial_independent_blocking_review_identity': identity(initial_raw),
        'request_path_count': 13, 'changed_paths': changed,
        'unchanged_other_11_paths': sorted(path for path in old if old[path] == new[path]),
        'exporter_only_change_actual_source_manifest_size_and_SHA': True,
        'workflow_only_change_same_literal_and_corresponding_source_SHA': True,
        'embedded_exporter_bytes_and_frozen_SHA_match': True,
        'all_13_request_source_bytes_match_fixed_files': True,
        'fixed_exporter_identity': identity(new_export.encode()),
        'fixed_workflow_identity': identity(new_workflow.encode()),
        'independent_actual_small_manifest_controls': observed,
        'producer_reader_contract_strategy_frozen_inputs_tests_byte_unchanged': True,
        'earlier_full_five_acceptance_exact_support_anchor_and_original_resource_review_still_applies': True,
        'old_request_old_exporter_initial_review_and_scientific_originals_preserved': True,
        'initial_blocker_closed_for_this_new_request': True,
        'remaining_blocking_findings_in_this_finite_review': [],
        'safe_to_submit_this_request_for_root_review': True,
        'new_native_or_numeric_execution': False, 'large_array_contents_read': False,
        'scientific_ZIP_download_or_reverification': False, 'Git_write_or_Actions_start': False,
        'numeric_five_pass_qualification_claimed': False, 'H_frame_restore_executed': False}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'output_identity': identity(args.output.read_bytes()), 'all_four_controls_passed': True,
                      'initial_blocker_closed': True, 'new_native_execution': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-request', type=Path, required=True)
    parser.add_argument('--new-request', type=Path, required=True)
    parser.add_argument('--initial-review', type=Path, required=True)
    parser.add_argument('--original-n8-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args())
