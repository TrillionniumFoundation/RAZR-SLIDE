"""Create new named v5 bootstrap-only sources; preserve every v4 byte."""
from pathlib import Path
import ast
import hashlib
import json

HERE = Path(__file__).resolve().parent


def identity(path):
    data = Path(path).read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Expected exactly one immutable replacement')
    return text.replace(old, new)


def main():
    old_registrar = HERE / 'publication-v4/register_cloud_native_r5.py'
    old_builder = HERE / 'build_cloud_native_packet_r5.py'
    archive_builder = HERE / 'build_cloud_native_packet_r5_v4_frozen.py'
    new_registrar = HERE / 'register_cloud_native_r5_bootstrap_v5.py'
    new_builder = HERE / 'build_cloud_native_packet_r5_v5.py'
    report = HERE / 'bootstrap-v5/R5_BOOTSTRAP_V5_REVISION_PREPARATION.json'
    for path in (archive_builder, new_registrar, new_builder, report):
        if path.exists():
            raise ValueError('New immutable source names required: ' + str(path))
    if identity(old_registrar) != identity(HERE / 'register_cloud_native_r5.py'):
        raise ValueError('Working registrar is not exact frozen v4')
    with __import__('tarfile').open(HERE / 'publication-v4/scientific-inputs.tar.gz', 'r:gz') as tar:
        data = tar.extractfile('r5-native/cloud-native-v1/build_cloud_native_packet_r5.py').read()
    if data != old_builder.read_bytes():
        raise ValueError('Working builder is not exact frozen v4')
    archive_builder.write_bytes(data)
    text = old_registrar.read_text()
    text = once(text, 'import subprocess\n', 'import subprocess\nimport sys\n')
    text = once(text,
        "    with path.open('rb') as stream:\n        digest = hashlib.file_digest(stream, 'sha256').hexdigest()\n    return {'bytes': path.stat().st_size, 'sha256': digest}\n",
        "    digest = hashlib.sha256()\n    with path.open('rb') as stream:\n        for chunk in iter(lambda: stream.read(1024 * 1024), b''):\n            digest.update(chunk)\n    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}\n")
    text = once(text,
        "            'actual_triggering_commit': os.environ['GITHUB_SHA'],\n            'all_reviewed_assets_and_independent_workflow_verified': True,\n",
        "            'actual_triggering_commit': os.environ['GITHUB_SHA'],\n            'bootstrap_interpreter_observation': {\n                'executable': sys.executable, 'version': sys.version,\n                'version_info': list(sys.version_info), 'implementation': sys.implementation.name,\n                'hashlib_file_digest_available': hasattr(hashlib, 'file_digest'),\n                'SHA256_method': 'complete stream in 1048576-byte chunks',\n                'scientific_tar_extraction_method': 'individually bounded regular members; exclusive create; exact SHA256/size; no extractall/filter API',\n                'observation_is_not_new_runtime_qualification': True},\n            'all_reviewed_assets_and_independent_workflow_verified': True,\n")
    ast.parse(text, feature_version=(3, 10))
    new_registrar.write_text(text)
    text = old_builder.read_text()
    text = once(text,
        "    for name in ('qualify_fresh_runtime_r5.py', 'run_fresh_runtime_script_r5.py', 'register_cloud_native_r5.py'):\n        ast.parse((HERE / name).read_text())\n        shutil.copyfile(HERE / name, out / name)\n",
        "    for name in ('qualify_fresh_runtime_r5.py', 'run_fresh_runtime_script_r5.py', 'register_cloud_native_r5.py'):\n        source = HERE / ('register_cloud_native_r5_bootstrap_v5.py' if name == 'register_cloud_native_r5.py' else name)\n        ast.parse(source.read_text())\n        shutil.copyfile(source, out / name)\n")
    text = once(text,
        "    forbidden = {\n",
        "    bootstrap_report = HERE / 'bootstrap-v5/R5_BOOTSTRAP_V5_CONTROLS_ACTUAL.json'\n    bootstrap = json.loads(bootstrap_report.read_text())\n    require(bootstrap['completed'] and bootstrap['new_registrar_identity'] == identity(HERE / 'register_cloud_native_r5_bootstrap_v5.py'), 'Exact actual v5 bootstrap controls required')\n    for path in [HERE / 'prepare_bootstrap_revision_r5_v5.py', HERE / 'register_cloud_native_r5_bootstrap_v5.py', HERE / 'build_cloud_native_packet_r5_v4_frozen.py', HERE / 'check_bootstrap_compatibility_r5_v5.py', *sorted((HERE / 'bootstrap-v5').rglob('*'))]:\n        if path.is_file():\n            members[str(path.relative_to(ROOT))] = identity(path)\n    forbidden = {\n")
    text = once(text,
        "        'strict_entry_qualifier_argument_binding_actual_stdlib_controls': controls,\n",
        "        'bootstrap_portable_hash_actual_stdlib_controls': bootstrap,\n        'bootstrap_control_report_member': str(bootstrap_report.relative_to(ROOT)),\n        'bootstrap_control_report_identity': identity(bootstrap_report),\n        'v4_actual_bootstrap_failure_retained': True,\n        'always_environment_success_assertions_preserved_exactly': True,\n        'strict_entry_qualifier_argument_binding_actual_stdlib_controls': controls,\n")
    ast.parse(text)
    new_builder.write_text(text)
    report.parent.mkdir(exist_ok=True)
    record = {'schema': 'razr-r5-new-named-bootstrap-v5-preparation-v1',
              'prior_publication_v4_source_lock': identity(HERE / 'publication-v4/SOURCE_LOCK.json'),
              'old_registrar': identity(old_registrar), 'new_registrar': identity(new_registrar),
              'old_builder': identity(old_builder), 'archived_builder': identity(archive_builder),
              'new_builder': identity(new_builder), 'creator': identity(__file__),
              'v4_source_bytes_unchanged': identity(old_registrar) == identity(HERE / 'register_cloud_native_r5.py') and identity(old_builder) == identity(archive_builder),
              'new_runtime_qualifier_or_entry_modified': False,
              'native_geometry_workers_or_gates_modified': False,
              'original_always_environment_success_assertions_modified': False,
              'new_native_or_runtime_execution': False}
    report.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
