"""Retain scientific ECAD outputs and explicit engineering projections only."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil

def sha(path):
    with Path(path).open('rb') as f:
        digest = hashlib.sha256()
        for block in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(block)
        return digest.hexdigest()

ALLOWED = {
    'execution.json': '''schema source_commit completed passed new_native_execution verifier_report_produced
        source_sha256 packages candidate_go fixture_fabrication_go manufacturing_go verifier_exit_code
        native_DRC_executed elapsed_seconds source_bytes_unchanged error_type'''.split(),
    'result/report.json': '''schema expected_head passed native_DRC_executed schematic_ERC_executed
        schematic_parity_requested OEM_assignment_qualified signal_integrity_or_power_qualified
        dynamic_FPC_qualified supplier_stackup_selected candidate_go fixture_fabrication_go manufacturing_go
        scope source_sha256_before artwork_report_sha256 candidate_id native_readback kicad_version kicad_release
        native_DRC_sha256 native_DRC_counts input_board_project_bytes_unchanged source_sha256_after
        source_bytes_unchanged source_head_after files_sha256 seconds'''.split(),
    'result/native-drc.json': '''$schema coordinate_units date included_severities kicad_version
        schematic_parity source unconnected_items violations'''.split(),
    'result/native-readback/readback.json': '''scope kicad_version kicad_release source_sha256 inputs_sha256
        project_loaded input_bytes_unchanged seconds tracks declared_board_thickness_mm footprints native_pad_objects
        unique_connected_terminals electrical_nets drc_sections drc_violation_types drc_zero_reported_items
        drc_report_sha256 exported_footprints native_pad_readback product_motion_or_OEM_qualification'''.split(),
}

def main():
    base = Path(os.environ['RUNNER_TEMP']) / 'razr-ec1-s4'
    root = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    out = Path(os.environ['RUNNER_TEMP']) / 'razr-ec1-engineering'
    out.mkdir(exist_ok=False)
    manifest = {'schema': 'razr-EC1-engineering-export-v1', 'raw_runtime_exported': False,
                'raw_runtime_durable': False, 'original_producer_records_modified': False,
                'source_commit': 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560', 'files': {}}
    for name in ['artwork/ep5_continuity26.kicad_pcb', 'artwork/ep5_continuity26.kicad_pro',
                 'artwork/conductor-schedule.csv', 'artwork/flat-material-outline.json', 'artwork/fp-lib-table']:
        source = base / 'result' / name
        if source.is_file() and not source.is_symlink():
            target = out / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            manifest['files'][name] = {'sha256': sha(source), 'bytes': source.stat().st_size, 'original_bytes': True}
    def normalize(value):
        if isinstance(value, str):
            value = value.replace(str(root), 'repository').replace(str(base), 'task-evidence')
            if (any(p in value for p in ('/home/', '/workspace/', '/tmp/', 'libfile_', 'oai-library:'))
                    or re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', value)):
                raise ValueError('unexpected runtime locator in engineering projection')
            return value
        if isinstance(value, list):
            return [normalize(v) for v in value]
        if isinstance(value, dict):
            return {normalize(k): normalize(v) for k, v in value.items()}
        return value
    for name in ['execution.json', 'result/report.json', 'result/native-drc.json', 'result/native-readback/readback.json']:
        source = base / name
        if not source.is_file():
            continue
        record = json.loads(source.read_text())
        selected = {k: record[k] for k in ALLOWED[name] if k in record}
        if isinstance(record.get('error'), dict):
            selected['error_type'] = record['error'].get('type')
        payload = {'schema': 'razr-EC1-derived-engineering-projection-v1', 'is_original_record': False,
                   'original_sha256': sha(source), 'original_bytes': source.stat().st_size,
                   'raw_runtime_durable': False, 'engineering_record': normalize(selected)}
        destname = name.replace('.json', '.engineering.json')
        target = out / destname
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2) + '\n')
        manifest['files'][destname] = {'sha256': sha(target), 'bytes': target.stat().st_size, 'original_bytes': False}
    (out / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')

if __name__ == '__main__':
    main()
