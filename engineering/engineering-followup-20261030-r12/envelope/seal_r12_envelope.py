"""Read-only verification and final scoped member inventory for R12 envelope."""
import hashlib
import json
from pathlib import Path


def identity(path):
    p=Path(path)
    return {"path":str(p.resolve()),"bytes":p.stat().st_size,
            "sha256":hashlib.sha256(p.read_bytes()).hexdigest()}


def main():
    root=Path(__file__).resolve().parent
    producer=json.loads((root/'producer-attempt1/report.json').read_text())
    reader=json.loads((root/'reader-attempt1/report.json').read_text())
    provenance=json.loads((root/'control-provenance-attempt1/report.json').read_text())
    assert all(r['completed'] for r in (producer,reader,provenance))
    assert all(r['recorded_budget_passed'] for r in (producer,reader))
    assert all(not reader[k] for k in ('full_continuous_G2','native_boundary_set_identity_proved',
        'uniform_compiled_geometry_error_proved','complete_region_union_proved','release_go'))
    for report in (producer,reader):
        for item in report['sources']:
            actual=identity(item['path'])
            assert all(actual[k]==item[k] for k in ('bytes','sha256'))
    scope={
        'schema':'razr-r12-envelope-final-exact-model-filling-scope-v1',
        'completed_components':{'original_nine_local_compact_filling_implication':True,
            'complete_cap_trim_and_spatial_boundary_radial_support':True,
            'independent_actual_originals_and_native_carrier_readback':True,
            'new_independent_empty_Common_agrees_with_exact_model_separation':True,
            'original_hollow_shell_counterexample_retained_and_exact_fibre_fill_verified':True,
            'positive_2_to_minus80_volume_and_singleton_fibres_retained':True},
        'totals':reader['totals'],
        'negative_controls_rejected':len(reader['negative_controls'])+len(provenance['negative_controls']),
        'producer_report':identity(root/'producer-attempt1/report.json'),
        'independent_reader_report':identity(root/'reader-attempt1/report.json'),
        'original_counterexample_provenance_report':identity(root/'control-provenance-attempt1/report.json'),
        'new_native_carriers_constructed':0,'new_native_Common_calls':79,'new_refinement_splits':0,
        'source_boundary_to_actual_native_material_set_identity_proved':False,
        'uniform_compiled_geometry_and_transform_error_proved':False,
        'original_initial_q_sweep_for_cases_016_to_019_proved':False,
        'full_B_SHELL_region_union_proved':False,
        'new_original_all16_full_search_executed':False,
        'current_K1_K3_candidate_continuous_domain_proved':False,
        'physical_independent_mechanical_domain_qualified':False,
        'full_continuous_G2':False,'G3_pass':False,'G4_pass':False,'G5_pass':False,'release_go':False,
        'exact_scope':'complete represented-boundary support plus compact-filling implication; actual native semantics remain unproved',
        'original_R11_input_files_unchanged':True,
        'seal_source':identity(__file__)}
    path=root/'R12_ENVELOPE_SCOPE.json'
    with path.open('x') as stream:
        stream.write(json.dumps(scope,indent=2)+'\n')
    records=[]
    for path in sorted(root.rglob('*')):
        if not path.is_file():continue
        if path.name=='R12_ENVELOPE_DELIVERY_MANIFEST.json':continue
        if '__pycache__' in path.parts:continue
        item=identity(path);item['path']=path.relative_to(root).as_posix();records.append(item)
    manifest={'schema':'razr-r12-envelope-all-members-v1','file_count':len(records),
              'content_bytes':sum(item['bytes'] for item in records),'files':records,
              'manifest_self_excluded':True}
    with (root/'R12_ENVELOPE_DELIVERY_MANIFEST.json').open('x') as stream:
        stream.write(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'file_count':manifest['file_count'],'content_bytes':manifest['content_bytes'],
                      'scope_sha256':identity(root/'R12_ENVELOPE_SCOPE.json')['sha256']}))


if __name__=='__main__':main()
